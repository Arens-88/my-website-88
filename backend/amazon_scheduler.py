import logging
import time
import threading
import traceback
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from models import Session, AmazonStore, SyncLog, SystemConfig, User

# 导入各数据模块
from amazon_oauth import AmazonOAuthManager
from backup_manager import BackupManager
from amazon_advertising import AmazonAdvertisingData
from amazon_inventory import AmazonInventoryManager
from amazon_sales import AmazonSalesData
from amazon_erp_cost import AmazonERPCostManager
from amazon_manual_cost import AmazonManualCostManager
from amazon_data_processor import AmazonDataProcessor
from report_generator import ReportGenerator
from report_pusher import ReportPusher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_scheduler')

class AmazonScheduler:
    def __init__(self):
        """
        初始化调度器
        """
        # 配置调度器的执行器
        executors = {
            'default': ThreadPoolExecutor(10),  # 线程池执行器
            'processpool': ProcessPoolExecutor(3)  # 进程池执行器
        }
        
        # 配置调度器的作业存储器
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///scheduler_jobs.db')  # 使用SQLite存储作业
        }
        
        # 配置调度器
        job_defaults = {
            'coalesce': False,  # 是否合并错过的作业运行
            'max_instances': 3  # 最大实例数
        }
        
        # 创建调度器
        self.scheduler = BackgroundScheduler(
            executors=executors,
            jobstores=jobstores,
            job_defaults=job_defaults
        )
        
        # 调度器状态
        self.is_running = False
        self._lock = threading.RLock()  # 递归锁，用于线程安全
        
        # 初始化备份管理器
        self.backup_manager = BackupManager()
        
        # 定时任务配置
        self.default_schedules = {
            'sync_all_stores': {
                'trigger': 'cron',
                'hour': 2,
                'minute': 0,
                'args': []
            },
            'backup_database': {
                'trigger': 'cron',
                'hour': 1,
                'minute': 0,
                'args': []
            },
            'cleanup_old_logs': {
                'trigger': 'cron',
                'hour': 23,
                'minute': 0,
                'args': [30]  # 清理30天前的日志
            },
            'recalculate_metrics': {
                'trigger': 'cron',
                'hour': 3,
                'minute': 0,
                'args': [7]  # 重新计算最近7天的指标
            },
            'send_daily_reports': {
                'trigger': 'cron',
                'hour': 8,
                'minute': 0,
                'args': []  # 每天8点发送日报
            }
        }
    
    def start(self):
        """
        启动调度器
        """
        with self._lock:
            if not self.is_running:
                try:
                    # 启动调度器
                    self.scheduler.start()
                    self.is_running = True
                    logger.info("调度器已启动")
                    
                    # 加载系统配置的任务
                    self._load_scheduled_tasks()
                    
                    return True
                except Exception as e:
                    logger.error(f"启动调度器失败: {str(e)}")
                    return False
            return True
    
    def stop(self):
        """
        停止调度器
        """
        with self._lock:
            if self.is_running:
                try:
                    self.scheduler.shutdown()
                    self.is_running = False
                    logger.info("调度器已停止")
                    return True
                except Exception as e:
                    logger.error(f"停止调度器失败: {str(e)}")
                    return False
            return True
    
    def _load_scheduled_tasks(self):
        """
        从系统配置加载定时任务
        """
        try:
            session = Session()
            
            # 获取系统配置中的调度设置
            configs = session.query(SystemConfig).filter(
                SystemConfig.key.like('schedule_%')
            ).all()
            
            # 配置字典
            schedule_configs = {}
            for config in configs:
                try:
                    import json
                    # 尝试解析JSON配置
                    schedule_configs[config.key] = json.loads(config.value)
                except (json.JSONDecodeError, TypeError):
                    # 如果不是JSON，使用默认配置
                    pass
            
            # 添加默认任务
            for task_name, task_config in self.default_schedules.items():
                # 检查是否已存在该任务
                job_exists = any(job.id == task_name for job in self.scheduler.get_jobs())
                if not job_exists:
                    # 使用配置中的设置或默认设置
                    actual_config = schedule_configs.get(f'schedule_{task_name}', task_config)
                    
                    # 创建触发器
                    if actual_config['trigger'] == 'cron':
                        trigger = CronTrigger(
                            hour=actual_config.get('hour', 0),
                            minute=actual_config.get('minute', 0),
                            day_of_week=actual_config.get('day_of_week', '*')
                        )
                    elif actual_config['trigger'] == 'interval':
                        trigger = IntervalTrigger(
                            seconds=actual_config.get('seconds', 0),
                            minutes=actual_config.get('minutes', 0),
                            hours=actual_config.get('hours', 0)
                        )
                    else:
                        # 默认使用cron触发器
                        trigger = CronTrigger(
                            hour=actual_config.get('hour', 0),
                            minute=actual_config.get('minute', 0)
                        )
                    
                    # 添加作业
                    self.scheduler.add_job(
                        id=task_name,
                        func=getattr(self, task_name, None),
                        trigger=trigger,
                        args=actual_config.get('args', []),
                        replace_existing=True
                    )
                    logger.info(f"已添加定时任务: {task_name}, 触发器类型: {actual_config['trigger']}")
            
            session.close()
            
        except Exception as e:
            logger.error(f"加载定时任务失败: {str(e)}")
    
    def sync_all_stores(self):
        """
        同步所有用户的所有店铺数据
        """
        logger.info("开始执行全量店铺数据同步任务")
        
        session = Session()
        try:
            # 获取所有用户的所有有效店铺
            stores = session.query(AmazonStore).filter_by(is_active=True).all()
            logger.info(f"发现 {len(stores)} 个活跃店铺需要同步")
            
            # 按用户分组
            stores_by_user = {}
            for store in stores:
                user_id = store.user_id
                if user_id not in stores_by_user:
                    stores_by_user[user_id] = []
                stores_by_user[user_id].append(store)
            
            # 为每个用户同步数据
            for user_id, user_stores in stores_by_user.items():
                try:
                    logger.info(f"开始同步用户 {user_id} 的 {len(user_stores)} 个店铺")
                    self._sync_user_stores(user_id, user_stores)
                    logger.info(f"用户 {user_id} 的店铺同步完成")
                except Exception as e:
                    logger.error(f"同步用户 {user_id} 的店铺失败: {str(e)}")
                    traceback.print_exc()
            
            # 记录同步日志
            sync_log = SyncLog(
                user_id=0,  # 系统任务
                sync_type='scheduled_full_sync',
                status='success',
                total_records=len(stores),
                success_records=len(stores),
                fail_records=0,
                details=f"全量店铺同步完成，共 {len(stores)} 个店铺"
            )
            session.add(sync_log)
            session.commit()
            
            logger.info("全量店铺数据同步任务执行完成")
            
        except Exception as e:
            logger.error(f"执行全量店铺数据同步任务失败: {str(e)}")
            traceback.print_exc()
            
            # 记录失败日志
            sync_log = SyncLog(
                user_id=0,  # 系统任务
                sync_type='scheduled_full_sync',
                status='failed',
                total_records=0,
                success_records=0,
                fail_records=0,
                details=f"全量店铺同步失败: {str(e)}"
            )
            session.add(sync_log)
            session.commit()
        finally:
            session.close()
    
    def _sync_user_stores(self, user_id, stores):
        """
        同步指定用户的所有店铺数据
        
        Args:
            user_id: 用户ID
            stores: 店铺列表
        """
        # 初始化各数据管理器
        oauth_manager = AmazonOAuthManager(user_id)
        sales_manager = AmazonSalesData(user_id)
        inventory_manager = AmazonInventoryManager(user_id)
        advertising_manager = AmazonAdvertisingData(user_id)
        data_processor = AmazonDataProcessor(user_id)
        
        # 为每个店铺同步数据
        for store in stores:
            try:
                logger.info(f"开始同步店铺: {store.store_name} ({store.store_id})")
                
                # 检查OAuth令牌是否有效
                if not oauth_manager.is_token_valid(store.store_id):
                    # 尝试刷新令牌
                    refresh_result = oauth_manager.refresh_token(store.store_id)
                    if not refresh_result['success']:
                        logger.warning(f"店铺 {store.store_name} 的OAuth令牌无效且无法刷新，跳过同步")
                        continue
                
                # 获取OAuth凭证
                credentials = oauth_manager.get_credentials(store.store_id)
                if not credentials:
                    logger.warning(f"无法获取店铺 {store.store_name} 的OAuth凭证，跳过同步")
                    continue
                
                # 设置区域和凭证
                region = store.region
                
                # 同步销售数据
                logger.info(f"同步店铺 {store.store_name} 的销售数据")
                sales_result = sales_manager.fetch_sales_data(
                    store_id=store.store_id,
                    credentials=credentials,
                    region=region,
                    days=7  # 同步最近7天的数据
                )
                
                if sales_result['success']:
                    # 整合销售数据
                    data_processor.integrate_data(
                        source_data=sales_result.get('data', []),
                        source_type='sales'
                    )
                
                # 同步库存数据
                logger.info(f"同步店铺 {store.store_name} 的库存数据")
                inventory_result = inventory_manager.fetch_inventory_data(
                    store_id=store.store_id,
                    credentials=credentials,
                    region=region
                )
                
                if inventory_result['success']:
                    # 整合库存数据
                    data_processor.integrate_data(
                        source_data=inventory_result.get('data', []),
                        source_type='inventory'
                    )
                
                # 同步广告数据
                logger.info(f"同步店铺 {store.store_name} 的广告数据")
                advertising_result = advertising_manager.fetch_advertising_data(
                    store_id=store.store_id,
                    credentials=credentials,
                    region=region,
                    days=7  # 同步最近7天的数据
                )
                
                if advertising_result['success']:
                    # 整合广告数据
                    data_processor.integrate_data(
                        source_data=advertising_result.get('data', []),
                        source_type='ad'
                    )
                
                logger.info(f"店铺 {store.store_name} 的数据同步完成")
                
                # 添加随机延迟，避免API速率限制
                time.sleep(5 + (user_id % 10))
                
            except Exception as e:
                logger.error(f"同步店铺 {store.store_name} 失败: {str(e)}")
                traceback.print_exc()
    
    def backup_database(self):
        """
        执行数据备份任务
        使用BackupManager执行完整的数据备份，包括数据库、报表和上传文件
        """
        logger.info("开始执行数据备份任务")
        
        try:
            # 使用备份管理器执行备份
            result = self.backup_manager.create_backup(description='每日自动备份')
            
            if result['status'] == 'success':
                logger.info(f"数据备份成功: {result['backup_file']}, 大小: {result['size_human']}")
                
                # 清理30天前的备份
                cleanup_result = self.backup_manager.cleanup_old_backups(days_to_keep=30)
                if cleanup_result['status'] == 'success':
                    logger.info(f"清理旧备份完成: 删除了 {cleanup_result['deleted_count']} 个备份")
                else:
                    logger.warning(f"清理旧备份失败: {cleanup_result['message']}")
                
                return True
            else:
                logger.error(f"数据备份失败: {result['message']}")
                return False
                
        except Exception as e:
            logger.error(f"执行备份任务时发生错误: {str(e)}")
            traceback.print_exc()
            return False
    

    
    def cleanup_old_logs(self, days_to_keep=30):
        """
        清理旧的同步日志
        
        Args:
            days_to_keep: 保留的日志天数
        """
        logger.info(f"开始清理 {days_to_keep} 天前的旧同步日志")
        
        try:
            session = Session()
            
            # 计算截止日期
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            
            # 删除旧日志
            deleted_count = session.query(SyncLog).filter(
                SyncLog.sync_time < cutoff_date
            ).delete()
            
            session.commit()
            logger.info(f"已清理 {deleted_count} 条旧同步日志")
            
        except Exception as e:
            logger.error(f"清理旧同步日志失败: {str(e)}")
            traceback.print_exc()
        finally:
            session.close()
    
    def recalculate_metrics(self, days=7):
        """
        重新计算指标
        
        Args:
            days: 重新计算最近多少天的指标
        """
        logger.info(f"开始重新计算最近 {days} 天的指标")
        
        try:
            session = Session()
            
            # 获取所有用户ID
            user_ids = session.query(AmazonStore.user_id).distinct().all()
            user_ids = [uid[0] for uid in user_ids]
            
            # 为每个用户重新计算指标
            for user_id in user_ids:
                try:
                    logger.info(f"重新计算用户 {user_id} 的指标")
                    processor = AmazonDataProcessor(user_id)
                    result = processor.recalculate_all_metrics(days=days)
                    processor.close_session()
                    
                    if result['success']:
                        logger.info(f"用户 {user_id} 的指标重新计算完成: {result['recalculated_count']} 条记录")
                    else:
                        logger.error(f"用户 {user_id} 的指标重新计算失败: {result.get('message', '未知错误')}")
                        
                except Exception as e:
                    logger.error(f"重新计算用户 {user_id} 的指标失败: {str(e)}")
                    traceback.print_exc()
            
            logger.info(f"指标重新计算任务执行完成")
            
        except Exception as e:
            logger.error(f"执行指标重新计算任务失败: {str(e)}")
            traceback.print_exc()
    
    def add_job(self, job_id, func, trigger_type='cron', **kwargs):
        """
        动态添加作业
        
        Args:
            job_id: 作业ID
            func: 要执行的函数
            trigger_type: 触发器类型 ('cron', 'interval', 'date')
            **kwargs: 触发器参数
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 创建触发器
            if trigger_type == 'cron':
                trigger = CronTrigger(**kwargs)
            elif trigger_type == 'interval':
                trigger = IntervalTrigger(**kwargs)
            elif trigger_type == 'date':
                # 对于一次性任务，使用具体日期
                from apscheduler.triggers.date import DateTrigger
                trigger = DateTrigger(run_date=kwargs.get('run_date', datetime.now()))
            else:
                logger.error(f"不支持的触发器类型: {trigger_type}")
                return False
            
            # 添加作业
            self.scheduler.add_job(
                id=job_id,
                func=func,
                trigger=trigger,
                replace_existing=True
            )
            
            logger.info(f"已添加作业: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加作业 {job_id} 失败: {str(e)}")
            return False
    
    def remove_job(self, job_id):
        """
        移除作业
        
        Args:
            job_id: 作业ID
            
        Returns:
            bool: 是否移除成功
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除作业: {job_id}")
            return True
        except Exception as e:
            logger.error(f"移除作业 {job_id} 失败: {str(e)}")
            return False
    
    def list_jobs(self):
        """
        列出所有作业
        
        Returns:
            list: 作业信息列表
        """
        jobs = []
        try:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'next_run_time': str(job.next_run_time) if job.next_run_time else None,
                    'trigger': str(job.trigger),
                    'name': job.name
                })
        except Exception as e:
            logger.error(f"列出作业失败: {str(e)}")
        
        return jobs
    
    def pause_job(self, job_id):
        """
        暂停作业
        
        Args:
            job_id: 作业ID
            
        Returns:
            bool: 是否暂停成功
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"已暂停作业: {job_id}")
            return True
        except Exception as e:
            logger.error(f"暂停作业 {job_id} 失败: {str(e)}")
            return False
    
    def resume_job(self, job_id):
        """
        恢复作业
        
        Args:
            job_id: 作业ID
            
        Returns:
            bool: 是否恢复成功
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"已恢复作业: {job_id}")
            return True
        except Exception as e:
            logger.error(f"恢复作业 {job_id} 失败: {str(e)}")
            return False
    
    def send_daily_reports(self):
        """
        发送每日报表（企业微信机器人推送和邮件推送）
        每天早上8点执行
        """
        logger.info("开始执行每日报表推送任务")
        
        session = Session()
        try:
            # 获取所有用户
            users = session.query(User).all()
            logger.info(f"发现 {len(users)} 个用户需要推送报表")
            
            # 为每个用户生成并推送报表
            for user in users:
                try:
                    logger.info(f"开始为用户 {user.username} (ID: {user.id}) 生成并推送报表")
                    
                    # 创建用户会话
                    user_session = Session()
                    
                    # 创建报表生成器
                    report_generator = ReportGenerator(user_session, user.id)
                    
                    # 获取昨日销售数据摘要
                    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                    summary_data = report_generator.generate_sales_summary(filters={'date': yesterday})
                    
                    # 添加用户标识
                    if summary_data:
                        summary_data['user'] = user.username
                    else:
                        summary_data = {'user': user.username}
                    
                    # 获取Top3 ASIN数据
                    top_asins = report_generator.get_top_profitable_asins(days=7, limit=3)
                    if top_asins:
                        summary_data['top_asins'] = top_asins
                    
                    # 创建报表推送器
                    pusher = ReportPusher(user_session, user.id)
                    
                    # 构建报表URLs（假设使用固定格式）
                    base_url = pusher.get_config('report_base_url') or 'http://localhost:5000'
                    report_urls = {
                        'profit_report': f"{base_url}/#/reports/profit",
                        'trend_report': f"{base_url}/#/reports/sales-trend",
                        'inventory_report': f"{base_url}/#/reports/inventory-health"
                    }
                    
                    # 准备报表文件路径
                     report_paths = []
                     # 从各类报表中收集文件路径
                     if 'profit_report' in reports and 'report_path' in reports['profit_report']:
                         report_paths.append(reports['profit_report']['report_path'])
                     if 'trend_report' in reports and 'report_path' in reports['trend_report']:
                         report_paths.append(reports['trend_report']['report_path'])
                     if 'inventory_report' in reports and 'report_path' in reports['inventory_report']:
                         report_paths.append(reports['inventory_report']['report_path'])
                      
                     # 发送每日报表（同时处理企业微信和邮件推送）
                     push_results = pusher.push_daily_reports(summary_data, report_paths, report_urls)
                    logger.info(f"用户 {user.username} 报表推送结果: 企业微信={push_results.get('wechat', {}).get('status')}, 邮件={push_results.get('email', {}).get('status')}")
                    
                    # 关闭用户会话
                    user_session.close()
                    
                except Exception as e:
                    logger.error(f"为用户 {user.username} 生成并推送报表失败: {str(e)}")
                    traceback.print_exc()
                
                # 添加间隔，避免API调用过于频繁
                time.sleep(2)
            
            logger.info("每日报表推送任务执行完成")
            
        except Exception as e:
            logger.error(f"执行每日报表推送任务失败: {str(e)}")
            traceback.print_exc()
        finally:
            session.close()
            
    def update_wechat_push_schedule(self, user_id, hour=8, minute=0, webhook_url=None):
        """
        更新用户的企业微信推送定时任务
        
        Args:
            user_id: 用户ID
            hour: 推送小时 (0-23)
            minute: 推送分钟 (0-59)
            webhook_url: 企业微信Webhook URL
        """
        try:
            # 生成任务ID
            job_id = f'wechat_push_user_{user_id}'
            
            # 移除现有的任务
            self.remove_job(job_id)
            
            # 创建新的定时任务
            self.add_job(
                job_id=job_id,
                func=self.send_user_wechat_report,
                trigger_type='cron',
                hour=hour,
                minute=minute,
                args=[user_id, webhook_url]
            )
            
            logger.info(f"已为用户 {user_id} 设置每日{hour:02d}:{minute:02d}的企业微信推送")
            return True
        except Exception as e:
            logger.error(f"更新用户 {user_id} 的微信推送定时任务失败: {str(e)}")
            return False
            
    def cancel_wechat_push(self, user_id):
        """
        取消用户的企业微信推送定时任务
        
        Args:
            user_id: 用户ID
        """
        try:
            job_id = f'wechat_push_user_{user_id}'
            self.remove_job(job_id)
            logger.info(f"已取消用户 {user_id} 的企业微信推送定时任务")
            return True
        except Exception as e:
            logger.error(f"取消用户 {user_id} 的微信推送定时任务失败: {str(e)}")
            return False
            
    def send_user_wechat_report(self, user_id, webhook_url=None):
        """
        发送用户的企业微信日报
        
        Args:
            user_id: 用户ID
            webhook_url: 企业微信Webhook URL（如果为None则从数据库获取）
        """
        try:
            logger.info(f"开始为用户 {user_id} 发送企业微信日报")
            
            session = Session()
            try:
                # 获取用户信息
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    logger.error(f"用户 {user_id} 不存在")
                    return
                
                # 创建用户会话
                user_session = Session()
                
                # 创建报表生成器
                report_generator = ReportGenerator(user_session, user_id)
                
                # 获取昨日销售数据摘要
                yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                summary_data = report_generator.generate_sales_summary(filters={'date': yesterday})
                
                # 添加用户标识
                if summary_data:
                    summary_data['user'] = user.username
                else:
                    summary_data = {'user': user.username}
                
                # 获取Top3 ASIN数据
                top_asins = report_generator.get_top_profitable_asins(days=7, limit=3)
                if top_asins:
                    summary_data['top_asins'] = top_asins
                
                # 创建报表推送器
                pusher = ReportPusher(user_session, user_id)
                
                # 如果没有提供Webhook URL，则从配置获取
                if not webhook_url:
                    webhook_url = pusher.get_config('wechat_webhook_url')
                
                if not webhook_url:
                    logger.warning(f"用户 {user.username} 未配置企业微信Webhook URL")
                    return
                
                # 构建报表URLs
                base_url = pusher.get_config('report_base_url') or 'http://localhost:5000'
                report_urls = {
                    'profit_report': f"{base_url}/#/reports/profit",
                    'trend_report': f"{base_url}/#/reports/sales-trend",
                    'inventory_report': f"{base_url}/#/reports/inventory-health"
                }
                
                # 发送企业微信报表
                push_result = pusher.send_wechat_report(summary_data, report_urls, webhook_url)
                
                if push_result['status'] == 'success':
                    logger.info(f"用户 {user.username} 的企业微信日报发送成功")
                else:
                    logger.error(f"用户 {user.username} 的企业微信日报发送失败: {push_result.get('message', '未知错误')}")
                    
                # 关闭用户会话
                user_session.close()
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"为用户 {user_id} 发送企业微信日报失败: {str(e)}")
            traceback.print_exc()

# 创建全局调度器实例
global_scheduler = AmazonScheduler()

# 应用启动时自动启动调度器
def init_scheduler():
    """
    初始化调度器
    """
    global global_scheduler
    
    # 尝试启动调度器
    if global_scheduler.start():
        logger.info("调度器初始化成功")
        return True
    else:
        logger.error("调度器初始化失败")
        return False

# 应用关闭时停止调度器
def shutdown_scheduler():
    """
    关闭调度器
    """
    global global_scheduler
    
    # 尝试停止调度器
    if global_scheduler.stop():
        logger.info("调度器关闭成功")
        return True
    else:
        logger.error("调度器关闭失败")
        return False

# 使用示例
if __name__ == "__main__":
    # 初始化调度器
    init_scheduler()
    
    try:
        # 列出当前作业
        print("当前作业列表:")
        jobs = global_scheduler.list_jobs()
        for job in jobs:
            print(f"- {job['id']}: {job['trigger']}, 下次运行: {job['next_run_time']}")
        
        # 等待一段时间，让作业有机会执行
        print("调度器已启动，按Ctrl+C退出...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在关闭调度器...")
        shutdown_scheduler()
        print("调度器已关闭")
