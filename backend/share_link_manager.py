import uuid
import time
import logging
from datetime import datetime, timedelta
from models import ShareLink, db_session
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)

class ShareLinkManager:
    """
    报表共享链接管理器，负责生成、验证和管理共享链接
    """
    
    def __init__(self):
        self.report_generator = ReportGenerator()
    
    def generate_share_link(self, report_type, report_id, user_id, expire_days=7, access_type='readonly'):
        """
        生成报表共享链接
        
        Args:
            report_type: 报表类型 ('profit', 'trend', 'inventory')
            report_id: 报表ID或相关标识符
            user_id: 创建共享链接的用户ID
            expire_days: 链接有效期（天），默认7天
            access_type: 访问类型 ('readonly' 或 'view')
            
        Returns:
            dict: 包含共享链接信息的字典
        """
        try:
            # 生成唯一的共享令牌
            share_token = str(uuid.uuid4())
            
            # 计算过期时间
            expire_at = datetime.utcnow() + timedelta(days=expire_days)
            
            # 创建共享链接记录
            share_link = ShareLink(
                token=share_token,
                report_type=report_type,
                report_id=report_id,
                user_id=user_id,
                access_type=access_type,
                created_at=datetime.utcnow(),
                expire_at=expire_at,
                is_active=True
            )
            
            db_session.add(share_link)
            db_session.commit()
            
            # 构建完整的共享链接URL
            share_url = f"/api/share/{share_token}"
            
            logger.info(f"用户 {user_id} 生成了报表类型 {report_type} 的共享链接")
            
            return {
                'token': share_token,
                'share_url': share_url,
                'report_type': report_type,
                'report_id': report_id,
                'created_at': share_link.created_at.isoformat(),
                'expire_at': expire_at.isoformat(),
                'access_type': access_type
            }
            
        except Exception as e:
            logger.error(f"生成共享链接失败: {str(e)}")
            db_session.rollback()
            raise
    
    def validate_share_link(self, token):
        """
        验证共享链接是否有效
        
        Args:
            token: 共享令牌
            
        Returns:
            ShareLink对象或None（如果链接无效）
        """
        try:
            share_link = db_session.query(ShareLink).filter_by(token=token, is_active=True).first()
            
            if not share_link:
                logger.warning(f"无效的共享令牌: {token}")
                return None
            
            # 检查是否过期
            if datetime.utcnow() > share_link.expire_at:
                # 标记为过期
                share_link.is_active = False
                db_session.commit()
                logger.warning(f"共享令牌已过期: {token}")
                return None
            
            # 更新最后访问时间
            share_link.last_accessed = datetime.utcnow()
            db_session.commit()
            
            return share_link
            
        except Exception as e:
            logger.error(f"验证共享链接失败: {str(e)}")
            return None
    
    def get_shared_report_data(self, token):
        """
        获取共享报表的数据
        
        Args:
            token: 共享令牌
            
        Returns:
            dict: 报表数据（只读权限）
        """
        share_link = self.validate_share_link(token)
        
        if not share_link:
            return None
        
        try:
            # 根据报表类型获取数据
            if share_link.report_type == 'profit':
                # 获取利润报表数据
                report_data = self.report_generator.generate_profit_report(
                    user_id=share_link.user_id,
                    report_id=share_link.report_id,
                    for_sharing=True
                )
            elif share_link.report_type == 'trend':
                # 获取趋势报表数据
                report_data = self.report_generator.generate_trend_report(
                    user_id=share_link.user_id,
                    report_id=share_link.report_id,
                    for_sharing=True
                )
            elif share_link.report_type == 'inventory':
                # 获取库存报表数据
                report_data = self.report_generator.generate_inventory_report(
                    user_id=share_link.user_id,
                    report_id=share_link.report_id,
                    for_sharing=True
                )
            else:
                logger.error(f"未知的报表类型: {share_link.report_type}")
                return None
            
            # 添加共享元数据
            report_data['share_metadata'] = {
                'report_type': share_link.report_type,
                'shared_by': share_link.user_id,
                'expire_at': share_link.expire_at.isoformat(),
                'access_type': share_link.access_type
            }
            
            logger.info(f"成功获取共享报表数据，令牌: {token}")
            return report_data
            
        except Exception as e:
            logger.error(f"获取共享报表数据失败: {str(e)}")
            return None
    
    def revoke_share_link(self, token, user_id):
        """
        撤销共享链接
        
        Args:
            token: 共享令牌
            user_id: 执行撤销操作的用户ID
            
        Returns:
            bool: 是否撤销成功
        """
        try:
            # 确保只有链接创建者才能撤销
            share_link = db_session.query(ShareLink).filter_by(
                token=token,
                user_id=user_id
            ).first()
            
            if not share_link:
                logger.warning(f"用户 {user_id} 尝试撤销不存在的共享链接: {token}")
                return False
            
            # 标记为已撤销
            share_link.is_active = False
            share_link.revoked_at = datetime.utcnow()
            db_session.commit()
            
            logger.info(f"用户 {user_id} 成功撤销共享链接: {token}")
            return True
            
        except Exception as e:
            logger.error(f"撤销共享链接失败: {str(e)}")
            db_session.rollback()
            return False
    
    def list_user_share_links(self, user_id, active_only=True):
        """
        列出用户创建的所有共享链接
        
        Args:
            user_id: 用户ID
            active_only: 是否只显示活跃的链接
            
        Returns:
            list: 共享链接列表
        """
        try:
            query = db_session.query(ShareLink).filter_by(user_id=user_id)
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            links = query.order_by(ShareLink.created_at.desc()).all()
            
            # 转换为可序列化的格式
            result = []
            for link in links:
                result.append({
                    'token': link.token,
                    'report_type': link.report_type,
                    'report_id': link.report_id,
                    'share_url': f"/api/share/{link.token}",
                    'created_at': link.created_at.isoformat(),
                    'expire_at': link.expire_at.isoformat(),
                    'last_accessed': link.last_accessed.isoformat() if link.last_accessed else None,
                    'access_type': link.access_type,
                    'is_active': link.is_active
                })
            
            return result
            
        except Exception as e:
            logger.error(f"列出用户共享链接失败: {str(e)}")
            return []
    
    def extend_share_link(self, token, user_id, additional_days):
        """
        延长共享链接的有效期
        
        Args:
            token: 共享令牌
            user_id: 用户ID
            additional_days: 额外增加的天数
            
        Returns:
            dict: 更新后的链接信息或None
        """
        try:
            share_link = db_session.query(ShareLink).filter_by(
                token=token,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not share_link:
                logger.warning(f"无法延长不存在或已过期的共享链接: {token}")
                return None
            
            # 延长有效期
            share_link.expire_at += timedelta(days=additional_days)
            db_session.commit()
            
            logger.info(f"用户 {user_id} 延长了共享链接 {token} 的有效期，增加 {additional_days} 天")
            
            return {
                'token': share_link.token,
                'expire_at': share_link.expire_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"延长共享链接有效期失败: {str(e)}")
            db_session.rollback()
            return None

# 全局实例
share_link_manager = ShareLinkManager()