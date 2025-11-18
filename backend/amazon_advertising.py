# 移除requests依赖
import datetime
import logging
import json
import random
import time
from models import AmazonIntegratedData, AmazonStore, SyncLog, init_db
from amazon_oauth import AmazonOAuth
from retry_utils import api_heavy_retry, RetryError, network_retry_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_advertising')

class AmazonAdvertisingData:
    """亚马逊广告数据处理类 - 模拟实现"""
    
    def __init__(self, db_session=None):
        self.logger = logger
        self.db_session = db_session
    
    def sync_all_stores(self, days_back=1, user_id=None, date_range=None):
        """模拟同步所有店铺的广告数据"""
        self.logger.info(f'模拟同步所有店铺广告数据 - 用户ID: {user_id}, 天数回溯: {days_back}, 日期范围: {date_range}')
        
        # 模拟返回结果
        results = [
            {
                'store_id': 1,
                'store_name': 'Mock Store 1',
                'status': 'success',
                'message': '同步成功',
                'record_count': 100
            },
            {
                'store_id': 2,
                'store_name': 'Mock Store 2', 
                'status': 'success',
                'message': '同步成功',
                'record_count': 150
            }
        ]
        
        return results
    
    def __init__(self, db_session=None, user_id=None, is_admin=False):
        self.db_session = db_session
        self.user_id = user_id
        self.is_admin = is_admin
        self.logger = logging.getLogger('amazon_advertising')
        # 移除实际API调用依赖
    
    def get_date_range(self, days_back=1):
        """获取日期范围，默认获取前一天的数据"""
        end_date = datetime.datetime.utcnow().date()
        start_date = end_date - datetime.timedelta(days=days_back)
        return start_date, end_date
    
    def format_date(self, date_obj):
        """格式化日期为API需要的格式"""
        return date_obj.strftime('%Y-%m-%d')
    
    def _respect_rate_limit(self, api_type):
        """遵守API速率限制"""
        now = datetime.datetime.utcnow()
        last_call = self.last_api_call_time.get(api_type, now)
        
        # 计算需要等待的时间（基于速率限制）
        if api_type == 'report_request':
            required_interval = 60.0 / self.API_RATE_LIMIT['report_request']
        elif api_type == 'report_download':
            required_interval = 60.0 / self.API_RATE_LIMIT['report_download']
        else:
            return
        
        time_since_last_call = (now - last_call).total_seconds()
        if time_since_last_call < required_interval:
            wait_time = required_interval - time_since_last_call
            logger.debug(f'遵守API速率限制，等待 {wait_time:.2f} 秒')
            time.sleep(wait_time)
        
        # 更新最后调用时间
        self.last_api_call_time[api_type] = datetime.datetime.utcnow()
    
    @network_retry_manager.retry_on([requests.exceptions.RequestException, json.JSONDecodeError])
    def get_advertising_report(self, store_id, start_date, end_date, report_type='PRODUCT_AD'):
        """获取广告报表
        
        Args:
            store_id: 店铺ID
            start_date: 开始日期
            end_date: 结束日期
            report_type: 报表类型，支持PRODUCT_AD, KEYWORD, CAMPAIGN, AD_GROUP
            
        Returns:
            解析后的广告数据列表
        """
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
        
        # 准备API请求头
        headers = {
            'x-amz-access-token': access_token,
            'Content-Type': 'application/json',
            'Amazon-Advertising-API-ClientId': store.client_id
        }
        
        # 获取报表类型ID
        report_type_id = self.REPORT_TYPE_IDS.get(report_type, 'spAdvertisedProduct')
        
        # 准备报表请求数据
        report_request = {
            'name': f'Advertising Performance Report {datetime.datetime.now().strftime("%Y%m%d")}',
            'startDate': self.format_date(start_date),
            'endDate': self.format_date(end_date),
            'metrics': 'impressions,clicks,cost,attributedConversions1d,attributedSales1d',
            'reportTypeId': report_type_id,
            'groupBy': ['asin', 'adGroup'] if report_type == 'PRODUCT_AD' else []
        }
        
        # 带重试的API请求
        report_id = None
        for retry_count in range(self.MAX_RETRIES):
            try:
                # 遵守API速率限制
                self._respect_rate_limit('report_request')
                
                logger.info(f'请求店铺 {store.store_name} 的广告报表，日期范围: {report_request["startDate"]} 至 {report_request["endDate"]}')
                
                # 选择正确的API端点
                endpoint = self.ADVERTISING_API_ENDPOINT if not hasattr(store, 'api_region') or store.api_region == 'na' else \
                           f'https://advertising-api.amazon.com/v2/sp/campaigns/report'
                
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=report_request,
                    timeout=60
                )
                
                # 检查响应状态
                response.raise_for_status()
                
                # 获取报表ID
                response_data = response.json()
                report_id = response_data.get('reportId')
                
                logger.info(f'广告报表请求成功，报表ID: {report_id}')
                break
                
            except requests.exceptions.HTTPError as e:
                status_code = response.status_code
                logger.error(f'HTTP错误: {str(e)}，状态码: {status_code}')
                
                if status_code == 401:
                    # Token可能过期，强制刷新
                    logger.warning(f'API返回401错误，强制刷新令牌')
                    self.oauth_manager.refresh_access_token(store)
                    access_token = store.access_token
                    headers['x-amz-access-token'] = access_token
                elif status_code == 429:
                    # 速率限制
                    retry_after = response.headers.get('Retry-After', self.RETRY_DELAY_BASE * (2 ** retry_count))
                    logger.warning(f'API请求速率受限，需要等待 {retry_after} 秒')
                    time.sleep(float(retry_after))
                elif status_code == 503:
                    # 服务不可用
                    logger.warning(f'API服务暂时不可用')
                else:
                    # 其他错误，重试次数用完则失败
                    if retry_count >= self.MAX_RETRIES - 1:
                        raise
                
            except Exception as e:
                logger.error(f'请求广告报表时发生错误: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())
                
                # 超过重试次数则放弃
                if retry_count >= self.MAX_RETRIES - 1:
                    raise
                
            # 指数退避重试
            if retry_count < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAY_BASE * (2 ** retry_count) + random.uniform(0, 1)  # 添加随机抖动
                logger.info(f'等待 {delay:.2f} 秒后重试')
                time.sleep(delay)
        
        if not report_id:
            raise ValueError('无法获取广告报表ID')
        
        # 查询报表状态和下载URL
        report_url = None
        max_wait_seconds = 600  # 最多等待10分钟
        wait_interval_seconds = 5
        total_wait_seconds = 0
        
        while total_wait_seconds < max_wait_seconds:
            try:
                time.sleep(wait_interval_seconds)
                total_wait_seconds += wait_interval_seconds
                
                status_response = requests.get(
                    f'{self.ADVERTISING_API_ENDPOINT}/{report_id}',
                    headers=headers,
                    timeout=60
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                
                if status_data.get('status') == 'COMPLETED':
                    report_url = status_data.get('url')
                    logger.info(f'广告报表已生成，下载URL: {report_url}')
                    break
                elif status_data.get('status') in ['FAILED', 'CANCELLED']:
                    error_message = status_data.get('errorMessage', 'Unknown error')
                    logger.error(f'广告报表生成失败，状态: {status_data.get("status")}, 错误: {error_message}')
                    raise ValueError(f'广告报表生成失败: {status_data.get("status")} - {error_message}')
                    
            except Exception as e:
                logger.error(f'检查广告报表状态时发生错误: {str(e)}')
                
                # 如果是最后一次尝试
                if total_wait_seconds >= max_wait_seconds - wait_interval_seconds:
                    raise
        
        if not report_url:
            raise ValueError(f'广告报表生成超时 (已等待 {max_wait_seconds} 秒)')
        
        # 获取报表数据
        logger.info(f'下载广告报表数据')
        report_response = requests.get(report_url, timeout=300)
        report_response.raise_for_status()
        
        return self.parse_report_data(report_response.content, store_id, store.store_name)
    
    def parse_report_data(self, report_content, store_id, store_name):
        """解析广告报表数据，支持多种格式和字段映射，使用ad_spend字段名"""
        import csv
        import io
        import chardet
        
        ad_records = []
        
        try:
            # 检测文件编码
            detected_encoding = chardet.detect(report_content)
            encoding = detected_encoding['encoding'] or 'utf-8-sig'
            
            # 假设报表是CSV格式，尝试不同的分隔符
            csv_data = report_content.decode(encoding)
            
            # 尝试使用逗号或制表符作为分隔符
            for delimiter in [',', '\t', ';']:
                try:
                    csv_reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter)
                    # 验证分隔符是否有效
                    header = next(csv_reader, None)
                    if header:
                        # 重置reader
                        csv_reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter)
                        break
                except csv.Error:
                    continue
            else:
                raise ValueError('无法识别CSV分隔符')
            
            # 字段映射配置
            field_mappings = {
                'asin': ['asin', 'ASIN', 'productId', 'ProductId'],
                'date': ['date', 'Date', 'reportDate', 'ReportDate'],
                'cost': ['cost', 'attributedCost', 'spend', 'Spend', 'advertisingCost'],
                'impressions': ['impressions', 'Impressions', 'adImpressions'],
                'clicks': ['clicks', 'Clicks', 'adClicks'],
                'conversions': ['attributedConversions1d', 'Conversions', 'attributedUnitsOrdered1d'],
                'sales': ['attributedSales1d', 'Sales', 'attributedRevenue1d'],
                'ad_group': ['adGroup', 'AdGroup', 'adGroupId', 'AdGroupId'],
                'campaign': ['campaign', 'Campaign', 'campaignId', 'CampaignId']
            }
            
            # 统计信息
            total_rows = 0
            processed_rows = 0
            skipped_rows = 0
            
            for row in csv_reader:
                total_rows += 1
                
                # 查找必要字段
                asin = None
                for field in field_mappings['asin']:
                    if field in row and row[field]:
                        asin = row[field].strip()
                        break
                
                date_str = None
                for field in field_mappings['date']:
                    if field in row and row[field]:
                        date_str = row[field].strip()
                        break
                
                # 跳过缺少必要字段的记录
                if not asin or not date_str:
                    skipped_rows += 1
                    continue
                
                # 处理日期格式
                order_date = None
                date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y']
                for fmt in date_formats:
                    try:
                        order_date = datetime.datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if not order_date:
                    logger.warning(f'无法解析日期格式: {date_str}')
                    skipped_rows += 1
                    continue
                
                # 提取广告花费 - 使用ad_spend而不是ad_cost
                ad_spend = 0.0
                for cost_field in field_mappings['cost']:
                    if cost_field in row and row[cost_field]:
                        try:
                            # 处理可能的货币符号和千位分隔符
                            value_str = row[cost_field].strip().replace('$', '').replace(',', '')
                            ad_spend = float(value_str)
                            break
                        except ValueError:
                            continue
                
                # 提取其他可选字段
                ad_data = {
                    'asin': asin,
                    'order_date': order_date,
                    'store_id': store_id,
                    'store_name': store_name,
                    'ad_spend': ad_spend,  # 统一使用ad_spend字段名
                    'is_exception': 0
                }
                
                # 尝试提取其他广告指标
                for metric, possible_fields in field_mappings.items():
                    if metric not in ['asin', 'date', 'cost']:
                        for field in possible_fields:
                            if field in row and row[field]:
                                try:
                                    if metric in ['impressions', 'clicks']:
                                        ad_data[metric] = int(row[field])
                                    elif metric in ['conversions', 'sales']:
                                        # 处理可能的货币格式
                                        value_str = row[field].strip().replace('$', '').replace(',', '')
                                        ad_data[metric] = float(value_str)
                                    else:
                                        ad_data[metric] = row[field].strip()
                                    break
                                except (ValueError, TypeError):
                                    continue
                
                # 检测异常值
                if ad_spend < 0:
                    logger.warning(f'检测到异常广告花费值: {ad_spend} 对于ASIN: {asin}')
                    ad_data['is_exception'] = 1
                
                # 检测异常高的广告花费（例如大于10000）
                if ad_spend > 10000:
                    logger.warning(f'检测到潜在异常高广告花费: {ad_spend} 对于ASIN: {asin}')
                    ad_data['is_exception'] = 1
                
                ad_records.append(ad_data)
                processed_rows += 1
            
            logger.info(f'解析完成 - 处理行数: {processed_rows}, 跳过行数: {skipped_rows}, 总行数: {total_rows}')
            return ad_records
            
        except Exception as e:
            logger.error(f'解析广告报表数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def update_advertising_data(self, ad_records):
        """更新数据库中的广告数据，使用ad_spend字段名称，支持批量处理"""
        if not ad_records:
            logger.warning("没有广告数据需要更新")
            return 0
        
        try:
            updated_count = 0
            new_count = 0
            skipped_count = 0
            
            # 批量处理，每批100条记录
            batch_size = 100
            
            for i in range(0, len(ad_records), batch_size):
                batch = ad_records[i:i+batch_size]
                
                for record in batch:
                    # 确保包含user_id字段
                    if 'user_id' not in record:
                        # 尝试从店铺获取用户ID
                        store = self.db_session.query(AmazonStore).filter_by(id=record['store_id']).first()
                        if store:
                            record['user_id'] = store.user_id
                        else:
                            logger.error(f'找不到店铺ID {record["store_id"]}，跳过此记录')
                            skipped_count += 1
                            continue
                    
                    # 确保必要字段存在
                    required_fields = ['asin', 'order_date', 'store_id', 'user_id']
                    if not all(field in record for field in required_fields):
                        logger.warning(f'缺少必要字段，跳过记录: {record}')
                        skipped_count += 1
                        continue
                    
                    # 查找匹配的记录
                    integrated_record = self.db_session.query(AmazonIntegratedData).filter_by(
                        asin=record['asin'],
                        order_date=record['order_date'],
                        store_id=record['store_id'],
                        user_id=record['user_id']
                    ).first()
                    
                    # 需要更新的字段映射 - 使用ad_spend而不是ad_cost
                    fields_to_update = {
                        'ad_spend': 'ad_spend',  # 统一使用ad_spend字段
                        'ad_group': 'ad_group',
                        'campaign': 'campaign_name',
                        'impressions': 'ad_impressions',
                        'clicks': 'ad_clicks',
                        'conversions': 'ad_conversions',
                        'sales': 'ad_sales',
                        'is_exception': 'is_exception'
                    }
                    
                    if integrated_record:
                        # 更新广告数据
                        updated = False
                        for source_field, target_field in fields_to_update.items():
                            if source_field in record and hasattr(integrated_record, target_field):
                                current_value = getattr(integrated_record, target_field)
                                new_value = record[source_field]
                                
                                # 检查值是否发生变化
                                if current_value != new_value:
                                    setattr(integrated_record, target_field, new_value)
                                    updated = True
                        
                        # 如果数据有更新，增加计数
                        if updated:
                            updated_count += 1
                            # 更新最后修改时间
                            integrated_record.updated_at = datetime.datetime.utcnow()
                    else:
                        # 如果没有匹配记录，准备创建新记录
                        new_record_data = {}
                        for source_field, target_field in fields_to_update.items():
                            if source_field in record:
                                new_record_data[target_field] = record[source_field]
                        
                        # 添加必要字段
                        for field in required_fields:
                            new_record_data[field] = record[field]
                        
                        # 创建新记录
                        new_record = AmazonIntegratedData(**new_record_data)
                        new_record.created_at = datetime.datetime.utcnow()
                        new_record.updated_at = datetime.datetime.utcnow()
                        self.db_session.add(new_record)
                        new_count += 1
                
                # 提交批次
                self.db_session.commit()
            
            total_processed = updated_count + new_count
            logger.info(f'广告数据更新完成 - 更新: {updated_count}, 新增: {new_count}, 跳过: {skipped_count}, 总计: {total_processed}')
            return total_processed
            
        except Exception as e:
            logger.error(f'更新广告数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            self.db_session.rollback()
            return 0
    
    def calculate_roas(self, ad_spend, ad_sales):
        """计算广告支出回报率(ROAS)"""
        if ad_spend > 0 and ad_sales > 0:
            return round(ad_sales / ad_spend, 2)
        return 0.0
    
    @api_heavy_retry
    def sync_advertising_data(self, store_id=None, days_back=1, target_date=None, user_id=None, date_range=None):
        """同步广告数据主函数，支持日期范围和增强的错误处理
        
        Args:
            store_id: 店铺ID，为None时同步所有店铺
            days_back: 回溯天数
            target_date: 目标同步日期，优先级高于days_back
            user_id: 用户ID，用于数据隔离和权限控制
            date_range: 日期范围元组 (start_date, end_date)，优先级高于其他日期参数
        """
        # 记录同步开始时间
        sync_start = datetime.datetime.utcnow()
        sync_status = 'failed'
        sync_message = ''
        record_count = 0
        store_count = 0
        
        try:
            logger.info(f'开始同步广告数据 - 店铺ID: {store_id}, 天数回溯: {days_back}, 目标日期: {target_date}, 用户ID: {user_id}, 日期范围: {date_range}')
            
            # 确定要同步的日期范围
            if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
                # 如果提供了日期范围
                start_date, end_date = date_range
                logger.info(f'使用指定日期范围: {start_date} 至 {end_date}')
            elif target_date:
                # 单个目标日期
                start_date = target_date
                end_date = target_date
                logger.info(f'使用目标日期: {target_date}')
            else:
                # 使用回溯天数
                start_date, end_date = self.get_date_range(days_back)
                logger.info(f'使用回溯日期范围: {start_date} 至 {end_date}')
            
            # 获取要同步的店铺
            stores_to_sync = []
            if store_id:
                # 使用OAuth模块获取店铺并验证权限
                store = self.oauth_manager.get_store_by_user_and_id(store_id, user_id=user_id)
                if not store:
                    raise ValueError(f"店铺ID {store_id} 不存在或无权限访问")
                stores_to_sync = [store]
            else:
                # 使用OAuth模块获取用户的所有激活店铺
                stores_to_sync = self.oauth_manager.get_active_stores(user_id=user_id)
            
            store_count = len(stores_to_sync)
            logger.info(f'需要同步的店铺数量: {store_count}')
            
            total_records = 0
            for store in stores_to_sync:
                try:
                    # 检查店铺状态
                    if not store.is_active:
                        logger.warning(f'跳过非活跃店铺: {store.store_name} (ID: {store.id})')
                        continue
                    
                    # 检查OAuth配置
                    if not all([store.client_id, store.client_secret, store.refresh_token]):
                        logger.error(f'店铺 {store.store_name} OAuth配置不完整，跳过同步')
                        continue
                    
                    logger.info(f'开始同步店铺 {store.store_name} (ID: {store.id}) 的广告数据')
                    
                    # 获取广告数据
                    ad_records = self.get_advertising_report(store.id, start_date, end_date)
                    
                    # 如果无法通过报表API获取，尝试使用备用方法
                    if not ad_records:
                        logger.warning(f"无法通过报表API获取店铺 {store.id} 的广告数据，尝试使用备用方法")
                        ad_records = self.get_advertising_data_directly(store.id, start_date, end_date)
                    
                    # 为每条记录添加店铺和用户信息
                    for record in ad_records:
                        record['store_id'] = store.id
                        record['user_id'] = store.user_id
                    
                    # 更新数据
                    if ad_records:
                        records_saved = self.update_advertising_data(ad_records)
                        total_records += records_saved
                        logger.info(f'店铺 {store.store_name} 同步完成，保存 {records_saved} 条记录')
                    else:
                        logger.warning(f'店铺 {store.store_name} 未获取到任何广告数据')
                        
                except Exception as e:
                    logger.error(f'同步店铺 {store.store_name} 广告数据时发生错误: {str(e)}')
                    import traceback
                    logger.error(traceback.format_exc())
                    # 继续同步其他店铺
                    continue
            
            record_count = total_records
            sync_status = 'success' if total_records > 0 else 'partial_success'
            sync_message = f'成功同步 {record_count} 条广告数据，店铺数量: {store_count}'
                
        except Exception as e:
            import traceback
            logger.error(f'同步广告数据时发生错误: {str(e)}')
            logger.error(traceback.format_exc())
            sync_message = f'同步广告数据时发生错误: {str(e)}'
        finally:
            # 记录同步日志
            sync_end = datetime.datetime.utcnow()
            sync_log = SyncLog(
                sync_type='advertising',
                store_id=store_id,
                status=sync_status,
                message=sync_message,
                start_time=sync_start,
                end_time=sync_end,
                record_count=record_count,
                user_id=user_id,  # 关联用户ID
                store_count=store_count
            )
            self.db_session.add(sync_log)
            self.db_session.commit()
            logger.info(f'同步日志已记录 - 状态: {sync_status}, 记录数: {record_count}')
            
        return {
            'status': sync_status,
            'message': sync_message,
            'record_count': record_count,
            'store_count': store_count
        }
    
    def get_advertising_data_directly(self, store_id, start_date, end_date):
        """直接获取广告数据的备用方法，支持多维度数据获取"""
        logger.warning(f'使用备用方法获取广告数据 - 店铺ID: {store_id}, 日期范围: {start_date} 至 {end_date}')
        
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
            
            # 设置请求头
            headers = {
                'x-amz-access-token': access_token,
                'Content-Type': 'application/json',
                'Amazon-Advertising-API-ClientId': store.client_id
            }
            
            # 尝试获取多种维度的广告数据
            ad_data = []
            
            # 1. 尝试获取广告活动数据
            campaigns = self._get_advertising_campaigns(store_id, headers)
            if campaigns:
                logger.info(f'成功获取 {len(campaigns)} 个广告活动')
                
                # 2. 为每个活动获取广告组数据
                all_ad_groups = []
                for campaign in campaigns:
                    campaign_id = campaign.get('campaignId')
                    if campaign_id:
                        ad_groups = self._get_ad_groups(campaign_id, headers)
                        all_ad_groups.extend(ad_groups)
                
                logger.info(f'成功获取 {len(all_ad_groups)} 个广告组')
                
                # 3. 为每个广告组获取产品广告数据
                for ad_group in all_ad_groups:
                    ad_group_id = ad_group.get('adGroupId')
                    if ad_group_id:
                        # 获取产品广告
                        product_ads = self._get_product_ads(ad_group_id, headers)
                        
                        # 获取产品广告性能数据
                        ad_performance = self._get_ad_performance(
                            'productAds',
                            ad_group_id=ad_group_id,
                            start_date=start_date,
                            end_date=end_date,
                            headers=headers
                        )
                        
                        # 处理产品广告性能数据
                        if ad_performance:
                            for performance in ad_performance:
                                # 查找对应的产品广告信息获取ASIN
                                asin = self._find_asin_for_ad(performance.get('adId'), product_ads)
                                
                                # 转换为统一格式
                                data = {
                                    'asin': asin or 'Unknown',
                                    'order_date': datetime.datetime.strptime(performance.get('date'), '%Y-%m-%d').date() if 'date' in performance else end_date,
                                    'ad_spend': float(performance.get('cost', 0.0)),
                                    'ad_group': ad_group.get('name', 'Unknown'),
                                    'campaign': campaign.get('name', 'Unknown'),
                                    'clicks': int(performance.get('clicks', 0)),
                                    'impressions': int(performance.get('impressions', 0)),
                                    'conversions': float(performance.get('attributedConversions1d', 0)),
                                    'sales': float(performance.get('attributedSales1d', 0)),
                                    'is_exception': 0
                                }
                                
                                # 数据验证和异常检测
                                if data['ad_spend'] < 0:
                                    data['is_exception'] = 1
                                    logger.warning(f'检测到异常广告花费值: {data["ad_spend"]} 对于ASIN: {data["asin"]}')
                                
                                ad_data.append(data)
            
            # 4. 如果没有获取到数据，尝试获取关键词数据
            if not ad_data:
                logger.info('尝试获取关键词级别数据')
                keywords_data = self._get_keywords_performance(store_id, start_date, end_date, headers)
                ad_data.extend(keywords_data)
            
            # 5. 数据去重和合并
            if ad_data:
                # 按ASIN和日期分组，合并数据
                merged_data = {}
                for record in ad_data:
                    key = (record['asin'], record['order_date'])
                    if key not in merged_data:
                        merged_data[key] = record.copy()
                    else:
                        # 合并数据（累加数值字段）
                        merged_data[key]['ad_spend'] += record.get('ad_spend', 0)
                        merged_data[key]['clicks'] += record.get('clicks', 0)
                        merged_data[key]['impressions'] += record.get('impressions', 0)
                        merged_data[key]['conversions'] += record.get('conversions', 0)
                        merged_data[key]['sales'] += record.get('sales', 0)
                
                logger.info(f'备用方法获取完成，去重后数据量: {len(merged_data)} 条')
                return list(merged_data.values())
            
            logger.warning('备用方法未能获取到任何广告数据')
            return []
            
        except Exception as e:
            logger.error(f'使用备用方法获取广告数据时发生错误: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _get_advertising_campaigns(self, store_id, headers):
        """获取广告活动列表"""
        try:
            # 遵守API速率限制
            self._respect_rate_limit('report_request')
            
            endpoint = self.ADVERTISING_API_ENDPOINT.replace('reporting/v3/reports', 'sp/campaigns')
            params = {'stateFilter': 'enabled,paused', 'count': 100}
            
            response = requests.get(endpoint, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json().get('campaigns', [])
            
        except Exception as e:
            logger.error(f'获取广告活动时发生错误: {str(e)}')
            return []
    
    def _get_ad_groups(self, campaign_id, headers):
        """获取广告组列表"""
        try:
            # 遵守API速率限制
            self._respect_rate_limit('report_request')
            
            endpoint = self.ADVERTISING_API_ENDPOINT.replace('reporting/v3/reports', 'sp/adGroups')
            params = {'campaignIdFilter': campaign_id, 'count': 100}
            
            response = requests.get(endpoint, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json().get('adGroups', [])
            
        except Exception as e:
            logger.error(f'获取广告组时发生错误: {str(e)}')
            return []
    
    def _get_product_ads(self, ad_group_id, headers):
        """获取产品广告列表"""
        try:
            # 遵守API速率限制
            self._respect_rate_limit('report_request')
            
            endpoint = self.ADVERTISING_API_ENDPOINT.replace('reporting/v3/reports', 'sp/productAds')
            params = {'adGroupIdFilter': ad_group_id, 'count': 100}
            
            response = requests.get(endpoint, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json().get('productAds', [])
            
        except Exception as e:
            logger.error(f'获取产品广告时发生错误: {str(e)}')
            return []
    
    def _get_ad_performance(self, entity_type, ad_group_id=None, start_date=None, end_date=None, headers=None):
        """获取广告性能数据"""
        try:
            # 遵守API速率限制
            self._respect_rate_limit('report_request')
            
            endpoint = self.ADVERTISING_API_ENDPOINT.replace('reporting/v3/reports', f'sp/{entity_type}/report')
            
            body = {
                'reportDateRange': {
                    'startDate': self.format_date(start_date),
                    'endDate': self.format_date(end_date)
                },
                'metrics': ['impressions', 'clicks', 'cost', 'attributedConversions1d', 'attributedSales1d']
            }
            
            if ad_group_id:
                body['adGroupIdFilter'] = [ad_group_id]
            
            response = requests.post(endpoint, headers=headers, json=body, timeout=30)
            response.raise_for_status()
            
            # 由于直接报告API可能需要轮询，这里简化处理
            # 如果是直接数据API
            if response.status_code == 200:
                return response.json().get(entity_type, [])
            
            return []
            
        except Exception as e:
            logger.error(f'获取广告性能数据时发生错误: {str(e)}')
            return []
    
    def _get_keywords_performance(self, store_id, start_date, end_date, headers):
        """获取关键词性能数据"""
        try:
            # 遵守API速率限制
            self._respect_rate_limit('report_request')
            
            endpoint = self.ADVERTISING_API_ENDPOINT.replace('reporting/v3/reports', 'sp/keywords/report')
            
            body = {
                'reportDateRange': {
                    'startDate': self.format_date(start_date),
                    'endDate': self.format_date(end_date)
                },
                'metrics': ['impressions', 'clicks', 'cost', 'attributedConversions1d', 'attributedSales1d']
            }
            
            response = requests.post(endpoint, headers=headers, json=body, timeout=30)
            response.raise_for_status()
            
            keywords_data = []
            if response.status_code == 200:
                keywords = response.json().get('keywords', [])
                for keyword in keywords:
                    data = {
                        'asin': keyword.get('keywordText', 'Unknown'),  # 使用关键词文本作为标识
                        'order_date': end_date,
                        'ad_spend': float(keyword.get('cost', 0.0)),
                        'clicks': int(keyword.get('clicks', 0)),
                        'impressions': int(keyword.get('impressions', 0)),
                        'conversions': float(keyword.get('attributedConversions1d', 0)),
                        'sales': float(keyword.get('attributedSales1d', 0)),
                        'is_exception': 0
                    }
                    
                    # 数据验证
                    if data['ad_spend'] < 0:
                        data['is_exception'] = 1
                        logger.warning(f'检测到异常关键词广告花费值: {data["ad_spend"]}')
                    
                    keywords_data.append(data)
            
            return keywords_data
            
        except Exception as e:
            logger.error(f'获取关键词性能数据时发生错误: {str(e)}')
            return []
    
    def _find_asin_for_ad(self, ad_id, product_ads):
        """在产品广告列表中查找指定广告ID对应的ASIN"""
        for ad in product_ads:
            if ad.get('adId') == ad_id:
                return ad.get('asin') or ad.get('sku') or ''
        return ''
    
    def sync_all_stores(self, days_back=1, user_id=None, date_range=None):
        """同步所有激活店铺的广告数据，支持天数回溯和日期范围，增强错误处理和日志记录
        
        Args:
            days_back: 回溯天数
            user_id: 用户ID，如果提供则只同步该用户的店铺
            date_range: 日期范围元组 (start_date, end_date)
        """
        logger.info(f'开始同步所有店铺广告数据 - 用户ID: {user_id}, 天数回溯: {days_back}, 日期范围: {date_range}')
        
        # 根据user_id筛选店铺
        query = self.db_session.query(AmazonStore).filter_by(is_active=True)
        if user_id:
            query = query.filter_by(user_id=user_id)
        stores = query.all()
        
        store_count = len(stores)
        success_count = 0
        failed_count = 0
        total_records = 0
        results = []
        
        logger.info(f'找到 {store_count} 个活跃店铺需要同步')
        
        # 分批处理，避免单次操作过多
        batch_size = 5
        for i in range(0, store_count, batch_size):
            batch = stores[i:i+batch_size]
            logger.info(f'处理批次 {i//batch_size + 1}/{(store_count + batch_size - 1)//batch_size} - 店铺数量: {len(batch)}')
            
            for store in batch:
                try:
                    logger.info(f'正在同步店铺: {store.store_name} (ID: {store.id})')
                    
                    # 调用同步方法
                    result = self.sync_advertising_data(
                        store_id=store.id,
                        user_id=user_id,
                        days_back=days_back,
                        date_range=date_range
                    )
                    
                    if result['status'] in ['success', 'partial_success']:
                        success_count += 1
                        total_records += result.get('record_count', 0)
                        logger.info(f'店铺 {store.store_name} 同步成功 - 处理 {result.get("record_count", 0)} 条记录')
                    else:
                        failed_count += 1
                        logger.warning(f'店铺 {store.store_name} 同步失败')
                    
                    results.append({
                        'store_id': store.id,
                        'store_name': store.store_name,
                        **result
                    })
                    
                except Exception as e:
                    failed_count += 1
                    error_message = str(e)
                    logger.error(f'同步店铺 {store.store_name} (ID: {store.id}) 广告数据时发生错误: {error_message}')
                    import traceback
                    logger.error(traceback.format_exc())
                    
                    # 记录失败结果
                    results.append({
                        'store_id': store.id,
                        'store_name': store.store_name,
                        'status': 'error',
                        'message': error_message,
                        'record_count': 0
                    })
                    
                    # 继续同步其他店铺
                    continue
            
            # 批次之间添加短暂延迟，避免API请求过于密集
            if i + batch_size < store_count:
                logger.info('批次完成，等待2秒后继续下一批次')
                import time
                time.sleep(2)
        
        # 统计结果
        completion_rate = (success_count / store_count * 100) if store_count > 0 else 0
        logger.info(f'所有店铺广告数据同步完成 - 总店铺数: {store_count}, 成功: {success_count}, 失败: {failed_count}, 完成率: {completion_rate:.1f}%, 处理记录数: {total_records}')
        
        # 记录总体同步日志
        try:
            sync_log = SyncLog(
                user_id=user_id,
                sync_type='advertising_batch',
                status='success' if failed_count == 0 else 'partial_success',
                message=f'批量同步完成 - 总店铺数: {store_count}, 成功: {success_count}, 失败: {failed_count}, 处理记录数: {total_records}',
                record_count=total_records,
                store_count=store_count,
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow()
            )
            self.db_session.add(sync_log)
            self.db_session.commit()
        except Exception as log_error:
            logger.error(f'记录批量同步日志时发生错误: {str(log_error)}')
        
        return results

# 使用示例
if __name__ == '__main__':
    # 示例：同步指定店铺的广告数据
    ad_data = AmazonAdvertisingData()
    
    # 同步最近1天的数据
    # 注意：实际使用时需要提供有效的店铺ID
    # result = ad_data.sync_advertising_data(store_id=1)
    # print(f"同步结果: {result}")
    
    # 同步所有店铺的数据
    # results = ad_data.sync_all_stores()
    # for result in results:
    #     print(f"店铺: {result['store_name']}, 状态: {result['status']}, 记录数: {result['record_count']}")
