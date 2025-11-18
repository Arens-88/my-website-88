import logging
import pandas as pd
import numpy as np
import datetime
from models import AmazonIntegratedData, AmazonStore, User, InventoryData
from sqlalchemy import and_, func

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_inventory_health')

class AmazonInventoryHealthReport:
    def __init__(self, db_session, user_id=None):
        self.db_session = db_session
        self.user_id = user_id
        logger.info(f'初始化库存健康报表模块，用户ID: {user_id}')
    
    def get_inventory_health_data(self, filters=None):
        """
        获取库存健康数据
        
        Args:
            filters: 筛选条件字典，包含：
                - store_id: 店铺ID
                - marketplace: 市场
                - min_days_of_supply: 最小库存天数阈值
                - max_days_of_supply: 最大库存天数阈值
                - include_asin: 包含特定ASIN列表
                - exclude_asin: 排除特定ASIN列表
                - sort_by: 排序字段（inventory_level, days_of_supply, sales_rate, profit_rate）
                - sort_order: 排序顺序（asc, desc）
        """
        try:
            # 默认筛选条件
            if filters is None:
                filters = {}
            
            # 设置默认值
            store_id = filters.get('store_id')
            marketplace = filters.get('marketplace')
            min_days_of_supply = filters.get('min_days_of_supply', 0)
            max_days_of_supply = filters.get('max_days_of_supply', 365)
            include_asin = filters.get('include_asin', [])
            exclude_asin = filters.get('exclude_asin', [])
            sort_by = filters.get('sort_by', 'days_of_supply')
            sort_order = filters.get('sort_order', 'asc')
            
            # 构建查询
            # 首先获取最近7天的销售数据作为销售速率
            recent_date = datetime.datetime.now().date() - datetime.timedelta(days=7)
            
            # 获取销售速率子查询
            sales_rate_subquery = (
                self.db_session.query(
                    AmazonIntegratedData.asin,
                    AmazonIntegratedData.store_id,
                    func.avg(AmazonIntegratedData.order_count).label('daily_sales_rate')
                )
                .filter(AmazonIntegratedData.date >= recent_date)
                .group_by(AmazonIntegratedData.asin, AmazonIntegratedData.store_id)
                .subquery()
            )
            
            # 主查询
            query = (
                self.db_session.query(
                    InventoryData.asin,
                    InventoryData.sku,
                    InventoryData.product_name,
                    InventoryData.store_id,
                    InventoryData.marketplace,
                    InventoryData.quantity,
                    InventoryData.fulfillable_quantity,
                    InventoryData.reserved_quantity,
                    InventoryData.supplier_info,
                    InventoryData.last_restock_date,
                    InventoryData.unit_cost,
                    sales_rate_subquery.c.daily_sales_rate
                )
                .outerjoin(
                    sales_rate_subquery,
                    and_(
                        InventoryData.asin == sales_rate_subquery.c.asin,
                        InventoryData.store_id == sales_rate_subquery.c.store_id
                    )
                )
            )
            
            # 添加用户过滤
            if self.user_id:
                query = query.join(AmazonStore).filter(AmazonStore.user_id == self.user_id)
            
            # 添加基本过滤条件
            conditions = []
            
            if store_id:
                conditions.append(InventoryData.store_id == store_id)
            
            if marketplace:
                conditions.append(InventoryData.marketplace == marketplace)
            
            if include_asin:
                conditions.append(InventoryData.asin.in_(include_asin))
            
            if exclude_asin:
                conditions.append(InventoryData.asin.notin_(exclude_asin))
            
            if conditions:
                query = query.filter(and_(*conditions))
            
            # 执行查询
            results = query.all()
            
            # 处理结果
            inventory_items = []
            for row in results:
                # 计算库存天数
                daily_sales = float(row.daily_sales_rate or 0)
                days_of_supply = 0
                if daily_sales > 0:
                    days_of_supply = round(float(row.fulfillable_quantity or 0) / daily_sales, 2)
                
                # 计算库存价值
                inventory_value = float(row.fulfillable_quantity or 0) * float(row.unit_cost or 0)
                
                # 确定库存状态和预警级别
                status, warning_level, status_message = self._determine_inventory_status(
                    days_of_supply, 
                    row.fulfillable_quantity or 0,
                    daily_sales
                )
                
                # 只有在库存天数范围内的才加入结果
                if min_days_of_supply <= days_of_supply <= max_days_of_supply:
                    inventory_items.append({
                        'asin': row.asin,
                        'sku': row.sku,
                        'product_name': row.product_name,
                        'store_id': row.store_id,
                        'marketplace': row.marketplace,
                        'total_quantity': row.quantity or 0,
                        'fulfillable_quantity': row.fulfillable_quantity or 0,
                        'reserved_quantity': row.reserved_quantity or 0,
                        'supplier_info': row.supplier_info,
                        'last_restock_date': str(row.last_restock_date) if row.last_restock_date else None,
                        'unit_cost': float(row.unit_cost or 0),
                        'inventory_value': inventory_value,
                        'daily_sales_rate': daily_sales,
                        'days_of_supply': days_of_supply,
                        'status': status,
                        'warning_level': warning_level,
                        'status_message': status_message
                    })
            
            # 排序
            if sort_by in ['inventory_level', 'days_of_supply', 'sales_rate']:
                key_mapping = {
                    'inventory_level': 'fulfillable_quantity',
                    'sales_rate': 'daily_sales_rate'
                }
                sort_key = key_mapping.get(sort_by, sort_by)
                
                # 处理空值，确保排序正确
                inventory_items.sort(
                    key=lambda x: (x[sort_key] is None, x[sort_key]),
                    reverse=(sort_order == 'desc')
                )
            
            # 计算汇总信息
            summary = self._calculate_inventory_summary(inventory_items)
            
            logger.info(f'获取库存健康数据成功，返回 {len(inventory_items)} 个SKU')
            
            return {
                'data': inventory_items,
                'summary': summary,
                'filters': filters
            }
            
        except Exception as e:
            logger.error(f'获取库存健康数据失败: {str(e)}')
            raise
    
    def _determine_inventory_status(self, days_of_supply, fulfillable_quantity, daily_sales):
        """
        确定库存状态和预警级别
        
        Args:
            days_of_supply: 库存天数
            fulfillable_quantity: 可销售数量
            daily_sales: 日销售速率
        
        Returns:
            tuple: (status, warning_level, status_message)
        """
        # 无库存或即将缺货
        if fulfillable_quantity == 0:
            return 'out_of_stock', 'danger', '无库存'
        elif days_of_supply <= 3:
            return 'critical_shortage', 'danger', '严重缺货风险（库存<3天）'
        elif days_of_supply <= 7:
            return 'shortage', 'warning', '库存紧张（库存3-7天）'
        
        # 库存适中
        elif 7 < days_of_supply <= 30:
            return 'optimal', 'success', '库存健康'
        
        # 库存过多
        elif days_of_supply > 90:
            return 'excess', 'danger', f'库存过剩（库存{days_of_supply:.0f}天）'
        elif days_of_supply > 60:
            return 'high', 'warning', f'库存偏高（库存{days_of_supply:.0f}天）'
        
        # 其他情况
        return 'normal', 'info', f'库存正常（库存{days_of_supply:.0f}天）'
    
    def _calculate_inventory_summary(self, inventory_items):
        """
        计算库存汇总信息
        """
        # 初始化统计变量
        total_items = len(inventory_items)
        total_quantity = sum(item['total_quantity'] for item in inventory_items)
        total_fulfillable = sum(item['fulfillable_quantity'] for item in inventory_items)
        total_inventory_value = sum(item['inventory_value'] for item in inventory_items)
        
        # 按状态统计
        status_counts = {
            'out_of_stock': 0,
            'critical_shortage': 0,
            'shortage': 0,
            'optimal': 0,
            'normal': 0,
            'high': 0,
            'excess': 0
        }
        
        warning_counts = {
            'danger': 0,
            'warning': 0,
            'success': 0,
            'info': 0
        }
        
        # 平均库存天数
        valid_days_of_supply = [item['days_of_supply'] for item in inventory_items 
                               if item['daily_sales_rate'] > 0 and item['days_of_supply'] > 0]
        avg_days_of_supply = np.mean(valid_days_of_supply) if valid_days_of_supply else 0
        
        # 统计状态分布
        for item in inventory_items:
            status_counts[item['status']] = status_counts.get(item['status'], 0) + 1
            warning_counts[item['warning_level']] = warning_counts.get(item['warning_level'], 0) + 1
        
        # 计算风险产品数量
        risky_products = status_counts['out_of_stock'] + status_counts['critical_shortage'] + status_counts['shortage']
        excess_products = status_counts['high'] + status_counts['excess']
        healthy_products = status_counts['optimal'] + status_counts['normal']
        
        return {
            'total_items': total_items,
            'total_quantity': total_quantity,
            'total_fulfillable_quantity': total_fulfillable,
            'total_inventory_value': total_inventory_value,
            'avg_days_of_supply': round(avg_days_of_supply, 2),
            'status_distribution': status_counts,
            'warning_distribution': warning_counts,
            'risky_products_count': risky_products,
            'excess_products_count': excess_products,
            'healthy_products_count': healthy_products,
            'risky_percentage': (risky_products / total_items * 100) if total_items > 0 else 0,
            'excess_percentage': (excess_products / total_items * 100) if total_items > 0 else 0,
            'healthy_percentage': (healthy_products / total_items * 100) if total_items > 0 else 0
        }
    
    def get_low_stock_items(self, days_threshold=7, filters=None):
        """
        获取低库存商品列表
        
        Args:
            days_threshold: 库存天数阈值
            filters: 其他筛选条件
        """
        try:
            # 设置筛选条件
            if filters is None:
                filters = {}
            
            filters['max_days_of_supply'] = days_threshold
            filters['sort_by'] = 'days_of_supply'
            filters['sort_order'] = 'asc'
            
            # 获取库存数据
            result = self.get_inventory_health_data(filters)
            
            # 过滤出库存紧张或缺货的商品
            low_stock_items = [item for item in result['data'] 
                              if item['warning_level'] in ['danger', 'warning']]
            
            logger.info(f'获取低库存商品成功，返回 {len(low_stock_items)} 个商品')
            
            return {
                'data': low_stock_items,
                'count': len(low_stock_items),
                'threshold_days': days_threshold
            }
            
        except Exception as e:
            logger.error(f'获取低库存商品失败: {str(e)}')
            raise
    
    def get_excess_stock_items(self, days_threshold=60, filters=None):
        """
        获取过剩库存商品列表
        
        Args:
            days_threshold: 库存天数阈值
            filters: 其他筛选条件
        """
        try:
            # 设置筛选条件
            if filters is None:
                filters = {}
            
            filters['min_days_of_supply'] = days_threshold
            filters['sort_by'] = 'days_of_supply'
            filters['sort_order'] = 'desc'
            
            # 获取库存数据
            result = self.get_inventory_health_data(filters)
            
            # 过滤出库存过剩的商品
            excess_stock_items = [item for item in result['data'] 
                                 if item['warning_level'] in ['danger', 'warning']]
            
            logger.info(f'获取过剩库存商品成功，返回 {len(excess_stock_items)} 个商品')
            
            return {
                'data': excess_stock_items,
                'count': len(excess_stock_items),
                'threshold_days': days_threshold,
                'total_excess_value': sum(item['inventory_value'] for item in excess_stock_items)
            }
            
        except Exception as e:
            logger.error(f'获取过剩库存商品失败: {str(e)}')
            raise
    
    def get_inventory_turnover_rate(self, period_days=30, filters=None):
        """
        计算库存周转率
        
        Args:
            period_days: 计算周期天数
            filters: 筛选条件
        """
        try:
            # 获取时间范围
            end_date = datetime.datetime.now().date()
            start_date = end_date - datetime.timedelta(days=period_days)
            
            # 构建查询获取期间销售成本
            query = (
                self.db_session.query(
                    AmazonIntegratedData.asin,
                    AmazonIntegratedData.store_id,
                    func.sum(AmazonIntegratedData.order_count).label('total_orders'),
                    func.avg(AmazonIntegratedData.cost).label('avg_cost')
                )
                .filter(
                    and_(
                        AmazonIntegratedData.date >= start_date,
                        AmazonIntegratedData.date <= end_date
                    )
                )
                .group_by(AmazonIntegratedData.asin, AmazonIntegratedData.store_id)
            )
            
            # 添加用户过滤
            if self.user_id:
                query = query.join(AmazonStore).filter(AmazonStore.user_id == self.user_id)
            
            # 添加额外过滤条件
            if filters:
                if 'store_id' in filters:
                    query = query.filter(AmazonIntegratedData.store_id == filters['store_id'])
                if 'marketplace' in filters:
                    query = query.filter(AmazonIntegratedData.marketplace == filters['marketplace'])
            
            # 执行查询
            sales_results = query.all()
            
            # 计算期间销售成本
            sales_cost_by_asin = {}
            for row in sales_results:
                key = (row.asin, row.store_id)
                sales_cost_by_asin[key] = float(row.total_orders or 0) * float(row.avg_cost or 0)
            
            # 获取当前库存成本
            inventory_query = (
                self.db_session.query(
                    InventoryData.asin,
                    InventoryData.store_id,
                    InventoryData.fulfillable_quantity,
                    InventoryData.unit_cost
                )
            )
            
            # 添加用户过滤
            if self.user_id:
                inventory_query = inventory_query.join(AmazonStore).filter(AmazonStore.user_id == self.user_id)
            
            # 执行查询
            inventory_results = inventory_query.all()
            
            # 计算平均库存成本
            total_average_inventory = 0
            for row in inventory_results:
                key = (row.asin, row.store_id)
                # 假设期初库存为0，计算平均库存成本
                current_inventory_cost = float(row.fulfillable_quantity or 0) * float(row.unit_cost or 0)
                sales_cost = sales_cost_by_asin.get(key, 0)
                
                # 简单平均库存成本 = (期初库存成本 + 期末库存成本) / 2
                # 由于没有期初数据，这里使用期末库存成本作为近似
                average_inventory_cost = current_inventory_cost
                total_average_inventory += average_inventory_cost
            
            # 计算总销售成本
            total_sales_cost = sum(sales_cost_by_asin.values())
            
            # 计算库存周转率
            turnover_rate = 0
            if total_average_inventory > 0:
                turnover_rate = total_sales_cost / total_average_inventory
            
            # 计算平均库存周转天数
            average_turnover_days = 0
            if turnover_rate > 0:
                average_turnover_days = period_days / turnover_rate
            
            logger.info(f'计算库存周转率成功，期间：{period_days}天，周转率：{turnover_rate:.2f}')
            
            return {
                'period_days': period_days,
                'total_sales_cost': total_sales_cost,
                'average_inventory_cost': total_average_inventory,
                'turnover_rate': round(turnover_rate, 2),
                'turnover_days': round(average_turnover_days, 2),
                'date_range': f'{start_date} 至 {end_date}'
            }
            
        except Exception as e:
            logger.error(f'计算库存周转率失败: {str(e)}')
            raise
    
    def get_inventory_aging_report(self, filters=None):
        """
        获取库存老化报告
        """
        try:
            # 默认筛选条件
            if filters is None:
                filters = {}
            
            # 设置默认值
            store_id = filters.get('store_id')
            marketplace = filters.get('marketplace')
            
            # 获取库存数据
            result = self.get_inventory_health_data(filters)
            
            # 按库存天数分组
            aging_groups = {
                '0-30天': {'items': [], 'quantity': 0, 'value': 0},
                '31-60天': {'items': [], 'quantity': 0, 'value': 0},
                '61-90天': {'items': [], 'quantity': 0, 'value': 0},
                '91-180天': {'items': [], 'quantity': 0, 'value': 0},
                '180天以上': {'items': [], 'quantity': 0, 'value': 0}
            }
            
            for item in result['data']:
                days = item['days_of_supply']
                
                if days <= 30:
                    group_key = '0-30天'
                elif days <= 60:
                    group_key = '31-60天'
                elif days <= 90:
                    group_key = '61-90天'
                elif days <= 180:
                    group_key = '91-180天'
                else:
                    group_key = '180天以上'
                
                aging_groups[group_key]['items'].append(item)
                aging_groups[group_key]['quantity'] += item['fulfillable_quantity']
                aging_groups[group_key]['value'] += item['inventory_value']
            
            # 转换为列表格式
            aging_data = []
            for group_name, group_data in aging_groups.items():
                aging_data.append({
                    'aging_group': group_name,
                    'item_count': len(group_data['items']),
                    'quantity': group_data['quantity'],
                    'value': group_data['value'],
                    'items': group_data['items']
                })
            
            logger.info(f'获取库存老化报告成功')
            
            return {
                'aging_data': aging_data,
                'total_items': sum(group['item_count'] for group in aging_data),
                'total_quantity': sum(group['quantity'] for group in aging_data),
                'total_value': sum(group['value'] for group in aging_data)
            }
            
        except Exception as e:
            logger.error(f'获取库存老化报告失败: {str(e)}')
            raise
    
    def export_to_excel(self, filters=None, filepath=None):
        """
        导出库存健康报表到Excel
        """
        try:
            # 获取库存健康数据
            health_data = self.get_inventory_health_data(filters)
            
            # 获取低库存和过剩库存数据
            low_stock_data = self.get_low_stock_items(filters=filters)
            excess_stock_data = self.get_excess_stock_items(filters=filters)
            
            # 获取库存周转率数据
            turnover_data = self.get_inventory_turnover_rate(filters=filters)
            
            # 获取库存老化数据
            aging_data = self.get_inventory_aging_report(filters=filters)
            
            # 如果没有提供文件路径，生成一个默认路径
            if not filepath:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f'../data/reports/inventory_health_report_{timestamp}.xlsx'
            
            # 创建Excel写入器
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                # 1. 库存健康总览
                df_summary = pd.DataFrame([{
                    '总SKU数': health_data['summary']['total_items'],
                    '总库存数量': health_data['summary']['total_quantity'],
                    '可销售库存数量': health_data['summary']['total_fulfillable_quantity'],
                    '总库存价值': health_data['summary']['total_inventory_value'],
                    '平均库存天数': health_data['summary']['avg_days_of_supply'],
                    '库存周转率': turnover_data['turnover_rate'],
                    '库存周转天数': turnover_data['turnover_days'],
                    '风险商品数': health_data['summary']['risky_products_count'],
                    '过剩库存数': health_data['summary']['excess_products_count'],
                    '健康库存数': health_data['summary']['healthy_products_count']
                }])
                df_summary.to_excel(writer, sheet_name='库存总览', index=False)
                
                # 2. 库存明细
                df_inventory = pd.DataFrame(health_data['data'])
                if not df_inventory.empty:
                    # 只保留必要的列
                    columns_to_keep = [
                        'asin', 'sku', 'product_name', 'marketplace', 
                        'fulfillable_quantity', 'days_of_supply', 
                        'inventory_value', 'status', 'status_message'
                    ]
                    df_inventory = df_inventory[columns_to_keep]
                    df_inventory.to_excel(writer, sheet_name='库存明细', index=False)
                
                # 3. 低库存预警
                df_low_stock = pd.DataFrame(low_stock_data['data'])
                if not df_low_stock.empty:
                    columns_to_keep = [
                        'asin', 'sku', 'product_name', 'marketplace', 
                        'fulfillable_quantity', 'days_of_supply', 
                        'daily_sales_rate', 'status_message'
                    ]
                    df_low_stock = df_low_stock[columns_to_keep]
                    df_low_stock.to_excel(writer, sheet_name='低库存预警', index=False)
                
                # 4. 过剩库存
                df_excess_stock = pd.DataFrame(excess_stock_data['data'])
                if not df_excess_stock.empty:
                    columns_to_keep = [
                        'asin', 'sku', 'product_name', 'marketplace', 
                        'fulfillable_quantity', 'days_of_supply', 
                        'inventory_value', 'status_message'
                    ]
                    df_excess_stock = df_excess_stock[columns_to_keep]
                    df_excess_stock.to_excel(writer, sheet_name='过剩库存', index=False)
                
                # 5. 库存老化分析
                df_aging = pd.DataFrame([
                    {
                        '库存周期': group['aging_group'],
                        'SKU数量': group['item_count'],
                        '库存数量': group['quantity'],
                        '库存价值': group['value']
                    } for group in aging_data['aging_data']
                ])
                df_aging.to_excel(writer, sheet_name='库存老化分析', index=False)
                
                # 获取xlsxwriter对象
                workbook = writer.book
                
                # 设置样式
                currency_format = workbook.add_format({'num_format': '¥#,##0.00'})
                
                # 格式化库存总览表
                worksheet = writer.sheets['库存总览']
                worksheet.set_column('D:D', 15, currency_format)
                
                # 格式化库存明细表
                if '库存明细' in writer.sheets:
                    worksheet = writer.sheets['库存明细']
                    worksheet.set_column('A:A', 15)  # ASIN
                    worksheet.set_column('B:B', 20)  # SKU
                    worksheet.set_column('C:C', 40)  # 产品名称
                    worksheet.set_column('D:D', 15)  # 市场
                    worksheet.set_column('E:F', 15)  # 数量和天数
                    worksheet.set_column('G:G', 15, currency_format)  # 库存价值
                    worksheet.set_column('H:I', 20)  # 状态
                
                # 格式化低库存预警表
                if '低库存预警' in writer.sheets:
                    worksheet = writer.sheets['低库存预警']
                    worksheet.set_column('A:A', 15)
                    worksheet.set_column('B:B', 20)
                    worksheet.set_column('C:C', 40)
                    worksheet.set_column('D:D', 15)
                    worksheet.set_column('E:G', 15)
                    worksheet.set_column('H:H', 25)
                
                # 格式化过剩库存表
                if '过剩库存' in writer.sheets:
                    worksheet = writer.sheets['过剩库存']
                    worksheet.set_column('A:A', 15)
                    worksheet.set_column('B:B', 20)
                    worksheet.set_column('C:C', 40)
                    worksheet.set_column('D:D', 15)
                    worksheet.set_column('E:F', 15)
                    worksheet.set_column('G:G', 15, currency_format)
                    worksheet.set_column('H:H', 25)
                
                # 格式化库存老化分析表
                if '库存老化分析' in writer.sheets:
                    worksheet = writer.sheets['库存老化分析']
                    worksheet.set_column('A:A', 15)
                    worksheet.set_column('B:C', 15)
                    worksheet.set_column('D:D', 15, currency_format)
            
            logger.info(f'库存健康报表导出到Excel成功: {filepath}')
            return filepath
            
        except Exception as e:
            logger.error(f'库存健康报表导出到Excel失败: {str(e)}')
            raise
    
    def update_inventory_alert_settings(self, asin, store_id, alert_settings):
        """
        更新特定ASIN的库存预警设置
        
        Args:
            asin: ASIN值
            store_id: 店铺ID
            alert_settings: 预警设置字典，包含：
                - low_stock_threshold: 低库存阈值
                - high_stock_threshold: 高库存阈值
                - alert_email: 告警邮箱
                - alert_wechat: 是否微信告警
        """
        try:
            # 查找或创建库存预警设置
            from models import InventoryAlertSetting
            
            setting = self.db_session.query(InventoryAlertSetting).filter(
                and_(
                    InventoryAlertSetting.asin == asin,
                    InventoryAlertSetting.store_id == store_id
                )
            ).first()
            
            if setting:
                # 更新现有设置
                setting.low_stock_threshold = alert_settings.get('low_stock_threshold')
                setting.high_stock_threshold = alert_settings.get('high_stock_threshold')
                setting.alert_email = alert_settings.get('alert_email')
                setting.alert_wechat = alert_settings.get('alert_wechat', False)
                setting.updated_at = datetime.datetime.now()
            else:
                # 创建新设置
                setting = InventoryAlertSetting(
                    asin=asin,
                    store_id=store_id,
                    low_stock_threshold=alert_settings.get('low_stock_threshold'),
                    high_stock_threshold=alert_settings.get('high_stock_threshold'),
                    alert_email=alert_settings.get('alert_email'),
                    alert_wechat=alert_settings.get('alert_wechat', False),
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now()
                )
                self.db_session.add(setting)
            
            self.db_session.commit()
            
            logger.info(f'更新库存预警设置成功，ASIN: {asin}, 店铺ID: {store_id}')
            return {
                'status': 'success',
                'message': '库存预警设置更新成功',
                'data': {
                    'asin': asin,
                    'store_id': store_id,
                    'settings': alert_settings
                }
            }
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f'更新库存预警设置失败: {str(e)}')
            raise