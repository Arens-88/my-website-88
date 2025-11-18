import datetime
import logging
import random
import time
from models import init_db

# 模拟AmazonOAuth类
class MockAmazonOAuth:
    def get_store_access_token(self, *args, **kwargs):
        return "mock_access_token"
    
    def refresh_token_if_needed(self, *args, **kwargs):
        return True

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_sales')

class AmazonSalesData:
    """亚马逊销售/订单数据抓取模块"""
    
    # 销售API端点
    SALES_API_ENDPOINT = 'https://sellingpartnerapi-na.amazon.com/sales/v1/orderMetrics'
    
    # 多区域API端点配置
    SALES_API_ENDPOINTS = {
        'na': 'https://sellingpartnerapi-na.amazon.com/sales/v1/orderMetrics',
        'eu': 'https://sellingpartnerapi-eu.amazon.com/sales/v1/orderMetrics',
        'fe': 'https://sellingpartnerapi-fe.amazon.com/sales/v1/orderMetrics'
    }
    
    # API调用重试配置
    MAX_RETRIES = 5
    RETRY_DELAY_BASE = 5  # 基础延迟（秒）
    
    # API速率限制配置
    API_RATE_LIMIT = {
        'sales_request': 10,  # 每分钟请求次数
        'sales_download': 5   # 每分钟下载次数
    }
    
    # 区域市场映射
    MARKETPLACE_REGIONS = {
        'US': {'region': 'na', 'marketplace_id': 'ATVPDKIKX0DER'},
        'UK': {'region': 'eu', 'marketplace_id': 'A1F83G8C2ARO7P'},
        'DE': {'region': 'eu', 'marketplace_id': 'A1PA6795UKMFR9'},
        'FR': {'region': 'eu', 'marketplace_id': 'A13V1IB3VIYZZH'},
        'IT': {'region': 'eu', 'marketplace_id': 'APJ6JRA9NG5V4'},
        'ES': {'region': 'eu', 'marketplace_id': 'A1RKKUPIHCS9HS'},
        'JP': {'region': 'fe', 'marketplace_id': 'A1VC38T7YXB528'}
    }
    
    def __init__(self, db_session=None, user_id=None, is_admin=False):
        self.db_session = db_session or init_db()
        self.user_id = user_id
        self.is_admin = is_admin
        self.oauth_manager = MockAmazonOAuth()  # 使用模拟的OAuth管理器
        
        # API调用时间跟踪，用于速率限制
        self.api_calls = {
            'sales_request': [],
            'sales_download': []
        }
    
    def get_date_range(self, days_back=1):
        """获取日期范围，默认获取前一天的数据"""
        end_date = datetime.datetime.utcnow().date()
        start_date = end_date - datetime.timedelta(days=days_back)
        return start_date, end_date
    
    def format_date(self, date_obj):
        """格式化日期为API需要的格式"""
        return date_obj.strftime('%Y-%m-%d')
    
    def parse_sales_response(self, response_data, store_id, store_name, start_date, end_date):
        """解析销售API响应数据"""
        sales_records = []
        processed_asin_dates = set()  # 用于去重
        
        try:
            # 字段映射配置
            FIELD_MAPPINGS = {
                'asin': 'asin',
                'date': 'date',
                'unitsOrdered': 'order_count',
                'orderedProductSales': 'sales_amount',
                'unitsOrderedB2B': 'platform_fee'
            }
            
            # 检查响应数据格式
            if not isinstance(response_data, dict):
                logger.error(f'响应数据格式错误，预期字典类型: {type(response_data)}')
                return []
            
            # 遍历API响应中的每个数据点
            if 'payload' in response_data and 'orderMetrics' in response_data['payload']:
                for metric in response_data['payload']['orderMetrics']:
                    try:
                        # 检查必要字段是否存在
                        if not all(key in metric for key in ['asin', 'date']):
                            logger.warning(f'跳过缺少必要字段的记录: {metric}')
                            continue
                            
                        asin = metric['asin'].strip()
                        date_str = metric['date']
                        
                        # 验证ASIN格式
                        if not asin or len(asin) < 10:
                            logger.warning(f'ASIN格式无效: {asin}')
                            continue
                            
                        try:
                            order_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            logger.warning(f'日期格式错误: {date_str}')
                            continue
                        
                        # 生成唯一键用于去重
                        unique_key = f'{asin}-{date_str}'
                        if unique_key in processed_asin_dates:
                            logger.warning(f'发现重复记录: {unique_key}')
                            continue
                        processed_asin_dates.add(unique_key)
                        
                        # 获取销售指标并进行数据验证
                        order_count = max(0, int(metric.get('unitsOrdered', 0)))  # 确保为非负数
                        
                        # 处理销售额数据
                        sales_amount = 0.0
                        ordered_sales = metric.get('orderedProductSales', {})
                        if isinstance(ordered_sales, dict) and 'amount' in ordered_sales:
                            try:
                                sales_amount = max(0.0, float(ordered_sales['amount']))  # 确保为非负数
                            except (ValueError, TypeError):
                                logger.warning(f'销售额格式错误: {ordered_sales}')
                        
                        # 平台费用（简化处理）
                        platform_fee = max(0.0, float(metric.get('unitsOrderedB2B', 0)))  # 确保为非负数
                        
                        # 异常值检测
                        is_exception = 0
                        if sales_amount > 100000:
                            is_exception = 1
                            logger.warning(f'检测到异常销售额: {sales_amount}，ASIN: {asin}')
                        elif order_count > 1000:
                            is_exception = 1
                            logger.warning(f'检测到异常订单量: {order_count}，ASIN: {asin}')
                        
                        # 构建记录
                        record = {
                            'asin': asin,
                            'order_date': order_date,
                            'store_id': store_id,
                            'store_name': store_name,
                            'order_count': order_count,
                            'sales_amount': sales_amount,
                            'platform_fee': platform_fee,
                            'is_exception': is_exception,
                            'is_estimated': 0  # 标记为实际数据
                        }
                        
                        sales_records.append(record)
                        
                    except Exception as e:
                        logger.error(f'处理单条销售记录时出错: {str(e)}, 记录: {metric}')
                        continue
            
            logger.info(f'成功解析 {len(sales_records)} 条销售记录，去重 {len(processed_asin_dates)} 个ASIN-日期组合')
            return sales_records
            
        except Exception as e:
            logger.error(f'解析销售数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def save_sales_data(self, sales_records):
        """保存销售数据到数据库，支持批量处理和数据验证"""
        if not sales_records:
            logger.warning("没有销售数据需要保存")
            return 0
        
        try:
            # 批量处理配置
            BATCH_SIZE = 100
            saved_count = 0
            updated_count = 0
            skipped_count = 0
            
            # 按批次处理记录
            for i in range(0, len(sales_records), BATCH_SIZE):
                batch = sales_records[i:i+BATCH_SIZE]
                
                for record in batch:
                    try:
                        # 数据验证
                        required_fields = ['asin', 'order_date', 'store_id']
                        if not all(field in record for field in required_fields):
                            logger.warning(f'跳过缺少必要字段的记录: {record}')
                            skipped_count += 1
                            continue
                        
                        # 确保包含user_id字段
                        if 'user_id' not in record:
                            # 尝试从店铺获取用户ID
                            store = self.db_session.query(AmazonStore).filter_by(id=record['store_id']).first()
                            if store:
                                record['user_id'] = store.user_id
                            else:
                                logger.error(f'无法找到店铺信息，跳过记录: {record}')
                                skipped_count += 1
                                continue
                        
                        # 查找是否已存在相同ASIN和日期的记录
                        existing_record = self.db_session.query(AmazonIntegratedData).filter_by(
                            asin=record['asin'],
                            order_date=record['order_date'],
                            store_id=record['store_id'],
                            user_id=record.get('user_id')
                        ).first()
                        
                        # 准备更新字段
                        update_fields = {
                            'order_count': record.get('order_count', 0),
                            'sales_amount': record.get('sales_amount', 0.0),
                            'platform_fee': record.get('platform_fee', 0.0),
                            'is_exception': record.get('is_exception', 0),
                            'is_estimated': record.get('is_estimated', 0),
                            'updated_at': datetime.datetime.utcnow()
                        }
                        
                        if existing_record:
                            # 检查是否有变化
                            has_changes = False
                            for key, value in update_fields.items():
                                if hasattr(existing_record, key) and getattr(existing_record, key) != value:
                                    has_changes = True
                                    setattr(existing_record, key, value)
                            
                            if has_changes:
                                updated_count += 1
                                # 记录增量更新
                                logger.debug(f'更新记录: ASIN={record["asin"]}, 日期={record["order_date"]}, '\
                                           f'订单量={record["order_count"]}, 销售额={record["sales_amount"]}')
                        else:
                            # 创建新记录
                            new_record = AmazonIntegratedData(**record)
                            self.db_session.add(new_record)
                            saved_count += 1
                            logger.debug(f'新增记录: ASIN={record["asin"]}, 日期={record["order_date"]}, '\
                                       f'订单量={record["order_count"]}, 销售额={record["sales_amount"]}')
                    
                    except Exception as e:
                        logger.error(f'处理单条记录时出错: {str(e)}, 记录: {record}')
                        skipped_count += 1
                        continue
                
                # 提交批次
                self.db_session.commit()
            
            total_processed = saved_count + updated_count
            logger.info(f'销售数据保存完成 - 新增: {saved_count}, 更新: {updated_count}, '\
                      f'跳过: {skipped_count}, 总计: {total_processed}/{len(sales_records)}')
            return total_processed
            
        except Exception as e:
            logger.error(f'保存销售数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            self.db_session.rollback()
            return 0
    
    def _respect_rate_limit(self, api_type):
        """遵守API速率限制，确保不超过Amazon的API调用限制"""
        if api_type not in self.api_calls:
            return
        
        # 获取当前时间
        current_time = time.time()
        
        # 清理过期的调用记录（保留最近60秒的记录）
        self.api_calls[api_type] = [t for t in self.api_calls[api_type] if current_time - t < 60]
        
        # 检查是否达到速率限制
        max_calls = self.API_RATE_LIMIT.get(api_type, 10)  # 默认每分钟10次
        if len(self.api_calls[api_type]) >= max_calls:
            # 计算需要等待的时间
            oldest_call = min(self.api_calls[api_type])
            wait_time = 60 - (current_time - oldest_call) + 0.1  # 加0.1秒保险
            if wait_time > 0:
                logger.info(f'API速率限制，等待 {wait_time:.2f} 秒...')
                time.sleep(wait_time)
        
        # 记录本次调用
        self.api_calls[api_type].append(time.time())
    
    def fetch_sales_data(self, store_id, start_date, end_date):
        """从亚马逊API获取销售数据，支持多区域、API速率限制和备用端点"""
        # 获取店铺信息
        store = self.oauth_manager.get_store_by_id(store_id)
        if not store:
            logger.error(f'未找到ID为 {store_id} 的店铺')
            return []
        
        # 获取访问令牌
        access_token = self.oauth_manager.get_valid_access_token(store_id)
        if not access_token:
            logger.error(f'无法获取店铺 {store.store_name} 的有效访问令牌')
            return []
        
        # 根据店铺区域选择正确的API端点
        region = getattr(store, 'region', 'US').upper()
        marketplace_info = self.MARKETPLACE_REGIONS.get(region, self.MARKETPLACE_REGIONS['US'])
        endpoint_region = marketplace_info['region']
        marketplace_id = marketplace_info['marketplace_id']
        
        # 准备API请求头
        headers = {
            'x-amz-access-token': access_token,
            'Content-Type': 'application/json'
        }
        
        # 准备请求参数
        params = {
            'marketplaceIds': marketplace_id,
            'interval': 'DAY',
            'startDate': self.format_date(start_date),
            'endDate': self.format_date(end_date),
            'granularity': 'Day'
        }
        
        # 获取API端点
        endpoint = self.SALES_API_ENDPOINTS.get(endpoint_region, self.SALES_API_ENDPOINTS['na'])
        
        # 带重试的API请求
        all_sales_records = []
        
        # 日期范围较大时，分批获取（每次最多90天）
        batch_size = 90
        current_start = start_date
        
        while current_start <= end_date:
            batch_end = min(current_start + datetime.timedelta(days=batch_size-1), end_date)
            params['startDate'] = self.format_date(current_start)
            params['endDate'] = self.format_date(batch_end)
            
            logger.info(f'获取店铺 {store.store_name} 的销售数据批次，日期范围: {params["startDate"]} 至 {params["endDate"]}')
            
            batch_records = self._fetch_sales_data_batch(store, headers, params, endpoint)
            all_sales_records.extend(batch_records)
            
            # 移动到下一批
            current_start = batch_end + datetime.timedelta(days=1)
            
            # 如果还有更多批次，添加短暂延迟
            if current_start <= end_date:
                logger.info(f'准备获取下一批数据，暂停2秒...')
                time.sleep(2)
        
        # 去重处理（跨批次可能出现重复）
        unique_records = []
        seen = set()
        for record in all_sales_records:
            key = f'{record["asin"]}-{record["order_date"]}-{record["store_id"]}'
            if key not in seen:
                seen.add(key)
                unique_records.append(record)
        
        logger.info(f'成功获取店铺 {store.store_name} 的所有销售数据，原始记录数: {len(all_sales_records)}, 去重后: {len(unique_records)}')
        return unique_records
    
    def _fetch_sales_data_batch(self, store, headers, params, endpoint):
        """获取单个批次的销售数据"""
        for retry_count in range(self.MAX_RETRIES):
            try:
                # 遵守API速率限制
                self._respect_rate_limit('sales_request')
                
                response = requests.get(
                    endpoint,
                    headers=headers,
                    params=params,
                    timeout=60
                )
                
                # 检查响应状态
                response.raise_for_status()
                
                # 解析响应数据
                response_data = response.json()
                sales_records = self.parse_sales_response(
                    response_data, 
                    store.id, 
                    store.store_name,
                    datetime.datetime.strptime(params['startDate'], '%Y-%m-%d').date(),
                    datetime.datetime.strptime(params['endDate'], '%Y-%m-%d').date()
                )
                
                return sales_records
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else 'Unknown'
                
                if status_code == 401:
                    # Token可能过期，强制刷新
                    logger.warning(f'API返回401错误，强制刷新令牌')
                    self.oauth_manager.refresh_access_token(store)
                    access_token = store.access_token
                    headers['x-amz-access-token'] = access_token
                elif status_code == 429:
                    # API速率限制，需要等待更长时间
                    retry_after = int(e.response.headers.get('Retry-After', 30))
                    logger.warning(f'API速率限制（429），服务器建议等待 {retry_after} 秒')
                    time.sleep(retry_after + random.uniform(1, 3))  # 添加随机延迟
                elif status_code >= 500:
                    # 服务器错误，添加随机退避
                    logger.error(f'服务器错误: {str(e)}，状态码: {status_code}')
                else:
                    logger.error(f'HTTP错误: {str(e)}，状态码: {status_code}')
                    
                # 超过重试次数则放弃
                if retry_count >= self.MAX_RETRIES - 1:
                    break
            
            except requests.exceptions.Timeout:
                logger.error('API请求超时')
                if retry_count >= self.MAX_RETRIES - 1:
                    break
            
            except Exception as e:
                logger.error(f'获取销售数据时发生错误: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())
                
                # 超过重试次数则放弃
                if retry_count >= self.MAX_RETRIES - 1:
                    break
            
            # 计算指数退避延迟，添加随机抖动
            base_delay = self.RETRY_DELAY_BASE * (2 ** retry_count)
            jitter = random.uniform(0.8, 1.2)  # 80%-120%的随机抖动
            delay = base_delay * jitter
            
            logger.info(f'重试 {retry_count + 1}/{self.MAX_RETRIES}，等待 {delay:.2f} 秒...')
            time.sleep(delay)
        
        return []
    
    def get_sales_data_alternatively(self, store_id, start_date, end_date):
        """备用销售数据获取方法，当主API不可用时使用"""
        logger.warning(f'使用备用方法获取销售数据，店铺ID: {store_id}')
        
        # 这里可以实现从其他API或报表获取销售数据的逻辑
        # 例如：订单API、销售报表等
        
        # 示例实现（返回空列表，实际项目中需要根据具体情况实现）
        return []
    
    def sync_sales_data(self, store_id=None, days_back=1, target_date=None, user_id=None, force_update=False):
        """同步销售数据主函数
        
        Args:
            store_id: 店铺ID，为None时同步所有店铺
            days_back: 回溯天数
            target_date: 目标同步日期，优先级高于days_back
            user_id: 用户ID，用于数据隔离和权限控制
            force_update: 是否强制更新已存在的数据
        """
        # 记录同步开始时间
        sync_start = datetime.datetime.utcnow()
        sync_status = 'failed'
        sync_message = ''
        record_count = 0
        store_sync_results = []
        
        try:
            # 验证用户权限
            if user_id is None and not self.is_admin:
                raise ValueError("必须提供用户ID进行数据隔离")
            
            # 获取日期范围
            if target_date:
                start_date = target_date
                end_date = target_date
                logger.info(f'同步指定日期 {start_date} 的销售数据')
            else:
                start_date, end_date = self.get_date_range(days_back)
                logger.info(f'同步日期范围 {start_date} 至 {end_date} 的销售数据，回溯 {days_back} 天')
            
            # 验证日期范围有效性
            if start_date > end_date:
                raise ValueError(f'无效的日期范围: {start_date} 晚于 {end_date}')
            
            # 验证日期范围长度
            date_diff = (end_date - start_date).days
            if date_diff > 365:
                raise ValueError(f'日期范围过大，最多支持365天，当前请求 {date_diff} 天')
            
            # 获取店铺列表
            stores_to_sync = []
            if store_id:
                # 使用OAuth模块获取店铺并验证权限
                store = self.oauth_manager.get_store_by_user_and_id(store_id, user_id=user_id)
                if not store:
                    raise ValueError(f"店铺ID {store_id} 不存在或无权限访问")
                if not store.is_active:
                    raise ValueError(f"店铺 {store.store_name} 当前未激活")
                stores_to_sync = [store]
                logger.info(f'同步单个店铺: {store.store_name} (ID: {store.id})')
            else:
                # 使用OAuth模块获取用户的所有激活店铺
                stores_to_sync = self.oauth_manager.get_active_stores(user_id=user_id)
                logger.info(f'同步用户 {user_id} 的 {len(stores_to_sync)} 个激活店铺')
            
            # 如果没有店铺需要同步，直接返回成功
            if not stores_to_sync:
                sync_status = 'success'
                sync_message = '没有激活的店铺需要同步'
                record_count = 0
                return {
                    'status': sync_status,
                    'message': sync_message,
                    'record_count': record_count,
                    'store_results': []
                }
            
            # 分批处理店铺以避免超时
            BATCH_SIZE = 5
            total_records = 0
            total_success = 0
            total_failed = 0
            
            for i in range(0, len(stores_to_sync), BATCH_SIZE):
                batch = stores_to_sync[i:i+BATCH_SIZE]
                
                for store in batch:
                    store_start = datetime.datetime.utcnow()
                    store_success = True
                    store_records = 0
                    
                    try:
                        logger.info(f'开始同步店铺 {store.store_name} 的销售数据')
                        
                        # 检查是否有最近的成功同步记录，如果有且未强制更新，可以跳过
                        if not force_update:
                            recent_sync = self.db_session.query(SyncLog).filter_by(
                                user_id=store.user_id,
                                store_id=store.id,
                                sync_type='sales',
                                status='success'
                            ).order_by(SyncLog.end_time.desc()).first()
                            
                            if recent_sync and recent_sync.end_time > sync_start - datetime.timedelta(hours=1):
                                logger.info(f'店铺 {store.store_name} 最近1小时内已成功同步，跳过本次同步')
                                store_records = recent_sync.record_count
                                store_sync_results.append({
                                    'store_id': store.id,
                                    'store_name': store.store_name,
                                    'status': 'skipped',
                                    'message': '最近1小时内已同步',
                                    'record_count': store_records,
                                    'sync_time': (datetime.datetime.utcnow() - store_start).total_seconds()
                                })
                                continue
                        
                        # 获取销售数据
                        sales_records = self.fetch_sales_data(store.id, start_date, end_date)
                        
                        # 检查是否获取到数据
                        if not sales_records:
                            # 如果主方法失败，尝试备用方法
                            logger.warning(f'主方法未获取到店铺 {store.store_name} 的数据，尝试备用方法')
                            sales_records = self.get_sales_data_alternatively(store.id, start_date, end_date)
                        
                        # 为每条记录添加店铺和用户信息
                        for record in sales_records:
                            record['store_id'] = store.id
                            record['user_id'] = store.user_id
                        
                        # 保存数据
                        if sales_records:
                            store_records = self.save_sales_data(sales_records)
                            total_records += store_records
                            logger.info(f'店铺 {store.store_name} 同步完成，共 {store_records} 条记录')
                        else:
                            logger.warning(f'未获取到店铺 {store.store_name} 的销售数据')
                            store_records = 0
                            store_success = False
                        
                    except Exception as e:
                        error_msg = f'同步店铺 {store.store_name} 时出错: {str(e)}'
                        logger.error(error_msg)
                        import traceback
                        logger.error(traceback.format_exc())
                        store_success = False
                        store_records = 0
                    
                    # 记录店铺同步结果
                    store_sync_results.append({
                        'store_id': store.id,
                        'store_name': store.store_name,
                        'status': 'success' if store_success else 'failed',
                        'message': f'同步 {store_records} 条记录' if store_success else '同步失败',
                        'record_count': store_records,
                        'sync_time': (datetime.datetime.utcnow() - store_start).total_seconds()
                    })
                    
                    if store_success:
                        total_success += 1
                    else:
                        total_failed += 1
                    
                    # 添加短暂延迟避免API调用过于频繁
                    if i + 1 < len(stores_to_sync):
                        time.sleep(1)
            
            # 设置同步结果
            record_count = total_records
            sync_status = 'success' if total_success > 0 and total_failed == 0 else 'partial' if total_success > 0 else 'failed'
            
            if sync_status == 'success':
                sync_message = f'成功同步所有 {total_success} 个店铺，共 {record_count} 条销售数据'
            elif sync_status == 'partial':
                sync_message = f'部分同步成功 - 成功: {total_success}, 失败: {total_failed}, 总计: {record_count} 条记录'
            else:
                sync_message = f'所有店铺同步失败，失败数: {total_failed}'
                
        except Exception as e:
            sync_message = f'同步销售数据时发生错误: {str(e)}'
            logger.error(sync_message)
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # 记录同步日志
            sync_end = datetime.datetime.utcnow()
            sync_duration = (sync_end - sync_start).total_seconds()
            
            sync_log = SyncLog(
                sync_type='sales',
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
            
            logger.info(f'销售数据同步完成 - 状态: {sync_status}, 记录数: {record_count}, 耗时: {sync_duration:.2f} 秒')
            
        return {
            'status': sync_status,
            'message': sync_message,
            'record_count': record_count,
            'store_results': store_sync_results,
            'sync_duration': (datetime.datetime.utcnow() - sync_start).total_seconds()
        }
    
    def sync_all_stores(self, days_back=1, user_id=None, force_update=False):
        """同步所有激活店铺的销售数据 - 模拟实现，避免实际API调用
        
        Args:
            days_back: 回溯天数
            user_id: 用户ID，如果提供则只同步该用户的店铺
            force_update: 是否强制更新已存在的数据
        """
        start_time = time.time()
        logger.info(f'开始同步所有激活店铺的销售数据，回溯 {days_back} 天')
        
        # 模拟同步过程
        time.sleep(3)  # 模拟同步延迟
        
        # 生成模拟统计数据
        mock_stores_count = 3
        store_results = []
        
        # 模拟每个店铺的同步结果
        for i in range(mock_stores_count):
            store_results.append({
                'store_id': i + 1,
                'store_name': f'模拟店铺{i+1}',
                'status': 'success',
                'message': '同步成功',
                'record_count': random.randint(10, 100),
                'sync_time': random.uniform(0.5, 2.0)
            })
        
        # 生成总记录数
        total_records = sum(store['record_count'] for store in store_results)
        
        # 计算统计信息
        total_stores = len(store_results)
        success_stores = sum(1 for s in store_results if s['status'] == 'success')
        failed_stores = sum(1 for s in store_results if s['status'] == 'failed')
        skipped_stores = sum(1 for s in store_results if s['status'] == 'skipped')
        
        sync_duration = time.time() - start_time
        
        # 添加详细的统计信息
        summary = {
            'total_stores': total_stores,
            'success_stores': success_stores,
            'failed_stores': failed_stores,
            'skipped_stores': skipped_stores,
            'total_records': total_records,
            'sync_duration': sync_duration,
            'average_store_time': sync_duration / total_stores if total_stores > 0 else 0,
            'success_rate': (success_stores / total_stores * 100) if total_stores > 0 else 0
        }
        
        logger.info(f'所有店铺销售数据同步完成 - 成功率: {summary["success_rate"]:.1f}%, '\
                  f'店铺数: 成功={success_stores}, 失败={failed_stores}, 跳过={skipped_stores}, '\
                  f'总记录: {summary["total_records"]}, 耗时: {summary["sync_duration"]:.2f} 秒')
        
        return {
            'status': 'success',
            'message': f'成功同步 {success_stores} 个店铺，共 {total_records} 条记录',
            'record_count': total_records,
            'store_results': store_results,
            'sync_duration': sync_duration,
            'summary': summary
        }

# 使用示例
if __name__ == '__main__':
    # 示例：同步指定店铺的销售数据
    sales_data = AmazonSalesData()
    
    # 同步最近1天的数据
    # 注意：实际使用时需要提供有效的店铺ID
    # result = sales_data.sync_sales_data(store_id=1)
    # print(f"同步结果: {result}")
    
    # 同步所有店铺的数据
    # results = sales_data.sync_all_stores()
    # for result in results:
    #     print(f"店铺: {result['store_name']}, 状态: {result['status']}, 记录数: {result['record_count']}")
