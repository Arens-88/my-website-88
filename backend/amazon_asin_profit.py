import logging
import pandas as pd
import datetime
import hashlib
from models import AmazonIntegratedData, AmazonStore, User
from sqlalchemy import and_, or_, func

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_asin_profit')

class SimpleCache:
    """简单的内存缓存实现"""
    def __init__(self, timeout=300):  # 默认5分钟缓存
        self.cache = {}
        self.timeout = timeout
    
    def get(self, key):
        """获取缓存数据，如果过期则返回None"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.datetime.now().timestamp() - timestamp < self.timeout:
                return value
            # 过期缓存自动清理
            del self.cache[key]
        return None
    
    def set(self, key, value):
        """设置缓存数据"""
        self.cache[key] = (value, datetime.datetime.now().timestamp())
    
    def clear(self):
        """清空缓存"""
        self.cache = {}

# 创建全局缓存实例
_asin_report_cache = SimpleCache()

class AmazonASINProfitReport:
    def __init__(self, db_session, user_id=None):
        self.db_session = db_session
        self.user_id = user_id
        self.cache = _asin_report_cache
        logger.info(f'初始化ASIN利润报表模块，用户ID: {user_id}')
    
    def _generate_cache_key(self, filters):
        """生成缓存键"""
        # 创建一个可排序的键值对列表，确保相同参数生成相同的键
        sorted_filters = sorted((k, v) for k, v in filters.items() if v is not None)
        # 添加用户ID以确保缓存隔离
        cache_data = f"{self.user_id}:{str(sorted_filters)}"
        # 使用哈希生成缓存键
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def get_asin_profit_data(self, filters=None):
        """
        获取ASIN利润数据
        
        Args:
            filters: 筛选条件字典，包含：
                - start_date: 开始日期
                - end_date: 结束日期
                - store_id: 店铺ID
                - asin: ASIN值
                - marketplace: 市场
                - min_profit: 最小利润
                - max_profit: 最大利润
                - sort_by: 排序字段
                - sort_order: 排序方向
                - page: 页码
                - page_size: 每页大小
        """
        try:
            # 默认筛选条件
            if filters is None:
                filters = {}
            
            # 设置默认值
            start_date = filters.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = filters.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            store_id = filters.get('store_id')
            asin = filters.get('asin')
            marketplace = filters.get('marketplace')
            min_profit = filters.get('min_profit')
            max_profit = filters.get('max_profit')
            sort_by = filters.get('sort_by', 'profit')
            sort_order = filters.get('sort_order', 'desc')
            page = int(filters.get('page', 1))
            # 限制最大页面大小，防止过大的查询
            page_size = min(int(filters.get('page_size', 50)), 100)
            
            # 构建完整的筛选条件字典用于缓存键
            cache_filters = {
                'start_date': start_date,
                'end_date': end_date,
                'store_id': store_id,
                'asin': asin,
                'marketplace': marketplace,
                'min_profit': min_profit,
                'max_profit': max_profit,
                'sort_by': sort_by,
                'sort_order': sort_order,
                'page': page,
                'page_size': page_size
            }
            
            # 生成缓存键
            cache_key = self._generate_cache_key(cache_filters)
            
            # 尝试从缓存获取结果
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f'从缓存返回ASIN利润数据，键: {cache_key}，用户ID: {self.user_id}')
                return cached_result
            
            # 构建查询
            query = self.db_session.query(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.sku,
                AmazonIntegratedData.product_name,
                AmazonIntegratedData.marketplace,
                AmazonStore.store_name,
                func.sum(AmazonIntegratedData.order_count).label('total_orders'),
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
                func.sum(AmazonIntegratedData.platform_fee).label('total_platform_fee'),
                func.sum(AmazonIntegratedData.ad_spend).label('total_ad_spend'),
                func.sum(AmazonIntegratedData.product_cost).label('total_product_cost'),
                func.sum(AmazonIntegratedData.profit).label('total_profit'),
                func.avg(AmazonIntegratedData.profit_rate).label('avg_profit_rate')
            ).join(AmazonStore, AmazonIntegratedData.store_id == AmazonStore.id)
            
            # 添加用户过滤
            if self.user_id:
                query = query.filter(AmazonStore.user_id == self.user_id)
            
            # 添加日期过滤
            query = query.filter(
                and_(
                    AmazonIntegratedData.date >= start_date,
                    AmazonIntegratedData.date <= end_date
                )
            )
            
            # 添加店铺过滤
            if store_id:
                query = query.filter(AmazonIntegratedData.store_id == store_id)
            
            # 添加ASIN过滤
            if asin:
                query = query.filter(AmazonIntegratedData.asin.ilike(f'%{asin}%'))
            
            # 添加市场过滤
            if marketplace:
                query = query.filter(AmazonIntegratedData.marketplace == marketplace)
            
            # 保存查询副本用于计算总数
            count_query = query
            
            # 添加利润范围过滤
            if min_profit is not None or max_profit is not None:
                having_conditions = []
                if min_profit is not None:
                    having_conditions.append(func.sum(AmazonIntegratedData.profit) >= min_profit)
                if max_profit is not None:
                    having_conditions.append(func.sum(AmazonIntegratedData.profit) <= max_profit)
                query = query.having(and_(*having_conditions))
                count_query = count_query.having(and_(*having_conditions))
            
            # 分组
            query = query.group_by(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.sku,
                AmazonIntegratedData.product_name,
                AmazonIntegratedData.marketplace,
                AmazonStore.store_name
            )
            count_query = count_query.group_by(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.sku,
                AmazonIntegratedData.product_name,
                AmazonIntegratedData.marketplace,
                AmazonStore.store_name
            )
            
            # 排序
            # 验证排序字段
            valid_sort_fields = ['total_sales', 'total_profit', 'total_orders', 'avg_profit_rate']
            if sort_by not in valid_sort_fields:
                sort_by = 'total_profit'  # 默认按利润排序
            
            # 根据字段选择正确的排序表达式
            sort_expressions = {
                'total_sales': func.sum(AmazonIntegratedData.sales_amount),
                'total_profit': func.sum(AmazonIntegratedData.profit),
                'total_orders': func.sum(AmazonIntegratedData.order_count),
                'avg_profit_rate': func.avg(AmazonIntegratedData.profit_rate)
            }
            
            order_column = sort_expressions[sort_by]
            if sort_order == 'desc':
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
            
            # 计算总数 - 使用更高效的方式
            # 创建子查询获取总数，避免加载所有数据到内存
            count_subquery = count_query.statement.with_only_columns([func.count()]).order_by(None)
            total_count = self.db_session.execute(count_subquery).scalar() or 0
            
            # 分页
            offset = (page - 1) * page_size
            # 预先限制结果集大小
            result = query.offset(offset).limit(page_size).all()
            
            # 转换为字典列表 - 使用列表推导式提高效率
            data = [{
                'asin': row.asin or '',
                'sku': row.sku or '',
                'product_name': row.product_name or '',
                'marketplace': row.marketplace or '',
                'store_name': row.store_name or '',
                'total_orders': int(row.total_orders) if row.total_orders is not None else 0,
                'total_sales': float(row.total_sales or 0),
                'total_platform_fee': float(row.total_platform_fee or 0),
                'total_ad_spend': float(row.total_ad_spend or 0),
                'total_product_cost': float(row.total_product_cost or 0),
                'total_profit': float(row.total_profit or 0),
                'avg_profit_rate': float(row.avg_profit_rate or 0),
                'avg_order_value': float(row.total_sales / row.total_orders) if row.total_orders and row.total_orders > 0 else 0
            } for row in result]
            
            # 构建返回结果
            response_data = {
                'data': data,
                'pagination': {
                    'total': total_count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total_count + page_size - 1) // page_size
                },
                'filters': filters
            }
            
            # 缓存结果
            self.cache.set(cache_key, response_data)
            
            logger.info(f'获取ASIN利润数据成功，返回 {len(data)} 条记录，共 {total_count} 条，用户ID: {self.user_id}')
            
            return response_data
            
        except Exception as e:
            logger.error(f'获取ASIN利润数据失败: {str(e)}')
            import traceback
            traceback.print_exc()
            raise
    
    def get_asin_details(self, asin, store_id=None, start_date=None, end_date=None):
        """
        获取单个ASIN的详细数据
        """
        try:
            # 设置默认日期范围（最近30天）
            if not start_date:
                start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # 构建缓存键
            cache_filters = {
                'asin': asin,
                'store_id': store_id,
                'start_date': start_date,
                'end_date': end_date,
                'type': 'asin_details'
            }
            cache_key = self._generate_cache_key(cache_filters)
            
            # 尝试从缓存获取
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f'从缓存返回ASIN详情数据，键: {cache_key}，用户ID: {self.user_id}')
                return cached_data
            
            # 构建查询 - 只选择需要的字段以优化性能
            query = self.db_session.query(
                AmazonIntegratedData.date,
                AmazonIntegratedData.order_count,
                AmazonIntegratedData.sales_amount,
                AmazonIntegratedData.platform_fee,
                AmazonIntegratedData.ad_spend,
                AmazonIntegratedData.product_cost,
                AmazonIntegratedData.profit,
                AmazonIntegratedData.profit_rate,
                AmazonIntegratedData.is_estimated
            ).filter(
                and_(
                    AmazonIntegratedData.asin == asin,
                    AmazonIntegratedData.date >= start_date,
                    AmazonIntegratedData.date <= end_date
                )
            )
            
            # 添加用户过滤
            if self.user_id:
                query = query.join(AmazonStore).filter(AmazonStore.user_id == self.user_id)
            
            # 添加店铺过滤
            if store_id:
                query = query.filter(AmazonIntegratedData.store_id == store_id)
            
            # 按日期排序
            result = query.order_by(AmazonIntegratedData.date).all()
            
            # 转换为字典列表 - 使用列表推导式提高效率
            daily_data = [{
                'date': row.date.strftime('%Y-%m-%d'),
                'order_count': row.order_count or 0,
                'sales_amount': float(row.sales_amount or 0),
                'platform_fee': float(row.platform_fee or 0),
                'ad_spend': float(row.ad_spend or 0),
                'product_cost': float(row.product_cost or 0),
                'profit': float(row.profit or 0),
                'profit_rate': float(row.profit_rate or 0),
                'is_estimated': row.is_estimated
            } for row in result]
            
            # 缓存结果
            self.cache.set(cache_key, daily_data)
            
            logger.info(f'获取ASIN {asin} 详细数据成功，返回 {len(daily_data)} 条记录，用户ID: {self.user_id}')
            return daily_data
            
        except Exception as e:
            logger.error(f'获取ASIN {asin} 详细数据失败: {str(e)}')
            import traceback
            traceback.print_exc()
            raise
    
    def export_to_excel(self, filters=None, filepath=None):
        """
        导出报表到Excel
        """
        try:
            # 获取数据
            if filters is None:
                filters = {}
            
            # 构建缓存键（但不缓存实际的Excel文件，只缓存数据）
            cache_filters = filters.copy() if filters else {}
            cache_filters['page'] = 1
            cache_filters['page_size'] = 10000  # 设置一个较大的值以获取所有数据
            cache_filters['type'] = 'export_data'
            cache_key = self._generate_cache_key(cache_filters)
            
            # 尝试从缓存获取数据
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f'从缓存获取导出数据，键: {cache_key}，用户ID: {self.user_id}')
                asin_data = cached_data['asin_data']
                summary_stats = cached_data['summary_stats']
            else:
                # 获取ASIN利润数据
                result = self.get_asin_profit_data(cache_filters)
                asin_data = result['data']
                
                # 同时获取汇总统计（复用现有的缓存方法）
                summary_stats = self.get_summary_statistics(filters)
                
                # 缓存数据（避免重复计算）
                self.cache.set(cache_key, {
                    'asin_data': asin_data,
                    'summary_stats': summary_stats
                })
            
            # 创建DataFrame
            df = pd.DataFrame(asin_data)
            
            # 优化：确保所有数值列都是数字类型
            numeric_columns = ['total_orders', 'total_sales', 'total_platform_fee',
                             'total_ad_spend', 'total_product_cost', 'total_profit',
                             'avg_profit_rate', 'avg_order_value']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 如果没有提供文件路径，生成一个默认路径
            if not filepath:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f'../data/reports/asin_profit_report_{timestamp}.xlsx'
            
            # 导出到Excel
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                # 主工作表
                df.to_excel(writer, sheet_name='ASIN利润报表', index=False)
                
                # 获取xlsxwriter对象
                workbook = writer.book
                worksheet = writer.sheets['ASIN利润报表']
                
                # 设置列宽
                worksheet.set_column('A:C', 20)  # ASIN, SKU, 产品名称
                worksheet.set_column('D:E', 15)  # 市场, 店铺
                worksheet.set_column('F:M', 12)  # 数值列
                
                # 添加货币格式
                currency_format = workbook.add_format({'num_format': '¥#,##0.00'})
                percent_format = workbook.add_format({'num_format': '0.00%'})
                
                # 应用格式
                for col in range(6, 12):  # 销售额到利润
                    worksheet.set_column(col, col, 12, currency_format)
                worksheet.set_column(12, 12, 12, percent_format)  # 利润率
                worksheet.set_column(13, 13, 12, currency_format)  # 客单价
                
                # 创建汇总页
                total_asin = len(asin_data)
                total_orders = summary_stats.get('total_orders', 0)
                total_sales = summary_stats.get('total_sales', 0)
                total_profit = summary_stats.get('total_profit', 0)
                avg_profit_rate = summary_stats.get('avg_profit_rate', 0)
                
                summary_data = {
                    '指标': ['ASIN总数', '订单总数', '销售总额', '利润总额', '平均利润率', '日期范围'],
                    '值': [total_asin, total_orders, total_sales, total_profit, 
                          f'{avg_profit_rate:.2%}', summary_stats.get('date_range', '')]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='汇总统计', index=False)
                
                # 设置汇总页格式
                summary_sheet = writer.sheets['汇总统计']
                summary_sheet.set_column('A:A', 12)
                summary_sheet.set_column('B:B', 20)
                
                # 优化：只在有数据时创建市场汇总
                if not df.empty and 'marketplace' in df.columns:
                    # 按市场汇总
                    marketplace_summary = df.groupby('marketplace', as_index=False).agg({
                        'total_sales': 'sum',
                        'total_profit': 'sum',
                        'total_orders': 'sum',
                        'asin': 'count'
                    }).rename(columns={'asin': 'asin_count'})
                    
                    # 计算市场占比 - 避免除零错误
                    marketplace_summary['销售占比'] = marketplace_summary['total_sales'].apply(
                        lambda x: (x / total_sales * 100) if total_sales > 0 else 0
                    )
                    marketplace_summary['利润占比'] = marketplace_summary['total_profit'].apply(
                        lambda x: (x / total_profit * 100) if total_profit > 0 else 0
                    )
                    
                    # 写入市场汇总
                    marketplace_summary.to_excel(writer, sheet_name='市场汇总', index=False)
                    
                    # 设置市场汇总页格式
                    marketplace_sheet = writer.sheets['市场汇总']
                    marketplace_sheet.set_column('A:A', 15)  # 市场
                    marketplace_sheet.set_column('B:F', 12)  # 数值列
            
            logger.info(f'报表导出到Excel成功: {filepath}，用户ID: {self.user_id}，包含 {len(asin_data)} 条记录')
            return filepath
            
        except Exception as e:
            logger.error(f'报表导出到Excel失败: {str(e)}')
            import traceback
            traceback.print_exc()
            raise
    
    def get_summary_statistics(self, filters=None):
        """
        获取汇总统计信息
        """
        try:
            # 获取数据
            if filters is None:
                filters = {}
            
            # 设置默认值
            start_date = filters.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = filters.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            store_id = filters.get('store_id')
            marketplace = filters.get('marketplace')
            
            # 构建缓存键
            cache_filters = {
                'start_date': start_date,
                'end_date': end_date,
                'store_id': store_id,
                'marketplace': marketplace,
                'type': 'summary'
            }
            cache_key = self._generate_cache_key(cache_filters)
            
            # 尝试从缓存获取
            cached_summary = self.cache.get(cache_key)
            if cached_summary:
                logger.info(f'从缓存返回汇总统计信息，键: {cache_key}，用户ID: {self.user_id}')
                return cached_summary
            
            # 构建查询
            query = self.db_session.query(
                func.count(func.distinct(AmazonIntegratedData.asin)).label('asin_count'),
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
            
            # 执行查询
            result = query.first()
            
            # 安全地处理空结果
            asin_count = result.asin_count or 0
            total_orders = result.total_orders or 0
            total_sales = float(result.total_sales or 0)
            total_profit = float(result.total_profit or 0)
            
            # 构建返回数据
            summary = {
                'asin_count': asin_count,
                'total_orders': total_orders,
                'total_sales': total_sales,
                'total_profit': total_profit,
                'avg_profit_rate': float(result.avg_profit_rate or 0),
                'avg_order_value': float(total_sales / total_orders) if total_orders > 0 else 0,
                'date_range': f'{start_date} 至 {end_date}',
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            # 缓存结果
            self.cache.set(cache_key, summary)
            
            logger.info(f'获取汇总统计信息成功，用户ID: {self.user_id}，ASIN数量: {asin_count}')
            return summary
            
        except Exception as e:
            logger.error(f'获取汇总统计信息失败: {str(e)}')
            import traceback
            traceback.print_exc()
            raise
    
    def get_marketplace_performance(self, filters=None):
        """
        获取不同市场的性能对比
        """
        try:
            # 获取数据
            if filters is None:
                filters = {}
            
            # 设置默认值
            start_date = filters.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = filters.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            store_id = filters.get('store_id')
            
            # 构建缓存键
            cache_filters = {
                'start_date': start_date,
                'end_date': end_date,
                'store_id': store_id,
                'type': 'marketplace_performance'
            }
            cache_key = self._generate_cache_key(cache_filters)
            
            # 尝试从缓存获取
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f'从缓存返回市场性能对比数据，键: {cache_key}，用户ID: {self.user_id}')
                return cached_data
            
            # 构建查询 - 只选择需要的字段
            query = self.db_session.query(
                AmazonIntegratedData.marketplace,
                func.count(func.distinct(AmazonIntegratedData.asin)).label('asin_count'),
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
            
            query = query.filter(and_(*conditions))
            query = query.group_by(AmazonIntegratedData.marketplace)
            query = query.order_by(func.sum(AmazonIntegratedData.sales_amount).desc())
            
            # 执行查询
            result = query.all()
            
            # 计算总额
            total_sales = sum(row.total_sales or 0 for row in result)
            total_profit = sum(row.total_profit or 0 for row in result)
            
            # 转换为字典列表 - 使用列表推导式提高效率
            marketplace_data = [{
                'marketplace': row.marketplace or 'Unknown',
                'asin_count': row.asin_count or 0,
                'total_orders': int(row.total_orders or 0),
                'total_sales': float(row.total_sales or 0),
                'total_profit': float(row.total_profit or 0),
                'avg_profit_rate': float(row.avg_profit_rate or 0),
                'avg_order_value': float(row.total_sales / row.total_orders) if row.total_orders and row.total_orders > 0 else 0,
                'sales_percentage': float(row.total_sales / total_sales) if total_sales > 0 else 0,
                'profit_percentage': float(row.total_profit / total_profit) if total_profit > 0 else 0
            } for row in result]
            
            # 缓存结果
            self.cache.set(cache_key, marketplace_data)
            
            logger.info(f'获取市场性能对比成功，返回 {len(marketplace_data)} 个市场，用户ID: {self.user_id}')
            return marketplace_data
            
        except Exception as e:
            logger.error(f'获取市场性能对比失败: {str(e)}')
            import traceback
            traceback.print_exc()
            raise
    
    def get_store_performance(self, filters=None):
        """
        获取各店铺性能对比数据
        """
        try:
            # 获取数据
            if filters is None:
                filters = {}
            
            # 设置默认值
            start_date = filters.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = filters.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            
            # 构建缓存键
            cache_filters = {
                'start_date': start_date,
                'end_date': end_date,
                'type': 'store_performance'
            }
            cache_key = self._generate_cache_key(cache_filters)
            
            # 尝试从缓存获取
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f'从缓存返回店铺性能对比数据，键: {cache_key}，用户ID: {self.user_id}')
                return cached_data
            
            # 构建查询 - 只选择需要的字段
            query = self.db_session.query(
                AmazonIntegratedData.store_id,
                AmazonStore.store_name,
                func.count(func.distinct(AmazonIntegratedData.asin)).label('asin_count'),
                func.sum(AmazonIntegratedData.order_count).label('total_orders'),
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
                func.sum(AmazonIntegratedData.profit).label('total_profit'),
                func.avg(AmazonIntegratedData.profit_rate).label('avg_profit_rate')
            )
            
            # 添加用户过滤
            if self.user_id:
                query = query.filter(AmazonStore.user_id == self.user_id)
            
            # 添加过滤条件
            query = query.join(AmazonStore).filter(
                AmazonIntegratedData.date >= start_date,
                AmazonIntegratedData.date <= end_date
            )
            
            # 按店铺分组
            query = query.group_by(AmazonIntegratedData.store_id, AmazonStore.store_name)
            query = query.order_by(func.sum(AmazonIntegratedData.profit).desc())
            
            # 执行查询
            result = query.all()
            
            # 计算总额
            total_sales = sum(row.total_sales or 0 for row in result)
            total_profit = sum(row.total_profit or 0 for row in result)
            
            # 转换为字典列表 - 使用列表推导式提高效率
            store_data = [{
                'store_id': row.store_id,
                'store_name': row.store_name or 'Unknown',
                'asin_count': row.asin_count or 0,
                'total_orders': int(row.total_orders or 0),
                'total_sales': float(row.total_sales or 0),
                'total_profit': float(row.total_profit or 0),
                'avg_profit_rate': float(row.avg_profit_rate or 0),
                'avg_order_value': float(row.total_sales / row.total_orders) if row.total_orders and row.total_orders > 0 else 0,
                'sales_percentage': float(row.total_sales / total_sales) if total_sales > 0 else 0,
                'profit_percentage': float(row.total_profit / total_profit) if total_profit > 0 else 0
            } for row in result]
            
            # 缓存结果
            self.cache.set(cache_key, store_data)
            
            logger.info(f'获取店铺性能对比成功，返回 {len(store_data)} 个店铺，用户ID: {self.user_id}')
            return store_data
            
        except Exception as e:
            logger.error(f'获取店铺性能对比失败: {str(e)}')
            import traceback
            traceback.print_exc()
            raise