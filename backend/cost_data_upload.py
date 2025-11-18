import os
import pandas as pd
import datetime
import uuid
import logging
from models import AmazonIntegratedData, CostRecord, ManualCost, User, ERPCostFile, ERPCostData, ERPCostMapping, init_db

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cost_data_upload')

class CostDataUploader:
    """ERP成本数据文件上传处理模块"""
    
    # 支持的文件格式
    SUPPORTED_FORMATS = ['.xlsx', '.xls', '.csv']
    
    # 必填字段
    REQUIRED_FIELDS = ['asin', 'product_cost', 'shipping_cost', 'date']
    
    # 文件上传目录
    UPLOAD_DIR = 'uploads'
    
    def __init__(self, db_session=None):
        self.db_session = db_session or init_db()
        # 确保上传目录存在
        if not os.path.exists(self.UPLOAD_DIR):
            os.makedirs(self.UPLOAD_DIR)
            logging.info(f'创建上传目录: {self.UPLOAD_DIR}')
    
    def validate_file_format(self, file_path):
        """验证文件格式是否支持"""
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f'不支持的文件格式: {ext}。支持的格式: {", ".join(self.SUPPORTED_FORMATS)}')
        return True
    
    def read_file(self, file_path):
        """读取文件内容"""
        try:
            _, ext = os.path.splitext(file_path)
            
            if ext.lower() == '.csv':
                # 尝试不同的编码
                encodings = ['utf-8', 'gbk', 'latin-1']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        logger.info(f'使用编码 {encoding} 成功读取CSV文件')
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    raise ValueError('无法识别CSV文件的编码格式')
                    
            else:
                # Excel文件
                df = pd.read_excel(file_path)
                
            logger.info(f'成功读取文件，共 {len(df)} 行数据')
            return df
            
        except Exception as e:
            logger.error(f'读取文件时发生错误: {str(e)}')
            raise
    
    def validate_data(self, df):
        """验证数据格式和必填字段"""
        # 检查必填字段是否存在
        missing_fields = [field for field in self.REQUIRED_FIELDS if field not in df.columns.str.lower()]
        if missing_fields:
            raise ValueError(f'缺少必填字段: {", ".join(missing_fields)}')
        
        # 转换列名为小写
        df.columns = df.columns.str.lower()
        
        # 检查ASIN是否为空
        if df['asin'].isnull().any():
            raise ValueError('ASIN字段包含空值')
        
        # 检查成本字段是否为数字
        for cost_field in ['product_cost', 'shipping_cost']:
            try:
                df[cost_field] = pd.to_numeric(df[cost_field], errors='coerce')
                if df[cost_field].isnull().any():
                    raise ValueError(f'{cost_field}字段包含非数字值')
            except Exception:
                raise ValueError(f'{cost_field}字段格式错误')
        
        # 检查日期字段
        try:
            df['date'] = pd.to_datetime(df['date'])
        except Exception:
            raise ValueError('日期字段格式错误')
        
        return df
    
    def process_cost_data(self, df):
        """处理成本数据"""
        processed_data = []
        
        for _, row in df.iterrows():
            record = {
                'asin': row['asin'].strip() if isinstance(row['asin'], str) else str(row['asin']),
                'product_cost': float(row['product_cost']),
                'shipping_cost': float(row['shipping_cost']),
                'date': row['date'].date(),
                # 处理可选字段
                'store_name': row.get('store_name', '').strip() if pd.notna(row.get('store_name')) else '',
                'currency': row.get('currency', 'USD').strip() if pd.notna(row.get('currency')) else 'USD',
                'notes': row.get('notes', '').strip() if pd.notna(row.get('notes')) else ''
            }
            processed_data.append(record)
        
        return processed_data
    
    def save_cost_data(self, cost_records, user_id):
        """保存成本数据到数据库，支持用户数据隔离"""
        if not cost_records:
            logger.warning("没有成本数据需要保存")
            return 0, 0
        
        try:
            new_count = 0
            update_count = 0
            
            for record in cost_records:
                # 查找是否已存在相同的成本记录（按用户ID过滤）
                existing_record = self.db_session.query(CostRecord).filter_by(
                    asin=record['asin'],
                    date=record['date'],
                    user_id=user_id
                ).first()
                
                if existing_record:
                    # 更新现有记录
                    for key, value in record.items():
                        if hasattr(existing_record, key):
                            setattr(existing_record, key, value)
                    update_count += 1
                else:
                    # 创建新记录
                    new_cost_record = CostRecord(**record)
                    self.db_session.add(new_cost_record)
                    new_count += 1
            
            # 提交数据库事务
            self.db_session.commit()
            
            logger.info(f'成功保存成本数据: 新增 {new_count} 条，更新 {update_count} 条')
            return new_count, update_count
            
        except Exception as e:
            logger.error(f'保存成本数据时发生错误: {str(e)}')
            self.db_session.rollback()
            raise
    
    def update_integrated_data(self, cost_records, user_id):
        """更新整合数据表中的成本数据，支持用户数据隔离"""
        updated_count = 0
        
        try:
            for record in cost_records:
                # 查找匹配的整合数据记录（按用户ID过滤）
                integrated_records = self.db_session.query(AmazonIntegratedData).filter(
                    AmazonIntegratedData.asin == record['asin'],
                    AmazonIntegratedData.order_date >= record['date'],
                    AmazonIntegratedData.user_id == user_id
                ).all()
                
                for integrated_record in integrated_records:
                    # 更新成本数据
                    integrated_record.product_cost = record['product_cost']
                    integrated_record.shipping_cost = record['shipping_cost']
                    updated_count += 1
            
            if updated_count > 0:
                self.db_session.commit()
                logger.info(f'成功更新 {updated_count} 条整合数据记录的成本信息')
            
            return updated_count
            
        except Exception as e:
            logger.error(f'更新整合数据时发生错误: {str(e)}')
            self.db_session.rollback()
            return 0
    
    def process_file(self, file_path, user_id):
        """上传并处理成本数据文件，支持用户数据隔离"""
        try:
            # 验证文件格式
            self.validate_file_format(file_path)
            
            # 读取文件
            df = self.read_file(file_path)
            
            # 验证数据
            validated_df = self.validate_data(df)
            
            # 处理数据
            cost_records = self.process_cost_data(validated_df)
            
            # 为每条记录添加用户ID
            for record in cost_records:
                record['user_id'] = user_id
            
            # 保存成本记录
            new_count, update_count = self.save_cost_data(cost_records, user_id)
            
            # 更新整合数据表
            integrated_updated = self.update_integrated_data(cost_records, user_id)
            
            result = {
                'status': 'success',
                'message': f'文件上传成功',
                'total_records': len(cost_records),
                'new_records': new_count,
                'updated_records': update_count,
                'integrated_updated': integrated_updated
            }
            
            logger.info(f'文件上传处理完成: {result}')
            return result
            
        except Exception as e:
            error_message = f'文件上传失败: {str(e)}'
            logger.error(error_message)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def get_erp_cost_data(self, user_id, asin=None, start_date=None, end_date=None, limit=100):
        """获取ERP成本数据"""
        try:
            query = self.db_session.query(ERPCostData).filter_by(user_id=user_id)
            
            if asin:
                query = query.filter(ERPCostData.asin == asin)
            
            if start_date:
                query = query.filter(ERPCostData.cost_date >= start_date)
            
            if end_date:
                query = query.filter(ERPCostData.cost_date <= end_date)
            
            records = query.order_by(ERPCostData.cost_date.desc()).limit(limit).all()
            
            return [{
                'id': r.id,
                'asin': r.asin,
                'sku': r.sku,
                'product_name': r.product_name,
                'cost_value': r.cost_value,
                'cost_date': r.cost_date,
                'currency': r.currency,
                'cost_category': r.cost_category,
                'supplier': r.supplier,
                'order_number': r.order_number,
                'source_system': r.source_system,
                'is_processed': r.is_processed
            } for r in records]
            
        except Exception as e:
            logger.error(f'获取ERP成本数据时发生错误: {str(e)}')
            return []
    
    def mark_cost_data_processed(self, data_ids, user_id):
        """标记成本数据为已处理"""
        try:
            updated = self.db_session.query(ERPCostData).filter(
                ERPCostData.id.in_(data_ids),
                ERPCostData.user_id == user_id
            ).update({ERPCostData.is_processed: 1}, synchronize_session=False)
            
            self.db_session.commit()
            logger.info(f'标记ERP成本数据为已处理: 更新 {updated} 条记录')
            return updated
            
        except Exception as e:
            logger.error(f'标记成本数据为已处理时发生错误: {str(e)}')
            self.db_session.rollback()
            return 0
    
    def save_cost_data(self, cost_records, user_id):
        """保存成本数据到数据库，支持用户数据隔离"""
        if not cost_records:
            logger.warning("没有成本数据需要保存")
            return 0, 0
        
        try:
            new_count = 0
            update_count = 0
            
            for record in cost_records:
                # 查找是否已存在相同的成本记录（按用户ID过滤）
                existing_record = self.db_session.query(CostRecord).filter_by(
                    asin=record['asin'],
                    date=record['date'],
                    user_id=user_id
                ).first()
                
                if existing_record:
                    # 更新现有记录
                    for key, value in record.items():
                        if hasattr(existing_record, key):
                            setattr(existing_record, key, value)
                    update_count += 1
                else:
                    # 创建新记录
                    new_cost_record = CostRecord(**record)
                    self.db_session.add(new_cost_record)
                    new_count += 1
            
            # 提交数据库事务
            self.db_session.commit()
            
            logger.info(f'成功保存成本数据: 用户ID={user_id}, 新增 {new_count} 条，更新 {update_count} 条')
            return new_count, update_count
            
        except Exception as e:
            logger.error(f'保存成本数据时发生错误: {str(e)}')
            self.db_session.rollback()
            raise
    
    def save_erp_cost_file(self, file_path, user_id, file_size, file_type='excel'):
        """保存ERP成本文件记录到数据库"""
        try:
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex}_{os.path.basename(file_path)}"
            # 目标文件路径
            target_path = os.path.join(self.UPLOAD_DIR, unique_filename)
            
            # 移动文件到上传目录
            os.rename(file_path, target_path)
            
            # 创建文件记录
            erp_file = ERPCostFile(
                user_id=user_id,
                file_name=os.path.basename(file_path),
                file_path=target_path,
                file_size=file_size,
                file_type=file_type,
                status='pending'
            )
            
            self.db_session.add(erp_file)
            self.db_session.commit()
            
            logger.info(f'保存ERP成本文件记录: ID={erp_file.id}, 用户ID={user_id}, 文件名={erp_file.file_name}')
            return erp_file
            
        except Exception as e:
            logger.error(f'保存ERP成本文件记录时发生错误: {str(e)}')
            self.db_session.rollback()
            raise
    
    def save_erp_cost_data(self, erp_file_id, parsed_data, user_id):
        """保存ERP成本数据到数据库"""
        try:
            saved_count = 0
            
            for record in parsed_data:
                # 检查是否已存在相同记录
                existing = self.db_session.query(ERPCostData).filter_by(
                    user_id=user_id,
                    asin=record['asin'],
                    cost_date=record['cost_date']
                ).first()
                
                if not existing:
                    erp_data = ERPCostData(
                        user_id=user_id,
                        cost_file_id=erp_file_id,
                        asin=record['asin'],
                        sku=record.get('sku', ''),
                        product_name=record.get('product_name', ''),
                        cost_value=record.get('cost_value', 0.0),
                        cost_date=record['cost_date'],
                        currency=record.get('currency', 'USD'),
                        cost_category=record.get('cost_category', 'product'),
                        supplier=record.get('supplier', ''),
                        order_number=record.get('order_number', ''),
                        source_system=record.get('source_system', 'ERP'),
                        is_processed=0
                    )
                    self.db_session.add(erp_data)
                    saved_count += 1
            
            self.db_session.commit()
            logger.info(f'保存ERP成本数据: 文件ID={erp_file_id}, 新增 {saved_count} 条记录')
            return saved_count
            
        except Exception as e:
            logger.error(f'保存ERP成本数据时发生错误: {str(e)}')
            self.db_session.rollback()
            raise
    
    def process_erp_file(self, erp_file_id):
        """处理已上传的ERP成本文件"""
        try:
            # 获取文件记录
            erp_file = self.db_session.query(ERPCostFile).filter_by(id=erp_file_id).first()
            if not erp_file:
                raise ValueError(f'ERP成本文件不存在: ID={erp_file_id}')
            
            # 更新文件状态
            erp_file.status = 'processing'
            self.db_session.commit()
            
            # 读取文件
            df = self.read_file(erp_file.file_path)
            erp_file.total_rows = len(df)
            self.db_session.commit()
            
            # 解析数据
            parsed_data = []
            for _, row in df.iterrows():
                # 尝试不同的列名映射
                asin = None
                cost_value = None
                cost_date = None
                
                # 查找ASIN
                for col in ['asin', 'ASIN', 'product_id', 'Product ID']:
                    if col in df.columns and pd.notna(row[col]):
                        asin = str(row[col]).strip()
                        break
                
                # 查找成本值
                for col in ['cost', 'price', 'product_cost', 'cost_value', '成本', '价格']:
                    if col in df.columns and pd.notna(row[col]):
                        try:
                            cost_value = float(row[col])
                        except:
                            pass
                        break
                
                # 查找日期
                for col in ['date', 'order_date', 'cost_date', '日期', '订单日期']:
                    if col in df.columns and pd.notna(row[col]):
                        try:
                            cost_date = pd.to_datetime(row[col]).date()
                        except:
                            pass
                        break
                
                if asin and cost_value is not None and cost_date:
                    record = {
                        'asin': asin,
                        'cost_value': cost_value,
                        'cost_date': cost_date
                    }
                    # 添加其他可选字段
                    for col in ['sku', 'SKU']:
                        if col in df.columns and pd.notna(row[col]):
                            record['sku'] = str(row[col]).strip()
                            break
                    
                    for col in ['product_name', 'name', '产品名称']:
                        if col in df.columns and pd.notna(row[col]):
                            record['product_name'] = str(row[col]).strip()
                            break
                    
                    parsed_data.append(record)
            
            # 保存解析后的数据
            saved_count = self.save_erp_cost_data(erp_file_id, parsed_data, erp_file.user_id)
            
            # 更新文件状态
            erp_file.status = 'completed'
            erp_file.processed_rows = saved_count
            erp_file.process_time = datetime.datetime.utcnow()
            self.db_session.commit()
            
            logger.info(f'ERP文件处理完成: ID={erp_file_id}, 处理记录={saved_count}/{erp_file.total_rows}')
            return {
                'status': 'success',
                'file_id': erp_file_id,
                'processed_rows': saved_count,
                'total_rows': erp_file.total_rows
            }
            
        except Exception as e:
            error_message = str(e)
            # 更新错误状态
            erp_file = self.db_session.query(ERPCostFile).filter_by(id=erp_file_id).first()
            if erp_file:
                erp_file.status = 'failed'
                erp_file.error_message = error_message[:1000]  # 限制错误消息长度
                self.db_session.commit()
            
            logger.error(f'处理ERP文件时发生错误: {error_message}')
            raise
    
    def get_file_mappings(self, file_id):
        """获取文件的字段映射信息"""
        try:
            mappings = self.db_session.query(ERPCostMapping).filter_by(cost_file_id=file_id).all()
            return [{
                'source_column': m.source_column,
                'target_field': m.target_field,
                'field_type': m.field_type,
                'is_required': m.is_required
            } for m in mappings]
        except Exception as e:
            logger.error(f'获取文件映射信息时发生错误: {str(e)}')
            return []
    
    def set_file_mappings(self, file_id, mappings):
        """设置文件的字段映射信息"""
        try:
            # 删除现有映射
            self.db_session.query(ERPCostMapping).filter_by(cost_file_id=file_id).delete()
            
            # 添加新映射
            for mapping in mappings:
                erp_mapping = ERPCostMapping(
                    cost_file_id=file_id,
                    source_column=mapping['source_column'],
                    target_field=mapping['target_field'],
                    field_type=mapping.get('field_type', ''),
                    is_required=mapping.get('is_required', False)
                )
                self.db_session.add(erp_mapping)
            
            self.db_session.commit()
            logger.info(f'更新文件映射信息: 文件ID={file_id}, 映射数量={len(mappings)}')
            return True
            
        except Exception as e:
            logger.error(f'设置文件映射信息时发生错误: {str(e)}')
            self.db_session.rollback()
            return False
    
    def get_user_files(self, user_id):
        """获取用户的所有成本文件"""
        try:
            files = self.db_session.query(ERPCostFile).filter_by(user_id=user_id).order_by(ERPCostFile.upload_time.desc()).all()
            return [{
                'id': f.id,
                'file_name': f.file_name,
                'file_size': f.file_size,
                'file_type': f.file_type,
                'status': f.status,
                'processed_rows': f.processed_rows,
                'total_rows': f.total_rows,
                'upload_time': f.upload_time,
                'process_time': f.process_time
            } for f in files]
        except Exception as e:
            logger.error(f'获取用户文件列表时发生错误: {str(e)}')
            return []
    
    def get_file_status(self, file_id, user_id):
        """获取文件处理状态"""
        try:
            file = self.db_session.query(ERPCostFile).filter_by(
                id=file_id,
                user_id=user_id
            ).first()
            
            if not file:
                return None
            
            return {
                'id': file.id,
                'file_name': file.file_name,
                'status': file.status,
                'processed_rows': file.processed_rows,
                'total_rows': file.total_rows,
                'error_message': file.error_message,
                'upload_time': file.upload_time,
                'process_time': file.process_time
            }
        except Exception as e:
            logger.error(f'获取文件状态时发生错误: {str(e)}')
            return None
    
    def upload_file(self, file_path):
        """上传并处理成本数据文件（兼容旧版本，不推荐使用）"""
        logger.warning("使用了不推荐的upload_file方法，请使用process_file方法并提供user_id参数")
        # 调用process_file，使用默认user_id=1（管理员）
        return self.process_file(file_path, user_id=1)
    
    def add_manual_cost(self, asin, cost_type, amount, date=None, notes='', user_id=None):
        """手动添加成本记录，支持用户数据隔离"""
        try:
            # 验证参数
            if not asin:
                raise ValueError('ASIN不能为空')
            
            valid_cost_types = ['promotion', 'handling', 'other', 'storage', 'commission', 'advertising', 'return', 'refund', 'other_fee']
            if cost_type not in valid_cost_types:
                raise ValueError(f'费用类型必须是以下之一: {', '.join(valid_cost_types)}')
            
            if user_id is None:
                raise ValueError('用户ID不能为空')
            
            try:
                amount = float(amount)
                if amount < 0:
                    raise ValueError('金额不能为负数')
            except (ValueError, TypeError):
                raise ValueError('金额必须是有效的数字')
            
            # 设置日期
            if date is None:
                date = datetime.datetime.now().date()
            elif isinstance(date, str):
                date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            
            # 创建手动成本记录
            manual_cost = ManualCost(
                asin=asin,
                cost_type=cost_type,
                amount=amount,
                cost_date=date,
                description=notes,
                user_id=user_id
            )
            
            # 保存到数据库
            self.db_session.add(manual_cost)
            self.db_session.commit()
            
            # 获取所有符合条件的整合数据记录
            integrated_records = self.db_session.query(AmazonIntegratedData).filter(
                AmazonIntegratedData.asin == asin,
                AmazonIntegratedData.order_date >= date,
                AmazonIntegratedData.user_id == user_id
            ).all()
            
            if integrated_records:
                # 根据费用类型更新相应字段
                for record in integrated_records:
                    if cost_type == 'promotion':
                        record.promotion_fee = record.promotion_fee + amount if record.promotion_fee else amount
                    elif cost_type == 'handling':
                        record.handling_fee = record.handling_fee + amount if record.handling_fee else amount
                    elif cost_type == 'storage':
                        record.storage_fee = record.storage_fee + amount if record.storage_fee else amount
                    elif cost_type == 'commission':
                        record.amazon_fee = record.amazon_fee + amount if record.amazon_fee else amount
                    elif cost_type == 'advertising':
                        record.advertising_fee = record.advertising_fee + amount if record.advertising_fee else amount
                    elif cost_type == 'return':
                        record.return_fee = record.return_fee + amount if record.return_fee else amount
                    elif cost_type == 'refund':
                        record.refund_fee = record.refund_fee + amount if record.refund_fee else amount
                    elif cost_type in ['other', 'other_fee']:
                        record.other_fee = record.other_fee + amount if record.other_fee else amount
                
                self.db_session.commit()
            
            logger.info(f'成功添加手动成本记录: ASIN={asin}, 类型={cost_type}, 金额={amount}, 用户ID={user_id}')
            
            return {
                'status': 'success',
                'message': '手动成本记录添加成功',
                'record_id': manual_cost.id
            }
            
        except Exception as e:
            error_message = f'添加手动成本记录失败: {str(e)}'
            logger.error(error_message)
            self.db_session.rollback()
            return {
                'status': 'error',
                'message': error_message
            }
    
    def get_cost_summary(self, start_date=None, end_date=None, user_id=None):
        """获取成本汇总信息，支持用户数据隔离"""
        try:
            # 同时查询CostRecord和ManualCost
            cost_query = self.db_session.query(CostRecord)
            manual_query = self.db_session.query(ManualCost)
            
            # 应用用户ID过滤
            if user_id:
                cost_query = cost_query.filter(CostRecord.user_id == user_id)
                manual_query = manual_query.filter(ManualCost.user_id == user_id)
            
            # 应用日期过滤
            if start_date:
                cost_query = cost_query.filter(CostRecord.date >= start_date)
                manual_query = manual_query.filter(ManualCost.cost_date >= start_date)
            if end_date:
                cost_query = cost_query.filter(CostRecord.date <= end_date)
                manual_query = manual_query.filter(ManualCost.cost_date <= end_date)
            
            cost_records = cost_query.all()
            manual_records = manual_query.all()
            
            # 计算汇总
            summary = {
                'total_records': len(cost_records),
                'total_manual_records': len(manual_records),
                'total_product_cost': sum(r.product_cost for r in cost_records if r.product_cost),
                'total_shipping_cost': sum(r.shipping_cost for r in cost_records if r.shipping_cost),
                'total_manual_cost': sum(r.amount for r in manual_records)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f'获取成本汇总时发生错误: {str(e)}')
            return None

# 使用示例
if __name__ == '__main__':
    # 示例：上传成本数据文件
    # uploader = CostDataUploader()
    # result = uploader.upload_file('path/to/cost_data.csv')
    # print(f"上传结果: {result}")
    
    # 示例：手动添加成本
    # result = uploader.add_manual_cost(
    #     asin='B0123456789',
    #     cost_type='promotion',
    #     amount=100.0,
    #     notes='促销活动费用'
    # )
    # print(f"手动添加结果: {result}")
