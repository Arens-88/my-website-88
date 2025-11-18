import smtplib
import os
import io
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('email_sender')


class EmailSender:
    """
    邮件发送器类，用于发送报表邮件和Excel附件
    """
    
    def __init__(self):
        self.server = None
        self.is_connected = False
    
    def connect(self, smtp_server, smtp_port, username, password, use_ssl=True):
        """
        连接到SMTP服务器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP服务器端口
            username: 邮箱用户名
            password: 邮箱密码
            use_ssl: 是否使用SSL连接
        """
        try:
            if use_ssl:
                self.server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            else:
                self.server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                self.server.starttls()
            
            self.server.login(username, password)
            self.is_connected = True
            logger.info(f"成功连接到SMTP服务器: {smtp_server}")
            return True
        except Exception as e:
            logger.error(f"连接SMTP服务器失败: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """
        断开SMTP服务器连接
        """
        if self.server:
            try:
                self.server.quit()
                self.is_connected = False
                logger.info("已断开SMTP服务器连接")
            except Exception as e:
                logger.error(f"断开SMTP服务器连接失败: {str(e)}")
    
    def send_report_email(self, sender_name, sender_email, recipients, subject, report_data, 
                         report_summary=None, attach_excel=True, report_type="销售报表"):
        """
        发送报表邮件
        
        Args:
            sender_name: 发件人名称
            sender_email: 发件人邮箱
            recipients: 收件人列表
            subject: 邮件主题
            report_data: 报表数据字典，包含各个报表的数据
            report_summary: 报表摘要文本
            attach_excel: 是否附加Excel文件
            report_type: 报表类型名称
        """
        if not self.is_connected:
            logger.error("SMTP服务器未连接，无法发送邮件")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = formataddr((sender_name, sender_email))
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # 构建邮件正文
            email_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    h2 {{ color: #2c3e50; }}
                    h3 {{ color: #3498db; }}
                    .summary {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0; }}
                    .report-link {{ margin-top: 20px; padding: 10px; background-color: #e8f4f8; text-align: center; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #7f8c8d; }}
                </style>
            </head>
            <body>
                <h2>亚马逊{report_type}</h2>
                
                <p>尊敬的用户，您的{report_type}已生成，请查看详情。</p>
            """
            
            # 添加报表摘要
            if report_summary:
                email_body += f"""
                <div class="summary">
                    <h3>报表摘要</h3>
                    <p>{report_summary}</p>
                </div>
                """
            
            # 添加报表链接
            email_body += f"""
                <div class="report-link">
                    <h3>访问完整报表</h3>
                    <p>您可以通过以下链接访问完整的报表数据：</p>
                    <a href="http://your-domain.com/reports" style="color: #3498db; text-decoration: none; font-weight: bold;">
                        访问报表系统
                    </a>
                </div>
                
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿直接回复。</p>
                    <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """
            
            # 添加HTML正文
            msg.attach(MIMEText(email_body, 'html', 'utf-8'))
            
            # 添加Excel附件
            if attach_excel and report_data:
                excel_buffer = self._generate_excel_attachment(report_data)
                if excel_buffer:
                    attachment = MIMEApplication(excel_buffer.getvalue(), Name=f"amazon_{report_type}_{datetime.now().strftime('%Y%m%d')}.xlsx")
                    attachment['Content-Disposition'] = f'attachment; filename="amazon_{report_type}_{datetime.now().strftime("%Y%m%d")}.xlsx"'
                    msg.attach(attachment)
                    logger.info("Excel附件已添加到邮件")
            
            # 发送邮件
            self.server.send_message(msg)
            logger.info(f"邮件已成功发送至 {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            return False
    
    def _generate_excel_attachment(self, report_data):
        """
        生成Excel附件
        
        Args:
            report_data: 报表数据字典，每个键对应一个DataFrame
        """
        try:
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for sheet_name, data in report_data.items():
                    if isinstance(data, pd.DataFrame) and not data.empty:
                        data.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                        
                        # 美化Excel表格
                        worksheet = writer.sheets[sheet_name[:31]]
                        
                        # 设置列宽自动调整
                        for column in data:
                            column_width = max(data[column].astype(str).map(len).max(), len(column)) + 2
                            col_idx = data.columns.get_loc(column)
                            worksheet.set_column(col_idx, col_idx, column_width)
            
            output.seek(0)
            logger.info("Excel文件已生成")
            return output
        except Exception as e:
            logger.error(f"生成Excel文件失败: {str(e)}")
            return None


# 创建全局邮件发送器实例
_email_sender_instance = None


def get_email_sender():
    """
    获取邮件发送器单例
    """
    global _email_sender_instance
    if _email_sender_instance is None:
        _email_sender_instance = EmailSender()
    return _email_sender_instance