import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class WechatBot:
    """
    企业微信机器人推送类
    用于向企业微信群发送消息和报表
    """
    
    def __init__(self, webhook_url: str):
        """
        初始化企业微信机器人
        
        Args:
            webhook_url: 企业微信机器人Webhook URL
        """
        self.webhook_url = webhook_url
        self.session = requests.Session()
    
    def send_text_message(self, content: str, mentioned_list: Optional[List[str]] = None, 
                         mentioned_mobile_list: Optional[List[str]] = None) -> bool:
        """
        发送文本消息
        
        Args:
            content: 消息内容
            mentioned_list: 需要@的成员列表
            mentioned_mobile_list: 需要@的手机号列表
            
        Returns:
            bool: 发送是否成功
        """
        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content,
                }
            }
            
            if mentioned_list:
                data["text"]["mentioned_list"] = mentioned_list
            
            if mentioned_mobile_list:
                data["text"]["mentioned_mobile_list"] = mentioned_mobile_list
            
            return self._send_request(data)
        except Exception as e:
            logger.error(f"发送文本消息失败: {str(e)}")
            return False
    
    def send_markdown_message(self, content: str) -> bool:
        """
        发送Markdown格式消息
        
        Args:
            content: Markdown格式的消息内容
            
        Returns:
            bool: 发送是否成功
        """
        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
            
            return self._send_request(data)
        except Exception as e:
            logger.error(f"发送Markdown消息失败: {str(e)}")
            return False
    
    def send_report_summary(self, report_data: Dict) -> bool:
        """
        发送报表摘要信息
        
        Args:
            report_data: 包含报表数据的字典
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建Markdown格式的报表摘要
            markdown_content = f"""## 📊 亚马逊报表每日摘要

**📅 生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 📈 核心指标
- **总销售额**: ¥{report_data.get('total_sales', 0):,.2f}
- **总订单数**: {report_data.get('total_orders', 0):,} 单
- **总利润**: ¥{report_data.get('total_profit', 0):,.2f}
- **平均利润率**: {report_data.get('avg_profit_rate', 0):.2f}%

### 🛍️ 表现最佳ASIN
- **ASIN**: {report_data.get('top_asin', {}).get('asin', 'N/A')}
- **产品名称**: {report_data.get('top_asin', {}).get('product_name', 'N/A')}
- **销售额**: ¥{report_data.get('top_asin', {}).get('sales', 0):,.2f}
- **利润**: ¥{report_data.get('top_asin', {}).get('profit', 0):,.2f}

### 📉 库存预警
- **低库存ASIN数**: {report_data.get('low_stock_count', 0)}
- **库存不足7天的ASIN数**: {report_data.get('stock_danger_count', 0)}

### 🔗 详细报表
请点击 [报表链接]({report_data.get('report_url', '#')}) 查看完整报表
            """
            
            return self.send_markdown_message(markdown_content)
        except Exception as e:
            logger.error(f"发送报表摘要失败: {str(e)}")
            return False
    
    def _send_request(self, data: Dict) -> bool:
        """
        发送HTTP请求到企业微信机器人
        
        Args:
            data: 要发送的数据
            
        Returns:
            bool: 请求是否成功
        """
        try:
            headers = {'Content-Type': 'application/json'}
            response = self.session.post(
                self.webhook_url, 
                headers=headers, 
                data=json.dumps(data)
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('errcode') == 0:
                logger.info("企业微信消息发送成功")
                return True
            else:
                logger.error(f"企业微信消息发送失败: {response_data.get('errmsg', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"发送请求失败: {str(e)}")
            return False


# 创建全局实例供其他模块使用
wechat_bot_instance = None


def get_wechat_bot(webhook_url: str = None) -> WechatBot:
    """
    获取企业微信机器人实例（单例模式）
    
    Args:
        webhook_url: 企业微信机器人Webhook URL
        
    Returns:
        WechatBot: 企业微信机器人实例
    """
    global wechat_bot_instance
    
    if webhook_url and (wechat_bot_instance is None or wechat_bot_instance.webhook_url != webhook_url):
        wechat_bot_instance = WechatBot(webhook_url)
    
    return wechat_bot_instance