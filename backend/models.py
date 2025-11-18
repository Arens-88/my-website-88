from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, create_engine, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import hashlib
import os

Base = declarative_base()

# 用户表 - 基础用户信息
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # 存储密码哈希值
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    is_admin = Column(Boolean, default=False)  # 是否管理员权限
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系定义
    amazon_stores = relationship("AmazonStore", back_populates="user", cascade="all, delete-orphan")
    integrated_data = relationship("AmazonIntegratedData", back_populates="user", cascade="all, delete-orphan")
    manual_costs = relationship("ManualCost", back_populates="user", cascade="all, delete-orphan")
    cost_records = relationship("CostRecord", back_populates="user", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="user", cascade="all, delete-orphan")
    push_configs = relationship("PushConfig", back_populates="user", cascade="all, delete-orphan")
    report_shares = relationship("ReportShare", back_populates="user", cascade="all, delete-orphan")
    share_links = relationship("ShareLink", back_populates="user", cascade="all, delete-orphan")
    erp_cost_files = relationship("ERPCostFile", back_populates="user", cascade="all, delete-orphan")
    erp_cost_data = relationship("ERPCostData", back_populates="user", cascade="all, delete-orphan")
    inventory_data = relationship('InventoryData', back_populates='user', cascade="all, delete-orphan")
    custom_metrics = relationship("CustomMetric", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password):
        """设置用户密码，存储哈希值"""
        self.password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def check_password(self, password):
        """验证密码是否正确"""
        return self.password_hash == hashlib.sha256(password.encode('utf-8')).hexdigest()

# 配置信息表 - 存储API认证信息和系统配置
class SystemConfig(Base):
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(String(500))
    description = Column(String(255))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # 系统配置可为空，用户配置不能为空
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", backref="system_configs")

# 亚马逊店铺配置表
class AmazonStore(Base):
    __tablename__ = 'amazon_stores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    store_name = Column(String(100), nullable=False)
    region = Column(String(20), nullable=False)  # US, JP, EU等
    client_id = Column(String(255))
    client_secret = Column(String(255))
    refresh_token = Column(String(255))
    access_token = Column(String(255))
    token_expiry = Column(DateTime)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="amazon_stores")
    cost_records = relationship('CostRecord', back_populates='store')

# 亚马逊整合数据表 - 存储所有整合后的数据
class AmazonIntegratedData(Base):
    __tablename__ = 'amazon_integrated_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    asin = Column(String(20), nullable=False, index=True)  # 产品ASIN
    order_date = Column(Date, nullable=False, index=True)  # 订单日期
    store_id = Column(Integer, ForeignKey('amazon_stores.id'))
    store_name = Column(String(100))  # 冗余存储，便于查询
    order_count = Column(Integer, default=0)  # 订单量
    sales_amount = Column(Float, default=0.0)  # 销售额
    platform_fee = Column(Float, default=0.0)  # 平台费
    ad_spend = Column(Float, default=0.0)  # 广告花费
    product_cost = Column(Float, default=0.0)  # 产品成本
    shipping_cost = Column(Float, default=0.0)  # 头程运费
    promotion_fee = Column(Float, default=0.0)  # 促销费
    handling_fee = Column(Float, default=0.0)  # 手续费
    # 新增费用字段
    storage_fee = Column(Float, default=0.0)  # 仓储费
    commission_fee = Column(Float, default=0.0)  # 佣金
    advertising_fee = Column(Float, default=0.0)  # 广告费
    return_fee = Column(Float, default=0.0)  # 退货费
    refund_fee = Column(Float, default=0.0)  # 退款费
    other_fee = Column(Float, default=0.0)  # 其他费用
    
    # 核心指标字段
    net_profit = Column(Float, default=0.0)  # 净利润
    net_profit_rate = Column(Float, default=0.0)  # 净利润率
    average_order_value = Column(Float, default=0.0)  # 客单价
    roas = Column(Float, default=0.0)  # 广告投入产出比
    profit_level = Column(String(10))  # 利润率等级（高/中/低/亏损）
    
    # 库存相关字段
    inventory_quantity = Column(Integer, default=0)  # 在库量
    inbound_quantity = Column(Integer, default=0)  # 在途量
    sales_30days = Column(Integer, default=0)  # 30天销量
    inventory_turnover_rate = Column(Float, default=0.0)  # 库存周转率
    inventory_coverage_days = Column(Float, default=0.0)  # 库存覆盖天数
    inventory_note = Column(String(255))  # 库存备注
    
    # 费用率字段
    platform_fee_rate = Column(Float, default=0.0)  # 平台总费用率
    ad_spend_rate = Column(Float, default=0.0)  # 广告总费用率
    cost_of_goods_rate = Column(Float, default=0.0)  # 商品成本率
    storage_fee_rate = Column(Float, default=0.0)  # 仓储费用率
    return_fee_rate = Column(Float, default=0.0)  # 退货费用率
    
    # 异常标记和记录
    is_exception = Column(Integer, default=0)  # 是否异常数据
    exception_note = Column(String(500))  # 异常备注
    exception_reasons = Column(Text)  # 异常原因列表（JSON格式存储）
    is_estimated = Column(Integer, default=0)  # 是否为估算数据
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="integrated_data")
    store = relationship("AmazonStore")
    
    # 索引优化
    __table_args__ = (
        # 复合索引，加速按日期和店铺的查询
        Index('idx_date_store', 'order_date', 'store_id'),
        # 复合索引，加速按日期和ASIN的查询
        Index('idx_date_asin', 'order_date', 'asin'),
    )
    
    def to_dict(self):
        """转换为字典格式，方便JSON序列化"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'asin': self.asin,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'store_id': self.store_id,
            'store_name': self.store_name,
            'order_count': self.order_count,
            'sales_amount': self.sales_amount,
            'platform_fee': self.platform_fee,
            'ad_spend': self.ad_spend,
            'product_cost': self.product_cost,
            'shipping_cost': self.shipping_cost,
            'promotion_fee': self.promotion_fee,
            'handling_fee': self.handling_fee,
            'storage_fee': self.storage_fee,
            'commission_fee': self.commission_fee,
            'advertising_fee': self.advertising_fee,
            'return_fee': self.return_fee,
            'refund_fee': self.refund_fee,
            'other_fee': self.other_fee,
            'net_profit': self.net_profit,
            'net_profit_rate': self.net_profit_rate,
            'average_order_value': self.average_order_value,
            'roas': self.roas,
            'profit_level': self.profit_level,
            'inventory_quantity': self.inventory_quantity,
            'inbound_quantity': self.inbound_quantity,
            'sales_30days': self.sales_30days,
            'inventory_turnover_rate': self.inventory_turnover_rate,
            'inventory_coverage_days': self.inventory_coverage_days,
            'inventory_note': self.inventory_note,
            'platform_fee_rate': self.platform_fee_rate,
            'ad_spend_rate': self.ad_spend_rate,
            'cost_of_goods_rate': self.cost_of_goods_rate,
            'storage_fee_rate': self.storage_fee_rate,
            'return_fee_rate': self.return_fee_rate,
            'is_exception': self.is_exception,
            'exception_note': self.exception_note,
            'exception_reasons': self.exception_reasons,
            'is_estimated': self.is_estimated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# 成本记录表
class CostRecord(Base):
    __tablename__ = 'cost_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(50), nullable=False, index=True)
    cost_type = Column(String(50), nullable=False)  # promotion, handling, other
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False, index=True)
    notes = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 外键关联到用户表
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    user = relationship('User', back_populates='cost_records')
    
    # 外键关联到亚马逊店铺表
    store_id = Column(Integer, ForeignKey('amazon_stores.id'), nullable=True)
    store = relationship('AmazonStore', back_populates='cost_records')
    
    @property
    def cost_type_display(self):
        """获取显示用的成本类型名称"""
        type_map = {'promotion': '促销费', 'handling': '手续费', 'other': '其他'}
        return type_map.get(self.cost_type, self.cost_type)

# 手动补充成本表（已废弃，请使用CostRecord表）
class DataExceptionRecord(Base):
    __tablename__ = 'data_exception_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    asin = Column(String(20), nullable=False, index=True)
    sku = Column(String(100), nullable=True)
    field_name = Column(String(50), nullable=False)
    field_value = Column(Float, nullable=True)
    exception_type = Column(String(50), nullable=False, index=True)  # 异常类型
    description = Column(String(500), nullable=False)
    date = Column(Date, nullable=True, index=True)  # 关联的数据日期
    store_id = Column(Integer, ForeignKey('amazon_stores.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User")
    store = relationship("AmazonStore")

class ManualCost(Base):
    __tablename__ = 'manual_cost'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    asin = Column(String(20), nullable=False)
    cost_type = Column(String(50), nullable=False)  # 促销费/手续费/其他
    amount = Column(Float, nullable=False)
    cost_date = Column(Date, nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="manual_costs")

# 数据同步日志表 - 记录每次同步的状态
class SyncLog(Base):
    __tablename__ = 'sync_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sync_type = Column(String(50), nullable=False)  # sales, advertising, inventory, all
    store_id = Column(Integer, ForeignKey('amazon_stores.id'))
    status = Column(Integer, default=0)  # 状态: 0-失败, 1-成功, 2-部分成功
    message = Column(Text)  # 同步消息或错误信息
    
    # 时间信息
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    sync_duration = Column(Float)  # 同步持续时间(秒)
    
    # 记录统计
    record_count = Column(Integer, default=0)  # 处理的记录总数
    processed_count = Column(Integer, default=0)  # 成功处理的记录数
    updated_count = Column(Integer, default=0)  # 更新的记录数
    new_count = Column(Integer, default=0)  # 新增的记录数
    skipped_count = Column(Integer, default=0)  # 跳过的记录数
    
    # 异常统计
    exception_count = Column(Integer, default=0)  # 总异常数
    saved_exception_count = Column(Integer, default=0)  # 保存的异常记录数
    field_stats = Column(Text)  # 字段异常统计(JSON格式)
    
    # 数据范围
    data_date_start = Column(Date)  # 同步的数据开始日期
    data_date_end = Column(Date)  # 同步的数据结束日期
    
    # 系统信息
    ip_address = Column(String(50))  # 同步请求的IP地址
    sync_method = Column(String(50))  # 同步方式: manual, scheduled, api
    api_version = Column(String(20))  # API版本
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="sync_logs")
    store = relationship("AmazonStore")
    
    # 索引优化
    __table_args__ = (
        # 按用户和同步类型查询的索引
        Index('idx_user_sync_type', 'user_id', 'sync_type'),
        # 按状态和创建时间查询的索引
        Index('idx_status_created', 'status', 'created_at'),
    )
    
    def to_dict(self):
        """转换为字典格式，方便JSON序列化"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sync_type': self.sync_type,
            'store_id': self.store_id,
            'status': self.status,
            'message': self.message,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'sync_duration': self.sync_duration,
            'record_count': self.record_count,
            'processed_count': self.processed_count,
            'updated_count': self.updated_count,
            'new_count': self.new_count,
            'skipped_count': self.skipped_count,
            'exception_count': self.exception_count,
            'saved_exception_count': self.saved_exception_count,
            'field_stats': self.field_stats,
            'data_date_start': self.data_date_start.isoformat() if self.data_date_start else None,
            'data_date_end': self.data_date_end.isoformat() if self.data_date_end else None,
            'ip_address': self.ip_address,
            'sync_method': self.sync_method,
            'api_version': self.api_version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# 报表共享链接表
class ReportShare(Base):
    __tablename__ = 'report_share'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    share_token = Column(String(100), unique=True, nullable=False)
    report_type = Column(String(50), nullable=False)  # profit, sales_trend, inventory
    filter_params = Column(String(1000))  # JSON格式存储筛选参数
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="report_shares")

# 推送配置表
class PushConfig(Base):
    __tablename__ = 'push_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    push_type = Column(String(20), nullable=False)  # wechat, email
    push_url = Column(String(500))  # webhook url or email address
    template = Column(String(2000))  # 推送模板
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="push_configs")

# ERP成本文件上传记录表
class ERPCostFile(Base):
    __tablename__ = 'erp_cost_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)  # excel, csv
    status = Column(String(50), nullable=False, default='pending')  # pending, processing, completed, failed
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    upload_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    process_time = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship('User', back_populates='erp_cost_files')
    cost_data = relationship('ERPCostData', back_populates='cost_file')
    mappings = relationship('ERPCostMapping', back_populates='cost_file')

# ERP成本映射配置表
class ERPCostMapping(Base):
    __tablename__ = 'erp_cost_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cost_file_id = Column(Integer, ForeignKey('erp_cost_files.id'), nullable=False)
    source_column = Column(String(100), nullable=False)  # 源文件中的列名
    target_field = Column(String(50), nullable=False)  # 目标字段名
    field_type = Column(String(50), nullable=False, default='string')  # string, number, date
    is_required = Column(Boolean, nullable=False, default=False)
    
    # 关系
    cost_file = relationship('ERPCostFile', back_populates='mappings')

# ERP成本数据表
class ERPCostData(Base):
    __tablename__ = 'erp_cost_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    cost_file_id = Column(Integer, ForeignKey('erp_cost_files.id'), nullable=False)
    asin = Column(String(50), nullable=False, index=True)
    sku = Column(String(100), nullable=True)
    product_name = Column(String(500), nullable=True)
    cost_value = Column(Float, nullable=False, default=0.0)
    cost_date = Column(Date, nullable=False, index=True)
    currency = Column(String(10), nullable=False, default='USD')
    cost_category = Column(String(50), nullable=False, default='product')  # product, shipping, etc.
    supplier = Column(String(100), nullable=True)
    order_number = Column(String(100), nullable=True)
    source_system = Column(String(50), nullable=False, default='ERP')
    is_processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship('User', back_populates='erp_cost_data')
    cost_file = relationship('ERPCostFile', back_populates='cost_data')

# 初始化数据库连接
def init_db(db_url='sqlite:///amazon_report.db'):
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    
    # 初始化默认管理员账号（如果不存在）
    session = Session()
    admin_user = session.query(User).filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            full_name='系统管理员',
            is_admin=True
        )
        admin_user.set_password('admin123')  # 默认密码，建议首次登录后修改
        session.add(admin_user)
        session.commit()
        print("已创建默认管理员账号: username=admin, password=admin123")
    
    session.close()
    return Session()

class InventoryData(Base):
    """
    库存数据表
    """
    __tablename__ = 'inventory_data'
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(100), index=True, nullable=False)
    sku = Column(String(100), index=True)
    product_name = Column(String(500))
    store_id = Column(String(100), index=True, nullable=False)
    marketplace = Column(String(50), index=True)
    quantity = Column(Integer, default=0)
    fulfillable_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    supplier_info = Column(String(200))
    last_restock_date = Column(Date)
    unit_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 外键关系
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 关联关系
    user = relationship('User', back_populates='inventory_data')
    
    def to_dict(self):
        return {
            'id': self.id,
            'asin': self.asin,
            'sku': self.sku,
            'product_name': self.product_name,
            'store_id': self.store_id,
            'marketplace': self.marketplace,
            'quantity': self.quantity,
            'fulfillable_quantity': self.fulfillable_quantity,
            'reserved_quantity': self.reserved_quantity,
            'supplier_info': self.supplier_info,
            'last_restock_date': str(self.last_restock_date) if self.last_restock_date else None,
            'unit_cost': float(self.unit_cost) if self.unit_cost else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class InventoryAlertSetting(Base):
    """
    库存预警设置表
    """
    __tablename__ = 'inventory_alert_settings'
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(100), index=True, nullable=False)
    store_id = Column(String(100), index=True, nullable=False)
    low_stock_threshold = Column(Integer, default=7)
    high_stock_threshold = Column(Integer, default=60)
    alert_email = Column(String(255))
    alert_wechat = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'asin': self.asin,
            'store_id': self.store_id,
            'low_stock_threshold': self.low_stock_threshold,
            'high_stock_threshold': self.high_stock_threshold,
            'alert_email': self.alert_email,
            'alert_wechat': self.alert_wechat,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CustomMetric(Base):
    __tablename__ = 'custom_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 所属用户
    metric_name = Column(String(100), nullable=False)  # 指标名称
    metric_code = Column(String(100), unique=True, nullable=False)  # 指标代码(用于报表引用)
    formula = Column(Text, nullable=False)  # 计算公式(使用字段标识符)
    description = Column(String(500))  # 指标描述
    data_type = Column(String(20), default='float')  # 数据类型: float, int, percentage
    precision = Column(Integer, default=2)  # 小数点精度
    is_active = Column(Boolean, default=True)  # 是否启用
    is_system = Column(Boolean, default=False)  # 是否系统预置
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User", backref="custom_metrics")

class ShareLink(Base):
    __tablename__ = 'share_links'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(100), unique=True, nullable=False, index=True)  # 共享令牌
    report_type = Column(String(50), nullable=False)  # 报表类型: profit, trend, inventory
    report_id = Column(String(100))  # 报表ID或标识符
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 创建者ID
    access_type = Column(String(20), default='readonly')  # 访问类型: readonly, view
    created_at = Column(DateTime, default=datetime.datetime.utcnow)  # 创建时间
    expire_at = Column(DateTime, nullable=False)  # 过期时间
    last_accessed = Column(DateTime, nullable=True)  # 最后访问时间
    revoked_at = Column(DateTime, nullable=True)  # 撤销时间
    is_active = Column(Boolean, default=True)  # 是否活跃
    access_count = Column(Integer, default=0)  # 访问次数
     ...
    user = relationship("User", back_populates="share_links")
    
    def to_dict(self):
        """转换为字典格式，方便JSON序列化"""
        return {
            'id': self.id,
            'token': self.token,
            'report_type': self.report_type,
            'report_id': self.report_id,
            'user_id': self.user_id,
            'access_type': self.access_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expire_at': self.expire_at.isoformat() if self.expire_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'is_active': self.is_active,
            'access_count': self.access_count
        }

if __name__ == '__main__':
    # 示例：初始化SQLite数据库
    session = init_db()
    print("数据库表创建完成！")
