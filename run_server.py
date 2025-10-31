#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接启动更新服务器并在后台运行
"""

import subprocess
import os
import sys
import time

# 确保在正确的目录中
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("正在启动FBA费用计算器更新服务器...")

# 使用Popen启动服务器，并将输出重定向到文件
with open('server_output.log', 'w') as outfile:
    process = subprocess.Popen(
        [sys.executable, 'start_update_server.py'],
        stdout=outfile,
        stderr=outfile,
        creationflags=subprocess.CREATE_NEW_CONSOLE  # 在新窗口中运行
    )

print(f"服务器进程已启动，PID: {process.pid}")
print("服务器输出将保存到 server_output.log 文件中")
print("更新服务器应该会在新的命令提示符窗口中运行")
print("您可以查看 server_output.log 文件了解服务器是否成功启动")