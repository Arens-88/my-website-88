#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单启动更新服务器的脚本
支持HTTP和HTTPS模式
"""

import subprocess
import os
import sys
import time

# 确保在正确的目录中
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 检查命令行参数，确定启动模式
use_https = False
if len(sys.argv) > 1 and sys.argv[1] == "--https":
    use_https = True

print("正在启动FBA费用计算器更新服务器...")

# 构建启动命令
if use_https:
    command = [sys.executable, "start_update_server.py", "--https"]
    print("模式: HTTPS (需要SSL证书)")
else:
    command = [sys.executable, "start_update_server.py"]
    print("模式: HTTP (默认)")

# 使用最简单的方式启动服务器，不捕获输出
import subprocess
process = subprocess.Popen(
    command,
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print("服务器启动命令已执行")
print("请检查是否有新的命令窗口打开")

# 获取本地IP地址
import socket
try:
    local_ip = socket.gethostbyname(socket.gethostname())
    if use_https:
        print(f"如果服务器成功启动，您可以访问 https://localhost:8443 或 https://{local_ip}:8443")
        print("注意: 使用HTTPS需要在D:\ssl_certs目录下有有效的SSL证书")
    else:
        print(f"如果服务器成功启动，您可以访问 http://localhost:8081 或 http://{local_ip}:8081")
        print("提示: 要使用HTTPS，请运行: python launch_server.py --https")
except Exception as e:
    if use_https:
        print("如果服务器成功启动，您可以访问 https://localhost:8443")
        print("注意: 使用HTTPS需要在D:\ssl_certs目录下有有效的SSL证书")
    else:
        print("如果服务器成功启动，您可以访问 http://localhost:8081")
        print("提示: 要使用HTTPS，请运行: python launch_server.py --https")

print("脚本执行完毕")

# 提供快速帮助信息
time.sleep(1)
print("快速指南:")
print("1. HTTP模式可直接使用，无需额外配置")
print("2. HTTPS模式需要SSL证书，请参考SSL证书配置指南.md")
print("3. 证书默认存放位置: D:\ssl_certs")
print("4. 您可以使用start_https_server.py进行简单的HTTPS测试")
print("\n重要提示:")
print("- 请确保Windows防火墙允许端口8081的访问")
print("- 外部用户需要使用您的IP地址访问: http://[您的IP]:8081")
print("- 如有访问问题，请检查网络配置和防火墙设置")