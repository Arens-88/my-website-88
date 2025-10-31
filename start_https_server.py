#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单HTTPS测试服务器
用于快速测试SSL配置和证书是否正常工作
"""

import http.server
import socketserver
import ssl
import os
import sys
import webbrowser
from datetime import datetime

# 服务器配置
PORT = 8443

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """自定义HTTP请求处理器"""
    
    def log_message(self, format, *args):
        """自定义日志记录格式"""
        log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        client_ip = self.client_address[0]
        request_line = format % args
        log_entry = f"[{log_time}] {client_ip} - {request_line}\n"
        
        print(log_entry, end='')
    
    def end_headers(self):
        """添加CORS头以支持跨域请求"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

# 创建SSL证书目录
ssl_dir = "D:\ssl_certs"
if not os.path.exists(ssl_dir):
    os.makedirs(ssl_dir)
    print(f"已创建SSL证书目录: {ssl_dir}")

# SSL证书文件路径
cert_file = os.path.join(ssl_dir, "server.crt")
key_file = os.path.join(ssl_dir, "server.key")

# 检查证书是否存在
if not os.path.exists(cert_file) or not os.path.exists(key_file):
    print("警告: 未找到SSL证书文件")
    print("请按照以下步骤生成自签名SSL证书:")
    print("1. 打开命令提示符(以管理员身份运行)")
    print("2. 执行以下命令生成自签名证书:")
    print("   openssl req -x509 -newkey rsa:4096 -nodes -keyout D:\\ssl_certs\\server.key -out D:\\ssl_certs\\server.crt -days 365 -subj \"/CN=localhost\"")
    print("   或者使用PowerShell:")
    print("   New-SelfSignedCertificate -DnsName localhost -CertStoreLocation Cert:\LocalMachine\My")
    print("3. 生成后再运行此脚本")
    print("\n注意: 您也可以跳过HTTPS配置，直接使用HTTP服务器(端口8081)")
    
    # 询问是否继续使用HTTP
    response = input("是否继续启动HTTP服务器? (y/n): ")
    if response.lower() == 'y':
        # 启动HTTP服务器作为备选
        Handler = CustomHTTPRequestHandler
        with socketserver.TCPServer(("", 8081), Handler) as httpd:
            print("\nHTTP服务器启动成功！")
            print(f"访问地址: http://localhost:8081")
            print(f"或: http://tomarens.xyz:8081")
            print("按 Ctrl+C 停止服务器")
            try:
                # 自动打开浏览器
                webbrowser.open("http://localhost:8081")
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n服务器已停止")
    sys.exit(1)

# 启动HTTPS服务器
Handler = CustomHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    # 包装SSL上下文
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    
    # 包装socket
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    print("HTTPS服务器启动成功！")
    print(f"访问地址: https://localhost:{PORT}")
    print("\n注意:")
    print("1. 使用自签名证书访问时浏览器会显示安全警告，这是正常的")
    print("2. 您可以选择继续访问(在高级选项中)")
    print("3. 对于生产环境，请使用Let's Encrypt等可信证书颁发机构的证书")
    print("4. 要使用tomarens.xyz域名，请确保hosts文件已正确配置")
    print("\n按 Ctrl+C 停止服务器")
    
    try:
        # 自动打开浏览器
        webbrowser.open(f"https://localhost:{PORT}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")