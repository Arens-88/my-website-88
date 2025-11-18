# 移除requests依赖
import logging
import random
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
import json
import datetime
import logging
from models import AmazonStore, SystemConfig, User, init_db
from retry_utils import api_retry, RetryError, network_retry_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('amazon_oauth')

class AmazonOAuth:
    """亚马逊SP-API OAuth2.0认证管理器，支持用户数据隔离"""
    
    # 区域端点配置
    REGION_ENDPOINTS = {
        'US': 'https://api.amazon.com/auth/o2/token',
        'EU': 'https://api.amazon.eu/auth/o2/token',
        'FE': 'https://api.amazon.com/auth/o2/token',  # 远东
        'JP': 'https://api.amazon.co.jp/auth/o2/token'
    }
    
    def __init__(self, db_session=None, user_id=None, is_admin=False):
        """
        初始化OAuth管理器 - 模拟实现
        
        Args:
            db_session: 数据库会话对象
            user_id: 当前用户ID，用于数据隔离
            is_admin: 是否为管理员用户
        """
        # 移除数据库依赖和models导入
        self.db_session = None
        self.user_id = user_id
        self.is_admin = is_admin
        logger.info(f"初始化模拟OAuth管理器 - 用户ID: {user_id}, 管理员: {is_admin}")
    
    def get_store_by_id(self, store_id):
        """根据ID获取店铺信息 - 模拟实现"""
        logger.info(f"模拟获取店铺ID: {store_id} 的信息")
        # 创建一个模拟的店铺对象
        class MockStore:
            def __init__(self, id, name):
                self.id = id
                self.store_name = f"模拟店铺_{name}"
                self.access_token = f"mock_token_{id}"
                self.token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                self.refresh_token = f"mock_refresh_token_{id}"
                self.client_id = f"mock_client_id_{id}"
                self.client_secret = f"mock_client_secret_{id}"
                self.region = "US"
        
        return MockStore(store_id, store_id)
    
    def get_store_by_user_and_id(self, user_id, store_id):
        """根据用户ID和店铺ID获取店铺信息，用于严格权限验证"""
        return self.db_session.query(AmazonStore).filter_by(
            id=store_id,
            user_id=user_id
        ).first()
    
    def get_active_stores(self):
        """获取激活的店铺，支持用户数据隔离"""
        query = self.db_session.query(AmazonStore).filter_by(is_active=1)
        
        # 应用数据隔离：非管理员只能看到自己的店铺
        if not self.is_admin and self.user_id:
            query = query.filter_by(user_id=self.user_id)
        
        return query.all()
    
    def get_user_stores(self, user_id):
        """获取指定用户的所有店铺（管理员功能）"""
        if not self.is_admin:
            # 非管理员只能查看自己的店铺
            user_id = self.user_id or user_id
        
        return self.db_session.query(AmazonStore).filter_by(user_id=user_id).all()
    
    def is_token_valid(self, store):
        """检查令牌是否有效 - 模拟实现"""
        return True
    
    @network_retry_manager.retry_on([Exception])
    def refresh_access_token(self, store):
        """刷新访问令牌 - 模拟实现（带自动重试）"""
        logger.info(f'模拟刷新店铺 {store.store_name} 的访问令牌')
        time.sleep(0.5)  # 模拟网络延迟
        
        # 模拟成功的响应数据
        mock_token = f"mock_access_token_{store.id}_{random.randint(1000, 9999)}"
        expires_in = 3600  # 默认1小时
        
        # 更新店铺信息
        store.access_token = mock_token
        store.token_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
        
        self.db_session.commit()
        logger.info(f'店铺 {store.store_name} 的访问令牌模拟刷新成功，有效期至 {store.token_expiry}')
        
        return store.access_token
    
    def _log_api_error(self, api_type, store_id, error_msg):
        """记录API错误信息 - 模拟实现"""
        logger.info(f"模拟记录API错误: {api_type}, 店铺ID: {store_id}, 错误: {error_msg}")
    
    @network_retry_manager.retry_on([Exception])
    def get_valid_access_token(self, store_id):
        """获取有效访问令牌 - 模拟实现（带自动重试）"""
        logger.info(f"模拟获取店铺{store_id}的有效访问令牌")
        return f"mock_valid_token_{store_id}_{random.randint(1000, 9999)}"
    
    def add_store(self, store_name, region, client_id, client_secret, refresh_token, merchant_id=None, marketplace_id=None, country=None):
        """
        添加新店铺配置，支持用户数据隔离
        
        Args:
            store_name: 店铺名称
            region: 区域代码(US/EU/FE/JP)
            client_id: 客户端ID
            client_secret: 客户端密钥
            refresh_token: 刷新令牌
            merchant_id: 商家ID
            marketplace_id: 市场ID
            country: 国家/地区
            
        Returns:
            成功返回{'status': 'success', 'store': store对象}，失败返回{'status': 'error', 'message': 错误信息}
        """
        try:
            if not self.user_id:
                logger.error('添加店铺失败：未指定用户ID')
                return {'status': 'error', 'message': '未指定用户ID'}
            
            # 检查是否已存在同名店铺（在当前用户的店铺中）
            existing_store = self.db_session.query(AmazonStore).filter_by(
                store_name=store_name, 
                region=region,
                user_id=self.user_id
            ).first()
            
            if existing_store:
                logger.warning(f'用户ID {self.user_id} 的店铺 {store_name} 已存在，将更新配置')
                store = existing_store
                store.client_id = client_id
                store.client_secret = client_secret
                store.refresh_token = refresh_token
                store.is_active = 1
                # 更新可选字段
                if merchant_id:
                    store.merchant_id = merchant_id
                if marketplace_id:
                    store.marketplace_id = marketplace_id
                if country:
                    store.country = country
            else:
                # 创建新店铺，关联到当前用户
                store = AmazonStore(
                    store_name=store_name,
                    region=region,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    merchant_id=merchant_id,
                    marketplace_id=marketplace_id,
                    country=country,
                    user_id=self.user_id,  # 关联用户ID
                    is_active=1
                )
                self.db_session.add(store)
            
            # 立即刷新token以验证配置有效性
            if not self.refresh_access_token(store):
                self.db_session.rollback()
                return {'status': 'error', 'message': '刷新访问令牌失败，请检查认证信息'}
            
            self.db_session.commit()
            logger.info(f'店铺 {store_name} 配置成功')
            return {'status': 'success', 'store': store}
            
        except Exception as e:
            logger.error(f'添加店铺时发生错误: {str(e)}')
            self.db_session.rollback()
            return {'status': 'error', 'message': str(e)}
    
    def update_store(self, store_id, **kwargs):
        """
        更新店铺配置，支持用户数据隔离
        
        Args:
            store_id: 店铺ID
            **kwargs: 要更新的字段和值
            
        Returns:
            成功返回{'status': 'success', 'store': store对象}，失败返回{'status': 'error', 'message': 错误信息}
        """
        try:
            # 根据权限获取店铺：管理员可以更新所有店铺，普通用户只能更新自己的
            if self.is_admin:
                store = self.db_session.query(AmazonStore).filter_by(id=store_id).first()
            else:
                store = self.get_store_by_user_and_id(self.user_id, store_id)
            
            if not store:
                logger.error(f'未找到ID为 {store_id} 的店铺，或者无权访问')
                return {'status': 'error', 'message': '未找到店铺或无权访问'}
            
            # 不允许普通用户修改user_id字段
            if not self.is_admin and 'user_id' in kwargs:
                logger.warning(f'用户 {self.user_id} 尝试修改店铺 {store_id} 的所有权，操作被拒绝')
                del kwargs['user_id']
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(store, key):
                    setattr(store, key, value)
            
            # 如果更新了凭证，清除token以强制重新刷新
            if any(k in kwargs for k in ['client_id', 'client_secret', 'refresh_token']):
                store.access_token = None
                store.token_expiry = None
                # 尝试刷新token以验证凭证有效性
                if not self.refresh_access_token(store):
                    self.db_session.rollback()
                    return {'status': 'error', 'message': '刷新访问令牌失败，请检查认证信息'}
            
            self.db_session.commit()
            logger.info(f'用户 {self.user_id} 更新了店铺 {store.store_name} 配置')
            return {'status': 'success', 'store': store}
            
        except Exception as e:
            logger.error(f'更新店铺时发生错误: {str(e)}')
            self.db_session.rollback()
            return {'status': 'error', 'message': str(e)}
    
    def deactivate_store(self, store_id):
        """
        停用店铺，支持用户数据隔离
        
        Args:
            store_id: 店铺ID
            
        Returns:
            成功返回{'status': 'success', 'store': store对象}，失败返回{'status': 'error', 'message': 错误信息}
        """
        try:
            # 根据权限获取店铺
            if self.is_admin:
                store = self.db_session.query(AmazonStore).filter_by(id=store_id).first()
            else:
                store = self.get_store_by_user_and_id(self.user_id, store_id)
            
            if not store:
                logger.error(f'未找到ID为 {store_id} 的店铺，或者无权访问')
                return {'status': 'error', 'message': '未找到店铺或无权访问'}
            
            store.is_active = 0
            # 清除凭证以防误用
            store.access_token = None
            store.token_expiry = None
            
            self.db_session.commit()
            logger.info(f'用户 {self.user_id} 停用了店铺 {store.store_name}')
            return {'status': 'success', 'store': store}
        except Exception as e:
            logger.error(f'停用店铺时发生错误: {str(e)}')
            self.db_session.rollback()
            return {'status': 'error', 'message': str(e)}
        
    def activate_store(self, store_id):
        """
        激活店铺，支持用户数据隔离
        
        Args:
            store_id: 店铺ID
            
        Returns:
            成功返回{'status': 'success', 'store': store对象}，失败返回{'status': 'error', 'message': 错误信息}
        """
        try:
            # 根据权限获取店铺
            if self.is_admin:
                store = self.db_session.query(AmazonStore).filter_by(id=store_id).first()
            else:
                store = self.get_store_by_user_and_id(self.user_id, store_id)
            
            if not store:
                logger.error(f'未找到ID为 {store_id} 的店铺，或者无权访问')
                return {'status': 'error', 'message': '未找到店铺或无权访问'}
            
            # 检查必要的凭证是否存在
            if not all([store.client_id, store.client_secret, store.refresh_token]):
                logger.error(f'店铺 {store.store_name} 缺少必要的认证凭证')
                return {'status': 'error', 'message': '店铺缺少必要的认证凭证'}
            
            store.is_active = 1
            
            # 尝试刷新token以验证凭证有效性
            if not self.refresh_access_token(store):
                self.db_session.rollback()
                logger.error(f'激活店铺失败：无法刷新访问令牌')
                return {'status': 'error', 'message': '无法刷新访问令牌，激活失败'}
            
            self.db_session.commit()
            logger.info(f'用户 {self.user_id} 激活了店铺 {store.store_name}')
            return {'status': 'success', 'store': store}
            
        except Exception as e:
            logger.error(f'激活店铺时发生错误: {str(e)}')
            self.db_session.rollback()
            return {'status': 'error', 'message': str(e)}

# 使用示例
if __name__ == '__main__':
    # 示例1：以管理员身份初始化
    # admin_manager = AmazonOAuth(is_admin=True, user_id=1)  # 假设管理员用户ID为1
    
    # 示例2：以普通用户身份初始化
    # user_manager = AmazonOAuth(user_id=2)
    
    # 示例3：添加店铺
    # store_id = user_manager.add_store(
    #     store_name="美国站测试店铺",
    #     region="US",
    #     client_id="YOUR_CLIENT_ID",
    #     client_secret="YOUR_CLIENT_SECRET",
    #     refresh_token="YOUR_REFRESH_TOKEN",
    #     merchant_id="YOUR_MERCHANT_ID",
    #     marketplace_id="ATVPDKIKX0DER",  # 美国市场ID
    #     country="US"
    # )
    # print(f"添加店铺成功，ID: {store_id}")
    
    # 示例4：获取有效令牌
    # if store_id:
    #     token = user_manager.get_valid_access_token(store_id)
    #     print(f"获取访问令牌: {token}")
    
    # 示例5：获取用户的激活店铺
    # active_stores = user_manager.get_active_stores()
    # for store in active_stores:
    #     print(f"店铺: {store.store_name}, 状态: {'激活' if store.is_active else '停用'}")
    pass  # 添加pass语句避免缩进错误
