# 移除requests依赖
import logging
import time
import random
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import datetime
import logging
import json
import random
import time
from models import AmazonIntegratedData, AmazonStore, SyncLog, init_db
from amazon_oauth import AmazonOAuth

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_inventory')

class AmazonInventoryData:
    """亚马逊库存数据处理类 - 模拟实现"""
    
    def __init__(self, db_session=None, user_id=None, is_admin=False):
        """初始化库存数据处理器"""
        self.db_session = None  # 不使用实际数据库
        self.user_id = user_id
        self.is_admin = is_admin
        # 移除OAuth依赖
        self.logger = logging.getLogger(__name__)
        logger.info(f"初始化模拟库存数据处理器 - 用户ID: {user_id}")
        # 模拟数据存储
        self.mock_inventory_data = {}
        self.mock_stores = {
            1: {'id': 1, 'store_name': '测试店铺1', 'user_id': user_id, 'region': 'US'},
            2: {'id': 2, 'store_name': '测试店铺2', 'user_id': user_id, 'region': 'UK'}
        }
        # 模拟库存记录
        self._init_mock_data()
    
    def _init_mock_data(self):
        """初始化模拟数据"""
        # 为测试店铺创建模拟库存数据
        for store_id in [1, 2]:
            store_name = self.mock_stores[store_id]['store_name']
            self.mock_inventory_data[store_id] = [
                {
                    'asin': 'B08XWZXLZH',
                    'order_date': datetime.datetime.utcnow().date(),
                    'store_id': store_id,
                    'store_name': store_name,
                    'instock_quantity': 150,
                    'inbound_quantity': 50,
                    'sellable_quantity_30d': 30,
                    'inventory_turnover': 6.0,
                    'days_of_coverage': 20.0,
                    'is_estimated': False
                },
                {
                    'asin': 'B07Q2ZQR35',
                    'order_date': datetime.datetime.utcnow().date(),
                    'store_id': store_id,
                    'store_name': store_name,
                    'instock_quantity': 20,
                    'inbound_quantity': 100,
                    'sellable_quantity_30d': 60,
                    'inventory_turnover': 15.0,
                    'days_of_coverage': 6.0,
                    'is_estimated': False
                },
                {
                    'asin': 'B07K14XDFW',
                    'order_date': datetime.datetime.utcnow().date(),
                    'store_id': store_id,
                    'store_name': store_name,
                    'instock_quantity': 500,
                    'inbound_quantity': 0,
                    'sellable_quantity_30d': 20,
                    'inventory_turnover': 1.2,
                    'days_of_coverage': 75.0,
                    'is_estimated': False
                }
            ]
    
    def get_store_inventory(self, store_id):
        """获取店铺库存信息，支持多区域和备用API"""
        logger.info(f'开始获取店铺ID: {store_id} 的库存数据')
        
        # 获取店铺信息并验证权限
        store = self.oauth_manager.get_store_by_user_and_id(store_id, user_id=self.user_id)
        if not store:
            logger.error(f'未找到ID为 {store_id} 的店铺或无权限访问')
            return []
        
        # 获取访问令牌
        access_token = self.oauth_manager.get_valid_access_token(store_id)
        if not access_token:
            logger.error(f'无法获取店铺 {store.store_name} 的有效访问令牌')
            return []
        
        # 获取店铺区域信息，如果未指定默认为美国站
        store_region = getattr(store, 'region', 'US')
        marketplace_info = self.MARKETPLACE_REGIONS.get(store_region, self.MARKETPLACE_REGIONS['US'])
        
        # 准备API请求头
        headers = {
            'x-amz-access-token': access_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # 准备请求参数，根据区域选择合适的marketplace_id
        params = {
            'granularityType': 'Marketplace',
            'granularityId': marketplace_info['marketplace_id'],
            'details': 'true'
        }
        
        # 确定API端点
        endpoints = [self.INVENTORY_API_ENDPOINT]
        region_endpoint = self.ALTERNATIVE_INVENTORY_ENDPOINTS.get(marketplace_info['region'])
        if region_endpoint and region_endpoint != self.INVENTORY_API_ENDPOINT:
            endpoints.append(region_endpoint)
        
        # 尝试所有可能的端点
        for endpoint in endpoints:
            logger.info(f'尝试从端点获取库存数据: {endpoint}')
            
            # 带重试的API请求
            for retry_count in range(self.MAX_RETRIES):
                try:
                    # 遵守API速率限制
                    self._respect_rate_limit('inventory_request')
                    
                    logger.info(f'获取店铺 {store.store_name} 的库存数据 (尝试 {retry_count + 1}/{self.MAX_RETRIES})')
                    response = requests.get(
                        endpoint,
                        headers=headers,
                        params=params,
                        timeout=60
                    )
                    
                    # 检查响应状态
                    response.raise_for_status()
                    
                    # 验证响应内容是否有效JSON
                    response_text = response.text
                    if not response_text.strip():
                        logger.warning('API返回空响应')
                        continue
                    
                    try:
                        response_data = response.json()
                    except json.JSONDecodeError:
                        logger.error(f'API返回非JSON格式响应: {response_text[:200]}...')
                        continue
                    
                    # 解析响应数据
                    inventory_records = self.parse_inventory_response(
                        response_data, 
                        store_id, 
                        store.store_name
                    )
                    
                    logger.info(f'成功从端点 {endpoint} 获取店铺 {store.store_name} 的库存数据，共 {len(inventory_records)} 条记录')
                    return inventory_records
                    
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 401:
                        # Token可能过期，强制刷新
                        logger.warning(f'API返回401错误，强制刷新令牌')
                        self.oauth_manager.refresh_access_token(store)
                        access_token = store.access_token
                        headers['x-amz-access-token'] = access_token
                    elif response.status_code == 429:
                        # 速率限制错误，增加延迟
                        logger.warning(f'API返回429错误（超出速率限制），等待更长时间')
                        delay = self.RETRY_DELAY_BASE * (2 ** retry_count) * 2  # 增加一倍延迟
                    elif response.status_code == 503:
                        # 服务不可用，重试
                        logger.warning(f'API返回503错误（服务不可用）')
                        delay = self.RETRY_DELAY_BASE * (2 ** retry_count)
                    else:
                        logger.error(f'HTTP错误: {str(e)}，状态码: {response.status_code}')
                        
                        # 超过重试次数则尝试下一个端点
                        if retry_count >= self.MAX_RETRIES - 1:
                            logger.warning(f'当前端点 {endpoint} 重试次数用尽，尝试下一个端点')
                            break
                        delay = self.RETRY_DELAY_BASE * (2 ** retry_count)
                
                except Exception as e:
                    logger.error(f'获取库存数据时发生错误: {str(e)}')
                    import traceback
                    logger.error(traceback.format_exc())
                    
                    # 超过重试次数则尝试下一个端点
                    if retry_count >= self.MAX_RETRIES - 1:
                        logger.warning(f'当前端点 {endpoint} 重试次数用尽，尝试下一个端点')
                        break
                    delay = self.RETRY_DELAY_BASE * (2 ** retry_count)
                
                # 计算退避延迟并添加随机抖动
                jitter = random.uniform(0.5, 1.5)
                actual_delay = delay * jitter
                logger.info(f'重试 {retry_count + 1}/{self.MAX_RETRIES}，等待 {actual_delay:.2f} 秒...')
                time.sleep(actual_delay)
        
        # 如果所有端点都失败，尝试备用方法
        logger.warning(f'所有标准API端点失败，尝试备用方法获取库存数据')
        return self.get_inventory_data_alternatively(store_id)
    
    def _respect_rate_limit(self, api_type):
        """遵守API速率限制，确保不超过亚马逊API的请求频率限制"""
        if api_type not in self.last_api_call_time:
            self.last_api_call_time[api_type] = datetime.datetime.utcnow()
            return
        
        # 获取当前API类型的限制
        limit_per_minute = self.API_RATE_LIMIT.get(api_type, 10)
        min_interval = 60 / limit_per_minute  # 最小请求间隔（秒）
        
        # 计算需要等待的时间
        current_time = datetime.datetime.utcnow()
        last_call_time = self.last_api_call_time[api_type]
        elapsed = (current_time - last_call_time).total_seconds()
        
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug(f'遵守API速率限制，等待 {wait_time:.2f} 秒')
            time.sleep(wait_time)
            current_time = datetime.datetime.utcnow()
        
        # 更新最后调用时间
        self.last_api_call_time[api_type] = current_time
    
    def get_inventory_data_alternatively(self, store_id):
        """备用方法获取库存数据，使用不同的API或方法"""
        logger.warning(f'使用备用方法获取库存数据 - 店铺ID: {store_id}')
        
        try:
            # 获取店铺信息
            store = self.oauth_manager.get_store_by_user_and_id(store_id, user_id=self.user_id)
            if not store:
                logger.error(f'找不到店铺ID: {store_id}')
                return []
            
            # 获取访问令牌
            access_token = self.oauth_manager.get_valid_access_token(store_id)
            if not access_token:
                logger.error('无法获取访问令牌')
                return []
            
            # 准备请求头
            headers = {
                'x-amz-access-token': access_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # 获取店铺区域信息
            store_region = getattr(store, 'region', 'US')
            marketplace_info = self.MARKETPLACE_REGIONS.get(store_region, self.MARKETPLACE_REGIONS['US'])
            
            # 尝试使用Seller Central Reports API作为备用方案
            # 这里使用一个简化的实现，实际项目中可能需要实现报表请求和下载流程
            
            # 作为最后的备用，从数据库获取最近的库存记录并标记为"估计"
            recent_inventory = self._get_recent_inventory_from_db(store_id)
            if recent_inventory:
                logger.info(f'从数据库获取最近库存记录作为备用，共 {len(recent_inventory)} 条')
                return recent_inventory
            
            return []
            
        except Exception as e:
            logger.error(f'使用备用方法获取库存数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _get_recent_inventory_from_db(self, store_id):
        """从数据库获取最近的库存记录作为备用"""
        try:
            # 获取最近7天的数据
            seven_days_ago = datetime.datetime.utcnow().date() - datetime.timedelta(days=7)
            
            # 查询最近的库存记录
            recent_records = self.db_session.query(AmazonIntegratedData).filter(
                AmazonIntegratedData.store_id == store_id,
                AmazonIntegratedData.order_date >= seven_days_ago,
                AmazonIntegratedData.instock_quantity.isnot(None)
            ).order_by(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.order_date.desc()
            ).all()
            
            # 按ASIN分组，获取每个ASIN的最新记录
            latest_records_dict = {}
            for record in recent_records:
                if record.asin not in latest_records_dict:
                    latest_records_dict[record.asin] = record
            
            # 转换为字典格式并更新日期和标记
            inventory_records = []
            current_date = datetime.datetime.utcnow().date()
            
            for asin, record in latest_records_dict.items():
                # 计算天数差
                days_difference = (current_date - record.order_date).days
                
                # 基于天数差调整库存估计（简单模型）
                estimated_instock = record.instock_quantity
                if days_difference > 0 and record.sellable_quantity_30d > 0:
                    daily_sales_rate = record.sellable_quantity_30d / 30.0
                    estimated_instock = max(0, record.instock_quantity - (daily_sales_rate * days_difference))
                
                # 构建记录
                inventory_record = {
                    'asin': record.asin,
                    'order_date': current_date,
                    'store_id': record.store_id,
                    'store_name': record.store_name,
                    'instock_quantity': int(estimated_instock),
                    'inbound_quantity': record.inbound_quantity or 0,
                    'sellable_quantity_30d': record.sellable_quantity_30d or 0,
                    'inventory_turnover': record.inventory_turnover or 0,
                    'days_of_coverage': record.days_of_coverage or 0,
                    'is_estimated': True,  # 标记为估计数据
                    'estimated_from_days_ago': days_difference
                }
                
                # 重新计算库存指标
                total_inventory = inventory_record['instock_quantity'] + inventory_record['inbound_quantity']
                if inventory_record['sellable_quantity_30d'] > 0:
                    inventory_record['inventory_turnover'] = (inventory_record['sellable_quantity_30d'] / total_inventory) * 30 if total_inventory > 0 else 0
                    inventory_record['days_of_coverage'] = total_inventory / inventory_record['sellable_quantity_30d'] * 30
                
                inventory_records.append(inventory_record)
            
            return inventory_records
            
        except Exception as e:
            logger.error(f'从数据库获取最近库存记录时发生错误: {str(e)}')
            return []
    
    def parse_inventory_response(self, response_data, store_id, store_name):
        """解析库存API响应数据，支持多种响应格式和更详细的库存指标"""
        inventory_records = []
        
        try:
            logger.info(f'开始解析库存响应数据，检查响应格式')
            
            # 获取当前日期作为记录日期
            record_date = datetime.datetime.utcnow().date()
            processed_count = 0
            exception_count = 0
            
            # 检查不同的响应格式
            if 'payload' in response_data:
                # 标准SP-API格式
                if 'summaries' in response_data['payload']:
                    logger.info(f'发现标准SP-API格式响应，包含 {len(response_data["payload"]["summaries"])} 个库存汇总')
                    for summary in response_data['payload']['summaries']:
                        try:
                            record = self._parse_inventory_summary(summary, record_date, store_id, store_name)
                            if record:
                                inventory_records.append(record)
                                processed_count += 1
                        except Exception as e:
                            logger.error(f'解析库存汇总项时出错: {str(e)}')
                            exception_count += 1
                # 备用格式
                elif 'inventoryItems' in response_data['payload']:
                    logger.info(f'发现备用格式响应，包含 {len(response_data["payload"]["inventoryItems"])} 个库存项')
                    for item in response_data['payload']['inventoryItems']:
                        try:
                            record = self._parse_inventory_item(item, record_date, store_id, store_name)
                            if record:
                                inventory_records.append(record)
                                processed_count += 1
                        except Exception as e:
                            logger.error(f'解析库存项时出错: {str(e)}')
                            exception_count += 1
            # 简单数组格式
            elif isinstance(response_data, list):
                logger.info(f'发现简单数组格式响应，包含 {len(response_data)} 个项目')
                for item in response_data:
                    try:
                        record = self._parse_inventory_item(item, record_date, store_id, store_name)
                        if record:
                            inventory_records.append(record)
                            processed_count += 1
                    except Exception as e:
                        logger.error(f'解析简单格式库存项时出错: {str(e)}')
                        exception_count += 1
            # 单个库存项格式
            elif isinstance(response_data, dict) and 'asin' in response_data:
                try:
                    record = self._parse_inventory_summary(response_data, record_date, store_id, store_name)
                    if record:
                        inventory_records.append(record)
                        processed_count += 1
                except Exception as e:
                    logger.error(f'解析单个库存项时出错: {str(e)}')
                    exception_count += 1
            else:
                logger.warning(f'未知的响应数据格式: {list(response_data.keys())[:5]}...')
            
            # 数据验证和清理
            validated_records = []
            for record in inventory_records:
                # 验证必填字段
                if not record.get('asin') or record.get('asin') == 'Unknown':
                    logger.warning(f'跳过没有有效ASIN的记录')
                    continue
                
                # 验证数值字段
                record['instock_quantity'] = max(0, int(record.get('instock_quantity', 0)))
                record['inbound_quantity'] = max(0, int(record.get('inbound_quantity', 0)))
                record['sellable_quantity_30d'] = max(0, int(record.get('sellable_quantity_30d', 0)))
                
                # 设置默认值并确保类型正确
                record['inventory_turnover'] = float(record.get('inventory_turnover', 0.0))
                record['days_of_coverage'] = float(record.get('days_of_coverage', 0.0))
                
                # 检查异常值
                is_exception = 0
                total_inventory = record['instock_quantity'] + record['inbound_quantity']
                
                # 库存数量异常检测
                if total_inventory > 10000:  # 根据实际业务设定合理阈值
                    is_exception = 1
                    logger.warning(f'检测到异常高的库存数量: {total_inventory} 对于ASIN: {record["asin"]}')
                
                record['is_exception'] = is_exception
                validated_records.append(record)
            
            logger.info(f'库存数据解析完成: 处理 {processed_count} 条，异常 {exception_count} 条，验证通过 {len(validated_records)} 条')
            return validated_records
            
        except Exception as e:
            logger.error(f'解析库存数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_inventory_summary(self, summary, record_date, store_id, store_name):
        """解析库存汇总项"""
        if 'inventoryDetails' not in summary:
            return None
        
        inventory_details = summary['inventoryDetails']
        
        # 获取ASIN信息，支持不同的字段名
        asin = None
        potential_asin_fields = ['asin', 'ASIN', 'productId', 'sellerSku', 'SKU', 'item-id']
        for field in potential_asin_fields:
            if field in summary:
                asin_value = summary[field]
                if asin_value and asin_value != 'N/A':
                    asin = asin_value
                    break
        
        if not asin:
            return None
        
        # 获取不同类型的库存数量
        instock_quantity = 0
        inbound_quantity = 0
        
        # 处理在库库存
        if isinstance(inventory_details, dict):
            # 标准格式
            instock_quantity = inventory_details.get('inStockSupplyQuantity', 0) or 0
            
            # 计算在途库存（包括各种状态）
            inbound_statuses = ['inboundWorkingQuantity', 'inboundShippedQuantity', 
                               'inboundReceivingQuantity', 'inboundTotalQuantity', 'reservedQuantity']
            for status in inbound_statuses:
                if status in inventory_details:
                    inbound_quantity += inventory_details[status] or 0
        
        # 获取30天销量（从不同可能的字段）
        sellable_quantity_30d = 0
        potential_sales_fields = ['sellableQuantity30d', 'sales30days', 'salesLast30Days', 'estimatedSales', 'recentSales']
        for field in potential_sales_fields:
            if field in summary and summary[field]:
                try:
                    sellable_quantity_30d = float(summary[field])
                    break
                except (ValueError, TypeError):
                    continue
        
        # 计算库存指标
        total_inventory = instock_quantity + inbound_quantity
        inventory_turnover = 0.0
        days_of_coverage = 0.0
        
        if sellable_quantity_30d > 0:
            inventory_turnover = (sellable_quantity_30d / total_inventory) * 30 if total_inventory > 0 else 0
            days_of_coverage = total_inventory / sellable_quantity_30d * 30
        
        # 构建完整记录
        record = {
            'asin': asin,
            'order_date': record_date,
            'store_id': store_id,
            'store_name': store_name,
            'instock_quantity': instock_quantity,
            'inbound_quantity': inbound_quantity,
            'sellable_quantity_30d': sellable_quantity_30d,
            'inventory_turnover': inventory_turnover,
            'days_of_coverage': days_of_coverage,
            'is_estimated': False
        }
        
        return record
    
    def _parse_inventory_item(self, item, record_date, store_id, store_name):
        """解析单个库存项"""
        # 获取ASIN
        asin = None
        potential_asin_fields = ['asin', 'ASIN', 'productId', 'sellerSku', 'SKU', 'itemId']
        for field in potential_asin_fields:
            if field in item:
                asin_value = item[field]
                if asin_value and asin_value != 'N/A':
                    asin = asin_value
                    break
        
        if not asin:
            return None
        
        # 获取库存数量
        instock_quantity = 0
        inbound_quantity = 0
        
        # 尝试不同的库存字段结构
        if isinstance(item, dict):
            # 直接字段
            instock_quantity = item.get('availableQuantity', 0) or item.get('instock', 0) or item.get('totalQuantity', 0) or 0
            inbound_quantity = item.get('inboundQuantity', 0) or item.get('pending', 0) or 0
            
            # 嵌套字段
            if 'inventoryDetails' in item:
                details = item['inventoryDetails']
                instock_quantity = details.get('available', 0) or details.get('instock', 0) or 0
                inbound_quantity = details.get('inbound', 0) or details.get('pending', 0) or 0
        
        # 获取30天销量
        sellable_quantity_30d = float(item.get('sales30Days', 0) or item.get('recentSales', 0) or 0)
        
        # 计算库存指标
        total_inventory = instock_quantity + inbound_quantity
        inventory_turnover = 0.0
        days_of_coverage = 0.0
        
        if sellable_quantity_30d > 0:
            inventory_turnover = (sellable_quantity_30d / total_inventory) * 30 if total_inventory > 0 else 0
            days_of_coverage = total_inventory / sellable_quantity_30d * 30
        
        # 构建记录
        record = {
            'asin': asin,
            'order_date': record_date,
            'store_id': store_id,
            'store_name': store_name,
            'instock_quantity': instock_quantity,
            'inbound_quantity': inbound_quantity,
            'sellable_quantity_30d': sellable_quantity_30d,
            'inventory_turnover': inventory_turnover,
            'days_of_coverage': days_of_coverage,
            'is_estimated': False
        }
        
        return record
    
    def update_inventory_data(self, inventory_records):
        """更新数据库中的库存数据，支持批量处理和优化"""
        if not inventory_records:
            logger.warning("没有库存数据需要更新")
            return 0
        
        try:
            logger.info(f'开始更新库存数据，共 {len(inventory_records)} 条记录')
            
            # 分组处理以提高效率
            records_by_store = {}
            for record in inventory_records:
                store_id = record.get('store_id')
                if store_id not in records_by_store:
                    records_by_store[store_id] = []
                records_by_store[store_id].append(record)
            
            total_updated = 0
            total_new = 0
            total_skipped = 0
            
            # 处理每个店铺的数据
            for store_id, store_records in records_by_store.items():
                # 获取店铺信息，批量处理用户ID
                store = self.db_session.query(AmazonStore).filter_by(id=store_id).first()
                if not store:
                    logger.error(f'找不到店铺ID: {store_id}，跳过 {len(store_records)} 条记录')
                    total_skipped += len(store_records)
                    continue
                
                user_id = store.user_id
                
                # 批量获取已存在的记录
                asins = [r.get('asin') for r in store_records if r.get('asin')]
                record_date = store_records[0].get('order_date') if store_records else datetime.datetime.utcnow().date()
                
                existing_records = {}
                if asins:
                    query = self.db_session.query(AmazonIntegratedData).filter(
                        AmazonIntegratedData.store_id == store_id,
                        AmazonIntegratedData.order_date == record_date,
                        AmazonIntegratedData.asin.in_(asins)
                    )
                    for db_record in query.all():
                        existing_records[db_record.asin] = db_record
                
                # 处理每条记录
                for record in store_records:
                    # 确保用户ID设置
                    record['user_id'] = user_id
                    
                    asin = record.get('asin')
                    if not asin:
                        logger.warning(f'跳过没有ASIN的记录')
                        total_skipped += 1
                        continue
                    
                    # 处理现有记录或创建新记录
                    if asin in existing_records:
                        # 更新现有记录
                        db_record = existing_records[asin]
                        db_record.instock_quantity = record.get('instock_quantity', 0)
                        db_record.inbound_quantity = record.get('inbound_quantity', 0)
                        db_record.sellable_quantity_30d = record.get('sellable_quantity_30d', 0)
                        db_record.inventory_turnover = record.get('inventory_turnover', 0.0)
                        db_record.days_of_coverage = record.get('days_of_coverage', 0.0)
                        db_record.is_exception = record.get('is_exception', 0)
                        db_record.is_estimated = record.get('is_estimated', False)
                        
                        # 如果有估计标志，添加估计信息
                        if record.get('is_estimated'):
                            db_record.estimated_from_days_ago = record.get('estimated_from_days_ago', 0)
                        
                        total_updated += 1
                    else:
                        # 创建新记录，但先检查数据有效性
                        if record.get('instock_quantity') is None and record.get('inbound_quantity') is None:
                            logger.warning(f'跳过没有有效库存数据的记录: {asin}')
                            total_skipped += 1
                            continue
                        
                        new_record = AmazonIntegratedData(**record)
                        self.db_session.add(new_record)
                        total_new += 1
            
            # 提交所有更改
            self.db_session.commit()
            
            total_processed = total_updated + total_new + total_skipped
            logger.info(f'库存数据更新完成: 更新 {total_updated} 条，新增 {total_new} 条，跳过 {total_skipped} 条，总计处理 {total_processed} 条')
            return total_updated + total_new
            
        except Exception as e:
            logger.error(f'更新库存数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            self.db_session.rollback()
            return 0
    
    def get_sales_30d(self, asin, store_id):
        """获取ASIN的30天销量（从数据库历史数据计算）"""
        try:
            logger.debug(f'计算ASIN: {asin} 在店铺: {store_id} 的30天销量')
            
            # 计算30天前的日期
            thirty_days_ago = datetime.datetime.utcnow().date() - datetime.timedelta(days=30)
            
            # 查询过去30天的销售数据
            records = self.db_session.query(AmazonIntegratedData).filter(
                AmazonIntegratedData.asin == asin,
                AmazonIntegratedData.store_id == store_id,
                AmazonIntegratedData.order_date >= thirty_days_ago
            ).all()
            
            # 计算总销量，支持不同字段
            total_sales = 0
            has_valid_sales = False
            
            for record in records:
                # 优先使用order_count
                if record.order_count is not None and record.order_count > 0:
                    total_sales += record.order_count
                    has_valid_sales = True
                # 其次尝试从其他字段获取
                elif record.sellable_quantity_30d is not None and record.sellable_quantity_30d > 0:
                    # 如果找到直接的30天销量，优先使用
                    daily_rate = record.sellable_quantity_30d / 30.0
                    # 计算该记录到现在的天数比例
                    days_since_record = (datetime.datetime.utcnow().date() - record.order_date).days
                    if days_since_record > 0:
                        total_sales += min(record.sellable_quantity_30d, daily_rate * days_since_record)
                        has_valid_sales = True
            
            # 如果没有找到有效销售数据，尝试使用最近的销售记录作为估算
            if not has_valid_sales and records:
                # 找出最近的记录
                latest_record = max(records, key=lambda x: x.order_date)
                if latest_record.sellable_quantity_30d is not None and latest_record.sellable_quantity_30d > 0:
                    logger.info(f'使用最近记录的30天销量估算: {latest_record.sellable_quantity_30d}')
                    total_sales = latest_record.sellable_quantity_30d
                    has_valid_sales = True
            
            logger.debug(f'计算完成，ASIN: {asin} 的30天销量为: {total_sales}')
            return total_sales
            
        except Exception as e:
            logger.error(f'计算30天销量时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    def calculate_inventory_health(self, instock, inbound, sales_30d):
        """计算库存健康指标
        
        Args:
            instock: 在库库存
            inbound: 在途库存
            sales_30d: 30天销量
            
        Returns:
            dict: 包含库存健康指标的字典
        """
        total_inventory = instock + inbound
        
        # 库存周转率 = (30天销量 / 总库存) * 30
        inventory_turnover = 0.0
        if total_inventory > 0 and sales_30d > 0:
            inventory_turnover = (sales_30d / total_inventory) * 30
        
        # 库存覆盖天数 = 总库存 / (30天销量 / 30)
        days_of_coverage = 0.0
        if sales_30d > 0:
            days_of_coverage = total_inventory / (sales_30d / 30.0)
        
        # 库存健康状态
        health_status = '未知'
        status_color = '🟣'  # 默认紫色
        
        if days_of_coverage == 0:
            health_status = '无销售数据'
            status_color = '🟣'
        elif days_of_coverage < 7:
            health_status = '紧急'
            status_color = '🔴'  # 红色
        elif days_of_coverage <= 30:
            health_status = '低库存'
            status_color = '🟡'  # 黄色
        elif days_of_coverage <= 90:
            health_status = '健康'
            status_color = '✅'  # 绿色
        else:
            health_status = '过剩'
            status_color = '🟠'  # 橙色
        
        # 补货建议
        reorder_suggestion = ''
        reorder_quantity = 0
        
        if sales_30d > 0:
            daily_sales = sales_30d / 30.0
            ideal_days = 45  # 理想的库存覆盖天数
            
            if days_of_coverage < 30:
                reorder_quantity = max(0, int((ideal_days - days_of_coverage) * daily_sales))
                reorder_suggestion = f'建议补货 {reorder_quantity} 件，维持 {ideal_days} 天库存'
            elif days_of_coverage > 120:
                reorder_suggestion = '库存过多，建议减少补货'
        
        return {
            'inventory_turnover': round(inventory_turnover, 2),
            'days_of_coverage': round(days_of_coverage, 2),
            'health_status': health_status,
            'status_color': status_color,
            'reorder_suggestion': reorder_suggestion,
            'reorder_quantity': reorder_quantity
        }
    
    def sync_inventory_data(self, store_id=None, user_id=None, force_alternate=False):
        """同步库存数据主函数，支持更多控制选项
        
        Args:
            store_id: 店铺ID，为None时同步所有店铺
            user_id: 用户ID，用于数据隔离和权限控制
            force_alternate: 是否强制使用备用方法获取数据
            
        Returns:
            dict: 同步结果
        """
        # 记录同步开始时间
        sync_start = datetime.datetime.utcnow()
        sync_status = 'failed'
        sync_message = ''
        record_count = 0
        store_sync_results = []
        
        try:
            logger.info(f'开始库存数据同步 - 店铺ID: {store_id}, 用户ID: {user_id}')
            
            # 如果指定了user_id，只获取该用户的店铺
            stores_to_sync = []
            if store_id:
                # 使用OAuth模块获取店铺并验证权限
                store = self.oauth_manager.get_store_by_user_and_id(store_id, user_id=user_id)
                if not store:
                    raise ValueError(f"店铺ID {store_id} 不存在或无权限访问")
                if not store.is_active:
                    raise ValueError(f"店铺 {store.store_name} 未激活")
                stores_to_sync = [store]
            else:
                # 使用OAuth模块获取用户的所有激活店铺
                stores_to_sync = self.oauth_manager.get_active_stores(user_id=user_id)
            
            if not stores_to_sync:
                logger.warning(f'没有找到需要同步的店铺')
                sync_status = 'success'
                sync_message = '没有找到需要同步的活跃店铺'
                return self._create_sync_result(sync_status, sync_message, 0, store_sync_results, sync_start, datetime.datetime.utcnow())
            
            logger.info(f'找到 {len(stores_to_sync)} 个需要同步的店铺')
            
            # 批量处理店铺，避免同时处理太多店铺
            batch_size = 5  # 每批处理的店铺数
            for i in range(0, len(stores_to_sync), batch_size):
                batch = stores_to_sync[i:i+batch_size]
                logger.info(f'处理店铺批次 {i//batch_size + 1}/{(len(stores_to_sync)+batch_size-1)//batch_size}')
                
                for store in batch:
                    store_start_time = datetime.datetime.utcnow()
                    store_record_count = 0
                    store_status = 'failed'
                    store_message = ''
                    
                    try:
                        logger.info(f'开始同步店铺 {store.store_name} (ID: {store.id}) 的库存数据')
                        
                        # 获取库存数据
                        if force_alternate:
                            inventory_records = self.get_inventory_data_alternatively(store.id)
                            logger.info(f'使用备用方法获取库存数据')
                        else:
                            inventory_records = self.get_store_inventory(store.id)
                        
                        # 如果没有获取到数据，尝试备用方法
                        if not inventory_records and not force_alternate:
                            logger.warning(f'标准方法获取失败，尝试备用方法')
                            inventory_records = self.get_inventory_data_alternatively(store.id)
                        
                        # 处理获取到的数据
                        if inventory_records:
                            logger.info(f'获取到 {len(inventory_records)} 条库存记录')
                            
                            # 为每个记录更新30天销量和健康指标
                            for record in inventory_records:
                                # 从数据库计算30天销量
                                sales_30d = self.get_sales_30d(record['asin'], store.id)
                                if sales_30d > 0:
                                    record['sellable_quantity_30d'] = sales_30d
                                    
                                    # 计算库存健康指标
                                    health_metrics = self.calculate_inventory_health(
                                        record['instock_quantity'],
                                        record['inbound_quantity'],
                                        sales_30d
                                    )
                                    
                                    # 更新库存指标
                                    record['inventory_turnover'] = health_metrics['inventory_turnover']
                                    record['days_of_coverage'] = health_metrics['days_of_coverage']
                                    record['inventory_health'] = health_metrics['health_status']
                                    record['status_icon'] = health_metrics['status_color']
                                    record['reorder_suggestion'] = health_metrics['reorder_suggestion']
                                
                                # 确保店铺和用户信息
                                record['store_id'] = store.id
                                record['store_name'] = store.store_name
                                record['user_id'] = store.user_id
                        
                        # 更新数据
                        if inventory_records:
                            store_record_count = self.update_inventory_data(inventory_records)
                            store_status = 'success'
                            store_message = f'成功同步 {store_record_count} 条库存数据'
                        else:
                            store_status = 'warning'
                            store_message = '未获取到库存数据'
                        
                    except Exception as e:
                        store_message = f'同步店铺 {store.store_name} 时发生错误: {str(e)}'
                        logger.error(store_message)
                        import traceback
                        logger.error(traceback.format_exc())
                    
                    # 记录店铺同步结果
                    store_end_time = datetime.datetime.utcnow()
                    store_duration = (store_end_time - store_start_time).total_seconds()
                    store_sync_results.append({
                        'store_id': store.id,
                        'store_name': store.store_name,
                        'status': store_status,
                        'message': store_message,
                        'record_count': store_record_count,
                        'duration_seconds': round(store_duration, 2)
                    })
                    
                    record_count += store_record_count
                    
                    # 添加延迟，避免请求过于频繁
                    if i + len(batch) < len(stores_to_sync):
                        time.sleep(2)
            
            # 汇总结果
            success_count = sum(1 for r in store_sync_results if r['status'] == 'success')
            warning_count = sum(1 for r in store_sync_results if r['status'] == 'warning')
            failed_count = sum(1 for r in store_sync_results if r['status'] == 'failed')
            
            sync_status = 'success'
            if failed_count > 0:
                sync_status = 'partial'
            elif warning_count > 0:
                sync_status = 'partial'
            
            sync_message = f'同步完成: 成功 {success_count} 个店铺, 警告 {warning_count} 个, 失败 {failed_count} 个, 总计 {record_count} 条记录'
            logger.info(sync_message)
                
        except Exception as e:
            sync_message = f'同步库存数据时发生错误: {str(e)}'
            logger.error(sync_message)
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # 记录同步日志
            sync_end = datetime.datetime.utcnow()
            sync_log = SyncLog(
                sync_type='inventory',
                store_id=store_id,
                status=sync_status,
                message=sync_message,
                start_time=sync_start,
                end_time=sync_end,
                record_count=record_count,
                user_id=user_id  # 关联用户ID
            )
            self.db_session.add(sync_log)
            self.db_session.commit()
            
        return self._create_sync_result(sync_status, sync_message, record_count, store_sync_results, sync_start, sync_end)
    
    def _create_sync_result(self, status, message, record_count, store_results, start_time, end_time):
        """创建统一格式的同步结果"""
        duration = (end_time - start_time).total_seconds()
        
        return {
            'status': status,
            'message': message,
            'record_count': record_count,
            'duration_seconds': round(duration, 2),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'store_results': store_results
        }
    
    def sync_all_stores(self, user_id=None):
        """同步所有店铺的库存数据 - 模拟实现"""
        try:
            self.logger.info("开始模拟同步所有店铺库存数据")
            
            # 模拟处理延迟
            time.sleep(2)
            
            # 模拟生成统计数据
            stats = {
                'total_stores': random.randint(2, 5),
                'processed_stores': random.randint(2, 5),
                'total_inventory_items': random.randint(100, 500),
                'updated_items': random.randint(50, 300),
                'status': 'success' if random.random() > 0.05 else 'partial_success'
            }
            
            self.logger.info(f"库存数据同步完成 - 状态: {stats['status']}, 更新项目: {stats['updated_items']}")
            return stats
            
        except Exception as e:
            self.logger.error(f"库存数据同步失败: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'total_stores': 0,
                'processed_stores': 0,
                'total_inventory_items': 0,
                'updated_items': 0
            }

# 使用示例
if __name__ == '__main__':
    # 示例：同步指定店铺的库存数据
    inventory_data = AmazonInventoryData()
    
    # 同步库存数据
    # 注意：实际使用时需要提供有效的店铺ID
    # result = inventory_data.sync_inventory_data(store_id=1)
    # print(f"同步结果: {result}")
    
    # 同步所有店铺的数据
    # results = inventory_data.sync_all_stores()
    # for result in results:
    #     print(f"店铺: {result['store_name']}, 状态: {result['status']}, 记录数: {result['record_count']}")
