import os
import shutil
import datetime
import sqlite3
import logging
import zipfile
import json
from models import init_db

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('backup_manager')

class BackupManager:
    """数据备份管理模块"""
    
    def __init__(self, db_session=None, backup_dir=None):
        self.db_session = db_session or init_db()
        # 备份目录
        self.backup_dir = backup_dir or os.path.join('..', 'data', 'backups')
        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)
        # 数据文件目录
        self.data_dir = os.path.join('..', 'data')
        # 数据库文件路径（假设使用SQLite，实际路径可能需要调整）
        self.db_path = os.path.join(self.data_dir, 'amazon_report_tool.db')
    
    def create_backup(self, description=''):
        """创建数据备份"""
        try:
            # 生成备份文件名
            timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'backup_{timestamp}.zip'
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # 创建临时备份目录
            temp_backup_dir = os.path.join(self.backup_dir, f'temp_backup_{timestamp}')
            os.makedirs(temp_backup_dir, exist_ok=True)
            
            # 备份数据库文件
            if os.path.exists(self.db_path):
                db_backup_path = os.path.join(temp_backup_dir, os.path.basename(self.db_path))
                shutil.copy2(self.db_path, db_backup_path)
                logger.info(f'数据库文件已备份: {db_backup_path}')
            else:
                logger.warning(f'数据库文件不存在: {self.db_path}')
            
            # 备份报表数据
            reports_dir = os.path.join(self.data_dir, 'reports')
            if os.path.exists(reports_dir):
                reports_backup_dir = os.path.join(temp_backup_dir, 'reports')
                shutil.copytree(reports_dir, reports_backup_dir, dirs_exist_ok=True)
                logger.info(f'报表数据已备份: {reports_backup_dir}')
            
            # 备份上传的文件
            uploads_dir = os.path.join(self.data_dir, 'uploads')
            if os.path.exists(uploads_dir):
                uploads_backup_dir = os.path.join(temp_backup_dir, 'uploads')
                shutil.copytree(uploads_dir, uploads_backup_dir, dirs_exist_ok=True)
                logger.info(f'上传文件已备份: {uploads_backup_dir}')
            
            # 创建备份元数据
            metadata = {
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'description': description,
                'version': '1.0',
                'backup_path': backup_path
            }
            
            metadata_file = os.path.join(temp_backup_dir, 'metadata.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 创建压缩包
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历临时备份目录中的所有文件
                for root, dirs, files in os.walk(temp_backup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 计算相对路径，用于在压缩包中的路径结构
                        arcname = os.path.relpath(file_path, temp_backup_dir)
                        zipf.write(file_path, arcname)
            
            # 清理临时文件
            shutil.rmtree(temp_backup_dir)
            
            # 记录备份信息
            backup_info = {
                'backup_file': backup_filename,
                'backup_path': backup_path,
                'size': os.path.getsize(backup_path),
                'timestamp': timestamp,
                'description': description
            }
            
            # 更新备份日志
            self._update_backup_log(backup_info)
            
            logger.info(f'备份创建成功: {backup_path}, 大小: {self._format_size(backup_info["size"])}')
            
            return {
                'status': 'success',
                'message': '备份创建成功',
                'backup_file': backup_filename,
                'backup_path': backup_path,
                'size': backup_info['size'],
                'size_human': self._format_size(backup_info['size']),
                'timestamp': timestamp
            }
            
        except Exception as e:
            error_message = f'创建备份时发生错误: {str(e)}'
            logger.error(error_message)
            # 清理临时文件
            if 'temp_backup_dir' in locals() and os.path.exists(temp_backup_dir):
                shutil.rmtree(temp_backup_dir)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def restore_from_backup(self, backup_filename):
        """从备份恢复数据"""
        try:
            # 备份文件路径
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # 检查备份文件是否存在
            if not os.path.exists(backup_path):
                error_message = f'备份文件不存在: {backup_path}'
                logger.error(error_message)
                return {
                    'status': 'error',
                    'message': error_message
                }
            
            # 验证备份文件是否为有效的zip文件
            if not zipfile.is_zipfile(backup_path):
                error_message = f'无效的备份文件: {backup_path}'
                logger.error(error_message)
                return {
                    'status': 'error',
                    'message': error_message
                }
            
            # 创建临时恢复目录
            timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            temp_restore_dir = os.path.join(self.backup_dir, f'temp_restore_{timestamp}')
            os.makedirs(temp_restore_dir, exist_ok=True)
            
            # 解压缩备份文件
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_restore_dir)
            
            # 读取元数据
            metadata_file = os.path.join(temp_restore_dir, 'metadata.json')
            if not os.path.exists(metadata_file):
                logger.warning('备份文件中未找到元数据')
                metadata = None
            else:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # 停止应用相关服务（实际应用中可能需要更复杂的处理）
            logger.info('开始从备份恢复数据...')
            
            # 关闭数据库会话
            if self.db_session:
                self.db_session.close()
            
            # 备份当前数据，以防恢复失败
            safety_backup = self.create_backup(description='恢复前的安全备份')
            if safety_backup['status'] != 'success':
                logger.error('创建安全备份失败，中止恢复操作')
                return {
                    'status': 'error',
                    'message': '创建安全备份失败，中止恢复操作'
                }
            
            # 恢复数据库文件
            db_backup_path = os.path.join(temp_restore_dir, os.path.basename(self.db_path))
            if os.path.exists(db_backup_path):
                # 确保目标目录存在
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                shutil.copy2(db_backup_path, self.db_path)
                logger.info(f'数据库文件已恢复: {self.db_path}')
            else:
                logger.warning(f'备份中未找到数据库文件: {db_backup_path}')
            
            # 恢复报表数据
            reports_backup_dir = os.path.join(temp_restore_dir, 'reports')
            if os.path.exists(reports_backup_dir):
                reports_dir = os.path.join(self.data_dir, 'reports')
                # 清空现有报表目录
                if os.path.exists(reports_dir):
                    shutil.rmtree(reports_dir)
                # 恢复报表数据
                shutil.copytree(reports_backup_dir, reports_dir)
                logger.info(f'报表数据已恢复: {reports_dir}')
            
            # 恢复上传的文件
            uploads_backup_dir = os.path.join(temp_restore_dir, 'uploads')
            if os.path.exists(uploads_backup_dir):
                uploads_dir = os.path.join(self.data_dir, 'uploads')
                # 清空现有上传目录
                if os.path.exists(uploads_dir):
                    shutil.rmtree(uploads_dir)
                # 恢复上传文件
                shutil.copytree(uploads_backup_dir, uploads_dir)
                logger.info(f'上传文件已恢复: {uploads_dir}')
            
            # 清理临时文件
            shutil.rmtree(temp_restore_dir)
            
            logger.info(f'从备份恢复成功: {backup_filename}')
            
            return {
                'status': 'success',
                'message': '从备份恢复成功',
                'backup_file': backup_filename,
                'safety_backup': safety_backup.get('backup_file'),
                'metadata': metadata
            }
            
        except Exception as e:
            error_message = f'从备份恢复时发生错误: {str(e)}'
            logger.error(error_message)
            # 清理临时文件
            if 'temp_restore_dir' in locals() and os.path.exists(temp_restore_dir):
                shutil.rmtree(temp_restore_dir)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def list_backups(self):
        """列出所有备份"""
        try:
            # 获取备份日志
            backups = self._get_backup_logs()
            
            # 过滤掉不存在的备份文件
            valid_backups = []
            for backup in backups:
                backup_path = os.path.join(self.backup_dir, backup['backup_file'])
                if os.path.exists(backup_path):
                    # 更新大小信息
                    backup['size'] = os.path.getsize(backup_path)
                    backup['size_human'] = self._format_size(backup['size'])
                    backup['exists'] = True
                    valid_backups.append(backup)
                else:
                    logger.warning(f'备份文件不存在: {backup_path}')
            
            # 按时间戳降序排序
            valid_backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'status': 'success',
                'data': valid_backups,
                'total': len(valid_backups)
            }
            
        except Exception as e:
            error_message = f'列出备份时发生错误: {str(e)}'
            logger.error(error_message)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def delete_backup(self, backup_filename):
        """删除指定备份"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # 检查备份文件是否存在
            if not os.path.exists(backup_path):
                return {
                    'status': 'error',
                    'message': '备份文件不存在'
                }
            
            # 删除备份文件
            os.remove(backup_path)
            
            # 从备份日志中移除
            self._remove_from_backup_log(backup_filename)
            
            logger.info(f'备份已删除: {backup_filename}')
            
            return {
                'status': 'success',
                'message': '备份删除成功'
            }
            
        except Exception as e:
            error_message = f'删除备份时发生错误: {str(e)}'
            logger.error(error_message)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def cleanup_old_backups(self, days_to_keep=30):
        """清理旧备份"""
        try:
            # 计算保留期限
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_to_keep)
            cutoff_timestamp = cutoff_date.strftime('%Y%m%d_%H%M%S')
            
            # 获取所有备份
            backups = self._get_backup_logs()
            
            deleted_count = 0
            for backup in backups:
                # 比较时间戳
                if backup['timestamp'] < cutoff_timestamp:
                    delete_result = self.delete_backup(backup['backup_file'])
                    if delete_result['status'] == 'success':
                        deleted_count += 1
            
            logger.info(f'清理旧备份完成，共删除 {deleted_count} 个备份')
            
            return {
                'status': 'success',
                'message': f'清理旧备份完成',
                'deleted_count': deleted_count,
                'days_kept': days_to_keep
            }
            
        except Exception as e:
            error_message = f'清理旧备份时发生错误: {str(e)}'
            logger.error(error_message)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def _update_backup_log(self, backup_info):
        """更新备份日志"""
        try:
            # 备份日志文件路径
            log_file = os.path.join(self.backup_dir, 'backup_log.json')
            
            # 读取现有日志
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # 添加新备份信息
            logs.append(backup_info)
            
            # 保存日志
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f'更新备份日志时发生错误: {str(e)}')
    
    def _get_backup_logs(self):
        """获取备份日志"""
        try:
            # 备份日志文件路径
            log_file = os.path.join(self.backup_dir, 'backup_log.json')
            
            # 读取日志
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return []
                
        except Exception as e:
            logger.error(f'获取备份日志时发生错误: {str(e)}')
            return []
    
    def _remove_from_backup_log(self, backup_filename):
        """从备份日志中移除指定备份"""
        try:
            # 备份日志文件路径
            log_file = os.path.join(self.backup_dir, 'backup_log.json')
            
            # 读取现有日志
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                
                # 过滤掉要删除的备份
                new_logs = [log for log in logs if log['backup_file'] != backup_filename]
                
                # 保存更新后的日志
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(new_logs, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.error(f'从备份日志中移除备份时发生错误: {str(e)}')
    
    def _format_size(self, size_bytes):
        """格式化文件大小为人类可读的形式"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} GB"

# 使用示例
if __name__ == '__main__':
    # 示例：创建备份
    # backup_manager = BackupManager()
    # result = backup_manager.create_backup(description='每日自动备份')
    # print(f"创建备份: {result['message']}")
    
    # 示例：列出所有备份
    # backups = backup_manager.list_backups()
    # print(f"备份列表: {backups['total']} 个备份")
    # for backup in backups['data']:
    #     print(f"- {backup['backup_file']} ({backup['size_human']}, {backup['timestamp']})")
    
    # 示例：清理30天前的备份
    # cleanup_result = backup_manager.cleanup_old_backups(days_to_keep=30)
    # print(f"清理备份: {cleanup_result['message']}")
