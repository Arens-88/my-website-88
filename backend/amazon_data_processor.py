import json
import logging
import statistics
from datetime import datetime, date, timedelta
from models import Session, AmazonIntegratedData, SyncLog
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_data_processor')

class AmazonDataProcessor:
    def __init__(self, user_id):
        """
        初始化数据处理器
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.session = Session()
        
        # 异常检测配置
        self.outlier_detection_config = {
            'sales_amount': {'method': 'zscore', 'threshold': 3.0},
            'order_quantity': {'method': 'zscore', 'threshold': 3.0},
            'profit_margin': {'method': 'iqr', 'threshold': 1.5},
            'product_cost': {'method': 'zscore', 'threshold': 2.5}
        }
        
        # 数据清洗规则
        self.cleaning_rules = {
            'min_sales_amount': 0,
            'min_order_quantity': 0,
            'max_asin_length': 10,
            'max_product_name_length': 500,
            'required_fields': ['asin', 'order_date']
        }
        
        # 字段映射配置
        self.field_mappings = {
            'sales_fee': ['amazon_fee', 'platform_fee'],
            'other_fee': ['promotion_fee', 'custom_fee']
        }
    
    def __del__(self):
        """
        析构函数，关闭数据库会话
        """
    def close_session(self):
        if hasattr(self, 'session'):
            self.session.close()
    
    def clean_data(self, data):
        """
        清洗数据，去除无效值和异常值
        
        Args:
            data: 要清洗的数据记录
            
        Returns:
            dict: 清洗后的数据和清洗信息
        """
        cleaned_data = data.copy()
        cleaning_info = {
            'is_cleaned': False,
            'issues': [],
            'fixed_fields': []
        }
        
        # 检查必需字段
        for field in self.cleaning_rules['required_fields']:
            if field not in cleaned_data or not cleaned_data[field]:
                cleaning_info['issues'].append(f'缺少必需字段: {field}')
                return cleaned_data, cleaning_info
        
        # 清洗ASIN
        if 'asin' in cleaned_data:
            asin = str(cleaned_data['asin']).strip()
            if len(asin) != self.cleaning_rules['max_asin_length']:
                cleaning_info['issues'].append(f'ASIN格式错误: {asin}')
            cleaned_data['asin'] = asin
        
        # 清洗产品名称
        if 'product_name' in cleaned_data and cleaned_data['product_name']:
            product_name = str(cleaned_data['product_name']).strip()
            if len(product_name) > self.cleaning_rules['max_product_name_length']:
                product_name = product_name[:self.cleaning_rules['max_product_name_length']]
                cleaning_info['fixed_fields'].append('product_name')
            cleaned_data['product_name'] = product_name
        
        # 清洗数值字段
        numeric_fields = ['sales_amount', 'order_quantity', 'product_cost', 
                          'shipping_cost', 'platform_fee', 'ad_spend']
        
        for field in numeric_fields:
            if field in cleaned_data:
                try:
                    # 转换为数字
                    value = float(cleaned_data[field])
                    
                    # 检查最小值
                    if field in ['sales_amount', 'order_quantity']:
                        if value < self.cleaning_rules[f'min_{field}']:
                            value = 0
                            cleaning_info['fixed_fields'].append(field)
                    
                    # 确保非负数
                    if field not in ['profit_margin']:  # 利润率可以为负
                        value = max(0, value)
                        
                    cleaned_data[field] = value
                except (ValueError, TypeError):
                    # 设置为默认值
                    default_value = 0 if field not in ['profit_margin'] else 0.0
                    cleaned_data[field] = default_value
                    cleaning_info['fixed_fields'].append(field)
        
        # 清洗日期字段
        if 'order_date' in cleaned_data:
            date_value = cleaned_data['order_date']
            if isinstance(date_value, str):
                try:
                    # 尝试解析日期
                    parsed_date = datetime.fromisoformat(date_value)
                    cleaned_data['order_date'] = parsed_date.date()
                except ValueError:
                    cleaning_info['issues'].append(f'日期格式错误: {date_value}')
            elif isinstance(date_value, datetime):
                cleaned_data['order_date'] = date_value.date()
        
        # 标记清洗状态
        if cleaning_info['issues'] or cleaning_info['fixed_fields']:
            cleaning_info['is_cleaned'] = True
        
        return cleaned_data, cleaning_info
    
    def detect_outliers(self, records, field):
        """
        检测异常值
        
        Args:
            records: 记录列表
            field: 要检测的字段
            
        Returns:
            list: 异常记录的索引
        """
        if field not in self.outlier_detection_config:
            return []
        
        config = self.outlier_detection_config[field]
        method = config['method']
        threshold = config['threshold']
        
        # 提取有效数值
        values = []
        valid_indices = []
        
        for i, record in enumerate(records):
            if field in record and isinstance(record[field], (int, float)) and not np.isnan(record[field]):
                values.append(record[field])
                valid_indices.append(i)
        
        if len(values) < 4:  # 数据量太少，无法检测异常
            return []
        
        outliers = []
        
        if method == 'zscore':
            # 使用Z-Score方法
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 1
            
            for idx, value in enumerate(values):
                if std_val > 0:
                    z_score = abs((value - mean_val) / std_val)
                    if z_score > threshold:
                        outliers.append(valid_indices[idx])
        
        elif method == 'iqr':
            # 使用IQR方法
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            
            for idx, value in enumerate(values):
                if value < lower_bound or value > upper_bound:
                    outliers.append(valid_indices[idx])
        
        return outliers
    
    def calculate_metrics(self, record):
        """
        计算衍生指标
        
        Args:
            record: 数据记录
            
        Returns:
            dict: 更新后的记录
        """
        updated_record = record.copy()
        
        # 计算销售额（如果未提供）
        if 'sales_amount' not in updated_record or updated_record['sales_amount'] == 0:
            if 'order_quantity' in updated_record and 'avg_order_value' in updated_record:
                updated_record['sales_amount'] = updated_record['order_quantity'] * updated_record['avg_order_value']
        
        # 计算客单价
        if 'avg_order_value' not in updated_record or updated_record['avg_order_value'] == 0:
            if 'sales_amount' in updated_record and 'order_quantity' in updated_record and updated_record['order_quantity'] > 0:
                updated_record['avg_order_value'] = updated_record['sales_amount'] / updated_record['order_quantity']
        
        # 计算总成本
        cost_fields = ['product_cost', 'shipping_cost', 'platform_fee', 'ad_spend', 'promotion_fee']
        total_cost = sum(updated_record.get(field, 0) for field in cost_fields)
        updated_record['total_cost'] = total_cost
        
        # 计算净利润
        if 'sales_amount' in updated_record:
            updated_record['net_profit'] = updated_record['sales_amount'] - total_cost
        
        # 计算利润率
        if 'sales_amount' in updated_record and updated_record['sales_amount'] > 0:
            profit = updated_record.get('net_profit', 0)
            updated_record['profit_margin'] = (profit / updated_record['sales_amount']) * 100
        else:
            updated_record['profit_margin'] = 0
        
        # 计算广告占比
        if 'sales_amount' in updated_record and updated_record['sales_amount'] > 0 and 'ad_spend' in updated_record:
            updated_record['ad_to_sales_ratio'] = (updated_record['ad_spend'] / updated_record['sales_amount']) * 100
        else:
            updated_record['ad_to_sales_ratio'] = 0
        
        # 计算ROI
        if 'ad_spend' in updated_record and updated_record['ad_spend'] > 0:
            ad_profit = updated_record.get('net_profit', 0)  # 简化计算，实际应考虑广告带来的利润
            updated_record['roi'] = (ad_profit / updated_record['ad_spend']) * 100 if ad_profit > 0 else -100
        else:
            updated_record['roi'] = 0
        
        return updated_record
    
    def integrate_data(self, source_data, source_type='sales'):
        """
        整合数据到主数据表
        
        Args:
            source_data: 源数据列表
            source_type: 数据类型（sales/inventory/ad/cost）
            
        Returns:
            dict: 整合结果统计
        """
        try:
            stats = {
                'total_records': len(source_data),
                'successful_integrations': 0,
                'failed_integrations': 0,
                'cleaned_records': 0,
                'outliers_detected': 0,
                'warnings': []
            }
            
            # 按日期和ASIN分组，用于异常检测
            date_asin_groups = {}
            for record in source_data:
                if 'order_date' in record and 'asin' in record:
                    key = (record['order_date'], record['asin'])
                    if key not in date_asin_groups:
                        date_asin_groups[key] = []
                    date_asin_groups[key].append(record)
            
            # 处理每个记录
            for record in source_data:
                try:
                    # 清洗数据
                    cleaned_record, cleaning_info = self.clean_data(record)
                    if cleaning_info['is_cleaned']:
                        stats['cleaned_records'] += 1
                    
                    # 如果有严重问题，跳过此记录
                    if cleaning_info['issues']:
                        stats['failed_integrations'] += 1
                        stats['warnings'].append(f"数据清洗失败: {cleaning_info['issues']}")
                        continue
                    
                    # 计算指标
                    updated_record = self.calculate_metrics(cleaned_record)
                    
                    # 异常检测（使用组内数据）
                    is_outlier = False
                    if 'order_date' in updated_record and 'asin' in updated_record:
                        key = (updated_record['order_date'], updated_record['asin'])
                        if key in date_asin_groups:
                            group_records = date_asin_groups[key]
                            for field in self.outlier_detection_config.keys():
                                if field in updated_record:
                                    outliers = self.detect_outliers(group_records, field)
                                    # 检查当前记录是否在异常列表中
                                    if updated_record in group_records:
                                        record_idx = group_records.index(updated_record)
                                        if record_idx in outliers:
                                            is_outlier = True
                                            stats['outliers_detected'] += 1
                                            break
                    
                    # 查找或创建主记录
                    primary_key = {
                        'user_id': self.user_id,
                        'asin': updated_record['asin'],
                        'order_date': updated_record['order_date']
                    }
                    
                    # 检查是否已存在
                    existing_record = self.session.query(AmazonIntegratedData).filter_by(**primary_key).first()
                    
                    if existing_record:
                        # 更新现有记录
                        update_data = updated_record.copy()
                        # 移除主键字段
                        for key_field in primary_key.keys():
                            update_data.pop(key_field, None)
                        
                        # 标记为异常如果检测到异常
                        if is_outlier and not existing_record.is_exception:
                            update_data['is_exception'] = 1
                        
                        # 更新字段
                        for field, value in update_data.items():
                            if hasattr(existing_record, field):
                                # 对于成本字段，采用累加方式
                                if field in ['product_cost', 'shipping_cost', 'platform_fee', 'ad_spend'] and source_type == 'cost':
                                    current_value = getattr(existing_record, field, 0)
                                    setattr(existing_record, field, current_value + value)
                                else:
                                    setattr(existing_record, field, value)
                    else:
                        # 创建新记录
                        new_record_data = updated_record.copy()
                        new_record_data['user_id'] = self.user_id
                        new_record_data['is_exception'] = 1 if is_outlier else 0
                        new_record_data['is_estimated'] = 1 if source_type == 'cost' else 0
                        
                        # 添加来源信息
                        new_record_data['data_source'] = source_type
                        
                        new_record = AmazonIntegratedData(**new_record_data)
                        self.session.add(new_record)
                    
                    stats['successful_integrations'] += 1
                    
                except Exception as e:
                    logger.error(f"处理单条记录失败: {str(e)}")
                    stats['failed_integrations'] += 1
            
            # 提交更改
            self.session.commit()
            
            # 记录同步日志
            sync_log = SyncLog(
                user_id=self.user_id,
                sync_type=f'integrate_{source_type}',
                status='success' if stats['failed_integrations'] == 0 else 'partial',
                total_records=stats['total_records'],
                success_records=stats['successful_integrations'],
                fail_records=stats['failed_integrations'],
                details=json.dumps({
                    'cleaned_records': stats['cleaned_records'],
                    'outliers_detected': stats['outliers_detected'],
                    'warnings': stats['warnings'][:10]  # 只记录前10个警告
                })
            )
            self.session.add(sync_log)
            self.session.commit()
            
            logger.info(f"数据整合完成: 成功{stats['successful_integrations']}, 失败{stats['failed_integrations']}, 清洗{stats['cleaned_records']}, 异常{stats['outliers_detected']}")
            
            return {
                'success': True,
                'message': '数据整合完成',
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"数据整合失败: {str(e)}")
            self.session.rollback()
            return {
                'success': False,
                'message': f'数据整合失败: {str(e)}',
                'statistics': stats if 'stats' in locals() else {}
            }
    
    def process_outliers(self, action='mark', days=30):
        """
        处理异常数据
        
        Args:
            action: 处理动作（mark/ignore/recalculate）
            days: 处理最近多少天的数据
            
        Returns:
            dict: 处理结果
        """
        try:
            # 计算日期范围
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 查询最近的数据
            recent_data = self.session.query(AmazonIntegratedData).filter_by(
                user_id=self.user_id
            ).filter(
                AmazonIntegratedData.order_date >= start_date
            ).order_by(
                AmazonIntegratedData.order_date.desc()
            ).all()
            
            # 转换为字典列表便于处理
            records_dict = []
            for record in recent_data:
                record_dict = {}
                for column in AmazonIntegratedData.__table__.columns.keys():
                    if hasattr(record, column):
                        record_dict[column] = getattr(record, column)
                records_dict.append(record_dict)
            
            processed_count = 0
            
            # 按ASIN分组进行处理
            asin_groups = {}
            for record in records_dict:
                asin = record.get('asin')
                if asin not in asin_groups:
                    asin_groups[asin] = []
                asin_groups[asin].append(record)
            
            # 处理每个ASIN的数据
            for asin, asin_records in asin_groups.items():
                # 对每个字段检测异常
                for field in self.outlier_detection_config.keys():
                    outliers = self.detect_outliers(asin_records, field)
                    
                    for idx in outliers:
                        record = asin_records[idx]
                        db_record = self.session.query(AmazonIntegratedData).filter_by(
                            id=record['id'],
                            user_id=self.user_id
                        ).first()
                        
                        if db_record:
                            if action == 'mark':
                                db_record.is_exception = 1
                            elif action == 'ignore':
                                db_record.is_exception = 0
                            elif action == 'recalculate':
                                # 重新计算指标
                                updated_record = self.calculate_metrics(record)
                                for key, value in updated_record.items():
                                    if hasattr(db_record, key):
                                        setattr(db_record, key, value)
                                # 重新标记异常状态
                                db_record.is_exception = 1
                            
                            processed_count += 1
            
            self.session.commit()
            
            logger.info(f"异常数据处理完成: 处理了{processed_count}条记录，动作: {action}")
            
            return {
                'success': True,
                'message': '异常数据处理完成',
                'processed_count': processed_count,
                'total_records': len(recent_data)
            }
            
        except Exception as e:
            logger.error(f"处理异常数据失败: {str(e)}")
            self.session.rollback()
            return {
                'success': False,
                'message': f'处理异常数据失败: {str(e)}'
            }
    
    def recalculate_all_metrics(self, days=90):
        """
        重新计算所有指标
        
        Args:
            days: 处理最近多少天的数据
            
        Returns:
            dict: 处理结果
        """
        try:
            # 计算日期范围
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 查询数据
            records = self.session.query(AmazonIntegratedData).filter_by(
                user_id=self.user_id
            ).filter(
                AmazonIntegratedData.order_date >= start_date
            ).all()
            
            recalculated_count = 0
            
            for record in records:
                try:
                    # 转换为字典
                    record_dict = {}
                    for column in AmazonIntegratedData.__table__.columns.keys():
                        if hasattr(record, column):
                            record_dict[column] = getattr(record, column)
                    
                    # 重新计算指标
                    updated_record = self.calculate_metrics(record_dict)
                    
                    # 更新记录
                    for key, value in updated_record.items():
                        if hasattr(record, key) and key not in ['id', 'user_id', 'asin', 'order_date', 'created_at']:
                            setattr(record, key, value)
                    
                    recalculated_count += 1
                    
                except Exception as e:
                    logger.error(f"重新计算记录失败 (ID: {record.id}): {str(e)}")
            
            self.session.commit()
            
            logger.info(f"指标重新计算完成: 成功{recalculated_count}条，总计{len(records)}条")
            
            return {
                'success': True,
                'message': '指标重新计算完成',
                'recalculated_count': recalculated_count,
                'total_records': len(records)
            }
            
        except Exception as e:
            logger.error(f"重新计算指标失败: {str(e)}")
            self.session.rollback()
            return {
                'success': False,
                'message': f'重新计算指标失败: {str(e)}'
            }
    
    def get_integration_stats(self, start_date=None, end_date=None):
        """
        获取数据整合统计信息
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 统计信息
        """
        try:
            # 构建查询
            query = self.session.query(SyncLog).filter_by(
                user_id=self.user_id
            )
            
            # 应用日期过滤
            if start_date:
                query = query.filter(SyncLog.sync_time >= start_date)
            if end_date:
                query = query.filter(SyncLog.sync_time <= end_date)
            
            # 按类型分组统计
            logs = query.order_by(SyncLog.sync_time.desc()).all()
            
            # 计算统计信息
            stats_by_type = {}
            overall_stats = {
                'total_syncs': len(logs),
                'successful_syncs': 0,
                'partial_syncs': 0,
                'failed_syncs': 0,
                'total_records_processed': 0,
                'total_records_success': 0
            }
            
            for log in logs:
                sync_type = log.sync_type
                if sync_type not in stats_by_type:
                    stats_by_type[sync_type] = {
                        'syncs': 0,
                        'records_processed': 0,
                        'records_success': 0
                    }
                
                stats_by_type[sync_type]['syncs'] += 1
                stats_by_type[sync_type]['records_processed'] += log.total_records
                stats_by_type[sync_type]['records_success'] += log.success_records
                
                overall_stats['total_records_processed'] += log.total_records
                overall_stats['total_records_success'] += log.success_records
                
                if log.status == 'success':
                    overall_stats['successful_syncs'] += 1
                elif log.status == 'partial':
                    overall_stats['partial_syncs'] += 1
                else:
                    overall_stats['failed_syncs'] += 1
            
            return {
                'success': True,
                'overall_stats': overall_stats,
                'stats_by_type': stats_by_type,
                'recent_syncs': [
                    {
                        'id': log.id,
                        'type': log.sync_type,
                        'status': log.status,
                        'time': log.sync_time.isoformat(),
                        'records_processed': log.total_records,
                        'records_success': log.success_records
                    }
                    for log in logs[:10]  # 最近10次同步
                ]
            }
            
        except Exception as e:
            logger.error(f"获取整合统计失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取整合统计失败: {str(e)}'
            }

# 使用示例
if __name__ == "__main__":
    # 示例: 创建数据处理器
    processor = AmazonDataProcessor(user_id=1)
    print("数据处理器初始化完成")
