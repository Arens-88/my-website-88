import pandas as pd
import datetime
import logging
import os
import json
from models import AmazonIntegratedData, init_db, ShareLink
from sqlalchemy import func, desc
import matplotlib.pyplot as plt
import io
import base64

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('report_generator')

class ReportGenerator:
    """报表生成模块"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session or init_db()
        # 确保报表目录存在
        self.report_dir = os.path.join('..', 'data', 'reports')
        os.makedirs(self.report_dir, exist_ok=True)
        self.readonly_mode = False  # 默认不是只读模式
    
    def get_date_range(self, days=7):
        """获取日期范围"""
        end_date = datetime.datetime.utcnow().date()
        start_date = end_date - datetime.timedelta(days=days-1)  # days-1是因为包括今天
        return start_date, end_date
    
    def generate_asin_profit_report(self, start_date=None, end_date=None, group_by='day', asins=None, user_id=None, share_link=None):
        """生成ASIN利润报表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            group_by: 分组方式 ('day', 'week' 或 'month')
            asins: ASIN列表
            user_id: 用户ID，用于权限验证
            share_link: 共享链接对象，用于只读访问
        """
        try:
            # 设置只读模式
            if share_link:
                self.readonly_mode = True
                # 从共享链接获取过滤参数
                filter_params = json.loads(share_link.filter_params or '{}')
                if filter_params.get('store_id'):
                    user_id = None  # 共享链接已经包含了必要的过滤条件
            
            # 如果未提供日期范围，默认使用最近7天
            if not start_date or not end_date:
                start_date, end_date = self.get_date_range()
            
            logger.info(f'生成ASIN利润报表，日期范围: {start_date} 至 {end_date}，分组: {group_by}, 只读模式: {self.readonly_mode}')
            
            # 构建查询
            query = self.db_session.query(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.store_name,
                AmazonIntegratedData.order_date,
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
                func.sum(AmazonIntegratedData.platform_fee).label('total_platform_fee'),
                func.sum(AmazonIntegratedData.ad_cost).label('total_ad_cost'),
                func.sum(AmazonIntegratedData.product_cost).label('total_product_cost'),
                func.sum(AmazonIntegratedData.shipping_cost).label('total_shipping_cost'),
                func.sum(AmazonIntegratedData.promotion_fee).label('total_promotion_fee'),
                func.sum(AmazonIntegratedData.handling_fee).label('total_handling_fee'),
                func.sum(AmazonIntegratedData.net_profit).label('total_profit')
            ).filter(
                AmazonIntegratedData.order_date >= start_date,
                AmazonIntegratedData.order_date <= end_date
            )
            
            # 如果指定了用户ID，添加过滤条件
            if user_id:
                query = query.filter(AmazonIntegratedData.user_id == user_id)
            
            # 如果指定了ASIN列表，添加过滤
            if asins:
                query = query.filter(AmazonIntegratedData.asin.in_(asins))
            
            # 分组字段
            if group_by == 'day':
                # 按天分组
                grouped_query = query.group_by(
                    AmazonIntegratedData.asin,
                    AmazonIntegratedData.store_name,
                    AmazonIntegratedData.order_date
                )
            elif group_by == 'week':
                # 按周分组
                from sqlalchemy.sql import func
                grouped_query = query.group_by(
                    AmazonIntegratedData.asin,
                    AmazonIntegratedData.store_name,
                    func.strftime('%Y-%W', AmazonIntegratedData.order_date)
                )
            else:  # month
                # 按月分组
                from sqlalchemy.sql import func
                grouped_query = query.group_by(
                    AmazonIntegratedData.asin,
                    AmazonIntegratedData.store_name,
                    func.strftime('%Y-%m', AmazonIntegratedData.order_date)
                )
            
            # 按净利润降序排序
            results = grouped_query.order_by(desc('total_profit')).all()
            
            # 转换为DataFrame
            data = []
            for row in results:
                # 计算净利润率
                profit_rate = (row.total_profit / row.total_sales * 100) if row.total_sales > 0 else 0
                
                # 计算总运营成本
                total_cost = (row.total_platform_fee + row.total_ad_cost + row.total_product_cost + 
                            row.total_shipping_cost + row.total_promotion_fee + row.total_handling_fee)
                
                data.append({
                    'ASIN': row.asin,
                    '店铺名称': row.store_name,
                    '日期': row.order_date if group_by == 'day' else str(row.order_date),
                    '总销售额': float(row.total_sales),
                    '总运营成本': float(total_cost),
                    '总净利润': float(row.total_profit),
                    '净利润率': round(profit_rate, 2)
                })
            
            df = pd.DataFrame(data)
            
            # 保存为Excel（非只读模式下）
            if not self.readonly_mode:
                report_filename = f'asin_profit_{start_date}_{end_date}_{group_by}.xlsx'
                report_path = os.path.join(self.report_dir, report_filename)
                df.to_excel(report_path, index=False)
                logger.info(f'ASIN利润报表生成成功: {report_path}')
            else:
                report_path = None
                logger.info(f'ASIN利润报表（只读模式）生成成功')
            
            return {
                'status': 'success',
                'message': 'ASIN利润报表生成成功',
                'report_path': report_path,
                'data': df.to_dict('records'),
                'total_records': len(df),
                'readonly': self.readonly_mode
            }
            
        except Exception as e:
            error_message = f'生成ASIN利润报表时发生错误: {str(e)}'
            logger.error(error_message)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def generate_sales_trend_report(self, start_date=None, end_date=None, interval='day', user_id=None, share_link=None):
        """生成销量趋势报表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            interval: 间隔方式
            user_id: 用户ID，用于权限验证
            share_link: 共享链接对象，用于只读访问
        """
        try:
            # 设置只读模式
            if share_link:
                self.readonly_mode = True
                # 从共享链接获取过滤参数
                filter_params = json.loads(share_link.filter_params or '{}')
                if filter_params.get('store_id'):
                    user_id = None  # 共享链接已经包含了必要的过滤条件
            
            # 如果未提供日期范围，默认使用最近30天
            if not start_date or not end_date:
                start_date, end_date = self.get_date_range(days=30)
            
            logger.info(f'生成销量趋势报表，日期范围: {start_date} 至 {end_date}，间隔: {interval}, 只读模式: {self.readonly_mode}')
            
            # 构建查询
            query = self.db_session.query(
                AmazonIntegratedData.order_date,
                func.sum(AmazonIntegratedData.order_count).label('total_orders'),
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales')
            ).filter(
                AmazonIntegratedData.order_date >= start_date,
                AmazonIntegratedData.order_date <= end_date
            )
            
            # 如果指定了用户ID，添加过滤条件
            if user_id:
                query = query.filter(AmazonIntegratedData.user_id == user_id)
            
            # 分组
            results = query.group_by(AmazonIntegratedData.order_date).order_by(AmazonIntegratedData.order_date).all()
            
            # 转换为DataFrame
            data = []
            for row in results:
                data.append({
                    '日期': row.order_date,
                    '订单量': int(row.total_orders),
                    '销售额': float(row.total_sales)
                })
            
            df = pd.DataFrame(data)
            
            # 检测异常波动（订单量较前一天波动>50%）
            if len(df) > 1:
                df['订单量变化率'] = df['订单量'].pct_change() * 100
                df['是否异常'] = df['订单量变化率'].abs() > 50
            
            # 生成图表
            plt.figure(figsize=(12, 6))
            
            # 双Y轴图表
            ax1 = plt.subplot(111)
            ax2 = ax1.twinx()
            
            # 订单量折线图
            ax1.plot(df['日期'], df['订单量'], 'b-', marker='o', label='订单量')
            ax1.set_xlabel('日期')
            ax1.set_ylabel('订单量', color='b')
            ax1.tick_params(axis='y', labelcolor='b')
            
            # 销售额折线图
            ax2.plot(df['日期'], df['销售额'], 'r-', marker='s', label='销售额')
            ax2.set_ylabel('销售额', color='r')
            ax2.tick_params(axis='y', labelcolor='r')
            
            # 标注异常点
            if len(df) > 1:
                for i, row in df.iterrows():
                    if row['是否异常'] and i > 0:  # 跳过第一行（没有前一天数据）
                        ax1.annotate('销量异常波动', 
                                    xy=(row['日期'], row['订单量']),
                                    xytext=(0, 10),
                                    textcoords='offset points',
                                    color='orange',
                                    fontweight='bold')
            
            plt.title('销量趋势报表')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # 保存图表
            chart_filename = f'sales_trend_{start_date}_{end_date}.png'
            chart_path = os.path.join(self.report_dir, chart_filename)
            plt.savefig(chart_path)
            plt.close()
            
            # 将图表转换为base64编码（用于Web显示）
            with open(chart_path, 'rb') as img_file:
                chart_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            # 保存数据为Excel（非只读模式下）
            if not self.readonly_mode:
                report_filename = f'sales_trend_{start_date}_{end_date}.xlsx'
                report_path = os.path.join(self.report_dir, report_filename)
                df.to_excel(report_path, index=False)
                logger.info(f'销量趋势报表生成成功: {report_path}, {chart_path}')
            else:
                report_path = None
                logger.info(f'销量趋势报表（只读模式）生成成功')
            
            return {
                'status': 'success',
                'message': '销量趋势报表生成成功',
                'report_path': report_path,
                'chart_path': chart_path if not self.readonly_mode else None,
                'chart_base64': chart_base64,
                'data': df.to_dict('records'),
                'readonly': self.readonly_mode
            }
            
        except Exception as e:
            error_message = f'生成销量趋势报表时发生错误: {str(e)}'
            logger.error(error_message)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def generate_inventory_health_report(self, store_id=None, user_id=None, share_link=None):
        """生成库存健康报表
        
        Args:
            store_id: 店铺ID
            user_id: 用户ID，用于权限验证
            share_link: 共享链接对象，用于只读访问
        """
        try:
            # 设置只读模式
            if share_link:
                self.readonly_mode = True
                # 从共享链接获取过滤参数
                filter_params = json.loads(share_link.filter_params or '{}')
                if filter_params.get('store_id'):
                    store_id = filter_params.get('store_id')
                    user_id = None  # 共享链接已经包含了必要的过滤条件
            
            # 获取当前日期
            current_date = datetime.datetime.utcnow().date()
            
            logger.info(f'生成库存健康报表: 只读模式={self.readonly_mode}')
            
            # 构建查询
            query = self.db_session.query(
                AmazonIntegratedData.asin,
                AmazonIntegratedData.store_name,
                AmazonIntegratedData.instock_quantity,
                AmazonIntegratedData.inbound_quantity,
                AmazonIntegratedData.sellable_quantity_30d,
                AmazonIntegratedData.inventory_turnover,
                AmazonIntegratedData.days_of_coverage
            ).filter(
                AmazonIntegratedData.order_date == current_date
            )
            
            # 如果指定了用户ID，添加过滤条件
            if user_id:
                query = query.filter(AmazonIntegratedData.user_id == user_id)
            
            # 如果指定了店铺，添加过滤
            if store_id:
                query = query.filter(AmazonIntegratedData.store_id == store_id)
                # 如果指定了user_id，确保店铺属于该用户
                if user_id:
                    from models import AmazonStore
                    store = self.db_session.query(AmazonStore).filter(
                        AmazonStore.id == store_id,
                        AmazonStore.user_id == user_id
                    ).first()
                    if not store:
                        return {
                            'status': 'error',
                            'message': '无权限访问该店铺'
                        }
            
            results = query.all()
            
            # 转换为DataFrame
            data = []
            for row in results:
                # 确定库存状态
                if row.days_of_coverage < 7:
                    status = '紧急'  # 红色感叹号
                    icon = '🔴'
                elif row.days_of_coverage <= 90:
                    status = '健康'  # 绿色对勾
                    icon = '✅'
                else:
                    status = '过剩'  # 黄色警告
                    icon = '🟡'
                
                data.append({
                    'ASIN': row.asin,
                    '店铺名称': row.store_name,
                    '在库量': int(row.instock_quantity),
                    '在途量': int(row.inbound_quantity),
                    '30天销量': int(row.sellable_quantity_30d),
                    '库存周转率': round(float(row.inventory_turnover), 2),
                    '库存覆盖天数': round(float(row.days_of_coverage), 2),
                    '库存状态': status,
                    '状态图标': icon
                })
            
            df = pd.DataFrame(data)
            
            # 按库存状态排序（紧急 > 过剩 > 健康）
            status_order = {'紧急': 0, '过剩': 1, '健康': 2}
            df['_status_order'] = df['库存状态'].map(status_order)
            df = df.sort_values('_status_order').drop('_status_order', axis=1)
            
            # 保存为Excel（非只读模式下）
            if not self.readonly_mode:
                report_filename = f'inventory_health_{current_date}.xlsx'
                report_path = os.path.join(self.report_dir, report_filename)
                df.to_excel(report_path, index=False)
                logger.info(f'库存健康报表生成成功: {report_path}')
            else:
                report_path = None
                logger.info(f'库存健康报表（只读模式）生成成功')
            
            return {
                'status': 'success',
                'message': '库存健康报表生成成功',
                'report_path': report_path,
                'data': df.to_dict('records'),
                'total_records': len(df),
                'urgent_count': len(df[df['库存状态'] == '紧急']),
                'excess_count': len(df[df['库存状态'] == '过剩']),
                'healthy_count': len(df[df['库存状态'] == '健康']),
                'readonly': self.readonly_mode
            }
            
        except Exception as e:
            error_message = f'生成库存健康报表时发生错误: {str(e)}'
            logger.error(error_message)
            return {
                'status': 'error',
                'message': error_message
            }
    
    def generate_daily_reports(self, user_id=None):
        """生成每日报表（所有类型）"""
        try:
            # 获取昨天的日期
            yesterday = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
            
            # 生成各类报表
            reports = {}
            
            # 1. ASIN利润报表（昨天的数据，按日分组）
            profit_report = self.generate_asin_profit_report(start_date=yesterday, end_date=yesterday, group_by='day', user_id=user_id)
            if profit_report['status'] == 'success':
                reports['profit_report'] = profit_report
            
            # 2. 销量趋势报表（最近30天）
            start_date_30d = yesterday - datetime.timedelta(days=29)  # 包括昨天共30天
            trend_report = self.generate_sales_trend_report(start_date=start_date_30d, end_date=yesterday, user_id=user_id)
            if trend_report['status'] == 'success':
                reports['trend_report'] = trend_report
            
            # 3. 库存健康报表
            inventory_report = self.generate_inventory_health_report(user_id=user_id)
            if inventory_report['status'] == 'success':
                reports['inventory_report'] = inventory_report
            
            # 4. 生成汇总数据
            summary = self.generate_daily_summary(yesterday, user_id=user_id)
            reports['summary'] = summary
            
            return reports
            
        except Exception as e:
            logger.error(f'生成每日报表时发生错误: {str(e)}')
            return {}
    
    def generate_daily_summary(self, target_date, user_id=None):
        """生成每日汇总数据"""
        try:
            # 查询汇总数据
            summary = self.db_session.query(
                func.sum(AmazonIntegratedData.sales_amount).label('total_sales'),
                func.sum(AmazonIntegratedData.net_profit).label('total_profit'),
                func.sum(AmazonIntegratedData.order_count).label('total_orders')
            ).filter(
                AmazonIntegratedData.order_date == target_date
            )
            
            # 如果指定了用户ID，添加过滤条件
            if user_id:
                summary = summary.filter(AmazonIntegratedData.user_id == user_id)
            
            summary = summary.first()
            
            # 计算净利润率
            if summary.total_sales and summary.total_sales > 0:
                profit_rate = (summary.total_profit / summary.total_sales) * 100
            else:
                profit_rate = 0
            
            # 查询利润最高的前3个ASIN
            top_asins = self.db_session.query(
                AmazonIntegratedData.asin,
                func.sum(AmazonIntegratedData.net_profit).label('total_profit')
            ).filter(
                AmazonIntegratedData.order_date == target_date
            )
            
            # 如果指定了用户ID，添加过滤条件
            if user_id:
                top_asins = top_asins.filter(AmazonIntegratedData.user_id == user_id)
            
            top_asins = top_asins.group_by(
                AmazonIntegratedData.asin
            ).order_by(
                desc('total_profit')
            ).limit(3).all()
            
            return {
                'date': target_date.strftime('%Y-%m-%d'),
                'total_sales': float(summary.total_sales or 0),
                'total_profit': float(summary.total_profit or 0),
                'profit_rate': round(profit_rate, 2),
                'total_orders': int(summary.total_orders or 0),
                'top_asins': [
                    {'asin': asin.asin, 'profit': float(asin.total_profit or 0)}
                    for asin in top_asins
                ]
            }
            
        except Exception as e:
            logger.error(f'生成每日汇总时发生错误: {str(e)}')
            return {}

# 使用示例
if __name__ == '__main__':
    # 示例：生成ASIN利润报表
    # generator = ReportGenerator()
    # profit_report = generator.generate_asin_profit_report()
    # print(f"ASIN利润报表: {profit_report['message']}")
    
    # 示例：生成销量趋势报表
    # trend_report = generator.generate_sales_trend_report()
    # print(f"销量趋势报表: {trend_report['message']}")
    
    # 示例：生成库存健康报表
    # inventory_report = generator.generate_inventory_health_report()
    # print(f"库存健康报表: {inventory_report['message']}")
    
    # 示例：生成每日报表
    # daily_reports = generator.generate_daily_reports()
    # print(f"每日报表生成完成，共 {len(daily_reports)} 个报表")
