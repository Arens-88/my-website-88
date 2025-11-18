import os
import json
import random
import time
import pandas as pd
from datetime import datetime, timedelta
from models import Session, ERPCostFile, ERPCostMapping, ERPCostData, AmazonIntegratedData
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_erp_cost')

class AmazonERPCostManager:
    def __init__(self, user_id, upload_dir='uploads'):
        """
        初始化ERP成本数据管理器
        
        Args:
            user_id: 用户ID
            upload_dir: 文件上传目录
        """
        self.user_id = user_id
        self.upload_dir = upload_dir
        self.session = Session()
        
        # 创建上传目录
        os.makedirs(upload_dir, exist_ok=True)
        
        # 初始化API调用时间跟踪，用于速率限制控制
        self.api_calls = []
        
        # 配置
        self.MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        self.ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
        self.RATE_LIMIT = 10  # 每分钟最大处理文件数
        self.RATE_LIMIT_PERIOD = 60  # 60秒
        
        # 支持的字段映射
        self.SUPPORTED_FIELDS = {
            'asin': {'display': 'ASIN', 'required': True, 'type': 'string'},
            'sku': {'display': 'SKU', 'required': False, 'type': 'string'},
            'product_name': {'display': '产品名称', 'required': False, 'type': 'string'},
            'cost_value': {'display': '成本金额', 'required': True, 'type': 'float'},
            'cost_date': {'display': '成本日期', 'required': True, 'type': 'date'},
            'currency': {'display': '货币', 'required': False, 'type': 'string', 'default': 'USD'},
            'cost_category': {'display': '成本类别', 'required': False, 'type': 'string'},
            'supplier': {'display': '供应商', 'required': False, 'type': 'string'},
            'order_number': {'display': '订单号', 'required': False, 'type': 'string'}
        }
    
    def __del__(self):
        """
        析构函数，关闭数据库会话
        """
        if hasattr(self, 'session'):
            self.session.close()
    
    def _respect_rate_limit(self):
        """
        遵守速率限制，控制文件处理频率
        
        Returns:
            bool: 是否需要等待
        """
        current_time = time.time()
        
        # 清理过期的API调用记录
        self.api_calls = [call_time for call_time in self.api_calls if current_time - call_time < self.RATE_LIMIT_PERIOD]
        
        # 检查是否达到速率限制
        if len(self.api_calls) >= self.RATE_LIMIT:
            # 计算需要等待的时间
            wait_time = self.RATE_LIMIT_PERIOD - (current_time - self.api_calls[0]) + 0.1
            if wait_time > 0:
                logger.info(f"达到处理速率限制，等待 {wait_time:.2f} 秒")
                # 添加随机抖动，避免同时请求
                jitter = random.uniform(0.1, 0.5)
                time.sleep(wait_time + jitter)
                current_time = time.time()
                self.api_calls = [call_time for call_time in self.api_calls if current_time - call_time < self.RATE_LIMIT_PERIOD]
        
        # 记录新的API调用
        self.api_calls.append(time.time())
        return True
    
    def allowed_file(self, filename):
        """
        检查文件扩展名是否允许
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 是否允许上传
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def save_uploaded_file(self, file):
        """
        保存上传的文件
        
        Args:
            file: 文件对象
            
        Returns:
            dict: 包含文件信息的字典
        """
        try:
            # 检查文件扩展名
            if not self.allowed_file(file.filename):
                return {'success': False, 'message': '不支持的文件类型，仅支持Excel和CSV文件'}
            
            # 检查文件大小
            file.seek(0, 2)  # 移动到文件末尾
            file_size = file.tell()
            file.seek(0)  # 重置到文件开头
            
            if file_size > self.MAX_FILE_SIZE:
                return {'success': False, 'message': f'文件大小超过限制（最大{self.MAX_FILE_SIZE/1024/1024}MB）'}
            
            # 生成唯一文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_str = f"{random.randint(1000, 9999)}"
            original_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{self.user_id}_{timestamp}_{random_str}.{original_ext}"
            
            # 保存文件
            file_path = os.path.join(self.upload_dir, unique_filename)
            file.save(file_path)
            
            # 获取文件类型
            file_type = 'excel' if original_ext in ['xlsx', 'xls'] else 'csv'
            
            # 创建文件记录
            cost_file = ERPCostFile(
                user_id=self.user_id,
                file_name=file.filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                status='pending'
            )
            
            self.session.add(cost_file)
            self.session.commit()
            
            logger.info(f"文件上传成功: {file.filename}, ID: {cost_file.id}")
            
            return {
                'success': True,
                'file_id': cost_file.id,
                'message': '文件上传成功'
            }
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            self.session.rollback()
            return {'success': False, 'message': f'文件上传失败: {str(e)}'}
    
    def get_file_preview(self, file_id):
        """
        获取文件预览数据，用于字段映射
        
        Args:
            file_id: 文件ID
            
        Returns:
            dict: 包含预览数据和列名的字典
        """
        try:
            # 获取文件记录
            cost_file = self.session.query(ERPCostFile).filter_by(
                id=file_id,
                user_id=self.user_id
            ).first()
            
            if not cost_file:
                return {'success': False, 'message': '文件不存在'}
            
            # 读取文件
            if cost_file.file_type == 'excel':
                df = pd.read_excel(cost_file.file_path)
            else:  # csv
                # 尝试不同的编码
                encodings = ['utf-8', 'latin1', 'gbk', 'gb2312']
                df = None
                for encoding in encodings:
                    try:
                        df = pd.read_csv(cost_file.file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    return {'success': False, 'message': '无法识别文件编码'}
            
            # 获取列名
            columns = df.columns.tolist()
            
            # 获取预览数据（最多10行）
            preview_data = df.head(10).to_dict('records')
            
            # 计算总行数
            total_rows = len(df)
            
            # 更新文件记录
            cost_file.total_rows = total_rows
            self.session.commit()
            
            return {
                'success': True,
                'columns': columns,
                'preview_data': preview_data,
                'total_rows': total_rows,
                'supported_fields': {k: v['display'] for k, v in self.SUPPORTED_FIELDS.items()}
            }
            
        except Exception as e:
            logger.error(f"获取文件预览失败: {str(e)}")
            return {'success': False, 'message': f'获取文件预览失败: {str(e)}'}
    
    def save_field_mapping(self, file_id, mappings):
        """
        保存字段映射配置
        
        Args:
            file_id: 文件ID
            mappings: 字段映射配置
            
        Returns:
            dict: 操作结果
        """
        try:
            # 获取文件记录
            cost_file = self.session.query(ERPCostFile).filter_by(
                id=file_id,
                user_id=self.user_id
            ).first()
            
            if not cost_file:
                return {'success': False, 'message': '文件不存在'}
            
            # 验证必需字段
            required_fields = [k for k, v in self.SUPPORTED_FIELDS.items() if v.get('required')]
            mapped_fields = [m['target_field'] for m in mappings]
            
            missing_fields = set(required_fields) - set(mapped_fields)
            if missing_fields:
                return {'success': False, 'message': f'缺少必需字段映射: {missing_fields}'}
            
            # 删除旧的映射
            self.session.query(ERPCostMapping).filter_by(cost_file_id=file_id).delete()
            
            # 创建新的映射
            for mapping in mappings:
                field_info = self.SUPPORTED_FIELDS.get(mapping['target_field'], {})
                cost_mapping = ERPCostMapping(
                    cost_file_id=file_id,
                    source_column=mapping['source_column'],
                    target_field=mapping['target_field'],
                    field_type=field_info.get('type', 'string'),
                    is_required=field_info.get('required', False)
                )
                self.session.add(cost_mapping)
            
            self.session.commit()
            
            logger.info(f"字段映射保存成功: 文件ID {file_id}")
            
            return {'success': True, 'message': '字段映射保存成功'}
            
        except Exception as e:
            logger.error(f"保存字段映射失败: {str(e)}")
            self.session.rollback()
            return {'success': False, 'message': f'保存字段映射失败: {str(e)}'}
    
    def process_cost_file(self, file_id):
        """
        处理成本文件，导入数据
        
        Args:
            file_id: 文件ID
            
        Returns:
            dict: 处理结果
        """
        try:
            # 遵守速率限制
            self._respect_rate_limit()
            
            # 获取文件记录
            cost_file = self.session.query(ERPCostFile).filter_by(
                id=file_id,
                user_id=self.user_id
            ).first()
            
            if not cost_file:
                return {'success': False, 'message': '文件不存在'}
            
            # 检查状态
            if cost_file.status == 'processing':
                return {'success': False, 'message': '文件正在处理中'}
            
            # 更新状态
            cost_file.status = 'processing'
            cost_file.processed_rows = 0
            self.session.commit()
            
            # 获取字段映射
            mappings = self.session.query(ERPCostMapping).filter_by(
                cost_file_id=file_id
            ).all()
            
            if not mappings:
                cost_file.status = 'failed'
                cost_file.error_message = '未配置字段映射'
                self.session.commit()
                return {'success': False, 'message': '未配置字段映射'}
            
            # 创建映射字典
            mapping_dict = {m.source_column: m for m in mappings}
            
            # 读取文件
            if cost_file.file_type == 'excel':
                df = pd.read_excel(cost_file.file_path)
            else:  # csv
                # 尝试不同的编码
                encodings = ['utf-8', 'latin1', 'gbk', 'gb2312']
                df = None
                for encoding in encodings:
                    try:
                        df = pd.read_csv(cost_file.file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    cost_file.status = 'failed'
                    cost_file.error_message = '无法识别文件编码'
                    self.session.commit()
                    return {'success': False, 'message': '无法识别文件编码'}
            
            # 处理数据
            total_rows = len(df)
            success_count = 0
            error_count = 0
            batch_size = 1000
            
            for i in range(0, total_rows, batch_size):
                batch = df.iloc[i:i+batch_size]
                cost_records = []
                
                for _, row in batch.iterrows():
                    try:
                        # 映射数据
                        cost_data = {
                            'user_id': self.user_id,
                            'cost_file_id': file_id
                        }
                        
                        # 必需字段验证
                        has_required_fields = True
                        missing_fields = []
                        
                        for source_col, mapping in mapping_dict.items():
                            if source_col in row:
                                value = row[source_col]
                                
                                # 转换字段类型
                                if mapping.field_type == 'float':
                                    try:
                                        value = float(value)
                                    except (ValueError, TypeError):
                                        value = 0.0
                                elif mapping.field_type == 'date':
                                    try:
                                        if pd.isna(value):
                                            if mapping.is_required:
                                                has_required_fields = False
                                                missing_fields.append(mapping.target_field)
                                            continue
                                        value = pd.to_datetime(value).date()
                                    except Exception:
                                        if mapping.is_required:
                                            has_required_fields = False
                                            missing_fields.append(mapping.target_field)
                                        continue
                                elif mapping.field_type == 'string':
                                    if pd.isna(value):
                                        value = ''
                                    else:
                                        value = str(value).strip()
                            else:
                                if mapping.is_required:
                                    has_required_fields = False
                                    missing_fields.append(mapping.target_field)
                                continue
                            
                            cost_data[mapping.target_field] = value
                        
                        # 检查必需字段
                        if not has_required_fields:
                            error_count += 1
                            continue
                        
                        # 设置默认值
                        if 'currency' not in cost_data:
                            cost_data['currency'] = 'USD'
                        
                        # 创建记录
                        record = ERPCostData(**cost_data)
                        cost_records.append(record)
                        success_count += 1
                        
                    except Exception as e:
                        logger.error(f"处理行数据失败: {str(e)}")
                        error_count += 1
                
                # 批量保存
                if cost_records:
                    self.session.bulk_save_objects(cost_records)
                    self.session.commit()
                
                # 更新进度
                cost_file.processed_rows = min(success_count + error_count, total_rows)
                self.session.commit()
            
            # 更新文件状态
            cost_file.status = 'completed'
            cost_file.process_time = datetime.utcnow()
            self.session.commit()
            
            logger.info(f"文件处理完成: 文件ID {file_id}, 成功: {success_count}, 失败: {error_count}")
            
            return {
                'success': True,
                'message': '文件处理完成',
                'success_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            logger.error(f"处理文件失败: {str(e)}")
            if cost_file:
                cost_file.status = 'failed'
                cost_file.error_message = str(e)
                self.session.commit()
            else:
                self.session.rollback()
            return {'success': False, 'message': f'处理文件失败: {str(e)}'}
    
    def integrate_cost_data(self, file_id=None):
        """
        将ERP成本数据集成到主数据表
        
        Args:
            file_id: 文件ID，如果为None则处理所有未处理的数据
            
        Returns:
            dict: 集成结果
        """
        try:
            # 构建查询
            query = self.session.query(ERPCostData).filter_by(
                user_id=self.user_id,
                is_processed=0
            )
            
            if file_id:
                query = query.filter_by(cost_file_id=file_id)
            
            # 获取未处理的数据
            unprocessed_data = query.all()
            
            if not unprocessed_data:
                return {'success': True, 'message': '没有未处理的成本数据'}
            
            # 按ASIN和日期分组
            asin_date_groups = {}
            for data in unprocessed_data:
                key = (data.asin, data.cost_date)
                if key not in asin_date_groups:
                    asin_date_groups[key] = []
                asin_date_groups[key].append(data)
            
            # 处理每组数据
            integrated_count = 0
            
            for (asin, cost_date), cost_items in asin_date_groups.items():
                try:
                    # 查找或创建集成数据记录
                    integrated_record = self.session.query(AmazonIntegratedData).filter_by(
                        user_id=self.user_id,
                        asin=asin,
                        order_date=cost_date
                    ).first()
                    
                    if not integrated_record:
                        integrated_record = AmazonIntegratedData(
                            user_id=self.user_id,
                            asin=asin,
                            order_date=cost_date,
                            store_name='ERP',  # 默认值，后续可能会更新
                            is_estimated=1  # 标记为估算数据
                        )
                        self.session.add(integrated_record)
                    
                    # 累计成本数据
                    product_cost = 0
                    shipping_cost = 0
                    other_cost = 0
                    
                    for item in cost_items:
                        if item.cost_category == 'product':
                            product_cost += item.cost_value
                        elif item.cost_category == 'shipping':
                            shipping_cost += item.cost_value
                        else:
                            other_cost += item.cost_value
                    
                    # 更新成本字段
                    integrated_record.product_cost += product_cost
                    integrated_record.shipping_cost += shipping_cost
                    integrated_record.promotion_fee += other_cost  # 临时存储在促销费字段
                    
                    # 标记为已处理
                    for item in cost_items:
                        item.is_processed = 1
                    
                    integrated_count += len(cost_items)
                    
                except Exception as e:
                    logger.error(f"集成成本数据失败 (ASIN: {asin}, Date: {cost_date}): {str(e)}")
                    continue
            
            self.session.commit()
            
            logger.info(f"成本数据集成完成: 成功集成 {integrated_count} 条记录")
            
            return {
                'success': True,
                'message': '成本数据集成完成',
                'integrated_count': integrated_count
            }
            
        except Exception as e:
            logger.error(f"集成成本数据失败: {str(e)}")
            self.session.rollback()
            return {'success': False, 'message': f'集成成本数据失败: {str(e)}'}
    
    def get_upload_history(self, page=1, page_size=10):
        """
        获取上传历史记录
        
        Args:
            page: 页码
            page_size: 每页大小
            
        Returns:
            dict: 历史记录列表
        """
        try:
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 查询历史记录
            query = self.session.query(ERPCostFile).filter_by(
                user_id=self.user_id
            ).order_by(ERPCostFile.upload_time.desc())
            
            # 总记录数
            total = query.count()
            
            # 分页查询
            records = query.offset(offset).limit(page_size).all()
            
            # 格式化结果
            history_list = []
            for record in records:
                history_list.append({
                    'id': record.id,
                    'file_name': record.file_name,
                    'file_size': record.file_size,
                    'status': record.status,
                    'processed_rows': record.processed_rows,
                    'total_rows': record.total_rows,
                    'upload_time': record.upload_time.isoformat() if record.upload_time else None,
                    'process_time': record.process_time.isoformat() if record.process_time else None,
                    'error_message': record.error_message
                })
            
            return {
                'success': True,
                'data': history_list,
                'total': total,
                'page': page,
                'page_size': page_size
            }
            
        except Exception as e:
            logger.error(f"获取上传历史失败: {str(e)}")
            return {'success': False, 'message': f'获取上传历史失败: {str(e)}'}
    
    def delete_file(self, file_id):
        """
        删除上传的文件及相关数据
        
        Args:
            file_id: 文件ID
            
        Returns:
            dict: 删除结果
        """
        try:
            # 获取文件记录
            cost_file = self.session.query(ERPCostFile).filter_by(
                id=file_id,
                user_id=self.user_id
            ).first()
            
            if not cost_file:
                return {'success': False, 'message': '文件不存在'}
            
            # 删除相关的成本数据
            self.session.query(ERPCostData).filter_by(cost_file_id=file_id).delete()
            
            # 删除字段映射
            self.session.query(ERPCostMapping).filter_by(cost_file_id=file_id).delete()
            
            # 删除文件
            if os.path.exists(cost_file.file_path):
                try:
                    os.remove(cost_file.file_path)
                except Exception as e:
                    logger.error(f"删除文件失败: {str(e)}")
            
            # 删除文件记录
            self.session.delete(cost_file)
            self.session.commit()
            
            logger.info(f"文件删除成功: 文件ID {file_id}")
            
            return {'success': True, 'message': '文件删除成功'}
            
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            self.session.rollback()
            return {'success': False, 'message': f'删除文件失败: {str(e)}'}

# 使用示例
if __name__ == "__main__":
    # 示例: 创建ERP成本管理器
    erp_manager = AmazonERPCostManager(user_id=1)
    
    # 注意: 实际使用时，需要在Flask路由中集成这个模块
    # 并通过request.files获取上传的文件
    print("ERP成本数据管理器初始化完成")
