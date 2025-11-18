import logging
import pandas as pd
import numpy as np
import datetime
from models import AmazonIntegratedData, AmazonStore, User
from sqlalchemy import and_, func
from scipy import stats

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_sales_trend')

class AmazonSalesTrendReport:
    def __init__(self, db_session, user_id=None):
        self.db_session = db_session
        self.user_id = user_id
        logger.info(f'初始化销量趋势报表模块，用户ID: {user_id}')
    
    def get_sales_trend_data(self, filters=None):
        """
        获取销量趋势数据
        
        Args:
            filters: 筛选条件字典，包含：
                - start_date: 开始日期
                - end_date: 结束日期
                - store_id: 店铺ID
                - marketplace: 市场
                - asin: ASIN值（可选，指定后只显示该ASIN的趋势）
                - group_by: 分组方式（day, week, month）
                - metrics: 指标列表（orders, sales, profit）
                - anomaly_detection: 是否启用异常检测
        """
        try:
            # 默认筛选条件
            if filters is None:
                filters = {}
            
            # 设置默认值
            start_date = filters.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%Y-%m-%d'))
            end_date = filters.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            store_id = filters.get('store_id')
            marketplace = filters.get('marketplace')
            asin = filters.get('asin')
            group_by = filters.get('group_by', 'day')
            metrics = filters.get('metrics', ['orders', 'sales', 'profit'])
            anomaly_detection = filters.get('anomaly_detection', True)
            
            # 构建查询
            query = self.db_session.query(
                AmazonIntegratedData.date,
                func.sum(AmazonIntegratedData.order_count).label('total_orders'),
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
                func.sum(AmazonIntegratedData.profit).label('total_profit')
            )
            
            # 添加用户过滤
            if self.user_id:
                query = query.join(AmazonStore).filter(AmazonStore.user_id == self.user_id)
            
            # 添加基本过滤条件
            conditions = [
                AmazonIntegratedData.date >= start_date,
                AmazonIntegratedData.date <= end_date
            ]
            
            if store_id:
                conditions.append(AmazonIntegratedData.store_id == store_id)
            
            if marketplace:
                conditions.append(AmazonIntegratedData.marketplace == marketplace)
            
            if asin:
                conditions.append(AmazonIntegratedData.asin == asin)
            
            query = query.filter(and_(*conditions))
            
            # 分组和排序
            query = query.group_by(AmazonIntegratedData.date)
            query = query.order_by(AmazonIntegratedData.date)
            
            # 执行查询
            result = query.all()
            
            # 转换为DataFrame
            df = pd.DataFrame([{
                'date': row.date,
                'orders': row.total_orders or 0,
                'sales': float(row.total_sales or 0),
                'profit': float(row.total_profit or 0)
            } for row in result])
            
            # 如果没有数据，返回空结果
            if df.empty:
                logger.info('未找到销量趋势数据')
                return {
                    'data': [],
                    'summary': None,
                    'anomalies': []
                }
            
            # 按指定的分组方式聚合数据
            if group_by != 'day':
                df['date'] = pd.to_datetime(df['date'])
                if group_by == 'week':
                    df = df.groupby([pd.Grouper(key='date', freq='W-MON')]).agg({
                        'orders': 'sum',
                        'sales': 'sum',
                        'profit': 'sum'
                    }).reset_index()
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                elif group_by == 'month':
                    df = df.groupby([pd.Grouper(key='date', freq='M')]).agg({
                        'orders': 'sum',
                        'sales': 'sum',
                        'profit': 'sum'
                    }).reset_index()
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            else:
                df['date'] = df['date'].astype(str)
            
            # 计算汇总统计
            summary = {
                'total_orders': int(df['orders'].sum()),
                'total_sales': float(df['sales'].sum()),
                'total_profit': float(df['profit'].sum()),
                'avg_daily_orders': float(df['orders'].mean()),
                'avg_daily_sales': float(df['sales'].mean()),
                'avg_daily_profit': float(df['profit'].mean()),
                'date_range': f'{start_date} 至 {end_date}'
            }
            
            # 异常检测
            anomalies = []
            if anomaly_detection:
                for metric in metrics:
                    if metric in df.columns:
                        metric_anomalies = self._detect_anomalies(df['date'], df[metric], metric)
                        anomalies.extend(metric_anomalies)
            
            # 准备返回数据
            data = []
            for _, row in df.iterrows():
                record = {
                    'date': row['date'],
                    'orders': int(row['orders']),
                    'sales': float(row['sales']),
                    'profit': float(row['profit'])
                }
                # 添加日环比
                if len(data) > 0:
                    prev_row = data[-1]
                    record['orders_growth'] = ((row['orders'] - prev_row['orders']) / prev_row['orders'] * 100) if prev_row['orders'] > 0 else 0
                    record['sales_growth'] = ((row['sales'] - prev_row['sales']) / prev_row['sales'] * 100) if prev_row['sales'] > 0 else 0
                    record['profit_growth'] = ((row['profit'] - prev_row['profit']) / prev_row['profit'] * 100) if prev_row['profit'] > 0 else 0
                else:
                    record['orders_growth'] = 0
                    record['sales_growth'] = 0
                    record['profit_growth'] = 0
                data.append(record)
            
            logger.info(f'获取销量趋势数据成功，返回 {len(data)} 条记录')
            
            return {
                'data': data,
                'summary': summary,
                'anomalies': anomalies,
                'filters': filters
            }
            
        except Exception as e:
            logger.error(f'获取销量趋势数据失败: {str(e)}')
            raise
    
    def _detect_anomalies(self, dates, values, metric_name, threshold=2.0):
        """
        检测数据异常值
        使用Z-score方法检测异常
        """
        try:
            anomalies = []
            
            # 计算Z-score
            z_scores = np.abs(stats.zscore(values))
            
            # 识别异常值
            anomaly_indices = np.where(z_scores > threshold)[0]
            
            for idx in anomaly_indices:
                anomaly_type = 'high' if values.iloc[idx] > values.median() else 'low'
                anomalies.append({
                    'date': dates.iloc[idx],
                    'metric': metric_name,
                    'value': float(values.iloc[idx]),
                    'type': anomaly_type,
                    'z_score': float(z_scores[idx]),
                    'message': self._get_anomaly_message(metric_name, anomaly_type)
                })
            
            return anomalies
            
        except Exception as e:
            logger.warning(f'异常检测失败: {str(e)}')
            return []
    
    def _get_anomaly_message(self, metric, anomaly_type):
        """
        获取异常提示信息
        """
        messages = {
            'orders': {
                'high': '订单量异常高，可能是促销活动或流量突增',
                'low': '订单量异常低，需要关注店铺表现'
            },
            'sales': {
                'high': '销售额异常高，表现优异',
                'low': '销售额异常低，需要分析原因'
            },
            'profit': {
                'high': '利润异常高，运营效果好',
                'low': '利润异常低，需要检查成本或定价'
            }
        }
        
        return messages.get(metric, {}).get(anomaly_type, '数据异常')
    
    def get_product_comparison(self, filters=None, top_n=5):
        """
        获取产品销售对比数据
        
        Args:
            filters: 筛选条件
            top_n: 返回销量前N的产品
        """
        try:
            # 默认筛选条件
            if filters is None:
                filters = {}
            
            # 设置默认值
            start_date = filters.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = filters.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            store_id = filters.get('store_id')
            marketplace = filters.get('marketplace')
            
            # 构建查询
            query = self.db_session.query(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.sku,
                AmazonIntegratedData.product_name,
                func.sum(AmazonIntegratedData.order_count).label('total_orders'),
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
                func.sum(AmazonIntegratedData.profit).label('total_profit'),
                func.avg(AmazonIntegratedData.profit_rate).label('avg_profit_rate')
            )
            
            # 添加用户过滤
            if self.user_id:
                query = query.join(AmazonStore).filter(AmazonStore.user_id == self.user_id)
            
            # 添加过滤条件
            conditions = [
                AmazonIntegratedData.date >= start_date,
                AmazonIntegratedData.date <= end_date
            ]
            
            if store_id:
                conditions.append(AmazonIntegratedData.store_id == store_id)
            
            if marketplace:
                conditions.append(AmazonIntegratedData.marketplace == marketplace)
            
            query = query.filter(and_(*conditions))
            
            # 分组和排序
            query = query.group_by(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.sku,
                AmazonIntegratedData.product_name
            )
            query = query.order_by(func.sum(AmazonIntegratedData.sales_amount).desc())
            
            # 限制返回数量
            result = query.limit(top_n).all()
            
            # 转换为列表
            products = []
            for row in result:
                products.append({
                    'asin': row.asin,
                    'sku': row.sku,
                    'product_name': row.product_name,
                    'total_orders': row.total_orders or 0,
                    'total_sales': float(row.total_sales or 0),
                    'total_profit': float(row.total_profit or 0),
                    'avg_profit_rate': float(row.avg_profit_rate or 0)
                })
            
            logger.info(f'获取产品销售对比数据成功，返回 {len(products)} 个产品')
            return products
            
        except Exception as e:
            logger.error(f'获取产品销售对比数据失败: {str(e)}')
            raise
    
    def get_marketplace_comparison(self, filters=None):
        """
        获取不同市场的销售对比
        """
        try:
            # 默认筛选条件
            if filters is None:
                filters = {}
            
            # 设置默认值
            start_date = filters.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = filters.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            store_id = filters.get('store_id')
            
            # 构建查询
            query = self.db_session.query(
                AmazonIntegratedData.marketplace,
                func.sum(AmazonIntegratedData.order_count).label('total_orders'),
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
                func.sum(AmazonIntegratedData.profit).label('total_profit')
            )
            
            # 添加用户过滤
            if self.user_id:
                query = query.join(AmazonStore).filter(AmazonStore.user_id == self.user_id)
            
            # 添加过滤条件
            conditions = [
                AmazonIntegratedData.date >= start_date,
                AmazonIntegratedData.date <= end_date
            ]
            
            if store_id:
                conditions.append(AmazonIntegratedData.store_id == store_id)
            
            query = query.filter(and_(*conditions))
            
            # 分组和排序
            query = query.group_by(AmazonIntegratedData.marketplace)
            query = query.order_by(func.sum(AmazonIntegratedData.sales_amount).desc())
            
            # 执行查询
            result = query.all()
            
            # 转换为列表
            marketplaces = []
            total_sales = sum(row.total_sales or 0 for row in result)
            total_orders = sum(row.total_orders or 0 for row in result)
            total_profit = sum(row.total_profit or 0 for row in result)
            
            for row in result:
                marketplaces.append({
                    'marketplace': row.marketplace,
                    'total_orders': row.total_orders or 0,
                    'total_sales': float(row.total_sales or 0),
                    'total_profit': float(row.total_profit or 0),
                    'sales_percentage': float((row.total_sales or 0) / total_sales * 100) if total_sales > 0 else 0,
                    'orders_percentage': float((row.total_orders or 0) / total_orders * 100) if total_orders > 0 else 0,
                    'profit_percentage': float((row.total_profit or 0) / total_profit * 100) if total_profit > 0 else 0
                })
            
            logger.info(f'获取市场销售对比数据成功，返回 {len(marketplaces)} 个市场')
            return marketplaces
            
        except Exception as e:
            logger.error(f'获取市场销售对比数据失败: {str(e)}')
            raise
    
    def export_to_excel(self, filters=None, filepath=None):
        """
        导出销量趋势报表到Excel
        """
        try:
            # 获取销量趋势数据
            trend_data = self.get_sales_trend_data(filters)
            
            # 获取产品对比数据
            product_data = self.get_product_comparison(filters, top_n=20)
            
            # 获取市场对比数据
            marketplace_data = self.get_marketplace_comparison(filters)
            
            # 如果没有提供文件路径，生成一个默认路径
            if not filepath:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f'../data/reports/sales_trend_report_{timestamp}.xlsx'
            
            # 导出到Excel
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                # 销量趋势表
                df_trend = pd.DataFrame(trend_data['data'])
                df_trend.to_excel(writer, sheet_name='销量趋势', index=False)
                
                # 产品对比表
                df_products = pd.DataFrame(product_data)
                df_products.to_excel(writer, sheet_name='产品对比', index=False)
                
                # 市场对比表
                df_marketplaces = pd.DataFrame(marketplace_data)
                df_marketplaces.to_excel(writer, sheet_name='市场对比', index=False)
                
                # 获取xlsxwriter对象
                workbook = writer.book
                
                # 设置样式
                currency_format = workbook.add_format({'num_format': '¥#,##0.00'})
                percent_format = workbook.add_format({'num_format': '0.00%'})
                
                # 格式化销量趋势表
                worksheet = writer.sheets['销量趋势']
                worksheet.set_column('A:A', 15)  # 日期
                worksheet.set_column('B:B', 10)  # 订单数
                worksheet.set_column('C:M', 12, currency_format)  # 金额列
                
                # 格式化产品对比表
                worksheet = writer.sheets['产品对比']
                worksheet.set_column('A:C', 20)  # ASIN, SKU, 产品名称
                worksheet.set_column('D:D', 10)  # 订单数
                worksheet.set_column('E:G', 12, currency_format)  # 金额列
                worksheet.set_column('H:H', 12, percent_format)  # 利润率
                
                # 格式化市场对比表
                worksheet = writer.sheets['市场对比']
                worksheet.set_column('A:A', 15)  # 市场
                worksheet.set_column('B:B', 10)  # 订单数
                worksheet.set_column('C:E', 12, currency_format)  # 金额列
                worksheet.set_column('F:H', 12, percent_format)  # 百分比列
            
            logger.info(f'销量趋势报表导出到Excel成功: {filepath}')
            return filepath
            
        except Exception as e:
            logger.error(f'销量趋势报表导出到Excel失败: {str(e)}')
            raise
    
    def get_forecast(self, days=7, filters=None):
        """
        预测未来几天的销量趋势
        使用简单移动平均法进行预测
        """
        try:
            # 获取历史数据
            if filters is None:
                filters = {}
            
            # 设置历史数据范围为最近60天
            filters['start_date'] = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y-%m-%d')
            filters['end_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
            filters['group_by'] = 'day'
            
            trend_data = self.get_sales_trend_data(filters)
            
            # 如果没有足够的数据，返回空预测
            if len(trend_data['data']) < 7:
                logger.warning('历史数据不足，无法进行预测')
                return []
            
            # 转换为DataFrame进行预测
            df = pd.DataFrame(trend_data['data'])
            df['date'] = pd.to_datetime(df['date'])
            
            # 计算7天移动平均
            window_size = 7
            df['orders_ma7'] = df['orders'].rolling(window=window_size).mean()
            df['sales_ma7'] = df['sales'].rolling(window=window_size).mean()
            df['profit_ma7'] = df['profit'].rolling(window=window_size).mean()
            
            # 生成未来日期
            last_date = df['date'].max()
            future_dates = [last_date + datetime.timedelta(days=i+1) for i in range(days)]
            
            # 进行预测（使用最后一个移动平均值）
            forecast = []
            last_orders_ma7 = df['orders_ma7'].iloc[-1]
            last_sales_ma7 = df['sales_ma7'].iloc[-1]
            last_profit_ma7 = df['profit_ma7'].iloc[-1]
            
            for date in future_dates:
                forecast.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'orders': int(round(last_orders_ma7)),
                    'sales': float(last_sales_ma7),
                    'profit': float(last_profit_ma7),
                    'is_forecast': True
                })
            
            logger.info(f'生成未来 {days} 天的销量预测成功')
            return forecast
            
        except Exception as e:
            logger.error(f'生成销量预测失败: {str(e)}')
            raise