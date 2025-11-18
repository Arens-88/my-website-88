import os
import sys
import logging
import threading
import time
from models import init_db, SystemConfig
from app import app
from scheduler import TaskScheduler
from backup_manager import BackupManager
from sqlalchemy import select

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('..', 'data', 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')

def start_api_server():
    """启动API服务器"""
    try:
        logger.info('正在启动API服务器...')
        # 在生产环境中，应该使用WSGI服务器而不是直接运行Flask
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f'API服务器启动失败: {str(e)}')
        sys.exit(1)

def start_scheduler():
    """启动调度器"""
    try:
        # 初始化数据库会话
        db_session = init_db()
        
        # 获取调度器配置
        enable_scheduler = db_session.execute(
            select(SystemConfig).where(SystemConfig.config_name == 'enable_scheduler')
        ).scalar_one_or_none()
        
        # 默认启用调度器
        if not enable_scheduler or enable_scheduler.config_value.lower() != 'false':
            logger.info('正在启动任务调度器...')
            scheduler = TaskScheduler(db_session)
            scheduler.start()
            logger.info('任务调度器已启动')
        else:
            logger.info('任务调度器已禁用')
            
    except Exception as e:
        logger.error(f'调度器启动失败: {str(e)}')

def initialize_app():
    """初始化应用"""
    try:
        # 确保数据目录存在
        data_dir = os.path.join('..', 'data')
        reports_dir = os.path.join(data_dir, 'reports')
        uploads_dir = os.path.join(data_dir, 'uploads')
        backups_dir = os.path.join(data_dir, 'backups')
        
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(backups_dir, exist_ok=True)
        
        logger.info('数据目录初始化完成')
        
        # 初始化数据库
        db_session = init_db()
        logger.info('数据库初始化完成')
        
        # 创建默认配置
        default_configs = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': '587',
            'smtp_username': '',
            'smtp_password': '',
            'sender_email': '',
            'email_recipients': '',
            'smtp_use_tls': 'true',
            'wechat_webhook_url': '',
            'enable_wechat_push': 'false',
            'enable_email_push': 'false',
            'sync_hour': '2',
            'sync_minute': '0',
            'enable_scheduler': 'true',
            'backup_days_to_keep': '30'
        }
        
        # 初始化默认配置
        for config_name, default_value in default_configs.items():
            config = db_session.execute(
                select(SystemConfig).where(SystemConfig.config_name == config_name)
            ).scalar_one_or_none()
            
            if not config:
                new_config = SystemConfig(config_name=config_name, config_value=default_value)
                db_session.add(new_config)
                logger.info(f'创建默认配置: {config_name} = {default_value}')
        
        db_session.commit()
        logger.info('默认配置初始化完成')
        
        # 创建初始备份
        backup_manager = BackupManager(db_session)
        logger.info('创建初始备份...')
        backup_result = backup_manager.create_backup(description='系统初始化备份')
        if backup_result['status'] == 'success':
            logger.info(f'初始备份创建成功: {backup_result["backup_file"]}')
        else:
            logger.warning(f'初始备份创建失败: {backup_result["message"]}')
            
    except Exception as e:
        logger.error(f'应用初始化失败: {str(e)}')
        raise

def main():
    """主函数"""
    try:
        logger.info('========================================')
        logger.info('亚马逊多平台数据整合报表工具 - 启动中')
        logger.info('========================================')
        
        # 初始化应用
        initialize_app()
        
        # 启动调度器线程
        scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()
        
        # 等待调度器启动
        time.sleep(2)
        
        # 启动API服务器（主线程）
        start_api_server()
        
    except KeyboardInterrupt:
        logger.info('收到停止信号，正在优雅退出...')
    except Exception as e:
        logger.error(f'应用启动失败: {str(e)}')
        sys.exit(1)
    finally:
        logger.info('应用已停止')

if __name__ == '__main__':
    main()
