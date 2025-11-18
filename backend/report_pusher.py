import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import datetime
import logging
from models import SystemConfig, User
from sqlalchemy import select

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('report_pusher')

class ReportPusher:
    """报表推送模块"""
    
    def __init__(self, db_session, user_id=None):
        self.db_session = db_session
        self.user_id = user_id
        # 为每个用户创建独立的报表目录
        if user_id:
            self.report_dir = os.path.join('..', 'data', 'reports', str(user_id))
        else:
            self.report_dir = os.path.join('..', 'data', 'reports')
        
        # 确保报表目录存在
        os.makedirs(self.report_dir, exist_ok=True)
    
    def get_config(self, config_name):
        """从数据库获取配置信息，优先使用用户特定配置"""
        try:
            # 优先查询用户特定的配置
            if self.user_id:
                config = self.db_session.execute(
                    select(SystemConfig).where(
                        SystemConfig.config_name == config_name,
                        SystemConfig.user_id == self.user_id
                    )
                ).scalar_one_or_none()
                if config:
                    return config.config_value
            
            # 如果没有用户特定配置或没有指定用户ID，查询全局配置
            config = self.db_session.execute(
                select(SystemConfig).where(
                    SystemConfig.config_name == config_name,
                    SystemConfig.user_id.is_(None)
                )
            ).scalar_one_or_none()
            return config.config_value if config else None
        except Exception as e:
            logger.error(f'获取配置 {config_name} 时出错: {str(e)}')
            return None
    
    def push_wechat_robot(self, summary_data, report_urls):
        """使用企业微信机器人推送报表信息"""
        try:
            # 获取企业微信机器人webhook
            webhook_url = self.get_config('wechat_webhook_url')
            if not webhook_url:
                logger.error('未配置企业微信机器人webhook')
                return {'status': 'error', 'message': '未配置企业微信机器人webhook'}
            
            # 构建推送内容
            today = datetime.datetime.utcnow().date().strftime('%Y-%m-%d')
            user_identifier = summary_data.get('user', '')
            user_prefix = f"【{user_identifier}】" if user_identifier else ""
            
            # 格式化净利润TOP3 ASIN
            top_asins_text = '\n'.join([f"- {asin['asin']}: ￥{asin['profit']:,.2f}" for asin in summary_data.get('top_asins', [])])
            
            # 构建消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"""**【亚马逊运营日报】{user_prefix}{today}**\n\n"""
                    f"""## 核心数据\n\n"""
                    f"""- 总销售额：￥{summary_data.get('total_sales', 0):,.2f}\n"""
                    f"""- 总净利润：￥{summary_data.get('total_profit', 0):,.2f}\n"""
                    f"""- 净利润率：{summary_data.get('profit_rate', 0)}%\n"""
                    f"""- 订单总量：{summary_data.get('total_orders', 0)}单\n\n"""
                    f"""## 净利润 Top3 ASIN\n\n{top_asins_text}\n\n"""
                    f"""## 报表链接\n\n"""
                    f"""[ASIN利润报表]({report_urls.get('profit_report', '#')})\n"""
                    f"""[销量趋势报表]({report_urls.get('trend_report', '#')})\n"""
                    f"""[库存健康报表]({report_urls.get('inventory_report', '#')})\n"""
                }
            }
            
            # 发送请求
            response = requests.post(webhook_url, json=message)
            response.raise_for_status()
            
            logger.info(f'企业微信机器人推送成功: {response.text}')
            return {'status': 'success', 'message': '企业微信机器人推送成功', 'response': response.text}
            
        except requests.exceptions.RequestException as e:
            error_message = f'企业微信机器人推送失败: {str(e)}'
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
        except Exception as e:
            error_message = f'企业微信机器人推送时发生错误: {str(e)}'
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
    
    def push_email(self, recipient_emails, summary_data, report_files):
        """使用邮箱推送报表信息和附件"""
        try:
            # 获取邮箱配置
            smtp_server = self.get_config('smtp_server')
            smtp_port = self.get_config('smtp_port')
            smtp_username = self.get_config('smtp_username')
            smtp_password = self.get_config('smtp_password')
            sender_email = self.get_config('sender_email')
            
            if not all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
                logger.error('未完整配置邮箱推送参数')
                return {'status': 'error', 'message': '未完整配置邮箱推送参数'}
            
            # 确保收件人列表有效
            if not recipient_emails or not isinstance(recipient_emails, list) or len(recipient_emails) == 0:
                logger.error('收件人邮箱列表无效')
                return {'status': 'error', 'message': '收件人邮箱列表无效'}
            
            # 构建邮件内容
            today = datetime.datetime.utcnow().date().strftime('%Y-%m-%d')
            user_identifier = summary_data.get('user', '')
            user_prefix = f"【{user_identifier}】" if user_identifier else ""
            
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = f'【亚马逊运营日报】{user_prefix}{today}'
            
            # 构建邮件正文
            top_asins_text = '<br>'.join([f"- {asin['asin']}: ￥{asin['profit']:,.2f}" for asin in summary_data.get('top_asins', [])])
            
            body = f"""
            <h2>【亚马逊运营日报】{user_prefix}{today}</h2>
            
            <h3>核心数据</h3>
            <ul>
                <li>总销售额：￥{summary_data.get('total_sales', 0):,.2f}</li>
                <li>总净利润：￥{summary_data.get('total_profit', 0):,.2f}</li>
                <li>净利润率：{summary_data.get('profit_rate', 0)}%</li>
                <li>订单总量：{summary_data.get('total_orders', 0)}单</li>
            </ul>
            
            <h3>净利润 Top3 ASIN</h3>
            <p>{top_asins_text}</p>
            
            <p>请查看附件获取详细报表数据。</p>
            """
            
            # 添加正文
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # 添加附件
            for file_path in report_files:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as file:
                        part = MIMEApplication(file.read(), Name=os.path.basename(file_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                        msg.attach(part)
                    logger.info(f'添加附件: {os.path.basename(file_path)}')
                else:
                    logger.warning(f'附件不存在: {file_path}')
            
            # 连接SMTP服务器并发送邮件
            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                # 根据配置决定是否使用TLS
                use_tls = self.get_config('smtp_use_tls')
                if use_tls and use_tls.lower() == 'true':
                    server.starttls()
                
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f'邮件推送成功，收件人: {recipient_emails}')
            return {'status': 'success', 'message': '邮件推送成功', 'recipients': recipient_emails}
            
        except smtplib.SMTPException as e:
            error_message = f'邮件推送失败: {str(e)}'
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
        except Exception as e:
            error_message = f'邮件推送时发生错误: {str(e)}'
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
    
    def push_daily_reports(self, summary_data, report_paths, report_urls):
        """推送每日报表（包括微信和邮箱）"""
        results = {}
        
        try:
            # 获取推送配置
            enable_wechat = self.get_config('enable_wechat_push')
            enable_email = self.get_config('enable_email_push')
            email_recipients = self.get_config('email_recipients')
            
            # 添加用户标识到推送内容
            if self.user_id:
                user = self.db_session.get(User, self.user_id)
                user_identifier = user.username if user else f'用户{self.user_id}'
            else:
                user_identifier = '系统全局'
            
            # 更新摘要数据，添加用户标识
            summary_data['user'] = user_identifier
            
            # 企业微信推送
            if enable_wechat and enable_wechat.lower() == 'true':
                wechat_result = self.push_wechat_robot(summary_data, report_urls)
                results['wechat'] = wechat_result
                logger.info(f'企业微信推送结果({user_identifier}): {wechat_result.get("status")}')
            else:
                results['wechat'] = {'status': 'skipped', 'message': '企业微信推送已禁用'}
            
            # 邮件推送
            if enable_email and enable_email.lower() == 'true' and email_recipients:
                # 解析收件人列表
                recipients = [email.strip() for email in email_recipients.split(',')]
                # 只包含有效的文件路径
                valid_files = [path for path in report_paths if os.path.exists(path)]
                
                email_result = self.push_email(recipients, summary_data, valid_files)
                results['email'] = email_result
                logger.info(f'邮件推送结果({user_identifier}): {email_result.get("status")}')
            else:
                results['email'] = {'status': 'skipped', 'message': '邮件推送已禁用或未配置收件人'}
            
            return results
            
        except Exception as e:
            logger.error(f'推送每日报表时发生错误(user_id={self.user_id}): {str(e)}')
            return {}

# 使用示例
if __name__ == '__main__':
    from models import init_db
    
    # 示例：推送报表
    # db_session = init_db()
    # pusher = ReportPusher(db_session)
    # 
    # # 假设的数据
    # summary_data = {
    #     'total_sales': 100000.00,
    #     'total_profit': 30000.00,
    #     'profit_rate': 30.00,
    #     'total_orders': 500,
    #     'top_asins': [
    #         {'asin': 'B012345678', 'profit': 15000.00},
    #         {'asin': 'B087654321', 'profit': 10000.00},
    #         {'asin': 'B013579246', 'profit': 5000.00}
    #     ]
    # }
    # 
    # report_paths = [
    #     os.path.join(pusher.report_dir, 'asin_profit_2023-01-01_2023-01-01_day.xlsx'),
    #     os.path.join(pusher.report_dir, 'sales_trend_2023-01-01_2023-01-31.png'),
    #     os.path.join(pusher.report_dir, 'inventory_health_2023-01-31.xlsx')
    # ]
    # 
    # report_urls = {
    #     'profit_report': 'https://example.com/reports/profit',
    #     'trend_report': 'https://example.com/reports/trend',
    #     'inventory_report': 'https://example.com/reports/inventory'
    # }
    # 
    # # 推送报表
    # results = pusher.push_daily_reports(summary_data, report_paths, report_urls)
    # print(f"推送结果: {results}")
