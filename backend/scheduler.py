import time
import datetime
import logging
import threading
import os
from models import SystemConfig, init_db
from amazon_sales import AmazonSalesData
from amazon_advertising import AmazonAdvertisingData
from amazon_inventory import AmazonInventoryData
from data_integration import DataIntegration

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('scheduler')

class TaskScheduler:
    """定时任务调度系统 - 自定义实现"""
    
    def __init__(self, db_session=None):
        # 接收外部传入的数据库会话或初始化新会话
        self.db_session = db_session if db_session else init_db()
        self.running = False
        self.scheduler_thread = None
        self.lock = threading.Lock()
        self.schedule_enabled = False
        self.sync_time = '02:00'  # 默认同步时间：凌晨2点
        self.push_time = '08:00'  # 默认推送时间：早上8点
        self.auto_backup = True
        self.backup_time = '23:00'  # 默认备份时间：晚上11点
        self.last_sync_time = None
        self.last_push_time = None
        self.last_backup_time = None
        self.task_history = []  # 任务执行历史记录
    
    def load_config(self):
        """加载系统配置"""
        try:
            # 获取系统配置
            config = self.db_session.query(SystemConfig).filter_by(config_key='scheduler_config').first()
            
            if config and config.config_value:
                import json
                return json.loads(config.config_value)
            else:
                # 默认配置
                return {
                    'enabled': True,
                    'sync_time': '02:00',  # 每天凌晨2点
                    'push_time': '08:00',  # 每天早上8点
                    'days_to_sync': 1,     # 同步最近1天的数据
                    'auto_backup': True,   # 自动备份
                    'backup_time': '23:00'  # 每天晚上11点备份
                }
        except Exception as e:
            logger.error(f'加载配置时发生错误: {str(e)}')
            return {
                'enabled': True,
                'sync_time': '02:00',
                'push_time': '08:00',
                'days_to_sync': 1,
                'auto_backup': True,
                'backup_time': '23:00'
            }
    
    def save_config(self, config):
        """保存系统配置"""
        try:
            import json
            
            # 查找现有配置
            existing_config = self.db_session.query(SystemConfig).filter_by(config_key='scheduler_config').first()
            
            if existing_config:
                existing_config.config_value = json.dumps(config)
                existing_config.updated_at = datetime.datetime.utcnow()
            else:
                new_config = SystemConfig(
                    config_key='scheduler_config',
                    config_value=json.dumps(config),
                    description='定时任务调度配置'
                )
                self.db_session.add(new_config)
            
            self.db_session.commit()
            logger.info('调度配置已保存')
            return True
            
        except Exception as e:
            logger.error(f'保存配置时发生错误: {str(e)}')
            self.db_session.rollback()
            return False
    
    def record_task_history(self, task_name, status, message, details=None):
        """记录任务执行历史"""
        history_entry = {
            'task_name': task_name,
            'start_time': datetime.datetime.now(),
            'status': status,
            'message': message,
            'details': details or {}
        }
        # 保留最近100条历史记录
        if len(self.task_history) >= 100:
            self.task_history.pop(0)
        self.task_history.append(history_entry)
        return history_entry
    
    def full_sync_data(self):
        """完整的数据同步流程"""
        start_time = datetime.datetime.now()
        task_history = self.record_task_history('full_sync_data', 'running', '开始执行完整的数据同步流程')
        logger.info('开始执行完整的数据同步流程')
        
        try:
            # 获取配置
            config = self.load_config()
            days_to_sync = config.get('days_to_sync', 1)
            
            # 按用户ID分组处理数据同步
            from models import AmazonStore
            user_ids = self.db_session.query(AmazonStore.user_id).distinct().all()
            
            # 如果没有用户店铺，记录信息后返回
            if not user_ids:
                logger.info('没有可同步的用户店铺数据')
                task_history.update({
                    'status': 'success',
                    'end_time': datetime.datetime.now(),
                    'message': '没有可同步的用户店铺数据'
                })
                return {
                    'status': 'success',
                    'message': '没有可同步的用户店铺数据',
                    'execution_time': str(datetime.datetime.now() - start_time)
                }
            
            results = {
                'status': 'success',
                'message': '数据同步完成',
                'user_sync_results': [],
                'total_users': len(user_ids),
                'successful_users': 0,
                'failed_users': 0
            }
            
            for (user_id,) in user_ids:
                user_result = {
                    'user_id': user_id,
                    'sales_sync': None,
                    'ad_sync': None,
                    'inventory_sync': None,
                    'integration': None,
                    'status': 'success',
                    'start_time': datetime.datetime.now()
                }
                
                try:
                    logger.info(f'开始处理用户 {user_id} 的数据同步...')
                    
                    # 1. 同步销售数据
                    try:
                        logger.info(f'开始同步用户 {user_id} 的销售数据...')
                        sales_module = AmazonSalesData(self.db_session)
                        user_result['sales_sync'] = sales_module.sync_all_stores(days_back=days_to_sync, user_id=user_id)
                    except Exception as e:
                        logger.error(f'同步用户 {user_id} 的销售数据失败: {str(e)}')
                        user_result['sales_sync'] = {'status': 'error', 'message': str(e)}
                        user_result['status'] = 'partial_error'
                    
                    # 2. 同步广告数据
                    try:
                        logger.info(f'开始同步用户 {user_id} 的广告数据...')
                        ad_module = AmazonAdvertisingData(self.db_session)
                        user_result['ad_sync'] = ad_module.sync_all_stores(days_back=days_to_sync, user_id=user_id)
                    except Exception as e:
                        logger.error(f'同步用户 {user_id} 的广告数据失败: {str(e)}')
                        user_result['ad_sync'] = {'status': 'error', 'message': str(e)}
                        user_result['status'] = 'partial_error'
                    
                    # 3. 同步库存数据
                    try:
                        logger.info(f'开始同步用户 {user_id} 的库存数据...')
                        inventory_module = AmazonInventoryData(self.db_session)
                        user_result['inventory_sync'] = inventory_module.sync_all_stores(user_id=user_id)
                    except Exception as e:
                        logger.error(f'同步用户 {user_id} 的库存数据失败: {str(e)}')
                        user_result['inventory_sync'] = {'status': 'error', 'message': str(e)}
                        user_result['status'] = 'partial_error'
                    
                    # 4. 数据整合
                    try:
                        logger.info(f'开始整合用户 {user_id} 的数据...')
                        integrator = DataIntegration(self.db_session)
                        user_result['integration'] = integrator.handle_incremental_sync(user_id=user_id)
                    except Exception as e:
                        logger.error(f'整合用户 {user_id} 的数据失败: {str(e)}')
                        user_result['integration'] = {'status': 'error', 'message': str(e)}
                        user_result['status'] = 'partial_error'
                    
                    user_result['end_time'] = datetime.datetime.now()
                    user_result['execution_time'] = str(user_result['end_time'] - user_result['start_time'])
                    
                    if user_result['status'] == 'success':
                        results['successful_users'] += 1
                    else:
                        results['failed_users'] += 1
                    
                    logger.info(f'用户 {user_id} 的数据同步流程执行完成，状态: {user_result["status"]}')
                
                except Exception as e:
                    error_message = f'用户 {user_id} 的数据同步流程执行失败: {str(e)}'
                    logger.error(error_message)
                    user_result['status'] = 'error'
                    user_result['message'] = error_message
                    user_result['end_time'] = datetime.datetime.now()
                    results['failed_users'] += 1
                    results['status'] = 'partial_error'
                
                results['user_sync_results'].append(user_result)
            
            # 更新总体状态
            if results['failed_users'] == 0:
                results['status'] = 'success'
                results['message'] = '所有用户的数据同步完成'
            elif results['successful_users'] == 0:
                results['status'] = 'error'
                results['message'] = '所有用户数据同步失败，请查看日志'
            else:
                results['status'] = 'partial_error'
                results['message'] = f'部分用户数据同步失败，成功: {results["successful_users"]}, 失败: {results["failed_users"]}'
            
            # 计算总执行时间
            end_time = datetime.datetime.now()
            results['execution_time'] = str(end_time - start_time)
            
            # 更新任务历史
            task_history.update({
                'status': results['status'],
                'end_time': end_time,
                'message': results['message'],
                'details': {
                    'total_users': results['total_users'],
                    'successful_users': results['successful_users'],
                    'failed_users': results['failed_users'],
                    'execution_time': results['execution_time']
                }
            })
            
            # 记录同步完成日志
            logger.info(f'数据同步流程执行完成，状态: {results["status"]}, 耗时: {results["execution_time"]}')
            return results
            
        except Exception as e:
            error_message = f'数据同步流程执行失败: {str(e)}'
            logger.error(error_message, exc_info=True)
            
            # 更新任务历史
            task_history.update({
                'status': 'error',
                'end_time': datetime.datetime.now(),
                'message': error_message,
                'details': {'exception': str(e)}
            })
            
            return {
                'status': 'error',
                'message': error_message,
                'execution_time': str(datetime.datetime.now() - start_time)
            }
    
    def run_backup(self):
        """执行数据备份"""
        start_time = datetime.datetime.now()
        task_history = self.record_task_history('run_backup', 'running', '开始执行数据备份')
        logger.info('开始执行数据备份...')
        
        try:
            # 获取备份配置
            config = self.load_config()
            days_to_keep = config.get('backup_days_to_keep', 30)
            
            # 这里实现数据库备份逻辑
            # 简化版本：将SQLite数据库复制到备份目录
            db_path = 'amazon_report.db'  # 默认数据库路径
            
            if os.path.exists(db_path):
                # 创建备份目录
                backup_dir = os.path.join('..', 'data', 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                
                # 生成备份文件名
                backup_filename = f'backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
                backup_path = os.path.join(backup_dir, backup_filename)
                
                try:
                    # 复制文件
                    import shutil
                    shutil.copy2(db_path, backup_path)
                    
                    # 验证备份文件大小
                    if os.path.getsize(backup_path) > 0 and os.path.getsize(backup_path) == os.path.getsize(db_path):
                        logger.info(f'数据库备份成功: {backup_path}')
                        
                        # 清理旧备份
                        try:
                            self.cleanup_old_backups(backup_dir, days=days_to_keep)
                            logger.info(f'已清理 {days_to_keep} 天前的旧备份')
                        except Exception as cleanup_error:
                            logger.error(f'清理旧备份失败: {str(cleanup_error)}')
                            
                        # 更新任务历史
                        task_history.update({
                            'status': 'success',
                            'end_time': datetime.datetime.now(),
                            'message': '数据备份完成',
                            'details': {
                                'backup_path': backup_path,
                                'backup_size': os.path.getsize(backup_path),
                                'execution_time': str(datetime.datetime.now() - start_time)
                            }
                        })
                        
                        return {'status': 'success', 'message': '数据备份完成', 'backup_path': backup_path}
                    else:
                        logger.error(f'备份文件验证失败: {backup_path}')
                        # 删除无效的备份文件
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        raise Exception('备份文件验证失败，大小不匹配或为空')
                        
                except Exception as copy_error:
                    logger.error(f'复制数据库文件失败: {str(copy_error)}')
                    # 删除可能创建的不完整备份文件
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    raise copy_error
            else:
                logger.warning('数据库文件不存在，跳过备份')
                task_history.update({
                    'status': 'warning',
                    'end_time': datetime.datetime.now(),
                    'message': '数据库文件不存在，跳过备份'
                })
                return {'status': 'warning', 'message': '数据库文件不存在'}
                
        except Exception as e:
            error_message = f'数据备份失败: {str(e)}'
            logger.error(error_message, exc_info=True)
            
            # 更新任务历史
            task_history.update({
                'status': 'error',
                'end_time': datetime.datetime.now(),
                'message': error_message,
                'details': {'exception': str(e)}
            })
            
            return {'status': 'error', 'message': error_message}
    
    def cleanup_old_backups(self, backup_dir, days=30):
        """清理旧的备份文件"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
            for filename in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, filename)
                
                # 检查文件修改时间
                if os.path.isfile(file_path):
                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if mod_time < cutoff_date:
                        os.remove(file_path)
                        logger.info(f'已清理旧备份文件: {filename}')
        
        except Exception as e:
            logger.error(f'清理旧备份时发生错误: {str(e)}')
    
    def run_daily_sync(self):
        """每日同步任务"""
        logger.info('执行每日数据同步任务')
        
        # 在单独的线程中执行同步，避免阻塞调度器
        sync_thread = threading.Thread(target=self.full_sync_data)
        sync_thread.daemon = True
        sync_thread.start()
    
    def run_daily_backup(self):
        """每日备份任务"""
        logger.info('执行每日数据备份任务')
        
        # 在单独的线程中执行备份，避免阻塞调度器
        backup_thread = threading.Thread(target=self.run_backup)
        backup_thread.daemon = True
        backup_thread.start()
    
    def run_daily_push(self):
        """每日推送任务"""
        logger.info('执行每日报表推送任务')
        
        # 这里将在后续实现报表推送功能
        try:
            # 导入推送模块
            from report_generator import ReportGenerator
            from report_pusher import ReportPusher
            from models import AmazonStore, User
            
            # 按用户ID分组处理报表生成和推送
            user_ids = self.db_session.query(AmazonStore.user_id).distinct().all()
            
            for (user_id,) in user_ids:
                try:
                    logger.info(f'开始为用户 {user_id} 生成和推送报表...')
                    
                    # 生成报表
                    report_gen = ReportGenerator(self.db_session)
                    reports = report_gen.generate_daily_reports(user_id=user_id)
                    
                    # 推送报表
                    if reports and 'summary_data' in reports and 'report_paths' in reports and 'report_urls' in reports:
                        # 创建推送器，传递用户ID
                        pusher = ReportPusher(self.db_session, user_id=user_id)
                        # 执行推送
                        pusher.push_daily_reports(
                            summary_data=reports['summary_data'],
                            report_paths=reports['report_paths'],
                            report_urls=reports['report_urls']
                        )
                    
                    logger.info(f'用户 {user_id} 的报表推送完成')
                except Exception as e:
                    logger.error(f'为用户 {user_id} 执行报表推送任务时发生错误: {str(e)}')
                    
        except Exception as e:
            logger.error(f'执行每日推送任务时发生错误: {str(e)}')
    
    def setup_schedule(self):
        """设置定时任务配置"""
        # 加载配置
        config = self.load_config()
        
        if not config.get('enabled', True):
            logger.info('调度器已禁用')
            self.schedule_enabled = False
            return
        
        self.schedule_enabled = True
        
        # 保存任务时间配置
        self.sync_time = config.get('sync_time', '02:00')
        self.push_time = config.get('push_time', '08:00')
        self.auto_backup = config.get('auto_backup', True)
        self.backup_time = config.get('backup_time', '23:00')
        
        # 记录任务配置
        logger.info(f'调度器配置已加载:')
        logger.info(f'- 每日数据同步任务: {self.sync_time}')
        logger.info(f'- 每日报表推送任务: {self.push_time}')
        if self.auto_backup:
            logger.info(f'- 每日数据备份任务: {self.backup_time}')
        
        # 记录上次执行时间
        self.last_sync_time = None
        self.last_push_time = None
        self.last_backup_time = None
    
    def scheduler_loop(self):
        """调度器主循环，检查并执行任务"""
        logger.info('调度器开始运行')
        
        # 初始化最后配置加载时间
        last_config_reload = datetime.datetime.now()
        config_reload_interval = datetime.timedelta(minutes=30)  # 每30分钟重新加载配置
        
        while self.running:
            try:
                # 定期重新加载配置
                current_time = datetime.datetime.now()
                if current_time - last_config_reload > config_reload_interval:
                    try:
                        config = self.load_config()
                        logger.info('调度器配置已重新加载')
                        last_config_reload = current_time
                        # 重新设置任务计划
                        self.setup_schedule()
                    except Exception as config_error:
                        logger.error(f'重新加载配置失败: {str(config_error)}')
                
                # 如果调度器被禁用，等待一段时间后再次检查
                if not self.schedule_enabled:
                    time.sleep(300)  # 5分钟检查一次是否启用
                    continue
                
                # 获取当前时间
                now = datetime.datetime.now()
                current_time_str = now.strftime('%H:%M')
                
                # 检查是否需要执行同步任务
                if current_time_str == self.sync_time and (not self.last_sync_time or 
                                                         now.date() != self.last_sync_time.date()):
                    logger.info('触发每日数据同步任务')
                    task_history = self.record_task_history('daily_sync', 'running', '开始执行每日数据同步任务')
                    try:
                        start_time = datetime.datetime.now()
                        self.run_daily_sync()
                        self.last_sync_time = now
                        end_time = datetime.datetime.now()
                        execution_time = (end_time - start_time).total_seconds()
                        task_history.update({
                            'status': 'success',
                            'end_time': end_time,
                            'message': '每日数据同步任务执行成功',
                            'details': {'execution_time': f'{execution_time:.2f}秒'}
                        })
                    except Exception as e:
                        end_time = datetime.datetime.now()
                        logger.error(f'执行每日数据同步任务失败: {str(e)}', exc_info=True)
                        task_history.update({
                            'status': 'error',
                            'end_time': end_time,
                            'message': f'每日数据同步任务执行失败: {str(e)}',
                            'details': {'exception': str(e)}
                        })
                
                # 检查是否需要执行推送任务
                elif current_time_str == self.push_time and (not self.last_push_time or 
                                                          now.date() != self.last_push_time.date()):
                    logger.info('触发每日报表推送任务')
                    task_history = self.record_task_history('daily_push', 'running', '开始执行每日报表推送任务')
                    try:
                        start_time = datetime.datetime.now()
                        self.run_daily_push()
                        self.last_push_time = now
                        end_time = datetime.datetime.now()
                        execution_time = (end_time - start_time).total_seconds()
                        task_history.update({
                            'status': 'success',
                            'end_time': end_time,
                            'message': '每日报表推送任务执行成功',
                            'details': {'execution_time': f'{execution_time:.2f}秒'}
                        })
                    except Exception as e:
                        end_time = datetime.datetime.now()
                        logger.error(f'执行每日报表推送任务失败: {str(e)}', exc_info=True)
                        task_history.update({
                            'status': 'error',
                            'end_time': end_time,
                            'message': f'每日报表推送任务执行失败: {str(e)}',
                            'details': {'exception': str(e)}
                        })
                
                # 检查是否需要执行备份任务
                elif self.auto_backup and current_time_str == self.backup_time and \
                     (not self.last_backup_time or now.date() != self.last_backup_time.date()):
                    logger.info('触发每日数据备份任务')
                    task_history = self.record_task_history('daily_backup', 'running', '开始执行每日数据备份任务')
                    try:
                        start_time = datetime.datetime.now()
                        self.run_daily_backup()
                        self.last_backup_time = now
                        end_time = datetime.datetime.now()
                        execution_time = (end_time - start_time).total_seconds()
                        task_history.update({
                            'status': 'success',
                            'end_time': end_time,
                            'message': '每日数据备份任务执行成功',
                            'details': {'execution_time': f'{execution_time:.2f}秒'}
                        })
                    except Exception as e:
                        end_time = datetime.datetime.now()
                        logger.error(f'执行每日数据备份任务失败: {str(e)}', exc_info=True)
                        task_history.update({
                            'status': 'error',
                            'end_time': end_time,
                            'message': f'每日数据备份任务执行失败: {str(e)}',
                            'details': {'exception': str(e)}
                        })
                
                # 每分钟检查一次
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info('接收到终止信号，调度器正在停止...')
                self.running = False
                break
            except Exception as e:
                logger.error(f'调度器循环错误: {str(e)}', exc_info=True)
                time.sleep(60)  # 发生错误后等待一分钟再继续
        
        logger.info('调度器已停止')
    
    def start(self):
        """启动调度器"""
        with self.lock:
            if self.running:
                logger.warning('调度器已经在运行中')
                return False
            
            self.running = True
            self.schedule_enabled = False
            
            # 设置定时任务配置
            self.setup_schedule()
            
            # 创建并启动调度器线程
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            
            logger.info('调度器启动成功')
            return True
    
    def stop(self):
        """停止调度器"""
        with self.lock:
            if not self.running:
                logger.warning('调度器未在运行')
                return False
            
            self.running = False
            self.schedule_enabled = False
            
            # 等待调度器线程结束
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=10)
            
            logger.info('调度器停止成功')
            return True
    
    def restart(self):
        """重启调度器"""
        logger.info('重启调度器...')
        
        # 停止调度器
        self.stop()
        
        # 重新启动调度器
        return self.start()
    
    def get_status(self):
        """获取调度器状态"""
        # 构建任务信息
        next_jobs = []
        config = self.load_config()
        
        # 计算下一次执行时间
        def get_next_run_time(time_str):
            now = datetime.datetime.now()
            hour, minute = map(int, time_str.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += datetime.timedelta(days=1)
            return next_run
        
        # 添加同步任务
        next_jobs.append({
            'job_id': 'run_daily_sync',
            'job_name': '每日数据同步',
            'next_run': get_next_run_time(config.get('sync_time', '02:00')).strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'enabled' if config.get('enabled', True) else 'disabled',
            'last_run': self.last_sync_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_sync_time else None
        })
        
        # 添加推送任务
        next_jobs.append({
            'job_id': 'run_daily_push',
            'job_name': '每日报表推送',
            'next_run': get_next_run_time(config.get('push_time', '08:00')).strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'enabled' if config.get('enabled', True) else 'disabled',
            'last_run': self.last_push_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_push_time else None
        })
        
        # 添加备份任务
        if config.get('auto_backup', True) and config.get('enabled', True):
            next_jobs.append({
                'job_id': 'run_daily_backup',
                'job_name': '每日数据备份',
                'next_run': get_next_run_time(config.get('backup_time', '23:00')).strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'enabled',
                'last_run': self.last_backup_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_backup_time else None
            })
        
        # 获取最近的任务历史记录（最多10条）
        recent_history = self.task_history[-10:][::-1]  # 最近10条，按时间倒序排列
        
        # 获取各类型任务的最新执行状态
        latest_status = {}
        for task_name in ['full_sync_data', 'run_backup', 'run_daily_sync', 'run_daily_push', 'run_daily_backup']:
            # 查找该任务的最新历史记录
            for history in self.task_history:
                if history['task_name'] == task_name:
                    latest_status[task_name] = {
                        'status': history['status'],
                        'start_time': history['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        'end_time': history['end_time'].strftime('%Y-%m-%d %H:%M:%S') if history.get('end_time') else None,
                        'message': history['message']
                    }
                    break
        
        return {
            'running': self.running,
            'enabled': self.schedule_enabled,
            'job_count': len(next_jobs),
            'next_jobs': next_jobs,
            'config': config,
            'recent_history': recent_history,
            'latest_status': latest_status,
            'task_history_count': len(self.task_history)
        }
    
    def manual_sync(self):
        """手动触发同步"""
        logger.info('手动触发数据同步...')
        
        # 在单独的线程中执行同步
        sync_thread = threading.Thread(target=self.full_sync_data)
        sync_thread.daemon = True
        sync_thread.start()
        
        return {'status': 'started', 'message': '数据同步已开始'}

# 全局调度器实例
_scheduler_instance = None

def get_scheduler(db_session=None):
    """获取调度器实例"""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        # 如果没有提供数据库会话，则初始化
        if db_session is None:
            db_session = init_db()
        
        # 创建调度器实例
        _scheduler_instance = TaskScheduler(db_session=db_session)
    elif db_session is not None and _scheduler_instance.db_session is None:
        # 如果实例已存在但没有数据库会话，则设置
        _scheduler_instance.db_session = db_session
    
    return _scheduler_instance

# 使用示例
if __name__ == '__main__':
    # 示例：启动调度器
    scheduler = get_scheduler()
    scheduler.start()
    
    try:
        # 保持程序运行
        print("调度器已启动，按Ctrl+C停止...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # 停止调度器
        scheduler.stop()
        print("调度器已停止")
