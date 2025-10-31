#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FBA费用计算器 - 更新服务器启动脚本
用于本地提供更新文件，实现无网站跳转的自动更新功能
"""

import http.server
import socketserver
import os
import sys
import webbrowser
import time
import subprocess
import threading
import ssl
from datetime import datetime

# 服务器配置
PORT = 8081
HTTPS_PORT = 8443

# SSL证书配置
SSL_DIR = "D:\ssl_certs"
# 默认证书文件路径
CERT_FILE = os.path.join(SSL_DIR, "server.crt")
KEY_FILE = os.path.join(SSL_DIR, "server.key")

# 支持备选证书文件名
ALT_CERT_NAMES = ["cert.pem", "fullchain.pem", "tomarens.crt"]
ALT_KEY_NAMES = ["privkey.pem", "tomarens.key"]

# 检查是否使用HTTPS
USE_HTTPS = False
if len(sys.argv) > 1 and sys.argv[1] == "--https":
    USE_HTTPS = True

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """自定义HTTP请求处理器，支持日志记录和CORS"""
    
    def log_message(self, format, *args):
        """自定义日志记录格式"""
        log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        client_ip = self.client_address[0]
        request_line = format % args
        log_entry = f"[{log_time}] {client_ip} - {request_line}\n"
        
        print(log_entry, end='')
        
        # 保存到日志文件
        try:
            with open('update_server.log', 'a', encoding='utf-8') as log_file:
                log_file.write(log_entry)
        except:
            pass
    
    def is_localhost(self):
        """检查请求是否来自本地主机或内网"""
        client_ip = self.client_address[0]
        # 本地IP地址列表和内网IP前缀
        localhost_ips = ['127.0.0.1', '::1', 'localhost']
        # 检查是否是内网IP
        return (client_ip in localhost_ips or 
                client_ip.startswith('10.') or 
                client_ip.startswith('192.168.') or 
                client_ip.startswith('172.16.') or 
                client_ip.startswith('172.17.') or 
                client_ip.startswith('172.18.') or 
                client_ip.startswith('172.19.') or 
                client_ip.startswith('172.20.') or 
                client_ip.startswith('172.21.') or 
                client_ip.startswith('172.22.') or 
                client_ip.startswith('172.23.') or 
                client_ip.startswith('172.24.') or 
                client_ip.startswith('172.25.') or 
                client_ip.startswith('172.26.') or 
                client_ip.startswith('172.27.') or 
                client_ip.startswith('172.28.') or 
                client_ip.startswith('172.29.') or 
                client_ip.startswith('172.30.') or 
                client_ip.startswith('172.31.'))
    
    def end_headers(self):
        """添加CORS头以支持跨域请求"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """处理OPTIONS请求"""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求，支持更新信息文件的动态生成和HTML页面"""
        # 提供主页面
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # 传递客户端IP给generate_main_html函数
            client_ip = self.client_address[0]
            html_content = self.generate_main_html(client_ip)
            self.wfile.write(html_content.encode('utf-8'))
            return
        
        # BUG收集箱页面 - 只有本地主机才能访问
        elif self.path == '/feedback.html':
            # 检查是否是本地主机
            if not self.is_localhost():
                self.send_response(404)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                not_found_html = '''
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                    <meta charset="UTF-8">
                    <title>页面未找到</title>
                </head>
                <body>
                    <h1>页面未找到</h1>
                    <p>您访问的页面不存在或无权访问。</p>
                </body>
                </html>
                '''
                self.wfile.write(not_found_html.encode('utf-8'))
                return
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html_content = self.generate_feedback_html()
            self.wfile.write(html_content.encode('utf-8'))
            return
        
        # 意见反馈收纳箱页面 - 只有本地主机才能访问
        elif self.path == '/feedback_box.html':
            # 检查是否是本地主机
            if not self.is_localhost():
                self.send_response(404)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                not_found_html = '''
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                    <meta charset="UTF-8">
                    <title>页面未找到</title>
                </head>
                <body>
                    <h1>页面未找到</h1>
                    <p>您访问的页面不存在或无权访问。</p>
                </body>
                </html>
                '''
                self.wfile.write(not_found_html.encode('utf-8'))
                return
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html_content = self.generate_feedback_box_html()
            self.wfile.write(html_content.encode('utf-8'))
            return
            
        # 处理BUG反馈提交
        elif self.path.startswith('/submit_feedback'):
            self.handle_feedback_submission()
            return
        
        elif self.path == '/update_info.json':
            # 尝试提供更新信息文件
            if os.path.exists('update_info.json'):
                self.path = '/update_info.json'
            elif os.path.exists('test_update_info.json'):
                self.path = '/test_update_info.json'
            else:
                # 动态生成更新信息文件
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                
                # 获取最新的可执行文件信息
                latest_version = "1.1.0"
                exe_size = 0
                
                # 查找最新的可执行文件
                exe_paths = [
                    os.path.join('dist', 'FBA费用计算器.exe'),
                    'FBA费用计算器.exe'
                ]
                
                for exe_path in exe_paths:
                    if os.path.exists(exe_path):
                        try:
                            exe_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
                            # 尝试从fba_gui.py中获取版本号
                            try:
                                import re
                                with open('fba_gui.py', 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
                                    if match:
                                        latest_version = match.group(1)
                            except:
                                pass
                        except:
                            pass
                        break
                
                # 获取本地IP地址
                import socket
                try:
                    local_ip = socket.gethostbyname(socket.gethostname())
                except:
                    local_ip = '127.0.0.1'
                
                # 获取当前服务器端口
                current_port = self.server.server_address[1]
                
                update_info = {
                    "version": latest_version,
                    "download_url": f"http://{local_ip}:{current_port}/downloads/FBA费用计算器.exe",
                    "release_notes": "本地服务器提供的最新版本更新",
                    "file_size_mb": f"{exe_size:.2f} MB",
                    "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                import json
                self.wfile.write(json.dumps(update_info, ensure_ascii=False).encode('utf-8'))
                return
        
        # 对于可执行文件请求的特殊处理
        elif self.path.endswith('.exe') or self.path.startswith('/downloads/'):
            # 提取文件名
            if self.path.startswith('/downloads/'):
                filename = self.path[len('/downloads/'):]
            else:
                filename = os.path.basename(self.path)
            
            # 尝试从多个位置查找文件，增加更多可能的路径
            possible_paths = [
                os.path.join('downloads', filename),
                os.path.join('dist', filename),
                os.path.join('FBA', 'downloads', filename),
                os.path.join('FBA', 'dist', filename),
                os.path.join('FBA', filename),
                filename
            ]
            
            found_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    found_path = path
                    break
            
            if found_path:
                # 对于大文件，使用优化的传输方式
                if filename.lower().endswith('.exe') and os.path.getsize(found_path) > 1024 * 1024:  # 大于1MB的文件
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(os.path.getsize(found_path)))
                    # 添加缓存控制头
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('Expires', '0')
                    self.end_headers()
                    
                    # 使用缓冲区分块发送大文件以提高速度
                    buffer_size = 8192
                    try:
                        with open(found_path, 'rb') as f:
                            while True:
                                data = f.read(buffer_size)
                                if not data:
                                    break
                                self.wfile.write(data)
                        return
                    except Exception as e:
                        print(f"发送文件时出错: {e}")
                        self.send_error(500, f"文件发送失败: {str(e)}")
                        return
                else:
                    # 小文件使用默认处理
                    self.path = '/' + os.path.relpath(found_path, os.getcwd()).replace('\\', '/')
        
        # 使用默认处理方法
        super().do_GET()
    
    def do_POST(self):
        """处理POST请求，用于BUG反馈提交，支持跨域请求"""
        # 设置CORS头，允许所有域的POST请求
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        # 处理反馈提交 - 允许从根路径和submit_feedback路径提交
        if self.path == '/' or self.path == '/index.html' or self.path == '/submit_feedback':
            self.handle_feedback_submission()
        else:
            self.send_response(404)
            self.end_headers()
    
    def generate_main_html(self, client_ip, port=None):
        """生成主HTML页面，根据客户端IP决定是否显示BUG收集箱"""
        # 获取当前服务器端口
        if port is None:
            port = self.server.server_address[1]
        
        # 检查是否是本地访问
        is_local = self.is_localhost()
        
        # 根据是否本地访问决定是否显示BUG收集箱和反馈收纳箱链接
        admin_tools_section = ''
        if is_local:
            admin_tools_section = '''
            <div class="container">
                <h2>管理员工具</h2>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 250px; background: #f7fafc; padding: 20px; border-radius: 8px;">
                        <h3>BUG收集箱</h3>
                        <p>提交新的反馈或问题报告。</p>
                        <a href="/feedback.html" class="feedback-button">提交反馈</a>
                    </div>
                    <div style="flex: 1; min-width: 250px; background: #f7fafc; padding: 20px; border-radius: 8px;">
                        <h3>意见反馈收纳箱</h3>
                        <p>查看用户提交的所有反馈内容。</p>
                        <a href="/feedback_box.html" class="feedback-button" style="background: #805ad5; margin-top: 20px;">查看反馈</a>
                    </div>
                </div>
            </div>
            '''
        
        # 获取本地IP地址用于显示
        import socket
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except:
            local_ip = '127.0.0.1'
        
        # 添加IP信息部分
        ip_info_section = f'''
            <div class="container">
                <h2>服务器信息</h2>
                <div class="ip-info">
                    <p><strong>本地访问地址:</strong> <a href="http://localhost:{port}" target="_blank">http://localhost:{port}</a></p>
                    <p><strong>网络访问地址:</strong> <a href="http://{local_ip}:{port}" target="_blank">http://{local_ip}:{port}</a></p>
                    <p><strong>客户端IP:</strong> {client_ip}</p>
                    <p><strong>访问类型:</strong> {'本地' if is_local else '远程'}</p>
                    <p><strong>重要:</strong> 请确保防火墙已允许端口{port}的访问</p>
                </div>
            </div>
        '''
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FBA费用计算器 - 更新服务器</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .ip-info {{
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    font-size: 14px;
                    color: #666;
                    margin-top: 10px;
                }}
                header {{
                    text-align: center;
                    padding: 30px 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: -20px -20px 30px -20px;
                }}
                h1 {{
                    margin: 0;
                    font-size: 2.5em;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 30px;
                    margin-bottom: 20px;
                }}
                h2 {{
                    color: #4a5568;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                }}
                .feature {{
                    background: #f7fafc;
                    border-left: 4px solid #667eea;
                    padding: 15px;
                    margin: 15px 0;
                }}
                .version {{
                    margin: 10px 0;
                    padding: 10px;
                    border: 1px solid #e2e8f0;
                    border-radius: 5px;
                }}
                .stable {{
                    background: #e6fffa;
                    border-color: #38b2ac;
                }}
                .stable::after {{
                    content: "[稳定版本]";
                    color: #38b2ac;
                    font-weight: bold;
                    margin-left: 10px;
                }}
                .feedback-button {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-weight: bold;
                    margin-top: 20px;
                }}
                .feedback-button:hover {{
                    background: #5a67d8;
                }}
                .download-section {{
                    text-align: center;
                    padding: 20px;
                    background: #f0f4ff;
                    border-radius: 8px;
                }}
                .download-link {{
                    display: inline-block;
                    background: #3182ce;
                    color: white;
                    padding: 15px 30px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-weight: bold;
                    font-size: 1.2em;
                }}
                .download-link:hover {{
                    background: #2c5282;
                }}
            </style>
        </head>
        <body>
            <header>
                <h1>FBA费用计算器</h1>
                <p>亚马逊卖家必备的费用计算工具</p>
            </header>
            
            <div class="container">
                <h2>功能介绍</h2>
                <div class="feature">
                    <h3>精确费用计算</h3>
                    <p>根据产品尺寸、重量和类别，准确计算FBA费用、佣金和净利润。</p>
                </div>
                <div class="feature">
                    <h3>数据分析</h3>
                    <p>提供销售数据分析和趋势预测，帮助优化定价策略。</p>
                </div>
                <div class="feature">
                    <h3>批量处理</h3>
                    <p>支持批量导入产品信息，一次性计算多个产品的费用。</p>
                </div>
                <div class="feature">
                    <h3>本地更新</h3>
                    <p>通过本地服务器实现无缝更新，无需额外的网络配置。</p>
                </div>
            </div>
            
            {ip_info_section}
            
            <div class="container">
                <h2>历史版本</h2>
                <div class="version stable">
                    <strong>版本 1.1.0</strong> - 2024年最新版本
                    <ul>
                        <li>优化安装程序布局，修复按钮显示问题</li>
                        <li>改进更新机制，支持本地快速更新</li>
                        <li>增强用户界面响应速度</li>
                        <li>修复已知bug</li>
                    </ul>
                </div>
                <div class="version">
                    <strong>版本 1.0.4</strong> - 2023年12月
                    <ul>
                        <li>添加新的费用计算模板</li>
                        <li>更新FBA费用标准</li>
                        <li>改进数据导入功能</li>
                    </ul>
                </div>
                <div class="version">
                    <strong>版本 1.0.0</strong> - 2023年10月
                    <ul>
                        <li>首次发布</li>
                        <li>基础FBA费用计算功能</li>
                        <li>简单的产品管理</li>
                    </ul>
                </div>
            </div>
            
            <div class="container">
                <h2>获取最新版本</h2>
                <div class="download-section">
                    <p>点击下方按钮下载最新版本的FBA费用计算器</p>
                    <a href="/downloads/FBA费用计算器.exe" class="download-link">立即下载</a>
                </div>
            </div>
            
            {admin_tools_section}
            
            <footer>
                <p style="text-align: center; margin-top: 30px; color: #666;">© 2024 FBA费用计算器 - 本地更新服务器</p>
            </footer>
        </body>
        </html>
        '''
    
    def generate_feedback_html(self):
        """生成BUG收集箱HTML页面"""
        return '''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FBA费用计算器 - BUG收集箱</title>
            <style>
                body {
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                header {
                    text-align: center;
                    padding: 20px 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: -20px -20px 30px -20px;
                }
                h1 {
                    margin: 0;
                    font-size: 2em;
                }
                .container {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 30px;
                }
                form {
                    display: flex;
                    flex-direction: column;
                }
                label {
                    margin: 10px 0 5px;
                    font-weight: bold;
                }
                input, select, textarea {
                    padding: 10px;
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 16px;
                }
                textarea {
                    height: 200px;
                    resize: vertical;
                }
                .submit-button {
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 20px;
                }
                .submit-button:hover {
                    background: #5a67d8;
                }
                .back-link {
                    display: inline-block;
                    margin-top: 20px;
                    color: #667eea;
                    text-decoration: none;
                }
                .back-link:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <header>
                <h1>BUG收集箱</h1>
            </header>
            
            <div class="container">
                <form action="/submit_feedback" method="post">
                    <div>
                        <label for="name">您的称呼：</label>
                        <input type="text" id="name" name="name" placeholder="请输入您的称呼（选填）" />
                    </div>
                    
                    <div>
                        <label for="email">联系方式：</label>
                        <input type="text" id="email" name="email" placeholder="请输入邮箱或其他联系方式（选填）" />
                    </div>
                    
                    <div>
                        <label for="version">软件版本：</label>
                        <input type="text" id="version" name="version" placeholder="请输入您使用的软件版本号" required />
                    </div>
                    
                    <div>
                        <label for="type">反馈类型：</label>
                        <select id="type" name="type" required>
                            <option value="">请选择反馈类型</option>
                            <option value="bug">功能异常/BUG</option>
                            <option value="suggestion">功能建议</option>
                            <option value="question">使用问题</option>
                            <option value="other">其他</option>
                        </select>
                    </div>
                    
                    <div>
                        <label for="description">问题描述：</label>
                        <textarea id="description" name="description" placeholder="请详细描述您遇到的问题或建议..." required></textarea>
                    </div>
                    
                    <div>
                        <label for="steps">复现步骤：</label>
                        <textarea id="steps" name="steps" placeholder="请描述如何复现这个问题（如果适用）"></textarea>
                    </div>
                    
                    <button type="submit" class="submit-button">提交反馈</button>
                </form>
                
                <a href="/" class="back-link">返回首页</a>
            </div>
        </body>
        </html>
        '''
    
    def handle_feedback_submission(self):
        """处理BUG反馈提交，支持跨域请求"""
        try:
            # 获取表单数据长度
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # 解析表单数据
            from urllib.parse import parse_qs
            form_data = parse_qs(post_data)
            
            # 提取表单数据
            name = form_data.get('name', [''])[0]
            email = form_data.get('email', [''])[0]
            version = form_data.get('version', [''])[0]
            feedback_type = form_data.get('type', [''])[0]
            description = form_data.get('description', [''])[0]
            steps = form_data.get('steps', [''])[0]
            source = form_data.get('source', ['local'])[0]  # 添加来源标识
            
            # 保存反馈到文件
            feedback_dir = 'feedback'
            if not os.path.exists(feedback_dir):
                os.makedirs(feedback_dir)
            
            feedback_filename = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            feedback_path = os.path.join(feedback_dir, feedback_filename)
            
            with open(feedback_path, 'w', encoding='utf-8') as f:
                f.write(f"反馈时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"反馈人: {name}\n")
                f.write(f"联系方式: {email}\n")
                f.write(f"软件版本: {version}\n")
                f.write(f"反馈类型: {feedback_type}\n")
                f.write(f"问题描述: {description}\n")
                f.write(f"复现步骤: {steps}\n")
                f.write(f"反馈来源: {source}\n")  # 添加来源信息
            
            # 发送成功响应，设置CORS头
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            success_html = '''
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>反馈提交成功</title>
                <style>
                    body {
                        font-family: 'Microsoft YaHei', Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background-color: #f5f5f5;
                    }
                    .success-container {
                        text-align: center;
                        padding: 40px;
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        max-width: 500px;
                    }
                    h1 {
                        color: #4caf50;
                    }
                    .back-button {
                        display: inline-block;
                        background: #667eea;
                        color: white;
                        padding: 12px 24px;
                        border-radius: 5px;
                        text-decoration: none;
                        font-weight: bold;
                        margin-top: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="success-container">
                    <h1>反馈提交成功！</h1>
                    <p>感谢您的反馈，我们会认真处理并持续改进产品。</p>
                    <a href="/" class="back-button">返回首页</a>
                </div>
            </body>
            </html>
            '''
            
            self.wfile.write(success_html.encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_html = f"<h1>提交失败</h1><p>处理反馈时发生错误: {str(e)}</p><a href='/feedback.html'>返回</a>"
            self.wfile.write(error_html.encode('utf-8'))
    
    def generate_feedback_box_html(self):
        """生成意见反馈收纳箱HTML页面，用于查看所有用户反馈"""
        feedback_items = []
        feedback_dir = 'feedback'
        
        if os.path.exists(feedback_dir):
            # 获取所有反馈文件并按时间倒序排列
            import glob
            feedback_files = glob.glob(os.path.join(feedback_dir, 'feedback_*.txt'))
            feedback_files.sort(reverse=True)  # 按文件名倒序，即时间倒序
            
            for feedback_file in feedback_files:
                try:
                    with open(feedback_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取反馈信息
                    feedback_info = {}
                    for line in content.split('\n'):
                        if ': ' in line:
                            key, value = line.split(': ', 1)
                            feedback_info[key] = value.strip()
                    
                    # 生成反馈项HTML
                    item_html = f'''
                    <div class="feedback-item">
                        <div class="feedback-header">
                            <span class="feedback-time">{feedback_info.get('反馈时间', '')}</span>
                            <span class="feedback-type">{feedback_info.get('反馈类型', '')}</span>
                            <span class="feedback-source">{feedback_info.get('反馈来源', '本地')}</span>
                        </div>
                        <div class="feedback-content">
                            <p><strong>反馈人:</strong> {feedback_info.get('反馈人', '匿名')}</p>
                            <p><strong>联系方式:</strong> {feedback_info.get('联系方式', '无')}</p>
                            <p><strong>软件版本:</strong> {feedback_info.get('软件版本', '未知')}</p>
                            <p><strong>问题描述:</strong></p>
                            <div class="description">{feedback_info.get('问题描述', '')}</div>
                            <p><strong>复现步骤:</strong></p>
                            <div class="steps">{feedback_info.get('复现步骤', '无')}</div>
                        </div>
                    </div>
                    '''
                    feedback_items.append(item_html)
                except Exception as e:
                    error_item = f'''
                    <div class="feedback-item error">
                        <p>无法读取反馈文件: {os.path.basename(feedback_file)}</p>
                        <p>错误: {str(e)}</p>
                    </div>
                    '''
                    feedback_items.append(error_item)
        
        feedback_list = '\n'.join(feedback_items) if feedback_items else '<div class="no-feedback">暂无反馈信息</div>'
        
        return f'''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>意见反馈收纳箱 - FBA费用计算器</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                header {{
                    text-align: center;
                    padding: 20px 0;
                    background: linear-gradient(135deg, #805ad5 0%, #6b46c1 100%);
                    color: white;
                    margin: -20px -20px 30px -20px;
                }}
                h1 {{
                    margin: 0;
                    font-size: 2em;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 30px;
                }}
                .feedback-item {{
                    background: #f7fafc;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-left: 4px solid #805ad5;
                }}
                .feedback-item.error {{
                    border-left-color: #e53e3e;
                    background: #fed7d7;
                }}
                .feedback-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .feedback-time {{
                    font-weight: bold;
                    color: #4a5568;
                }}
                .feedback-type {{
                    background: #805ad5;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                }}
                .feedback-source {{
                    background: #3182ce;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                }}
                .feedback-content p {{
                    margin: 10px 0;
                }}
                .description, .steps {{
                    background: white;
                    padding: 15px;
                    border-radius: 4px;
                    border: 1px solid #e2e8f0;
                    white-space: pre-wrap;
                    word-break: break-word;
                }}
                .no-feedback {{
                    text-align: center;
                    padding: 40px;
                    color: #718096;
                    font-style: italic;
                }}
                .back-link {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-weight: bold;
                    margin-top: 20px;
                }}
                .back-link:hover {{
                    background: #5a67d8;
                }}
                .refresh-button {{
                    background: #3182ce;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-top: 20px;
                }}
                .refresh-button:hover {{
                    background: #2c5282;
                }}
            </style>
        </head>
        <body>
            <header>
                <h1>意见反馈收纳箱</h1>
            </header>
            
            <div class="container">
                <h2>用户反馈列表</h2>
                <p>以下是所有用户提交的反馈信息，按时间倒序排列。</p>
                
                <div class="feedback-list">
                    {feedback_list}
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <button class="refresh-button" onclick="location.reload()">刷新反馈列表</button>
                    <a href="/" class="back-link">返回首页</a>
                </div>
            </div>
        </body>
        </html>
        '''

def ensure_required_files():
    """确保必要的文件存在"""
    # 确保dist目录存在
    if not os.path.exists('dist'):
        try:
            os.makedirs('dist')
            print("创建dist目录成功")
        except Exception as e:
            print(f"创建dist目录失败: {str(e)}")
    
    # 确保downloads目录存在
    if not os.path.exists('downloads'):
        try:
            os.makedirs('downloads')
            print("创建downloads目录成功")
        except Exception as e:
            print(f"创建downloads目录失败: {str(e)}")
    
    # 确保feedback目录存在
    if not os.path.exists('feedback'):
        try:
            os.makedirs('feedback')
            print("创建feedback目录成功")
        except Exception as e:
            print(f"创建feedback目录失败: {str(e)}")
    
    # 确保更新信息文件存在
    if not os.path.exists('update_info.json'):
        try:
            import json
            # 创建默认更新信息，使用本地地址
            import socket
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except:
                local_ip = '127.0.0.1'
            
            default_update_info = {
                "version": "1.1.0",
                "download_url": f"http://{local_ip}:{PORT}/downloads/FBA费用计算器.exe",
                "release_notes": "这是默认的更新信息，用于本地更新测试",
                "file_size_mb": "0.00 MB",
                "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open('update_info.json', 'w', encoding='utf-8') as f:
                json.dump(default_update_info, f, ensure_ascii=False, indent=4)
            print("创建默认更新信息文件成功")
        except Exception as e:
            print(f"创建更新信息文件失败: {str(e)}")
    
    # 复制可执行文件到必要位置
    exe_source = None
    exe_paths = [
        os.path.join('dist', 'FBA费用计算器.exe'),
        'FBA费用计算器.exe'
    ]
    
    for path in exe_paths:
        if os.path.exists(path):
            exe_source = path
            break
    
    if exe_source:
        # 确保在downloads目录中有一份副本
        import shutil
        try:
            target_path = os.path.join('downloads', 'FBA费用计算器.exe')
            if not os.path.exists(target_path) or os.path.getmtime(exe_source) > os.path.getmtime(target_path):
                shutil.copy2(exe_source, target_path)
                print(f"复制可执行文件到downloads目录成功")
        except Exception as e:
            print(f"复制可执行文件失败: {str(e)}")

def find_certificate_files():
    """查找可用的证书文件"""
    global CERT_FILE, KEY_FILE
    
    # 首先尝试从配置文件读取证书路径
    cert_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cert_config.txt")
    
    # 尝试读取配置文件
    if os.path.exists(cert_config_file):
        try:
            with open(cert_config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('cert_path='):
                        cert_path = line[10:]
                        # 验证证书路径是否有效
                        if os.path.exists(cert_path):
                            CERT_FILE = cert_path
                            print(f"使用配置文件中的证书路径: {CERT_FILE}")
                    elif line.startswith('key_path='):
                        key_path = line[9:]
                        # 验证私钥路径是否有效
                        if os.path.exists(key_path):
                            KEY_FILE = key_path
                            print(f"使用配置文件中的私钥路径: {KEY_FILE}")
            
            # 如果从配置文件中成功读取并验证了证书和私钥路径，直接返回
            if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
                return True
        except Exception as e:
            print(f"读取证书配置文件出错: {e}")
    
    # 如果配置文件不存在或无效，使用默认证书路径
    # 确保SSL目录存在
    if not os.path.exists(SSL_DIR):
        os.makedirs(SSL_DIR, exist_ok=True)
    
    # 检查默认证书文件
    if os.path.exists(CERT_FILE):
        print(f"找到默认证书: {CERT_FILE}")
    else:
        # 尝试查找备选证书文件
        found = False
        for cert_name in ALT_CERT_NAMES:
            cert_path = os.path.join(SSL_DIR, cert_name)
            if os.path.exists(cert_path):
                CERT_FILE = cert_path
                print(f"找到备选证书: {CERT_FILE}")
                found = True
                break
        if not found:
            print(f"未找到证书文件，默认使用: {CERT_FILE}")
    
    # 检查默认私钥文件
    if os.path.exists(KEY_FILE):
        print(f"找到默认私钥: {KEY_FILE}")
    else:
        # 尝试查找备选私钥文件
        found = False
        for key_name in ALT_KEY_NAMES:
            key_path = os.path.join(SSL_DIR, key_name)
            if os.path.exists(key_path):
                KEY_FILE = key_path
                print(f"找到备选私钥: {KEY_FILE}")
                found = True
                break
        if not found:
            print(f"未找到私钥文件，默认使用: {KEY_FILE}")
    
    return os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)

def start_server_with_mode(use_https=False):
    """根据指定模式启动服务器"""
    try:
        # 确保必要的文件存在
        ensure_required_files()
        
        # 确定服务器配置
        current_use_https = use_https
        if current_use_https:
            port = HTTPS_PORT
            scheme = "https"
            
            # 查找SSL证书文件
            print("正在查找SSL证书文件...")
            certificates_found = find_certificate_files()
            
            # 检查SSL证书是否存在
            if not certificates_found:
                print("警告: 未找到SSL证书文件")
                print(f"证书位置: {SSL_DIR}")
                print("请将证书文件放在SSL目录中，支持以下文件名：")
                print(f"证书: {', '.join(['server.crt'] + ALT_CERT_NAMES)}")
                print(f"私钥: {', '.join(['server.key'] + ALT_KEY_NAMES)}")
                print("自动切换到HTTP模式...")
                current_use_https = False
                port = PORT
                scheme = "http"
        else:
            port = PORT
            scheme = "http"
        
        # 获取本地IP地址
        import socket
        local_ip = socket.gethostbyname(socket.gethostname())
        
        # 创建服务器，绑定到所有网络接口
        server_address = ('', port)
        # 设置允许地址重用
        socketserver.TCPServer.allow_reuse_address = True
        Handler = CustomHTTPRequestHandler
        
        # 增加缓冲区大小以提高传输速度
        with socketserver.TCPServer(server_address, Handler) as httpd:
            httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            
            # 如果使用HTTPS，配置SSL上下文
            if current_use_https:
                try:
                    print(f"正在加载SSL证书: {CERT_FILE}")
                    print(f"正在加载私钥: {KEY_FILE}")
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
                    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
                    print("SSL配置成功！")
                except Exception as e:
                    print(f"SSL配置错误: {str(e)}")
                    print("请检查证书文件是否正确，或尝试使用其他证书文件")
                    print("切换到HTTP模式...")
                    current_use_https = False
                    scheme = "http"
                    # 重新创建服务器
                    httpd = socketserver.TCPServer(server_address, Handler)
            
            # 显示启动信息
            print("=" * 60)
            print("FBA费用计算器更新服务器启动中...")
            print(f"服务地址: {scheme}://localhost:{port}")
            print(f"本地IP访问: {scheme}://{local_ip}:{port}")
            print(f"更新信息: {scheme}://localhost:{port}/update_info.json")
            print(f"可执行文件: {scheme}://localhost:{port}/downloads/FBA费用计算器.exe")
            print("=" * 60)
            print("重要提示:")
            print(f"1. 请确保Windows防火墙允许端口{port}的访问")
            print(f"2. 外部用户需要使用您的IP地址访问: {scheme}://{local_ip}:{port}")
            print("3. 如有访问问题，请检查网络配置和防火墙设置")
            print("=" * 60)
            print("按 Ctrl+C 停止服务器")
            print("=" * 60)
            
            # 启动服务器
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n更新服务器已停止")
            except Exception as e:
                print(f"\n服务器错误: {str(e)}")
    except Exception as e:
        print(f"启动服务器时发生错误: {str(e)}")

def start_server():
    """启动HTTP/HTTPS服务器"""
    # 启动服务器
    start_server_with_mode(USE_HTTPS)

def start_in_background():
    """在后台启动服务器"""
    # 直接在当前窗口启动服务器，避免创建批处理文件的权限问题
    try:
        print("正在启动更新服务器...")
        # 直接返回True，表示启动成功
        return True
    except Exception as e:
        print(f"启动服务器失败: {str(e)}")
        return False

def check_port_in_use(port):
    """检查端口是否被占用，优化性能"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # 设置超时以加快检查速度
        s.settimeout(0.1)
        try:
            # 绑定到所有网络接口以检查端口
            return s.connect_ex(('', port)) == 0
        except:
            return False

def main():
    """主函数"""
    print("FBA费用计算器本地更新服务器")
    print("此服务器用于提供本地更新功能，无需网站跳转")
    
    # 检查端口是否被占用，如果被占用则尝试使用其他端口
    global PORT
    current_port = PORT
    max_attempts = 5
    for attempt in range(max_attempts):
        if not check_port_in_use(current_port):
            break
        print(f"警告: 端口 {current_port} 已被占用，尝试使用端口 {current_port + 1}")
        current_port += 1
    else:
        print(f"错误: 尝试了{max_attempts}个端口都被占用，请手动关闭占用端口的程序")
        return
    
    if current_port != PORT:
        PORT = current_port
        print(f"已切换到端口: {PORT}")
    
    # 启动服务器
    print("正在启动服务器...")
    if start_in_background():
        print(f"服务器正在启动！")
        # 获取本地IP地址
        import socket
        local_ip = socket.gethostbyname(socket.gethostname())
        print(f"您可以在浏览器中访问 http://localhost:{PORT} 或 http://{local_ip}:{PORT} 查看更新页面")
        # 尝试打开浏览器
        try:
            if USE_HTTPS:
                url = f"https://localhost:{HTTPS_PORT}"
                webbrowser.open(url)
                print(f"浏览器已自动打开: {url}")
            else:
                url = f"http://localhost:{PORT}"
                webbrowser.open(url)
                print(f"浏览器已自动打开: {url}")
        except:
            if USE_HTTPS:
                print(f"无法自动打开浏览器，请手动访问 https://localhost:{HTTPS_PORT}")
            else:
                # 获取本地IP地址
                import socket
                local_ip = socket.gethostbyname(socket.gethostname())
                print(f"无法自动打开浏览器，请手动访问 http://localhost:{PORT} 或 http://{local_ip}:{PORT}")
        
        # 启动实际的服务器代码
        start_server()
    else:
        print("启动失败，正在退出...")

if __name__ == "__main__":
    # 检查是否以管理员权限运行
    import ctypes
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    if not is_admin:
        print("警告: 建议以管理员权限运行，以便进行必要的文件操作")
        # 自动继续，不等待用户输入
    
    # 检查命令行参数
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--https":
        USE_HTTPS = True
    
    # 快速检查防火墙状态并提供提示
    print("\n重要提示:")
    print("1. 请确保Windows防火墙允许端口8081的访问")
    print("2. 外部用户需要使用您的IP地址访问: http://[您的IP]:8081")
    print("3. 如有访问问题，请检查网络配置和防火墙设置")
    
    main()