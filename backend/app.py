from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session
import os
import json
import datetime
import logging
import base64
import traceback
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from models import init_db, AmazonStore, SystemConfig, AmazonIntegratedData, SyncLog, CostRecord, User, InventoryData, InventoryAlertSetting, ERPCostFile, ERPCostData, ShareLink, CustomMetric
from share_link_manager import ShareLinkManager
from amazon_oauth import AmazonOAuth
from amazon_sales import AmazonSalesData
from amazon_advertising import AmazonAdvertisingData
from amazon_inventory import AmazonInventoryData
from cost_data_upload import CostDataUploader
from data_integration import DataIntegration
from amazon_scheduler import AmazonScheduler
from amazon_asin_profit import AmazonASINProfitReport
from amazon_sales_trend import AmazonSalesTrendReport
from amazon_inventory_health import AmazonInventoryHealthReport
from scheduler import TaskScheduler
from report_generator import ReportGenerator
from report_pusher import ReportPusher
from wechat_bot import get_wechat_bot
from email_sender import get_email_sender
from sqlalchemy import select, desc, func

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app')

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# 初始化数据库会话
db_session = init_db()

# 初始化调度器
scheduler = AmazonScheduler(db_session)

# 初始化库存健康报表
def get_inventory_health_report_instance():
    """获取库存健康报表实例"""
    return AmazonInventoryHealthReport(db_session)

def generate_report_summary():
    """
    生成报表摘要数据，用于企业微信推送
    
    Returns:
        dict: 包含报表摘要数据的字典
    """
    try:
        logger.info("开始生成报表摘要数据")
        
        # 初始化报表实例
        asin_profit_report = AmazonASINProfitReport(db_session)
        sales_trend_report = AmazonSalesTrendReport(db_session)
        inventory_health_report = get_inventory_health_report_instance()
        
        # 获取总销售额和总订单数
        sales_stats = get_sales_statistics_data()
        
        # 获取库存数据
        inventory_data = inventory_health_report.get_inventory_summary()
        
        # 获取最佳表现ASIN
        top_asin_data = get_top_performing_asin()
        
        # 生成报表URL（使用共享链接功能）
        share_link_manager = ShareLinkManager(db_session)
        share_link = share_link_manager.generate_share_link(
            report_type='dashboard',
            expire_days=1,
            access_level='view'
        )
        
        report_url = f"http://{request.host if request else 'localhost:5000'}/shared/{share_link['token']}"
        
        # 组装摘要数据
        summary_data = {
            'total_sales': sales_stats.get('total_sales', 0),
            'total_orders': sales_stats.get('total_orders', 0),
            'total_profit': sales_stats.get('total_profit', 0),
            'avg_profit_rate': sales_stats.get('avg_profit_rate', 0),
            'top_asin': top_asin_data,
            'low_stock_count': inventory_data.get('low_stock_count', 0),
            'stock_danger_count': inventory_data.get('stock_danger_count', 0),
            'report_url': report_url
        }
        
        logger.info("报表摘要数据生成成功")
        return summary_data
    except Exception as e:
        logger.error(f"生成报表摘要数据失败: {str(e)}")
        return {
            'total_sales': 0,
            'total_orders': 0,
            'total_profit': 0,
            'avg_profit_rate': 0,
            'top_asin': {'asin': 'N/A', 'product_name': 'N/A', 'sales': 0, 'profit': 0},
            'low_stock_count': 0,
            'stock_danger_count': 0,
            'report_url': '#'
        }

def get_sales_statistics_data():
    """
    获取销售统计数据
    
    Returns:
        dict: 销售统计数据
    """
    try:
        # 这里可以直接调用现有的销售统计API
        # 由于我们在定时任务中，不能直接使用Flask的request上下文
        # 所以直接查询数据库获取统计信息
        
        # 获取最近30天的销售数据
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        
        # 查询销售数据
        sales_data = db_session.query(
            func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
            func.sum(AmazonIntegratedData.order_quantity).label('total_orders'),
            func.sum(AmazonIntegratedData.profit).label('total_profit')
        ).filter(
            AmazonIntegratedData.report_date >= thirty_days_ago
        ).first()
        
        if sales_data:
            total_sales = float(sales_data.total_sales or 0)
            total_profit = float(sales_data.total_profit or 0)
            avg_profit_rate = (total_profit / total_sales * 100) if total_sales > 0 else 0
            
            return {
                'total_sales': total_sales,
                'total_orders': int(sales_data.total_orders or 0),
                'total_profit': total_profit,
                'avg_profit_rate': round(avg_profit_rate, 2)
            }
        
        return {
            'total_sales': 0,
            'total_orders': 0,
            'total_profit': 0,
            'avg_profit_rate': 0
        }
    except Exception as e:
        logger.error(f"获取销售统计数据失败: {str(e)}")
        return {
            'total_sales': 0,
            'total_orders': 0,
            'total_profit': 0,
            'avg_profit_rate': 0
        }

def get_top_performing_asin():
    """
    获取表现最佳的ASIN
    
    Returns:
        dict: 最佳ASIN数据
    """
    try:
        # 获取最近30天销售额最高的ASIN
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        
        top_asin = db_session.query(
            AmazonIntegratedData.asin,
            AmazonIntegratedData.product_name,
            func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
            func.sum(AmazonIntegratedData.profit).label('total_profit')
        ).filter(
            AmazonIntegratedData.report_date >= thirty_days_ago
        ).group_by(
            AmazonIntegratedData.asin, AmazonIntegratedData.product_name
        ).order_by(
            desc('total_sales')
        ).first()
        
        if top_asin:
            return {
                'asin': top_asin.asin or 'N/A',
                'product_name': top_asin.product_name or 'N/A',
                'sales': float(top_asin.total_sales or 0),
                'profit': float(top_asin.total_profit or 0)
            }
        
        return {
            'asin': 'N/A',
            'product_name': 'N/A',
            'sales': 0,
            'profit': 0
        }
    except Exception as e:
        logger.error(f"获取最佳ASIN数据失败: {str(e)}")
        return {
            'asin': 'N/A',
            'product_name': 'N/A',
            'sales': 0,
            'profit': 0
        }

def send_wechat_report_notification():
    """
    发送企业微信报表通知
    从系统配置中获取企业微信机器人Webhook URL，生成报表摘要并推送
    """
    try:
        logger.info("开始发送企业微信报表通知")
        
        # 从系统配置中获取企业微信机器人Webhook URL
        wechat_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'wechat_webhook_url'
        ).first()
        
        # 检查是否启用企业微信推送
        enable_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'enable_wechat_push'
        ).first()
        
        if enable_config and enable_config.config_value.lower() != 'true':
            logger.info("企业微信推送功能未启用，跳过推送")
            return False
        
        if not wechat_config or not wechat_config.config_value:
            logger.warning("未配置企业微信机器人Webhook URL，跳过推送")
            return False
        
        webhook_url = wechat_config.config_value
        
        # 获取企业微信机器人实例
        wechat_bot = get_wechat_bot(webhook_url)
        
        # 生成报表摘要数据
        report_summary = generate_report_summary()
        
        # 发送报表摘要到企业微信
        success = wechat_bot.send_report_summary(report_summary)
        
        if success:
            logger.info("企业微信报表通知发送成功")
        else:
            logger.error("企业微信报表通知发送失败")
        
        return success
    except Exception as e:
        logger.error(f"发送企业微信报表通知时出错: {str(e)}")
        return False


def send_email_report_notification():
    """
    发送邮件报表通知
    从系统配置中获取邮件服务器信息，生成报表并发送邮件
    """
    try:
        logger.info("开始发送邮件报表通知")
        
        # 检查是否启用邮件推送
        enable_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'enable_email_push'
        ).first()
        
        if enable_config and enable_config.config_value.lower() != 'true':
            logger.info("邮件推送功能未启用，跳过发送")
            return False
        
        # 获取邮件服务器配置
        smtp_server_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_smtp_server'
        ).first()
        
        smtp_port_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_smtp_port'
        ).first()
        
        email_username_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_username'
        ).first()
        
        email_password_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_password'
        ).first()
        
        email_recipients_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_recipients'
        ).first()
        
        email_sender_name_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_sender_name'
        ).first()
        
        # 检查必要配置是否存在
        if not all([smtp_server_config, smtp_port_config, email_username_config, email_password_config, email_recipients_config]):
            logger.warning("邮件发送配置不完整，跳过发送")
            return False
        
        # 解析配置
        smtp_server = smtp_server_config.config_value
        smtp_port = int(smtp_port_config.config_value)
        username = email_username_config.config_value
        password = email_password_config.config_value
        recipients = [email.strip() for email in email_recipients_config.config_value.split(',')]
        sender_name = email_sender_name_config.config_value if email_sender_name_config else "亚马逊报表系统"
        sender_email = username  # 默认使用用户名作为发件人邮箱
        
        # 生成报表摘要
        summary = generate_report_summary()
        if not summary:
            logger.error("生成报表摘要失败，跳过邮件发送")
            return False
        
        # 构建报表摘要文本
        summary_text = f"""销售概览：
- 总销售额: {summary['sales_overview']['total_sales']:.2f}元
- 订单总数: {summary['sales_overview']['total_orders']}个
- 平均订单价值: {summary['sales_overview']['avg_order_value']:.2f}元
- 总利润: {summary['sales_overview']['total_profit']:.2f}元
- 利润率: {summary['sales_overview']['profit_rate']:.2f}%

销售TOP3 ASIN：
"""
        for i, asin_info in enumerate(summary['top_asins'][:3], 1):
            summary_text += f"{i}. [{asin_info['asin']}] {asin_info['title']}\n  销售额: {asin_info['sales_amount']:.2f}元, 销量: {asin_info['quantity']}件\n"
        
        summary_text += f"""

库存状态：
- 总SKU数: {summary['inventory_status']['total_skus']}个
- 总库存数量: {summary['inventory_status']['total_quantity']}件
- 库存价值: {summary['inventory_status']['total_value']:.2f}元
- 警戒库存SKU数: {summary['inventory_status']['low_stock_skus']}个
"""
        
        # 准备报表数据用于生成Excel附件
        import pandas as pd
        
        # 销售概览数据
        sales_overview_data = pd.DataFrame([{
            '指标名称': '总销售额',
            '数值': summary['sales_overview']['total_sales'],
            '单位': '元'
        }, {
            '指标名称': '订单总数',
            '数值': summary['sales_overview']['total_orders'],
            '单位': '个'
        }, {
            '指标名称': '平均订单价值',
            '数值': summary['sales_overview']['avg_order_value'],
            '单位': '元'
        }, {
            '指标名称': '总利润',
            '数值': summary['sales_overview']['total_profit'],
            '单位': '元'
        }, {
            '指标名称': '利润率',
            '数值': summary['sales_overview']['profit_rate'],
            '单位': '%'
        }])
        
        # TOP ASIN数据
        top_asin_data = pd.DataFrame(summary['top_asins'])
        
        # 库存状态数据
        inventory_data = pd.DataFrame([{
            '指标名称': '总SKU数',
            '数值': summary['inventory_status']['total_skus'],
            '单位': '个'
        }, {
            '指标名称': '总库存数量',
            '数值': summary['inventory_status']['total_quantity'],
            '单位': '件'
        }, {
            '指标名称': '库存价值',
            '数值': summary['inventory_status']['total_value'],
            '单位': '元'
        }, {
            '指标名称': '警戒库存SKU数',
            '数值': summary['inventory_status']['low_stock_skus'],
            '单位': '个'
        }])
        
        report_data = {
            '销售概览': sales_overview_data,
            'Top_ASIN': top_asin_data,
            '库存状态': inventory_data
        }
        
        # 获取邮件发送器实例
        email_sender = get_email_sender()
        
        # 连接SMTP服务器
        connected = email_sender.connect(smtp_server, smtp_port, username, password)
        if not connected:
            return False
        
        try:
            # 发送邮件
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            subject = f"亚马逊日报表 - {today}"
            
            success = email_sender.send_report_email(
                sender_name=sender_name,
                sender_email=sender_email,
                recipients=recipients,
                subject=subject,
                report_data=report_data,
                report_summary=summary_text,
                attach_excel=True,
                report_type="日报表"
            )
            
            if success:
                logger.info(f"邮件报表通知发送成功，收件人：{', '.join(recipients)}")
            else:
                logger.error("邮件报表通知发送失败")
            
            return success
        finally:
            # 断开连接
            email_sender.disconnect()
            
    except Exception as e:
        logger.error(f"发送邮件报表通知时发生错误: {str(e)}")
        return False

# 确保上传目录存在
UPLOAD_FOLDER = os.path.join('..', 'data', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保报表目录可访问
REPORT_FOLDER = os.path.join('..', 'data', 'reports')
os.makedirs(REPORT_FOLDER, exist_ok=True)

# 用户认证装饰器
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'authenticated' not in session or 'user_id' not in session:
            return jsonify({'status': 'error', 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated

# 获取当前登录用户的辅助函数
def get_current_user():
    if 'user_id' not in session:
        return None
    return db_session.query(User).filter_by(id=session['user_id']).first()

# 检查用户是否为管理员
def is_admin():
    user = get_current_user()
    return user and user.is_admin

# 认证路由
@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400
        
        # 从数据库验证用户
        user = db_session.query(User).filter_by(username=username).first()
        
        if user and user.password == password:  # 注意：实际应用中应该使用密码哈希验证
            session['authenticated'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return jsonify({
                'status': 'success', 
                'message': '登录成功',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'is_admin': user.is_admin
                }
            })
        else:
            return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 401
    
    except Exception as e:
        logger.error(f'登录出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '登录失败'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.pop('authenticated', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return jsonify({'status': 'success', 'message': '登出成功'})

# 用户管理
@app.route('/api/users', methods=['POST'])
@require_auth
def create_user():
    """创建新用户，仅管理员可用"""
    try:
        current_user = get_current_user()
        
        # 检查是否为管理员
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有管理员可以创建用户'}), 403
        
        # 获取请求数据
        data = request.json
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        is_admin = data.get('is_admin', False)
        
        # 验证输入
        if not username or not password:
            return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400
        
        # 密码强度验证
        if len(password) < 6:
            return jsonify({'status': 'error', 'message': '密码长度至少为6位'}), 400
        
        # 检查用户名是否已存在
        existing_user = db_session.query(User).filter_by(username=username).first()
        if existing_user:
            return jsonify({'status': 'error', 'message': '用户名已存在'}), 400
        
        # 检查邮箱是否已存在
        if email:
            existing_email = db_session.query(User).filter_by(email=email).first()
            if existing_email:
                return jsonify({'status': 'error', 'message': '邮箱已存在'}), 400
        
        # 创建新用户
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            is_admin=is_admin,
            created_at=datetime.datetime.utcnow()
        )
        
        db_session.add(new_user)
        db_session.commit()
        
        logger.info(f'管理员 {current_user.username} 创建了新用户 {username}')
        
        return jsonify({
            'status': 'success',
            'message': '用户创建成功',
            'data': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'is_admin': new_user.is_admin,
                'created_at': new_user.created_at.isoformat()
            }
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f'创建用户失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '创建用户失败'}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    """更新用户信息，仅管理员可用"""
    try:
        current_user = get_current_user()
        
        # 检查是否为管理员
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有管理员可以更新用户信息'}), 403
        
        # 获取要更新的用户
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 不允许删除管理员权限（如果只有一个管理员）
        if user.is_admin and not user_id == current_user.id:
            admin_count = db_session.query(User).filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '系统至少需要保留一个管理员'}), 400
        
        # 获取请求数据
        data = request.json
        
        # 更新用户信息
        if 'username' in data and data['username'] != user.username:
            # 检查新用户名是否已存在
            existing_user = db_session.query(User).filter_by(username=data['username']).first()
            if existing_user:
                return jsonify({'status': 'error', 'message': '用户名已存在'}), 400
            user.username = data['username']
        
        if 'password' in data and data['password']:
            # 密码强度验证
            if len(data['password']) < 6:
                return jsonify({'status': 'error', 'message': '密码长度至少为6位'}), 400
            user.password_hash = generate_password_hash(data['password'])
        
        if 'email' in data and data['email'] != user.email:
            # 检查新邮箱是否已存在
            if data['email']:
                existing_email = db_session.query(User).filter_by(email=data['email']).first()
                if existing_email:
                    return jsonify({'status': 'error', 'message': '邮箱已存在'}), 400
            user.email = data['email']
        
        if 'is_admin' in data:
            # 不允许将自己的管理员权限移除
            if user_id == current_user.id and not data['is_admin']:
                return jsonify({'status': 'error', 'message': '不能移除自己的管理员权限'}), 400
            user.is_admin = data['is_admin']
        
        db_session.commit()
        
        logger.info(f'管理员 {current_user.username} 更新了用户 {user.username} 的信息')
        
        return jsonify({
            'status': 'success',
            'message': '用户信息更新成功',
            'data': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f'更新用户信息失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '更新用户信息失败'}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_auth
def delete_user(user_id):
    """删除用户，仅管理员可用"""
    try:
        current_user = get_current_user()
        
        # 检查是否为管理员
        if not current_user.is_admin:
            return jsonify({'status': 'error', 'message': '只有管理员可以删除用户'}), 403
        
        # 不允许删除自己
        if user_id == current_user.id:
            return jsonify({'status': 'error', 'message': '不能删除自己的账户'}), 400
        
        # 获取要删除的用户
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 不允许删除管理员（如果只有一个管理员）
        if user.is_admin:
            admin_count = db_session.query(User).filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '系统至少需要保留一个管理员'}), 400
        
        # 检查是否有关联数据
        store_count = db_session.query(AmazonStore).filter_by(user_id=user_id).count()
        if store_count > 0:
            return jsonify({'status': 'error', 'message': '该用户关联了店铺，请先移除店铺关联'}), 400
        
        # 检查是否有其他关联数据
        data_count = db_session.query(AmazonIntegratedData).filter_by(user_id=user_id).count()
        if data_count > 0:
            return jsonify({'status': 'error', 'message': '该用户有关联的业务数据，请先清理相关数据'}), 400
        
        sync_log_count = db_session.query(SyncLog).filter_by(user_id=user_id).count()
        if sync_log_count > 0:
            # 可以选择删除关联的同步日志，或者阻止删除
            # 这里选择阻止删除
            return jsonify({'status': 'error', 'message': '该用户有关联的同步日志记录，无法删除'}), 400
        
        # 删除用户
        db_session.delete(user)
        db_session.commit()
        
        logger.info(f'管理员 {current_user.username} 删除了用户 {user.username}')
        
        return jsonify({
            'status': 'success',
            'message': '用户删除成功'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f'删除用户失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '删除用户失败'}), 500

# 亚马逊店铺管理
@app.route('/api/stores', methods=['GET'])
@require_auth
def get_stores():
    """获取店铺列表"""
    try:
        user_id = session['user_id']
        user = get_current_user()
        
        # 使用OAuth模块获取店铺列表
        oauth = AmazonOAuth(db_session, user_id=user_id, is_admin=user.is_admin)
        stores = oauth.get_active_stores()
        
        # 构建响应数据，脱敏显示敏感信息
        result = []
        for store in stores:
            # 脱敏显示client_id和refresh_token
            masked_client_id = store.client_id[:4] + '...' + store.client_id[-4:] if store.client_id else None
            masked_refresh_token = store.refresh_token[:6] + '...' if store.refresh_token else None
            
            result.append({
                'id': store.id,
                'store_name': store.store_name,
                'region': store.region,
                'marketplace_id': store.marketplace_id,
                'merchant_id': store.merchant_id,
                'client_id': masked_client_id,
                'refresh_token': masked_refresh_token,
                'is_active': store.is_active,
                'created_at': store.created_at.isoformat() if store.created_at else None,
                'user_id': store.user_id
            })
        
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f'获取店铺列表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取店铺列表失败'}), 500

@app.route('/api/stores/<int:store_id>', methods=['GET'])
@require_auth
def get_store(store_id):
    """获取单个店铺信息"""
    try:
        user_id = session['user_id']
        user = get_current_user()
        
        # 使用OAuth模块获取店铺信息
        oauth = AmazonOAuth(db_session, user_id=user_id, is_admin=user.is_admin)
        store = oauth.get_store_by_user_and_id(store_id)
        
        if not store:
            return jsonify({'status': 'error', 'message': '店铺不存在或无权访问'}), 404
        
        # 脱敏显示敏感信息
        masked_client_id = store.client_id[:4] + '...' + store.client_id[-4:] if store.client_id else None
        masked_refresh_token = store.refresh_token[:6] + '...' if store.refresh_token else None
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': store.id,
                'store_name': store.store_name,
                'region': store.region,
                'marketplace_id': store.marketplace_id,
                'merchant_id': store.merchant_id,
                'client_id': masked_client_id,
                'refresh_token': masked_refresh_token,
                'is_active': store.is_active,
                'created_at': store.created_at.isoformat() if store.created_at else None,
                'user_id': store.user_id
            }
        })
    except Exception as e:
        logger.error(f'获取店铺信息失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取店铺信息失败'}), 500

@app.route('/api/stores', methods=['POST'])
@require_auth
def create_store():
    """创建新店铺"""
    try:
        user_id = session['user_id']
        user = get_current_user()
        data = request.json or {}
        
        # 验证必要字段
        required_fields = ['store_name', 'region', 'marketplace_id', 'merchant_id', 'client_id', 'refresh_token']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'status': 'error', 'message': f'{field} 是必填字段'}), 400
        
        # 使用OAuth模块添加店铺
        oauth = AmazonOAuth(db_session, user_id=user_id, is_admin=user.is_admin)
        result = oauth.add_store(
            store_name=data['store_name'],
            region=data['region'],
            marketplace_id=data['marketplace_id'],
            merchant_id=data['merchant_id'],
            client_id=data['client_id'],
            refresh_token=data['refresh_token']
        )
        
        if result['status'] == 'error':
            return jsonify(result), 400
        
        store = result['store']
        return jsonify({
            'status': 'success',
            'message': '店铺创建成功',
            'data': {
                'id': store.id,
                'store_name': store.store_name,
                'region': store.region,
                'marketplace_id': store.marketplace_id,
                'merchant_id': store.merchant_id,
                'is_active': store.is_active
            }
        }), 201
    except Exception as e:
        db_session.rollback()
        logger.error(f'创建店铺失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '创建店铺失败'}), 500

@app.route('/api/stores/<int:store_id>', methods=['PUT'])
@require_auth
def update_store(store_id):
    """更新店铺信息"""
    try:
        user_id = session['user_id']
        user = get_current_user()
        data = request.json or {}
        
        # 使用OAuth模块更新店铺
        oauth = AmazonOAuth(db_session, user_id=user_id, is_admin=user.is_admin)
        result = oauth.update_store(
            store_id=store_id,
            store_name=data.get('store_name'),
            client_id=data.get('client_id'),
            refresh_token=data.get('refresh_token'),
            is_active=data.get('is_active')
        )
        
        if result['status'] == 'error':
            return jsonify(result), 404
        
        store = result['store']
        # 脱敏显示敏感信息
        masked_client_id = store.client_id[:4] + '...' + store.client_id[-4:] if store.client_id else None
        masked_refresh_token = store.refresh_token[:6] + '...' if store.refresh_token else None
        
        return jsonify({
            'status': 'success',
            'message': '店铺更新成功',
            'data': {
                'id': store.id,
                'store_name': store.store_name,
                'region': store.region,
                'marketplace_id': store.marketplace_id,
                'merchant_id': store.merchant_id,
                'client_id': masked_client_id,
                'refresh_token': masked_refresh_token,
                'is_active': store.is_active,
                'user_id': store.user_id
            }
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f'更新店铺失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '更新店铺失败'}), 500

@app.route('/api/stores/<int:store_id>/activate', methods=['POST'])
@require_auth
def activate_store(store_id):
    """激活店铺"""
    try:
        user_id = session['user_id']
        user = get_current_user()
        
        # 使用OAuth模块激活店铺
        oauth = AmazonOAuth(db_session, user_id=user_id, is_admin=user.is_admin)
        result = oauth.activate_store(store_id)
        
        if result['status'] == 'error':
            return jsonify(result), 404
        
        return jsonify({
            'status': 'success',
            'message': '店铺激活成功',
            'data': {
                'id': result['store'].id,
                'store_name': result['store'].store_name,
                'is_active': True
            }
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f'激活店铺失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '激活店铺失败'}), 500

@app.route('/api/stores/<int:store_id>/deactivate', methods=['POST'])
@require_auth
def deactivate_store(store_id):
    """停用店铺"""
    try:
        user_id = session['user_id']
        user = get_current_user()
        
        # 使用OAuth模块停用店铺
        oauth = AmazonOAuth(db_session, user_id=user_id, is_admin=user.is_admin)
        result = oauth.deactivate_store(store_id)
        
        if result['status'] == 'error':
            return jsonify(result), 404
        
        return jsonify({
            'status': 'success',
            'message': '店铺停用成功',
            'data': {
                'id': result['store'].id,
                'store_name': result['store'].store_name,
                'is_active': False
            }
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f'停用店铺失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '停用店铺失败'}), 500

# 系统配置管理
@app.route('/api/configs', methods=['GET'])
@require_auth
def get_configs():
    """获取配置项（系统配置和用户配置）"""
    try:
        user_id = session['user_id']
        
        # 获取系统配置（user_id为空）和用户配置
        configs = db_session.query(SystemConfig).filter(
            (SystemConfig.user_id == None) | (SystemConfig.user_id == user_id)
        ).all()
        
        result = {}
        for config in configs:
            result[config.config_key] = config.config_value
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f'获取配置出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取配置失败'}), 500

@app.route('/api/configs/<config_key>', methods=['PUT'])
@require_auth
def update_config(config_key):
    """更新配置项"""
    try:
        data = request.json
        config_value = data.get('value')
        user_id = session['user_id']
        
        if config_value is None:
            return jsonify({'status': 'error', 'message': '缺少配置值'}), 400
        
        # 查找用户配置，如果不存在则创建
        config = db_session.query(SystemConfig).filter_by(
            config_key=config_key,
            user_id=user_id
        ).first()
        
        if config:
            config.config_value = config_value
            config.updated_at = datetime.datetime.utcnow()
        else:
            new_config = SystemConfig(
                config_key=config_key,
                config_value=config_value,
                user_id=user_id,
                description=data.get('description', '')
            )
            db_session.add(new_config)
        
        db_session.commit()
        
        # 如果是微信相关配置，更新定时推送设置
        if config_key.startswith('wechat_'):
            update_wechat_push_settings(user_id)
        
        return jsonify({'status': 'success', 'message': '配置更新成功'})
    except Exception as e:
        db_session.rollback()
        logger.error(f'更新配置出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '配置更新失败'}), 500

@app.route('/api/wechat/config', methods=['GET'])
@require_auth
def get_wechat_config():
    """获取企业微信配置"""
    try:
        user_id = session['user_id']
        
        # 获取所有微信相关配置
        configs = db_session.query(SystemConfig).filter(
            SystemConfig.config_key.in_([
                'wechat_webhook_url',
                'enable_wechat_push',
                'wechat_push_hour',
                'wechat_push_minute'
            ]),
            SystemConfig.user_id == user_id
        ).all()
        
        # 转换为字典格式
        config_dict = {}
        for config in configs:
            config_dict[config.config_key] = config.config_value
        
        # 设置默认值
        if 'wechat_push_hour' not in config_dict:
            config_dict['wechat_push_hour'] = '8'
        if 'wechat_push_minute' not in config_dict:
            config_dict['wechat_push_minute'] = '0'
        if 'enable_wechat_push' not in config_dict:
            config_dict['enable_wechat_push'] = 'false'
        
        return jsonify({
            'status': 'success',
            'config': config_dict
        })
    except Exception as e:
        logger.error(f'获取微信配置失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': '获取配置失败'
        }), 500

@app.route('/api/wechat/config', methods=['POST'])
@require_auth
def save_wechat_config():
    """保存企业微信配置"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        # 保存各个配置项
        config_keys = [
            'wechat_webhook_url',
            'enable_wechat_push',
            'wechat_push_hour',
            'wechat_push_minute'
        ]
        
        for key in config_keys:
            if key in data:
                # 查找或创建配置
                config = db_session.query(SystemConfig).filter_by(
                    config_key=key,
                    user_id=user_id
                ).first()
                
                if not config:
                    config = SystemConfig(
                        config_key=key,
                        user_id=user_id,
                        config_value=str(data[key])
                    )
                    db_session.add(config)
                else:
                    config.config_value = str(data[key])
        
        db_session.commit()
        
        # 更新定时任务
        update_wechat_push_settings(user_id)
        
        return jsonify({
            'status': 'success',
            'message': '配置保存成功'
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f'保存微信配置失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': '保存配置失败'
        }), 500

@app.route('/api/wechat/test-push', methods=['POST'])
@require_auth
def test_wechat_push():
    """测试企业微信机器人推送"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        # 优先使用请求中的Webhook URL，其次从数据库获取
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            # 从数据库获取Webhook URL
            webhook_config = db_session.query(SystemConfig).filter_by(
                config_key='wechat_webhook_url',
                user_id=user_id
            ).first()
            
            if not webhook_config or not webhook_config.config_value:
                return jsonify({'status': 'error', 'message': '请先配置企业微信Webhook URL'}), 400
            
            webhook_url = webhook_config.config_value
        
        # 验证Webhook URL格式
        if not webhook_url.startswith('https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key='):
            return jsonify({'status': 'error', 'message': 'Webhook URL格式不正确'}), 400
        
        # 生成测试消息
        test_content = f"""# 测试消息 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 消息类型
企业微信机器人测试推送

## 测试信息
- **推送时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **用户ID**: {user_id}
- **功能**: 报表自动推送测试

## 配置说明
- 此为测试消息，验证推送功能正常
- 配置每日报表推送后，将在设定时间收到类似格式的报表信息

*如有问题请检查Webhook URL或联系系统管理员*"""
        
        # 调用微信机器人推送
        wechat_bot = get_wechat_bot(webhook_url)
        success = wechat_bot.send_markdown(test_content)
        
        if success:
            return jsonify({'status': 'success', 'message': '测试消息发送成功，请检查企业微信'})
        else:
            return jsonify({'status': 'error', 'message': '测试消息发送失败，请检查Webhook URL是否正确'}), 500
    except Exception as e:
        logger.error(f'测试微信推送失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'测试推送失败: {str(e)}'}), 500

def update_wechat_push_settings(user_id):
    """更新微信推送设置"""
    try:
        # 获取微信配置
        webhook_config = db_session.query(SystemConfig).filter_by(
            config_key='wechat_webhook_url',
            user_id=user_id
        ).first()
        
        enable_config = db_session.query(SystemConfig).filter_by(
            config_key='enable_wechat_push',
            user_id=user_id
        ).first()
        
        hour_config = db_session.query(SystemConfig).filter_by(
            config_key='wechat_push_hour',
            user_id=user_id
        ).first()
        
        minute_config = db_session.query(SystemConfig).filter_by(
            config_key='wechat_push_minute',
            user_id=user_id
        ).first()
        
        # 默认配置 - 确保每日8点推送
        hour = 8
        minute = 0
        enable_push = False
        webhook_url = None
        
        # 获取配置值
        if hour_config:
            try:
                hour = int(hour_config.config_value)
            except (ValueError, TypeError):
                logger.warning(f'用户{user_id}的微信推送小时配置无效，使用默认值8')
        
        if minute_config:
            try:
                minute = int(minute_config.config_value)
            except (ValueError, TypeError):
                logger.warning(f'用户{user_id}的微信推送分钟配置无效，使用默认值0')
        
        if enable_config:
            enable_push = enable_config.config_value.lower() == 'true'
        
        if webhook_config:
            webhook_url = webhook_config.config_value
        
        # 日志记录配置信息
        logger.info(f'更新用户{user_id}的微信推送设置 - 启用:{enable_push}, 时间:{hour:02d}:{minute:02d}, 配置URL:{'是' if webhook_url else '否'}')
        
        # 检查是否启用推送
        if enable_push and webhook_url:
            # 验证Webhook URL格式
            if not webhook_url.startswith('https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key='):
                logger.error(f'用户{user_id}的企业微信Webhook URL格式不正确')
                return
            
            # 更新调度器中的定时任务
            success = scheduler.update_wechat_push_schedule(
                user_id=user_id,
                hour=hour,
                minute=minute,
                webhook_url=webhook_url
            )
            
            if success:
                logger.info(f'用户{user_id}已成功设置每日{hour:02d}:{minute:02d}自动推送企业微信日报')
            else:
                logger.error(f'用户{user_id}的微信推送定时任务设置失败')
        else:
            # 取消定时推送
            success = scheduler.cancel_wechat_push(user_id=user_id)
            if success:
                logger.info(f'用户{user_id}企业微信推送已禁用')
            else:
                logger.warning(f'用户{user_id}的微信推送取消失败，可能是任务不存在')
    except Exception as e:
        logger.error(f'更新微信推送设置失败: {str(e)}')
        traceback.print_exc()

# 自定义指标API
@app.route('/api/custom-metrics', methods=['GET'])
@require_auth
def get_custom_metrics():
    """获取用户的自定义指标列表"""
    try:
        user_id = session['user_id']
        
        # 获取用户的自定义指标和系统预置指标
        metrics = db_session.query(CustomMetric).filter(
            (CustomMetric.user_id == user_id) | (CustomMetric.is_system == True)
        ).all()
        
        result = []
        for metric in metrics:
            result.append({
                'id': metric.id,
                'metric_name': metric.metric_name,
                'metric_code': metric.metric_code,
                'formula': metric.formula,
                'description': metric.description,
                'data_type': metric.data_type,
                'precision': metric.precision,
                'is_active': metric.is_active,
                'is_system': metric.is_system,
                'created_at': metric.created_at.isoformat() if metric.created_at else None,
                'updated_at': metric.updated_at.isoformat() if metric.updated_at else None
            })
        
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f'获取自定义指标失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取自定义指标失败'}), 500

@app.route('/api/custom-metrics', methods=['POST'])
@require_auth
def create_custom_metric():
    """创建新的自定义指标"""
    try:
        data = request.json
        user_id = session['user_id']
        
        # 验证必填字段
        required_fields = ['metric_name', 'metric_code', 'formula']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'缺少必填字段: {field}'}), 400
        
        # 检查指标代码是否已存在
        existing = db_session.query(CustomMetric).filter_by(metric_code=data['metric_code']).first()
        if existing:
            return jsonify({'status': 'error', 'message': '指标代码已存在'}), 400
        
        # 创建新指标
        new_metric = CustomMetric(
            user_id=user_id,
            metric_name=data['metric_name'],
            metric_code=data['metric_code'],
            formula=data['formula'],
            description=data.get('description', ''),
            data_type=data.get('data_type', 'float'),
            precision=data.get('precision', 2),
            is_active=data.get('is_active', True),
            is_system=False
        )
        
        db_session.add(new_metric)
        db_session.commit()
        
        return jsonify({'status': 'success', 'message': '自定义指标创建成功', 'data': {
            'id': new_metric.id,
            'metric_name': new_metric.metric_name,
            'metric_code': new_metric.metric_code
        }})
    except Exception as e:
        db_session.rollback()
        logger.error(f'创建自定义指标失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '创建自定义指标失败'}), 500

@app.route('/api/custom-metrics/<int:metric_id>', methods=['GET'])
@require_auth
def get_custom_metric(metric_id):
    """获取单个自定义指标"""
    try:
        user_id = session['user_id']
        
        metric = db_session.query(CustomMetric).filter(
            CustomMetric.id == metric_id,
            (CustomMetric.user_id == user_id) | (CustomMetric.is_system == True)
        ).first()
        
        if not metric:
            return jsonify({'status': 'error', 'message': '自定义指标不存在'}), 404
        
        result = {
            'id': metric.id,
            'metric_name': metric.metric_name,
            'metric_code': metric.metric_code,
            'formula': metric.formula,
            'description': metric.description,
            'data_type': metric.data_type,
            'precision': metric.precision,
            'is_active': metric.is_active,
            'is_system': metric.is_system,
            'created_at': metric.created_at.isoformat() if metric.created_at else None,
            'updated_at': metric.updated_at.isoformat() if metric.updated_at else None
        }
        
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f'获取自定义指标详情失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取自定义指标详情失败'}), 500

@app.route('/api/custom-metrics/<int:metric_id>', methods=['PUT'])
@require_auth
def update_custom_metric(metric_id):
    """更新自定义指标"""
    try:
        data = request.json
        user_id = session['user_id']
        
        # 查找指标并验证权限
        metric = db_session.query(CustomMetric).filter_by(
            id=metric_id,
            user_id=user_id
        ).first()
        
        if not metric:
            return jsonify({'status': 'error', 'message': '自定义指标不存在或无权限修改'}), 404
        
        # 不允许修改系统预置指标
        if metric.is_system:
            return jsonify({'status': 'error', 'message': '系统预置指标不允许修改'}), 403
        
        # 更新字段
        if 'metric_name' in data:
            metric.metric_name = data['metric_name']
        if 'formula' in data:
            metric.formula = data['formula']
        if 'description' in data:
            metric.description = data['description']
        if 'data_type' in data:
            metric.data_type = data['data_type']
        if 'precision' in data:
            metric.precision = data['precision']
        if 'is_active' in data:
            metric.is_active = data['is_active']
        
        metric.updated_at = datetime.datetime.utcnow()
        db_session.commit()
        
        return jsonify({'status': 'success', 'message': '自定义指标更新成功'})
    except Exception as e:
        db_session.rollback()
        logger.error(f'更新自定义指标失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '更新自定义指标失败'}), 500

@app.route('/api/custom-metrics/<int:metric_id>', methods=['DELETE'])
@require_auth
def delete_custom_metric(metric_id):
    """删除自定义指标"""
    try:
        user_id = session['user_id']
        
        # 查找指标并验证权限
        metric = db_session.query(CustomMetric).filter_by(
            id=metric_id,
            user_id=user_id
        ).first()
        
        if not metric:
            return jsonify({'status': 'error', 'message': '自定义指标不存在或无权限删除'}), 404
        
        # 不允许删除系统预置指标
        if metric.is_system:
            return jsonify({'status': 'error', 'message': '系统预置指标不允许删除'}), 403
        
        db_session.delete(metric)
        db_session.commit()
        
        return jsonify({'status': 'success', 'message': '自定义指标删除成功'})
    except Exception as e:
        db_session.rollback()
        logger.error(f'删除自定义指标失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '删除自定义指标失败'}), 500

# 数据同步API
@app.route('/api/sync/now', methods=['POST'])
@require_auth
def sync_now():
    """手动触发数据同步"""
    try:
        data = request.json or {}
        store_id = data.get('store_id')
        sync_date = data.get('date')
        user_id = session['user_id']
        user = get_current_user()
        
        # 如果指定了店铺ID，检查权限
        if store_id:
            store = db_session.query(AmazonStore).filter_by(id=store_id).first()
            if not store or not store.is_active:
                return jsonify({'status': 'error', 'message': '店铺不存在或未激活'}), 404
            
            # 检查权限：只有管理员或店铺所有者可以同步
            if not user.is_admin and store.user_id != user_id:
                return jsonify({'status': 'error', 'message': '无权同步此店铺数据'}), 403
        
        # 验证日期格式
        if sync_date:
            try:
                target_date = datetime.datetime.strptime(sync_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'status': 'error', 'message': '日期格式错误，应为YYYY-MM-DD'}), 400
        else:
            # 默认同步昨天的数据
            target_date = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
        
        # 记录同步开始，添加用户ID关联
        sync_log = SyncLog(
            sync_type='manual',
            store_id=store_id,
            target_date=target_date,
            status='running',
            start_time=datetime.datetime.utcnow(),
            user_id=user_id
        )
        db_session.add(sync_log)
        db_session.commit()
        
        # 执行数据同步
        try:
            # 初始化各个模块，传入用户ID和管理员状态
            user_id = session['user_id']
            is_admin_flag = is_admin()
            sales_data = AmazonSalesData(db_session, user_id=user_id, is_admin=is_admin_flag)
            ad_data = AmazonAdvertisingData(db_session, user_id=user_id, is_admin=is_admin_flag)
            inventory_data = AmazonInventoryData(db_session, user_id=user_id, is_admin=is_admin_flag)
            integrator = DataIntegration(db_session, user_id=user_id, is_admin=is_admin_flag)
            
            # 执行同步
            sync_results = {
                'sales': False,
                'advertising': False,
                'inventory': False,
                'integration': False
            }
            
            # 同步销售数据
            sales_result = sales_data.sync_sales_data(store_id=store_id, target_date=target_date, user_id=user_id)
            sync_results['sales'] = sales_result.get('status') == 'success'
            
            # 同步广告数据
            ad_result = ad_data.sync_advertising_data(store_id=store_id, target_date=target_date, user_id=user_id)
            sync_results['advertising'] = ad_result.get('status') == 'success'
            
            # 同步库存数据
            inventory_result = inventory_data.sync_inventory_data(store_id=store_id, user_id=user_id)
            sync_results['inventory'] = inventory_result.get('status') == 'success'
            
            # 执行数据整合，传入用户ID确保数据隔离
            integration_result = integrator.integrate_data(target_date=target_date, store_id=store_id, user_id=user_id)
            sync_results['integration'] = integration_result.get('status') == 'success'
            
            # 更新同步日志
            sync_log.status = 'success' if all(sync_results.values()) else 'partial_success'
            sync_log.end_time = datetime.datetime.utcnow()
            sync_log.result = json.dumps(sync_results)
            
            db_session.commit()
            
            return jsonify({
                'status': 'success' if all(sync_results.values()) else 'partial_success',
                'message': '数据同步完成',
                'sync_results': sync_results,
                'sync_id': sync_log.id
            })
            
        except Exception as e:
            # 更新同步日志为失败
            sync_log.status = 'failed'
            sync_log.end_time = datetime.datetime.utcnow()
            sync_log.error_message = str(e)
            db_session.commit()
            
            logger.error(f'数据同步失败: {str(e)}')
            return jsonify({'status': 'error', 'message': '数据同步失败', 'error': str(e)}), 500
            
    except Exception as e:
        logger.error(f'手动触发同步出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '触发同步失败'}), 500

# 成本数据上传API
@app.route('/api/costs/upload', methods=['POST'])
@require_auth
def upload_cost_data():
    """上传成本数据文件"""
    try:
        user_id = session['user_id']
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': '没有文件上传'}), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({'status': 'error', 'message': '未选择文件'}), 400
        
        # 检查文件类型
        allowed_extensions = {'xlsx', 'xls', 'csv'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'status': 'error', 'message': '只支持Excel和CSV文件'}), 400
        
        # 保存文件
        filename = f"cost_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 处理上传的文件，传入用户ID
        uploader = CostDataUploader(db_session)
        result = uploader.process_file(filepath, user_id=user_id)
        
        if result['status'] != 'success':
            # 处理失败，删除文件
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'上传成本数据出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '上传文件失败'}), 500

@app.route('/api/costs', methods=['GET'])
@require_auth
def get_costs():
    """获取成本数据"""
    try:
        # 获取当前用户ID
        user_id = session['user_id']
        
        # 获取查询参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        asin = request.args.get('asin')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        fee_type = request.args.get('fee_type')
        
        # 使用CostDataUploader的get_cost_summary方法
        from cost_data_upload import CostDataUploader
        uploader = CostDataUploader(db_session)
        
        # 构建过滤条件
        filters = {
            'asin': asin,
            'start_date': start_date,
            'end_date': end_date,
            'cost_type': None,
            'page': page,
            'per_page': per_page
        }
        
        # 转换费用类型
        if fee_type:
            fee_type_map = {'promotion': '促销费', 'handling': '手续费', 'other': '其他'}
            # 支持中英文双向转换
            if fee_type in fee_type_map:
                filters['cost_type'] = fee_type
            elif fee_type in fee_type_map.values():
                for key, value in fee_type_map.items():
                    if value == fee_type:
                        filters['cost_type'] = key
                        break
        
        # 获取成本数据
        result = uploader.get_cost_summary(user_id=user_id, filters=filters)
        
        if result['status'] == 'success':
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取成本数据出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取成本数据失败'}), 500

@app.route('/api/products/asins', methods=['GET'])
@require_auth
def get_available_asins():
    """获取用户可用的ASIN列表，用于表单选择"""
    try:
        user_id = get_current_user().id
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', 50, type=int)
        
        # 从整合数据表中获取唯一的ASIN列表
        query = db_session.query(AmazonIntegratedData.asin).filter_by(user_id=user_id).distinct()
        
        # 如果有搜索关键词，添加搜索条件
        if search:
            query = query.filter(AmazonIntegratedData.asin.like(f'%{search}%'))
        
        # 限制结果数量并按ASIN排序
        asins = query.order_by(AmazonIntegratedData.asin).limit(limit).all()
        
        # 提取ASIN值
        asin_list = [asin[0] for asin in asins]
        
        return jsonify({
            'status': 'success',
            'data': asin_list,
            'total': len(asin_list)
        })
    except Exception as e:
        logger.error(f"获取ASIN列表失败: {str(e)}")
        return jsonify({"status": "error", "message": f"获取失败: {str(e)}"}), 500

@app.route('/api/costs/manual', methods=['GET'])
@require_auth
def get_manual_costs():
    """获取手动添加的成本记录列表"""
    try:
        user_id = get_current_user().id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        asin = request.args.get('asin')
        fee_type = request.args.get('fee_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 构建查询
        query = db_session.query(ManualCost).filter_by(user_id=user_id)
        
        # 添加筛选条件
        if asin:
            query = query.filter(ManualCost.asin == asin)
        if fee_type:
            # 转换中文费用类型为英文
            fee_type_map = {
                '促销费': 'promotion',
                '手续费': 'handling', 
                '其他': 'other',
                '仓储费': 'storage',
                '佣金费': 'commission',
                '广告费': 'advertising',
                '退货费': 'return',
                '退款费': 'refund',
                '其他费用': 'other_fee'
            }
            if fee_type in fee_type_map:
                query = query.filter(ManualCost.cost_type == fee_type_map[fee_type])
        if start_date:
            query = query.filter(ManualCost.cost_date >= datetime.datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(ManualCost.cost_date <= datetime.datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 分页查询
        pagination = query.order_by(ManualCost.cost_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        # 转换费用类型为中文
        reverse_fee_type_map = {
            'promotion': '促销费',
            'handling': '手续费',
            'other': '其他',
            'storage': '仓储费',
            'commission': '佣金费',
            'advertising': '广告费',
            'return': '退货费',
            'refund': '退款费',
            'other_fee': '其他费用'
        }
        
        # 格式化结果
        costs = []
        for cost in pagination.items:
            costs.append({
                'id': cost.id,
                'asin': cost.asin,
                'fee_type': reverse_fee_type_map.get(cost.cost_type, '未知'),
                'amount': float(cost.amount),
                'date': cost.cost_date.strftime('%Y-%m-%d'),
                'description': cost.description
            })
        
        return jsonify({
            'status': 'success',
            'data': costs,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        logger.error(f"获取手动成本记录失败: {str(e)}")
        return jsonify({"status": "error", "message": f"获取失败: {str(e)}"}), 500

@app.route('/api/costs/manual/<int:cost_id>', methods=['DELETE'])
@require_auth
def delete_manual_cost(cost_id):
    """删除手动添加的成本记录"""
    try:
        user_id = get_current_user().id
        cost = db_session.query(ManualCost).filter_by(id=cost_id, user_id=user_id).first()
        
        if not cost:
            return jsonify({'status': 'error', 'message': '记录不存在或无权访问'}), 404
        
        db_session.delete(cost)
        db_session.commit()
        
        logger.info(f"删除手动成本记录: ID={cost_id}, 用户ID={user_id}")
        return jsonify({'status': 'success', 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除手动成本记录失败: {str(e)}")
        db_session.rollback()
        return jsonify({"status": "error", "message": f"删除失败: {str(e)}"}), 500

@app.route('/api/costs/manual', methods=['POST'])
@require_auth
def add_manual_cost():
    """手动添加成本记录"""
    try:
        data = request.json
        user_id = session['user_id']
        
        # 检查必填字段
        required_fields = ['asin', 'fee_type', 'amount', 'date']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'缺少必填字段: {field}'}), 400
        
        # 验证费用类型
        valid_fee_types = ['促销费', '手续费', '其他', '仓储费', '佣金费', '广告费', '退货费', '退款费', '其他费用']
        if data['fee_type'] not in valid_fee_types:
            return jsonify({'status': 'error', 'message': '无效的费用类型'}), 400
        
        # 验证金额
        try:
            amount = float(data['amount'])
            if amount < 0:
                return jsonify({'status': 'error', 'message': '金额不能为负数'}), 400
        except ValueError:
            return jsonify({'status': 'error', 'message': '金额必须为数字'}), 400
        
        # 验证日期格式
        try:
            cost_date = datetime.datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': '日期格式错误，应为YYYY-MM-DD'}), 400
        
        # 使用CostDataUploader的add_manual_cost方法
        from cost_data_upload import CostDataUploader
        uploader = CostDataUploader(db_session)
        
        # 转换费用类型为英文
        fee_type_map = {
            '促销费': 'promotion',
            '手续费': 'handling',
            '其他': 'other',
            '仓储费': 'storage',
            '佣金费': 'commission',
            '广告费': 'advertising',
            '退货费': 'return',
            '退款费': 'refund',
            '其他费用': 'other_fee'
        }
        result = uploader.add_manual_cost(
            asin=data['asin'],
            cost_type=fee_type_map[data['fee_type']],
            amount=amount,
            date=cost_date,
            notes=data.get('description', ''),
            user_id=user_id
        )
        
        if result['status'] == 'success':
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f'手动添加成本出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '添加成本记录失败'}), 500

# 报表API
@app.route('/api/reports/asin-profit', methods=['GET'])
@require_auth
def get_asin_profit_report():
    """获取ASIN利润报表"""
    try:
        current_user = get_current_user()
        asin_profit = AmazonASINProfitReport(db_session, current_user.id)
        
        # 获取查询参数
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'store_id': request.args.get('store_id'),
            'asin': request.args.get('asin'),
            'marketplace': request.args.get('marketplace'),
            'min_profit': float(request.args.get('min_profit')) if request.args.get('min_profit') else None,
            'max_profit': float(request.args.get('max_profit')) if request.args.get('max_profit') else None,
            'sort_by': request.args.get('sort_by', 'total_profit'),
            'sort_order': request.args.get('sort_order', 'desc'),
            'page': request.args.get('page', 1),
            'page_size': request.args.get('page_size', 50)
        }
        
        # 过滤掉None值
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # 获取报表数据
        result = asin_profit.get_asin_profit_data(filters)
        
        return jsonify({
            'status': 'success',
            'data': result['data'],
            'pagination': result['pagination'],
            'filters': result['filters']
        })
    except Exception as e:
        logger.error(f'获取ASIN利润报表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'获取报表失败: {str(e)}'}), 500

@app.route('/api/reports/asin-profit/<asin>/details', methods=['GET'])
@require_auth
def get_asin_details(asin):
    """获取ASIN详细数据"""
    try:
        current_user = get_current_user()
        asin_profit = AmazonASINProfitReport(db_session, current_user.id)
        
        # 获取查询参数
        store_id = request.args.get('store_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 获取详细数据
        result = asin_profit.get_asin_details(asin, store_id, start_date, end_date)
        
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        logger.error(f'获取ASIN {asin} 详细数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取详细数据失败'}), 500

@app.route('/api/reports/asin-profit/export', methods=['POST'])
@require_auth
def export_asin_profit_report():
    """导出ASIN利润报表到Excel"""
    try:
        current_user = get_current_user()
        asin_profit = AmazonASINProfitReport(db_session, current_user.id)
        
        # 获取请求数据
        data = request.json or {}
        filters = data.get('filters', {})
        
        # 导出报表
        filepath = asin_profit.export_to_excel(filters)
        
        # 返回文件路径
        filename = os.path.basename(filepath)
        return jsonify({
            'status': 'success',
            'data': {
                'filename': filename,
                'download_url': f'/api/reports/download/{filename}'
            }
        })
    except Exception as e:
        logger.error(f'导出ASIN利润报表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '导出报表失败'}), 500

@app.route('/api/reports/asin-profit/summary', methods=['GET'])
@require_auth
def get_asin_profit_summary():
    """获取ASIN利润报表汇总统计"""
    try:
        current_user = get_current_user()
        asin_profit = AmazonASINProfitReport(db_session, current_user.id)
        
        # 获取查询参数
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'store_id': request.args.get('store_id'),
            'marketplace': request.args.get('marketplace')
        }
        
        # 过滤掉None值
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # 获取汇总数据
        summary = asin_profit.get_summary_statistics(filters)
        marketplace_data = asin_profit.get_marketplace_performance(filters)
        
        return jsonify({
            'status': 'success',
            'data': {
                'summary': summary,
                'marketplace_performance': marketplace_data
            }
        })
    except Exception as e:
        logger.error(f'获取ASIN利润报表汇总失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取汇总数据失败'}), 500

# 销量趋势报表
@app.route('/api/reports/sales-trend', methods=['POST'])
@require_auth
def get_sales_trend():
    """获取销量趋势报表"""
    try:
        current_user = get_current_user()
        report = AmazonSalesTrendReport(db_session, current_user.id)
        
        # 获取请求数据
        data = request.json or {}
        filters = data.get('filters', {})
        
        result = report.get_sales_trend_data(filters)
        
        return jsonify({
            'status': 'success',
            'data': result['data'],
            'summary': result['summary'],
            'anomalies': result['anomalies'],
            'filters': result['filters']
        })
    except Exception as e:
        logger.error(f'获取销量趋势报表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 产品销售对比
@app.route('/api/reports/product-comparison', methods=['POST'])
@require_auth
def get_product_comparison():
    """获取产品销售对比"""
    try:
        current_user = get_current_user()
        report = AmazonSalesTrendReport(db_session, current_user.id)
        
        # 获取请求数据
        data = request.json or {}
        filters = data.get('filters', {})
        top_n = data.get('top_n', 5)
        
        products = report.get_product_comparison(filters, top_n)
        
        return jsonify({
            'status': 'success',
            'data': products
        })
    except Exception as e:
        logger.error(f'获取产品销售对比失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 市场销售对比
@app.route('/api/reports/marketplace-comparison', methods=['POST'])
@require_auth
def get_marketplace_comparison():
    """获取市场销售对比"""
    try:
        current_user = get_current_user()
        report = AmazonSalesTrendReport(db_session, current_user.id)
        
        # 获取请求数据
        data = request.json or {}
        filters = data.get('filters', {})
        
        marketplaces = report.get_marketplace_comparison(filters)
        
        return jsonify({
            'status': 'success',
            'data': marketplaces
        })
    except Exception as e:
        logger.error(f'获取市场销售对比失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 销量趋势报表导出
@app.route('/api/reports/sales-trend/export', methods=['POST'])
@require_auth
def export_sales_trend_report():
    """导出销量趋势报表"""
    try:
        current_user = get_current_user()
        report = AmazonSalesTrendReport(db_session, current_user.id)
        
        # 获取请求数据
        data = request.json or {}
        filters = data.get('filters', {})
        
        filepath = report.export_to_excel(filters)
        
        # 返回文件路径
        filename = os.path.basename(filepath)
        return jsonify({
            'status': 'success',
            'data': {
                'filename': filename,
                'download_url': f'/api/reports/download/{filename}'
            }
        })
    except Exception as e:
        logger.error(f'导出销量趋势报表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 销量预测
@app.route('/api/reports/sales-forecast', methods=['POST'])
@require_auth
def get_sales_forecast():
    """获取销量预测"""
    try:
        current_user = get_current_user()
        report = AmazonSalesTrendReport(db_session, current_user.id)
        
        # 获取请求数据
        data = request.json or {}
        days = data.get('days', 7)
        filters = data.get('filters', {})
        
        forecast = report.get_forecast(days, filters)
        
        return jsonify({
            'status': 'success',
            'data': forecast,
            'days': days
        })
    except Exception as e:
        logger.error(f'获取销量预测失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/reports/sales-trend', methods=['GET'])
@require_auth
def get_sales_trend_report():
    """获取销量趋势报表"""
    try:
        # 获取当前用户
        user = get_current_user()
        user_id = user.id
        
        # 获取查询参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        store_id = request.args.get('store_id', type=int)
        
        # 解析日期
        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # 验证店铺权限（如果指定了店铺）
        if store_id and not user.is_admin:
            store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user_id).first()
            if not store:
                return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
        
        # 生成报表，传入用户ID确保数据隔离
        generator = ReportGenerator(db_session)
        result = generator.generate_sales_trend_report(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            store_id=store_id
        )
        
        if result['status'] != 'success':
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取销量趋势报表出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取报表失败'}), 500

@app.route('/api/reports/inventory-health', methods=['GET'])
@require_auth
def get_inventory_health_report():
    """获取库存健康报表"""
    try:
        # 获取当前用户
        user = get_current_user()
        user_id = user.id
        
        # 获取查询参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        store_id = request.args.get('store_id', type=int)
        
        # 解析日期
        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # 验证店铺权限（如果指定了店铺）
        if store_id and not user.is_admin:
            store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user_id).first()
            if not store:
                return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
        
        # 生成报表，传入用户ID确保数据隔离
        generator = ReportGenerator(db_session)
        result = generator.generate_inventory_health_report(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            store_id=store_id
        )
        
        if result['status'] != 'success':
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取库存健康报表出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取报表失败'}), 500


# 共享链接API
@app.route('/api/share-links/create', methods=['POST'])
@require_auth
def create_share_link():
    """创建报表共享链接"""
    try:
        user_id = get_current_user().id
        data = request.json or {}
        
        # 验证必要参数
        if 'report_type' not in data:
            return jsonify({'status': 'error', 'message': '缺少必要参数: report_type'}), 400
        
        # 创建共享链接管理器
        manager = ShareLinkManager(db_session)
        
        # 创建共享链接
        share_link = manager.create_share_link(
            user_id=user_id,
            report_type=data['report_type'],
            filter_params=data.get('filter_params', {}),
            expires_in=data.get('expires_in', 24)  # 默认24小时
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'token': share_link.token,
                'share_url': f"/shared/{share_link.token}",
                'report_type': share_link.report_type,
                'created_at': share_link.created_at.isoformat(),
                'expires_at': share_link.expires_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'创建共享链接失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '创建共享链接失败'}), 500

@app.route('/api/share-links', methods=['GET'])
@require_auth
def list_share_links():
    """列出用户的所有共享链接"""
    try:
        user_id = get_current_user().id
        
        # 创建共享链接管理器
        manager = ShareLinkManager(db_session)
        
        # 获取用户的所有共享链接
        links = manager.list_user_links(user_id)
        
        # 转换为字典列表
        result = []
        for link in links:
            result.append({
                'id': link.id,
                'token': link.token,
                'report_type': link.report_type,
                'is_active': link.is_active,
                'created_at': link.created_at.isoformat(),
                'expires_at': link.expires_at.isoformat()
            })
        
        return jsonify({'status': 'success', 'data': result})
        
    except Exception as e:
        logger.error(f'获取共享链接列表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取共享链接列表失败'}), 500

@app.route('/api/share-links/<link_id>/revoke', methods=['POST'])
@require_auth
def revoke_share_link(link_id):
    """撤销共享链接"""
    try:
        user_id = get_current_user().id
        
        # 创建共享链接管理器
        manager = ShareLinkManager(db_session)
        
        # 撤销共享链接
        success = manager.revoke_link(user_id, link_id)
        
        if not success:
            return jsonify({'status': 'error', 'message': '共享链接不存在或无权撤销'}), 404
        
        return jsonify({'status': 'success', 'message': '共享链接已撤销'})
        
    except Exception as e:
        logger.error(f'撤销共享链接失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '撤销共享链接失败'}), 500

@app.route('/api/share-links/<link_id>/extend', methods=['POST'])
@require_auth
def extend_share_link(link_id):
    """延长共享链接有效期"""
    try:
        user_id = get_current_user().id
        data = request.json or {}
        
        # 创建共享链接管理器
        manager = ShareLinkManager(db_session)
        
        # 延长有效期
        link = manager.extend_link(user_id, link_id, data.get('expires_in', 24))
        
        if not link:
            return jsonify({'status': 'error', 'message': '共享链接不存在或无权延长'}), 404
        
        return jsonify({
            'status': 'success',
            'data': {
                'expires_at': link.expires_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'延长共享链接有效期失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '延长共享链接有效期失败'}), 500

# 公开访问的共享链接端点
@app.route('/api/shared/<token>/verify', methods=['GET'])
def verify_share_link(token):
    """验证共享链接有效性"""
    try:
        manager = ShareLinkManager(db_session)
        
        # 验证链接
        link_info = manager.verify_link(token)
        
        if not link_info:
            return jsonify({'status': 'error', 'message': '无效或已过期的共享链接'}), 404
        
        return jsonify({
            'status': 'success',
            'data': {
                'report_type': link_info['report_type'],
                'created_by': link_info['created_by'],
                'created_at': link_info['created_at'],
                'expires_at': link_info['expires_at']
            }
        })
        
    except Exception as e:
        logger.error(f'验证共享链接失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '验证共享链接失败'}), 500

@app.route('/api/shared/<token>/data', methods=['GET'])
def get_shared_report_data(token):
    """获取共享报表数据"""
    try:
        manager = ShareLinkManager(db_session)
        
        # 验证链接并获取报表数据
        report_data = manager.get_shared_report_data(token)
        
        if not report_data:
            return jsonify({'status': 'error', 'message': '无效或已过期的共享链接'}), 404
        
        return jsonify({
            'status': 'success',
            'data': report_data,
            'readonly': True  # 标记为只读模式
        })
        
    except Exception as e:
        logger.error(f'获取共享报表数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取共享报表数据失败'}), 500
        
        # 验证店铺权限（如果指定了店铺）
        if store_id and not user.is_admin:
            store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user_id).first()
            if not store:
                return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
        
        # 生成报表，传入用户ID确保数据隔离
        generator = ReportGenerator(db_session)
        result = generator.generate_inventory_health_report(
            store_id=store_id,
            user_id=user_id
        )
        
        if result['status'] != 'success':
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'获取库存健康报表出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取报表失败'}), 500


# API接口：获取库存详情
@app.route('/api/reports/inventory-health/<asin>/details', methods=['GET'])
@require_auth
def get_inventory_details(asin):
    """
    获取指定ASIN的库存详细信息
    """
    try:
        # 获取当前用户
        user = get_current_user()
        user_id = user.id
        
        # 获取查询参数
        store_id = request.args.get('store_id', type=int)
        
        # 验证店铺权限
        if store_id and not user.is_admin:
            store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user_id).first()
            if not store:
                return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
        
        # 获取库存详情
        report = get_inventory_health_report_instance()
        details = report.get_inventory_details(
            asin=asin,
            store_id=store_id,
            user_id=user_id
        )
        
        if details:
            return jsonify({'status': 'success', 'data': details})
        else:
            return jsonify({'status': 'error', 'message': '库存数据不存在'}), 404
    except Exception as e:
        logger.error(f"获取库存详情失败: {str(e)}")
        return jsonify({'status': 'error', 'message': '获取库存详情失败'}), 500


# API接口：导出库存健康报表
@app.route('/api/reports/inventory-health/export', methods=['GET'])
@require_auth
def export_inventory_health_report():
    """
    导出库存健康报表为Excel文件
    """
    try:
        # 获取当前用户
        user = get_current_user()
        user_id = user.id
        
        # 获取查询参数
        store_id = request.args.get('store_id', type=int)
        marketplace = request.args.get('marketplace')
        asin = request.args.get('asin')
        sku = request.args.get('sku')
        status = request.args.get('status')
        
        # 验证店铺权限
        if store_id and not user.is_admin:
            store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user_id).first()
            if not store:
                return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
        
        # 导出报表
        report = get_inventory_health_report_instance()
        file_path = report.export_to_excel(
            store_id=store_id,
            marketplace=marketplace,
            asin=asin,
            sku=sku,
            status=status,
            user_id=user_id
        )
        
        return jsonify({'status': 'success', 'file_path': file_path})
    except Exception as e:
        logger.error(f"导出库存健康报表失败: {str(e)}")
        return jsonify({'status': 'error', 'message': '导出报表失败'}), 500


# API接口：获取库存汇总统计
@app.route('/api/reports/inventory-health/summary', methods=['GET'])
@require_auth
def get_inventory_summary():
    """
    获取库存汇总统计数据
    """
    try:
        # 获取当前用户
        user = get_current_user()
        user_id = user.id
        
        # 获取查询参数
        store_id = request.args.get('store_id', type=int)
        marketplace = request.args.get('marketplace')
        
        # 验证店铺权限
        if store_id and not user.is_admin:
            store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user_id).first()
            if not store:
                return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
        
        # 获取汇总统计
        report = get_inventory_health_report_instance()
        summary = report.get_inventory_summary(
            store_id=store_id,
            marketplace=marketplace,
            user_id=user_id
        )
        
        return jsonify({'status': 'success', 'data': summary})
    except Exception as e:
        logger.error(f"获取库存汇总统计失败: {str(e)}")
        return jsonify({'status': 'error', 'message': '获取汇总统计失败'}), 500


# API接口：获取库存预警设置
@app.route('/api/inventory/alert-settings', methods=['GET'])
@require_auth
def get_alert_settings():
    """
    获取库存预警设置
    """
    try:
        # 获取当前用户
        user = get_current_user()
        
        # 获取查询参数
        asin = request.args.get('asin')
        store_id = request.args.get('store_id', type=int)
        
        # 构建查询
        query = db_session.query(InventoryAlertSetting)
        
        # 应用筛选条件
        if asin:
            query = query.filter(InventoryAlertSetting.asin == asin)
        if store_id:
            # 验证店铺权限
            if not user.is_admin:
                store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user.id).first()
                if not store:
                    return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
            query = query.filter(InventoryAlertSetting.store_id == str(store_id))
        
        # 执行查询
        settings = query.all()
        
        return jsonify({
            'status': 'success',
            'data': [setting.to_dict() for setting in settings]
        })
    except Exception as e:
        logger.error(f"获取库存预警设置失败: {str(e)}")
        return jsonify({'status': 'error', 'message': '获取预警设置失败'}), 500


# API接口：设置库存预警
@app.route('/api/inventory/alert-settings', methods=['POST'])
@require_auth
def set_alert_settings():
    """
    设置库存预警
    """
    try:
        # 获取当前用户
        user = get_current_user()
        
        # 获取请求数据
        data = request.json
        if not data or 'asin' not in data or 'store_id' not in data:
            return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
        
        # 验证店铺权限
        store_id = data['store_id']
        if not user.is_admin:
            store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user.id).first()
            if not store:
                return jsonify({'status': 'error', 'message': '无权访问指定店铺的数据'}), 403
        
        # 检查是否已存在相同的ASIN和store_id设置
        existing = db_session.query(InventoryAlertSetting).filter(
            InventoryAlertSetting.asin == data['asin'],
            InventoryAlertSetting.store_id == str(data['store_id'])
        ).first()
        
        if existing:
            # 更新现有设置
            existing.low_stock_threshold = data.get('low_stock_threshold', existing.low_stock_threshold)
            existing.high_stock_threshold = data.get('high_stock_threshold', existing.high_stock_threshold)
            existing.alert_email = data.get('alert_email', existing.alert_email)
            existing.alert_wechat = data.get('alert_wechat', existing.alert_wechat)
            db_session.commit()
            return jsonify({'status': 'success', 'data': existing.to_dict()}), 200
        else:
            # 创建新设置
            new_setting = InventoryAlertSetting(
                asin=data['asin'],
                store_id=str(data['store_id']),
                low_stock_threshold=data.get('low_stock_threshold', 7),
                high_stock_threshold=data.get('high_stock_threshold', 60),
                alert_email=data.get('alert_email'),
                alert_wechat=data.get('alert_wechat', False)
            )
            db_session.add(new_setting)
            db_session.commit()
            return jsonify({'status': 'success', 'data': new_setting.to_dict()}), 201
    except Exception as e:
        db_session.rollback()
        logger.error(f"设置库存预警失败: {str(e)}")
        return jsonify({'status': 'error', 'message': '设置预警失败'}), 500


@app.route('/api/reports/generate-all', methods=['POST'])
@require_auth
def generate_all_reports():
    """生成所有报表"""
    try:
        # 获取当前用户ID
        user_id = session['user_id']
        
        # 生成报表，传入用户ID确保数据隔离
        generator = ReportGenerator(db_session)
        reports = generator.generate_daily_reports(user_id=user_id)
        
        # 检查是否生成成功
        if not reports or 'summary' not in reports:
            return jsonify({'status': 'error', 'message': '生成报表失败'}), 500
        
        return jsonify({'status': 'success', 'message': '所有报表生成成功', 'reports': reports})
        
    except Exception as e:
        logger.error(f'生成所有报表出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '生成报表失败'}), 500

@app.route('/api/scheduler/status', methods=['GET'])
@require_auth
def get_scheduler_status():
    """获取调度器状态"""
    try:
        return jsonify({
            'status': 'success',
            'data': {
                'running': scheduler.is_running(),
                'jobs': scheduler.get_jobs()
            }
        })
    except Exception as e:
        logger.error(f'获取调度器状态失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取调度器状态失败'}), 500

@app.route('/api/scheduler/start', methods=['POST'])
@require_auth
def start_scheduler():
    """启动调度器"""
    try:
        scheduler.start()
        return jsonify({'status': 'success', 'message': '调度器已启动'})
    except Exception as e:
        logger.error(f'启动调度器失败: {str(e)}')
        return jsonify({'status': 'error', 'message': '启动调度器失败'}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
@require_auth
def stop_scheduler():
    try:
        scheduler.stop()
        logger.info('调度器已停止')
        return jsonify({'status': 'success', 'message': '调度器已停止'})
    except Exception as e:
        logger.error(f'停止调度器出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '停止调度器失败'}), 500

# 数据备份相关API
@app.route('/api/backups', methods=['GET'])
@require_auth
def list_backups():
    """获取备份列表"""
    try:
        from backup_manager import BackupManager
        backup_manager = BackupManager(db_session)
        result = backup_manager.list_backups()
        return jsonify(result)
    except Exception as e:
        logger.error(f'获取备份列表出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取备份列表失败'}), 500

@app.route('/api/backups', methods=['POST'])
@require_auth
def create_backup():
    """创建新备份"""
    try:
        from backup_manager import BackupManager
        backup_manager = BackupManager(db_session)
        description = request.json.get('description', '手动创建的备份')
        result = backup_manager.create_backup(description=description)
        return jsonify(result)
    except Exception as e:
        logger.error(f'创建备份出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '创建备份失败'}), 500

@app.route('/api/backups/<backup_id>/restore', methods=['POST'])
@require_auth
def restore_backup(backup_id):
    """恢复备份"""
    try:
        from backup_manager import BackupManager
        backup_manager = BackupManager(db_session)
        # 从请求体中获取backup_filename
        data = request.json or {}
        backup_filename = data.get('backup_filename')
        if not backup_filename:
            return jsonify({'status': 'error', 'message': '缺少备份文件名'}), 400
        result = backup_manager.restore_from_backup(backup_filename)
        return jsonify(result)
    except Exception as e:
        logger.error(f'恢复备份出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '恢复备份失败'}), 500

@app.route('/api/backups/<backup_filename>', methods=['DELETE'])
@require_auth
def delete_backup(backup_filename):
    """删除备份"""
    try:
        from backup_manager import BackupManager
        backup_manager = BackupManager(db_session)
        result = backup_manager.delete_backup(backup_filename)
        return jsonify(result)
    except Exception as e:
        logger.error(f'删除备份出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '删除备份失败'}), 500

@app.route('/api/backups/cleanup', methods=['POST'])
@require_auth
def cleanup_backups():
    """清理旧备份"""
    try:
        from backup_manager import BackupManager
        backup_manager = BackupManager(db_session)
        days_to_keep = request.json.get('days_to_keep', 30)
        result = backup_manager.cleanup_old_backups(days_to_keep=days_to_keep)
        return jsonify(result)
    except Exception as e:
        logger.error(f'清理旧备份出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '清理旧备份失败'}), 500

# 文件下载API
@app.route('/api/reports/download/<filename>', methods=['GET'])
@require_auth
def download_report(filename):
    """下载报表文件"""
    try:
        return send_from_directory(REPORT_FOLDER, filename, as_attachment=True)
    except Exception as e:
        logger.error(f'下载报表文件出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '文件不存在或下载失败'}), 404

# 调度器管理
@app.route('/api/scheduler/status', methods=['GET'])
@require_auth
def get_scheduler_status():
    """获取调度器状态"""
    try:
        # 从单例获取调度器实例
        scheduler = get_scheduler()
        user_id = session['user_id']
        status = scheduler.get_status(user_id=user_id)
        return jsonify({'status': 'success', 'data': status})
    except Exception as e:
        logger.error(f'获取调度器状态出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取调度器状态失败'}), 500

@app.route('/api/scheduler/start', methods=['POST'])
@require_auth
def start_scheduler():
    """启动调度器"""
    try:
        # 从单例获取调度器实例
        scheduler = get_scheduler()
        user_id = session['user_id']
        result = scheduler.start(user_id=user_id)
        if result['status'] != 'success':
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        logger.error(f'启动调度器出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '启动调度器失败'}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
@require_auth
def stop_scheduler():
    """停止调度器"""
    try:
        # 从单例获取调度器实例
        scheduler = get_scheduler()
        user_id = session['user_id']
        result = scheduler.stop(user_id=user_id)
        if result['status'] != 'success':
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        logger.error(f'停止调度器出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '停止调度器失败'}), 500

# 同步日志查询
@app.route('/api/sync/logs', methods=['GET'])
@require_auth
def get_sync_logs():
    """获取同步日志"""
    try:
        user_id = session['user_id']
        user = get_current_user()
        
        # 获取查询参数
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        store_id = request.args.get('store_id', type=int)
        status = request.args.get('status')
        
        # 构建查询
        if user.is_admin:
            # 管理员可以查看所有同步日志
            query = db_session.query(SyncLog)
        else:
            # 普通用户只能查看自己的同步日志
            query = db_session.query(SyncLog).filter(SyncLog.user_id == user_id)
        
        if store_id:
            # 如果指定了店铺ID，还要检查权限
            if not user.is_admin:
                # 确保普通用户只能查看自己的店铺
                store = db_session.query(AmazonStore).filter_by(id=store_id, user_id=user_id).first()
                if not store:
                    return jsonify({'status': 'error', 'message': '无权查看此店铺的同步日志'}), 403
            query = query.filter(SyncLog.store_id == store_id)
        
        # 状态筛选
        if status:
            query = query.filter(SyncLog.status == status)
        
        # 查询日志
        logs = query.order_by(desc(SyncLog.start_time)).offset(offset).limit(limit).all()
        
        result = []
        for log in logs:
            result.append({
                'id': log.id,
                'sync_type': log.sync_type,
                'store_id': log.store_id,
                'target_date': log.target_date.isoformat() if log.target_date else None,
                'status': log.status,
                'start_time': log.start_time.isoformat() if log.start_time else None,
                'end_time': log.end_time.isoformat() if log.end_time else None,
                'result': json.loads(log.result) if log.result else None,
                'error_message': log.error_message,
                'user_id': log.user_id  # 添加用户ID标识
            })
        
        # 获取总数（需要考虑过滤条件）
        total = query.count()
        
        return jsonify({
            'status': 'success', 
            'data': result,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        logger.error(f'获取同步日志出错: {str(e)}')
        return jsonify({'status': 'error', 'message': '获取同步日志失败'}), 500

# 销售数据相关API
@app.route('/api/sales/sync', methods=['POST'])
@require_auth
def sync_sales_data():
    """
    同步销售数据API
    
    参数:
    - store_id: 可选，店铺ID，不提供则同步所有店铺
    - days_back: 可选，回溯天数，默认1天
    - target_date: 可选，目标同步日期，格式：YYYY-MM-DD
    - force_update: 可选，是否强制更新已存在的数据，默认false
    """
    user = get_current_user()
    data = request.get_json() or {}
    
    try:
        # 获取参数
        store_id = data.get('store_id')
        days_back = int(data.get('days_back', 1))
        target_date_str = data.get('target_date')
        force_update = data.get('force_update', False)
        
        # 验证参数
        if days_back < 1 or days_back > 365:
            return jsonify({
                'status': 'error',
                'message': '回溯天数必须在1-365之间'
            }), 400
        
        # 处理目标日期
        target_date = None
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': '目标日期格式错误，应为YYYY-MM-DD'
                }), 400
        
        # 创建销售数据实例
        sales_data = AmazonSalesData(db_session=db_session, user_id=user.id, is_admin=user.is_admin)
        
        # 同步数据
        logger.info(f"用户 {user.id} 开始同步销售数据，store_id={store_id}, days_back={days_back}, target_date={target_date}")
        result = sales_data.sync_sales_data(
            store_id=store_id,
            days_back=days_back,
            target_date=target_date,
            user_id=user.id,
            force_update=force_update
        )
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'data': result
        })
        
    except Exception as e:
        logger.error(f"同步销售数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"同步销售数据失败: {str(e)}"
        }), 500

@app.route('/api/sales/sync-all', methods=['POST'])
@require_auth
def sync_all_stores_sales():
    """
    同步所有店铺销售数据API
    
    参数:
    - days_back: 可选，回溯天数，默认1天
    - force_update: 可选，是否强制更新已存在的数据，默认false
    """
    user = get_current_user()
    data = request.get_json() or {}
    
    try:
        # 获取参数
        days_back = int(data.get('days_back', 1))
        force_update = data.get('force_update', False)
        
        # 验证参数
        if days_back < 1 or days_back > 365:
            return jsonify({
                'status': 'error',
                'message': '回溯天数必须在1-365之间'
            }), 400
        
        # 创建销售数据实例
        sales_data = AmazonSalesData(db_session=db_session, user_id=user.id, is_admin=user.is_admin)
        
        # 同步所有店铺数据
        logger.info(f"用户 {user.id} 开始同步所有店铺销售数据，days_back={days_back}")
        result = sales_data.sync_all_stores(
            days_back=days_back,
            user_id=user.id,
            force_update=force_update
        )
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'data': result
        })
        
    except Exception as e:
        logger.error(f"同步所有店铺销售数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"同步所有店铺销售数据失败: {str(e)}"
        }), 500

@app.route('/api/sales/statistics', methods=['GET'])
@require_auth
def get_sales_statistics():
    """
    获取销售统计数据API
    
    查询参数:
    - store_id: 可选，店铺ID
    - marketplace: 可选，市场
    - date_from: 可选，开始日期，格式：YYYY-MM-DD
    - date_to: 可选，结束日期，格式：YYYY-MM-DD
    """
    user = get_current_user()
    
    try:
        # 获取查询参数
        store_id = request.args.get('store_id', type=int)
        marketplace = request.args.get('marketplace')
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        # 处理日期参数
        date_from = None
        date_to = None
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': '开始日期格式错误，应为YYYY-MM-DD'
                }), 400
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': '结束日期格式错误，应为YYYY-MM-DD'
                }), 400
        
        # 创建销售数据实例
        sales_data = AmazonSalesData(db_session=db_session, user_id=user.id, is_admin=user.is_admin)
        
        # 获取统计数据
        statistics = sales_data.get_sales_statistics(
            store_id=store_id,
            marketplace=marketplace,
            date_from=date_from,
            date_to=date_to,
            user_id=user.id
        )
        
        if statistics is None:
            return jsonify({
                'status': 'error',
                'message': '获取销售统计数据失败'
            }), 500
        
        return jsonify({
            'status': 'success',
            'data': statistics
        })
        
    except Exception as e:
        logger.error(f"获取销售统计数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"获取销售统计数据失败: {str(e)}"
        }), 500

# ERP成本数据文件上传相关接口
@app.route('/api/erp-costs/upload', methods=['POST'])
@require_auth
def upload_erp_cost_file():
    """上传ERP成本数据文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': '没有提供文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
        
        user_id = get_current_user().id
        uploader = CostDataUploader(UPLOAD_FOLDER)
        result = uploader.process_erp_file(file, user_id)
        
        return jsonify({
            'status': 'success' if result['success'] else 'error',
            'message': result['message'],
            'file_id': result.get('file_id')
        })
    except Exception as e:
        logger.error(f"上传ERP成本文件失败: {str(e)}")
        return jsonify({"status": "error", "message": f"上传失败: {str(e)}"}), 500

@app.route('/api/erp-costs/files', methods=['GET'])
@require_auth
def get_erp_cost_files():
    """获取ERP成本文件列表"""
    try:
        user_id = get_current_user().id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        query = db_session.query(ERPCostFile).filter_by(user_id=user_id)
        if not is_admin():
            query = query.filter_by(user_id=user_id)
        
        pagination = query.order_by(ERPCostFile.upload_time.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        files = []
        for file in pagination.items:
            files.append({
                'id': file.id,
                'filename': file.filename,
                'file_size': file.file_size,
                'file_type': file.file_type,
                'status': file.status,
                'processed_count': file.processed_count,
                'failed_count': file.failed_count,
                'upload_time': file.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
                'error_message': file.error_message
            })
        
        return jsonify({
            'status': 'success',
            'data': files,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        logger.error(f"获取ERP成本文件列表失败: {str(e)}")
        return jsonify({"status": "error", "message": f"获取失败: {str(e)}"}), 500

@app.route('/api/erp-costs/files/<int:file_id>', methods=['GET'])
@require_auth
def get_erp_cost_file(file_id):
    """获取ERP成本文件详情"""
    try:
        user_id = get_current_user().id
        file = db_session.query(ERPCostFile).filter_by(id=file_id).first()
        
        if not file:
            return jsonify({'status': 'error', 'message': '文件不存在'}), 404
        
        if not is_admin() and file.user_id != user_id:
            return jsonify({'status': 'error', 'message': '无权访问'}), 403
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': file.id,
                'filename': file.filename,
                'file_size': file.file_size,
                'file_type': file.file_type,
                'status': file.status,
                'processed_count': file.processed_count,
                'failed_count': file.failed_count,
                'upload_time': file.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
                'error_message': file.error_message,
                'field_mappings': file.field_mappings
            }
        })
    except Exception as e:
        logger.error(f"获取ERP成本文件详情失败: {str(e)}")
        return jsonify({"status": "error", "message": f"获取失败: {str(e)}"}), 500

@app.route('/api/erp-costs/data', methods=['GET'])
@require_auth
def get_erp_cost_data():
    """获取ERP成本数据列表"""
    try:
        user_id = get_current_user().id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        asin = request.args.get('asin')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 构建查询
        query = db_session.query(ERPCostData).join(ERPCostFile).filter(ERPCostFile.user_id == user_id)
        
        # 添加筛选条件
        if asin:
            query = query.filter(ERPCostData.asin == asin)
        if start_date:
            query = query.filter(ERPCostData.date >= datetime.datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(ERPCostData.date <= datetime.datetime.strptime(end_date, '%Y-%m-%d'))
        
        pagination = query.order_by(ERPCostData.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        data = []
        for item in pagination.items:
            data.append({
                'id': item.id,
                'asin': item.asin,
                'date': item.date.strftime('%Y-%m-%d'),
                'cost_price': float(item.cost_price) if item.cost_price else 0,
                'shipping_fee': float(item.shipping_fee) if item.shipping_fee else 0,
                'customs_fee': float(item.customs_fee) if item.customs_fee else 0,
                'other_costs': float(item.other_costs) if item.other_costs else 0,
                'total_cost': float(item.total_cost) if item.total_cost else 0,
                'file_id': item.file_id
            })
        
        return jsonify({
            'status': 'success',
            'data': data,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        logger.error(f"获取ERP成本数据失败: {str(e)}")
        return jsonify({"status": "error", "message": f"获取失败: {str(e)}"}), 500

# 静态文件服务（用于生产环境）
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('../frontend/static', filename)

# 主页面
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

# 启动应用
def setup_app():
    """设置应用"""
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
        'wechat_report_hour': '8',
        'wechat_report_minute': '0',
        'email_report_hour': '8',
        'email_report_minute': '0'
    }
    
    # 初始化所有默认配置
    for config_name, default_value in default_configs.items():
        config = db_session.query(SystemConfig).filter_by(config_name=config_name).first()
        if not config:
            config = SystemConfig(config_name=config_name, config_value=default_value)
            db_session.add(config)
    db_session.commit()
    
    # 配置企业微信定时推送任务
    try:
        # 从配置中获取推送时间
        hour_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'wechat_report_hour'
        ).first()
        minute_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'wechat_report_minute'
        ).first()
        
        hour = int(hour_config.config_value) if hour_config else 8
        minute = int(minute_config.config_value) if minute_config else 0
        
        # 添加每日企业微信报表推送任务
        scheduler.scheduler.add_job(
            id='daily_wechat_report_push',
            func=send_wechat_report_notification,
            trigger=CronTrigger(hour=hour, minute=minute),
            replace_existing=True
        )
        logger.info(f'企业微信报表推送任务已添加，每日{hour:02d}:{minute:02d}执行')
    except Exception as e:
        logger.error(f'配置邮件推送任务失败: {str(e)}')
    
    # 配置邮件定时推送任务
    try:
        # 从配置中获取推送时间
        email_hour_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_report_hour'
        ).first()
        email_minute_config = db_session.query(SystemConfig).filter(
            SystemConfig.config_name == 'email_report_minute'
        ).first()
        
        email_hour = int(email_hour_config.config_value) if email_hour_config else 8
        email_minute = int(email_minute_config.config_value) if email_minute_config else 0
        
        # 添加每日邮件报表推送任务
        scheduler.scheduler.add_job(
            id='daily_email_report_push',
            func=send_email_report_notification,
            trigger=CronTrigger(hour=email_hour, minute=email_minute),
            replace_existing=True
        )
        logger.info(f'邮件报表推送任务已添加，每日{email_hour:02d}:{email_minute:02d}执行')
    except Exception as e:
        logger.error(f'配置邮件推送任务失败: {str(e)}')
    
    db_session.commit()
    
    # 启动调度器
    scheduler.start()
    logger.info('调度器已启动')

if __name__ == '__main__':
    try:
        setup_app()
        # 启动Flask应用
        # 注意：在生产环境中应该使用WSGI服务器而不是直接运行Flask
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        # 停止调度器
        if scheduler.is_running():
            scheduler.stop()
            logger.info('调度器已停止')
        # 关闭数据库会话
        db_session.close()
