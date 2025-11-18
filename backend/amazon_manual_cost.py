import json
import logging
from datetime import datetime, date
from models import Session, AmazonIntegratedData, ERPCostData, AmazonStore

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_manual_cost')

class AmazonManualCostManager:
    def __init__(self, user_id):
        """
        初始化手动成本管理模块
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.session = Session()
        
        # 成本类型定义
        self.COST_TYPES = {
            'product_cost': {'name': '产品成本', 'required': True, 'default': 0.0},
            'shipping_cost': {'name': '物流成本', 'required': False, 'default': 0.0},
            'custom_cost': {'name': '其他成本', 'required': False, 'default': 0.0},
            'custom_cost_name': {'name': '成本名称', 'required': False, 'default': ''}
        }
        
        # 验证规则
        self.validation_rules = {
            'asin': {'required': True, 'min_length': 10, 'max_length': 10},
            'quantity': {'required': True, 'min': 1},
            'cost_date': {'required': True, 'type': 'date'}
        }
    
    def __del__(self):
        """
        析构函数，关闭数据库会话
        """
        if hasattr(self, 'session'):
            self.session.close()
    
    def validate_input(self, data):
        """
        验证输入数据
        
        Args:
            data: 要验证的数据字典
            
        Returns:
            tuple: (是否有效, 错误消息)
        """
        # 验证必需字段
        for field, rules in self.validation_rules.items():
            if rules.get('required') and field not in data:
                return False, f'缺少必需字段: {field}'
            
            if field in data:
                value = data[field]
                
                # 类型验证
                if rules.get('type') == 'date':
                    try:
                        if isinstance(value, str):
                            # 尝试解析日期字符串
                            date.fromisoformat(value)
                    except ValueError:
                        return False, f'字段 {field} 不是有效的日期格式'
                
                # 长度验证
                if 'min_length' in rules and len(str(value)) < rules['min_length']:
                    return False, f'字段 {field} 长度不能小于 {rules["min_length"]}'
                
                if 'max_length' in rules and len(str(value)) > rules['max_length']:
                    return False, f'字段 {field} 长度不能大于 {rules["max_length"]}'
                
                # 数值验证
                if 'min' in rules and isinstance(value, (int, float)) and value < rules['min']:
                    return False, f'字段 {field} 不能小于 {rules["min"]}'
        
        # 验证ASIN格式（简化版，实际应根据亚马逊规则）
        if 'asin' in data and not data['asin'].strip():
            return False, 'ASIN不能为空'
        
        # 验证成本数据
        cost_fields = ['product_cost', 'shipping_cost', 'custom_cost']
        has_cost = False
        for field in cost_fields:
            if field in data and data[field] and data[field] > 0:
                has_cost = True
                break
        
        if not has_cost:
            return False, '至少需要输入一种成本'
        
        return True, '验证通过'
    
    def get_available_asins(self, store_id=None, limit=100):
        """
        获取可用的ASIN列表，用于表单选择
        
        Args:
            store_id: 店铺ID（可选）
            limit: 限制返回数量
            
        Returns:
            dict: ASIN列表及产品信息
        """
        try:
            # 构建查询
            query = self.session.query(AmazonIntegratedData).filter_by(
                user_id=self.user_id
            )
            
            if store_id:
                query = query.filter_by(store_id=store_id)
            
            # 获取唯一的ASIN列表，并包含最近的产品信息
            asins_data = query.distinct(AmazonIntegratedData.asin).order_by(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.order_date.desc()
            ).limit(limit).all()
            
            # 格式化结果
            asin_list = []
            for item in asins_data:
                asin_info = {
                    'asin': item.asin,
                    'product_name': item.product_name or '未知产品',
                    'last_date': item.order_date.isoformat() if item.order_date else None,
                    'store_name': item.store_name or '未知店铺'
                }
                asin_list.append(asin_info)
            
            return {
                'success': True,
                'asins': asin_list,
                'total': len(asin_list)
            }
            
        except Exception as e:
            logger.error(f"获取ASIN列表失败: {str(e)}")
            return {'success': False, 'message': f'获取ASIN列表失败: {str(e)}'}
    
    def search_asin(self, keyword, limit=50):
        """
        根据关键词搜索ASIN
        
        Args:
            keyword: 搜索关键词
            limit: 限制返回数量
            
        Returns:
            dict: 搜索结果
        """
        try:
            if not keyword or len(keyword.strip()) < 2:
                return {'success': False, 'message': '搜索关键词至少需要2个字符'}
            
            # 搜索ASIN或产品名称
            query = self.session.query(AmazonIntegratedData).filter_by(
                user_id=self.user_id
            ).filter(
                (AmazonIntegratedData.asin.ilike(f'%{keyword}%')) |
                (AmazonIntegratedData.product_name.ilike(f'%{keyword}%'))
            )
            
            # 获取唯一的ASIN列表
            results = query.distinct(AmazonIntegratedData.asin).order_by(
                AmazonIntegratedData.asin
            ).limit(limit).all()
            
            # 格式化结果
            search_results = []
            for item in results:
                search_results.append({
                    'asin': item.asin,
                    'product_name': item.product_name or '未知产品',
                    'store_name': item.store_name or '未知店铺'
                })
            
            return {
                'success': True,
                'results': search_results,
                'total': len(search_results)
            }
            
        except Exception as e:
            logger.error(f"搜索ASIN失败: {str(e)}")
            return {'success': False, 'message': f'搜索ASIN失败: {str(e)}'}
    
    def add_manual_cost(self, cost_data):
        """
        添加手动成本数据
        
        Args:
            cost_data: 成本数据字典
            
        Returns:
            dict: 操作结果
        """
        try:
            # 验证输入数据
            is_valid, error_msg = self.validate_input(cost_data)
            if not is_valid:
                return {'success': False, 'message': error_msg}
            
            # 准备成本记录数据
            asin = cost_data['asin'].strip()
            quantity = cost_data.get('quantity', 1)
            
            # 处理日期
            cost_date = cost_data['cost_date']
            if isinstance(cost_date, str):
                cost_date = date.fromisoformat(cost_date)
            elif isinstance(cost_date, datetime):
                cost_date = cost_date.date()
            
            # 计算单位成本（如果提供了数量）
            product_cost = cost_data.get('product_cost', 0.0)
            shipping_cost = cost_data.get('shipping_cost', 0.0)
            custom_cost = cost_data.get('custom_cost', 0.0)
            custom_cost_name = cost_data.get('custom_cost_name', '其他成本')
            
            unit_product_cost = product_cost / quantity if quantity > 0 else 0.0
            unit_shipping_cost = shipping_cost / quantity if quantity > 0 else 0.0
            unit_custom_cost = custom_cost / quantity if quantity > 0 else 0.0
            
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
                    store_name='Manual',  # 手动录入的标记
                    is_estimated=1,  # 标记为估算数据
                    product_name=cost_data.get('product_name', '')
                )
                self.session.add(integrated_record)
            else:
                # 更新产品名称（如果提供了新名称）
                if 'product_name' in cost_data and cost_data['product_name']:
                    integrated_record.product_name = cost_data['product_name']
            
            # 更新成本字段
            integrated_record.product_cost += product_cost
            integrated_record.shipping_cost += shipping_cost
            
            # 其他成本暂时存储在促销费字段
            if custom_cost > 0:
                integrated_record.promotion_fee += custom_cost
            
            # 创建手动成本记录（用于审计和历史追踪）
            manual_cost_record = ERPCostData(
                user_id=self.user_id,
                asin=asin,
                cost_date=cost_date,
                cost_value=product_cost,
                cost_category='manual_product',
                quantity=quantity,
                is_processed=1,  # 已处理
                source='manual_entry',
                notes=f'手动录入: 产品成本 {product_cost} (数量: {quantity})'
            )
            self.session.add(manual_cost_record)
            
            # 记录物流成本
            if shipping_cost > 0:
                shipping_record = ERPCostData(
                    user_id=self.user_id,
                    asin=asin,
                    cost_date=cost_date,
                    cost_value=shipping_cost,
                    cost_category='manual_shipping',
                    quantity=quantity,
                    is_processed=1,
                    source='manual_entry',
                    notes=f'手动录入: 物流成本 {shipping_cost} (数量: {quantity})'
                )
                self.session.add(shipping_record)
            
            # 记录其他成本
            if custom_cost > 0:
                custom_record = ERPCostData(
                    user_id=self.user_id,
                    asin=asin,
                    cost_date=cost_date,
                    cost_value=custom_cost,
                    cost_category='manual_custom',
                    quantity=quantity,
                    is_processed=1,
                    source='manual_entry',
                    notes=f'手动录入: {custom_cost_name} {custom_cost} (数量: {quantity})'
                )
                self.session.add(custom_record)
            
            self.session.commit()
            
            # 计算总成本
            total_cost = product_cost + shipping_cost + custom_cost
            
            logger.info(f"手动成本添加成功: ASIN={asin}, 日期={cost_date}, 总成本={total_cost}")
            
            return {
                'success': True,
                'message': '成本数据添加成功',
                'total_cost': total_cost,
                'unit_cost': {
                    'product_cost': unit_product_cost,
                    'shipping_cost': unit_shipping_cost,
                    'custom_cost': unit_custom_cost,
                    'total': (total_cost / quantity) if quantity > 0 else 0.0
                },
                'record_id': integrated_record.id
            }
            
        except Exception as e:
            logger.error(f"添加手动成本失败: {str(e)}")
            self.session.rollback()
            return {'success': False, 'message': f'添加手动成本失败: {str(e)}'}
    
    def update_manual_cost(self, record_id, cost_data):
        """
        更新手动成本数据
        
        Args:
            record_id: 记录ID
            cost_data: 更新的成本数据
            
        Returns:
            dict: 操作结果
        """
        try:
            # 查找记录
            integrated_record = self.session.query(AmazonIntegratedData).filter_by(
                id=record_id,
                user_id=self.user_id,
                is_estimated=1  # 只更新估算数据
            ).first()
            
            if not integrated_record:
                return {'success': False, 'message': '记录不存在或无权修改'}
            
            # 验证输入数据
            # 复制必要字段以通过验证
            validation_data = cost_data.copy()
            validation_data['asin'] = integrated_record.asin
            validation_data['cost_date'] = integrated_record.order_date
            
            is_valid, error_msg = self.validate_input(validation_data)
            if not is_valid:
                return {'success': False, 'message': error_msg}
            
            # 重置成本字段
            old_product_cost = integrated_record.product_cost
            old_shipping_cost = integrated_record.shipping_cost
            old_custom_cost = integrated_record.promotion_fee  # 其他成本存储在促销费字段
            
            # 更新记录
            if 'product_cost' in cost_data:
                integrated_record.product_cost = cost_data['product_cost']
            
            if 'shipping_cost' in cost_data:
                integrated_record.shipping_cost = cost_data['shipping_cost']
            
            if 'custom_cost' in cost_data:
                integrated_record.promotion_fee = cost_data['custom_cost']
            
            if 'product_name' in cost_data:
                integrated_record.product_name = cost_data['product_name']
            
            # 创建更新记录
            notes = f"更新手动成本: 产品成本 {old_product_cost}→{integrated_record.product_cost}, " \
                   f"物流成本 {old_shipping_cost}→{integrated_record.shipping_cost}, " \
                   f"其他成本 {old_custom_cost}→{integrated_record.promotion_fee}"
            
            update_record = ERPCostData(
                user_id=self.user_id,
                asin=integrated_record.asin,
                cost_date=integrated_record.order_date,
                cost_value=integrated_record.product_cost,
                cost_category='manual_update',
                is_processed=1,
                source='manual_entry',
                notes=notes
            )
            self.session.add(update_record)
            
            self.session.commit()
            
            logger.info(f"手动成本更新成功: 记录ID={record_id}, ASIN={integrated_record.asin}")
            
            return {
                'success': True,
                'message': '成本数据更新成功',
                'record_id': integrated_record.id
            }
            
        except Exception as e:
            logger.error(f"更新手动成本失败: {str(e)}")
            self.session.rollback()
            return {'success': False, 'message': f'更新手动成本失败: {str(e)}'}
    
    def delete_manual_cost(self, record_id):
        """
        删除手动成本数据
        
        Args:
            record_id: 记录ID
            
        Returns:
            dict: 操作结果
        """
        try:
            # 查找记录
            integrated_record = self.session.query(AmazonIntegratedData).filter_by(
                id=record_id,
                user_id=self.user_id,
                is_estimated=1  # 只删除估算数据
            ).first()
            
            if not integrated_record:
                return {'success': False, 'message': '记录不存在或无权删除'}
            
            # 记录删除信息
            notes = f"删除手动成本: 产品成本 {integrated_record.product_cost}, " \
                   f"物流成本 {integrated_record.shipping_cost}, " \
                   f"其他成本 {integrated_record.promotion_fee}"
            
            delete_record = ERPCostData(
                user_id=self.user_id,
                asin=integrated_record.asin,
                cost_date=integrated_record.order_date,
                cost_value=0,
                cost_category='manual_delete',
                is_processed=1,
                source='manual_entry',
                notes=notes
            )
            self.session.add(delete_record)
            
            # 删除记录
            self.session.delete(integrated_record)
            self.session.commit()
            
            logger.info(f"手动成本删除成功: 记录ID={record_id}, ASIN={integrated_record.asin}")
            
            return {
                'success': True,
                'message': '成本数据删除成功'
            }
            
        except Exception as e:
            logger.error(f"删除手动成本失败: {str(e)}")
            self.session.rollback()
            return {'success': False, 'message': f'删除手动成本失败: {str(e)}'}
    
    def get_manual_cost_history(self, filters=None, page=1, page_size=20):
        """
        获取手动成本记录历史
        
        Args:
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
            
        Returns:
            dict: 历史记录列表
        """
        try:
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 构建查询
            query = self.session.query(AmazonIntegratedData).filter_by(
                user_id=self.user_id,
                is_estimated=1  # 只查询估算数据
            )
            
            # 应用过滤条件
            if filters:
                if 'asin' in filters:
                    query = query.filter(AmazonIntegratedData.asin == filters['asin'])
                
                if 'start_date' in filters:
                    query = query.filter(AmazonIntegratedData.order_date >= filters['start_date'])
                
                if 'end_date' in filters:
                    query = query.filter(AmazonIntegratedData.order_date <= filters['end_date'])
                
                if 'min_cost' in filters:
                    # 计算总成本进行过滤
                    total_cost = AmazonIntegratedData.product_cost + AmazonIntegratedData.shipping_cost + AmazonIntegratedData.promotion_fee
                    query = query.filter(total_cost >= filters['min_cost'])
            
            # 总记录数
            total = query.count()
            
            # 分页查询
            records = query.order_by(
                AmazonIntegratedData.order_date.desc(),
                AmazonIntegratedData.id.desc()
            ).offset(offset).limit(page_size).all()
            
            # 格式化结果
            history_list = []
            for record in records:
                total_cost = record.product_cost + record.shipping_cost + record.promotion_fee
                
                history_list.append({
                    'id': record.id,
                    'asin': record.asin,
                    'product_name': record.product_name or '未知产品',
                    'order_date': record.order_date.isoformat() if record.order_date else None,
                    'store_name': record.store_name,
                    'product_cost': record.product_cost,
                    'shipping_cost': record.shipping_cost,
                    'custom_cost': record.promotion_fee,  # 其他成本
                    'total_cost': total_cost,
                    'created_at': record.created_at.isoformat() if record.created_at else None
                })
            
            return {
                'success': True,
                'data': history_list,
                'total': total,
                'page': page,
                'page_size': page_size
            }
            
        except Exception as e:
            logger.error(f"获取手动成本历史失败: {str(e)}")
            return {'success': False, 'message': f'获取手动成本历史失败: {str(e)}'}
    
    def get_product_info(self, asin):
        """
        获取产品信息
        
        Args:
            asin: 产品ASIN
            
        Returns:
            dict: 产品信息
        """
        try:
            # 查询产品信息
            product = self.session.query(AmazonIntegratedData).filter_by(
                user_id=self.user_id,
                asin=asin
            ).order_by(
                AmazonIntegratedData.order_date.desc()
            ).first()
            
            if not product:
                return {'success': False, 'message': '未找到产品信息'}
            
            return {
                'success': True,
                'data': {
                    'asin': product.asin,
                    'product_name': product.product_name or '未知产品',
                    'store_name': product.store_name,
                    'last_date': product.order_date.isoformat() if product.order_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"获取产品信息失败: {str(e)}")
            return {'success': False, 'message': f'获取产品信息失败: {str(e)}'}

# 使用示例
if __name__ == "__main__":
    # 示例: 创建手动成本管理器
    cost_manager = AmazonManualCostManager(user_id=1)
    print("手动成本管理器初始化完成")
