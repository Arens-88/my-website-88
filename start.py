#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
亚马逊多平台数据整合报表工具 - 启动脚本

此脚本用于启动整个应用程序，包括：
1. 检查并安装所需的Python依赖
2. 初始化必要的目录结构
3. 启动后端API服务
"""

import os
import sys
import subprocess
import time
import shutil
import webbrowser
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
# 后端目录
BACKEND_DIR = PROJECT_ROOT / 'backend'
# 前端目录
FRONTEND_DIR = PROJECT_ROOT / 'frontend'
# 数据目录
DATA_DIR = PROJECT_ROOT / 'data'
# 配置目录
CONFIG_DIR = PROJECT_ROOT / 'config'
# 备份目录
BACKUP_DIR = DATA_DIR / 'backups'
# 报表目录
REPORT_DIR = DATA_DIR / 'reports'
# 日志目录
LOG_DIR = PROJECT_ROOT / 'logs'

# 必要的Python依赖
REQUIRED_PACKAGES = [
    'flask>=2.0.0',
    'flask-cors>=3.0.0',
    'sqlalchemy>=1.4.0',
    'requests>=2.25.0',
    'pandas>=1.3.0',
    'openpyxl>=3.0.0',
    'apscheduler>=3.7.0',
    'email-validator>=1.1.0',
    'python-dotenv>=0.19.0',
    'gunicorn>=20.1.0;platform_system!="Windows"'
]

def print_header():
    """打印程序头部信息"""
    header = """
    ====================================================================
                  亚马逊多平台数据整合报表工具
    ====================================================================
    功能：自动抓取亚马逊数据 → 清洗整合 → 生成报表 → 定时推送
    版本：1.0.0
    ====================================================================
    """
    print(header)

def create_directory_structure():
    """创建必要的目录结构"""
    directories = [
        DATA_DIR,
        CONFIG_DIR,
        BACKUP_DIR,
        REPORT_DIR,
        LOG_DIR,
        FRONTEND_DIR / 'static' / 'css',
        FRONTEND_DIR / 'static' / 'js',
        FRONTEND_DIR / 'static' / 'images'
    ]
    
    for directory in directories:
        if not directory.exists():
            try:
                directory.mkdir(parents=True, exist_ok=True)
                print(f"创建目录: {directory}")
            except Exception as e:
                print(f"创建目录失败 {directory}: {e}")

def check_python_version():
    """检查Python版本"""
    required_version = (3, 7)
    current_version = sys.version_info
    
    if current_version < required_version:
        print(f"错误: 需要Python {required_version[0]}.{required_version[1]} 或更高版本，当前版本是 {current_version[0]}.{current_version[1]}")
        return False
    return True

def install_dependencies():
    """安装所需的Python依赖"""
    print("检查并安装Python依赖...")
    
    try:
        # 升级pip
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
        
        # 安装依赖
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + REQUIRED_PACKAGES)
        print("依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e}")
        print("请尝试手动安装依赖:")
        for package in REQUIRED_PACKAGES:
            print(f"  pip install {package}")
        return False

def create_config_file():
    """创建默认配置文件"""
    config_file = CONFIG_DIR / 'config.env'
    if not config_file.exists():
        print("创建默认配置文件...")
        try:
            default_config = """
# 数据库配置
DATABASE_URL=sqlite:///../data/amazon_report.db

# Flask配置
FLASK_ENV=development
FLASK_APP=backend/main.py
SECRET_KEY=your-secret-key-change-in-production

# 邮件配置
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-password
SMTP_FROM=your-email@example.com
SMTP_TO=recipient@example.com
SMTP_USE_TLS=True
ENABLE_EMAIL_PUSH=False

# 企业微信配置
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=
ENABLE_WECHAT_PUSH=False

# 同步配置
SYNC_HOUR=2
SYNC_MINUTE=0
ENABLE_SCHEDULER=True

# 备份配置
BACKUP_DAYS_TO_KEEP=30
ENABLE_AUTO_BACKUP=True

# API配置
API_TIMEOUT=30
MAX_RETRY=3
RETRY_DELAY=5
            """
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(default_config.strip())
            print(f"配置文件已创建: {config_file}")
        except Exception as e:
            print(f"创建配置文件失败: {e}")

def create_requirements_file():
    """创建requirements.txt文件"""
    requirements_file = PROJECT_ROOT / 'requirements.txt'
    if not requirements_file.exists():
        print("创建requirements.txt文件...")
        try:
            with open(requirements_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(REQUIRED_PACKAGES))
            print(f"requirements.txt已创建: {requirements_file}")
        except Exception as e:
            print(f"创建requirements.txt失败: {e}")

def start_backend_server():
    """启动后端API服务"""
    print("启动后端API服务...")
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        # 检查是否在Windows系统
        if os.name == 'nt':  # Windows
            print("在Windows系统上启动Flask开发服务器...")
            # 使用Flask开发服务器
            cmd = [sys.executable, str(BACKEND_DIR / 'main.py')]
            backend_process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务启动
            time.sleep(3)
            
            # 检查进程是否仍在运行
            if backend_process.poll() is not None:
                print("后端服务启动失败!")
                # 输出错误信息
                stdout, stderr = backend_process.communicate()
                if stdout:
                    print("STDOUT:", stdout)
                if stderr:
                    print("STDERR:", stderr)
                return False
        else:  # Linux/Mac
            print("在Unix系统上启动Gunicorn服务器...")
            # 使用Gunicorn
            cmd = ['gunicorn', '-w', '4', '-b', '127.0.0.1:5000', 'backend.main:app']
            backend_process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务启动
            time.sleep(5)
        
        print("后端API服务已启动在 http://127.0.0.1:5000")
        return True
    except Exception as e:
        print(f"启动后端服务失败: {e}")
        return False

def open_browser():
    """打开浏览器访问前端界面"""
    try:
        frontend_url = "http://127.0.0.1:5000"
        print(f"正在打开浏览器访问前端界面: {frontend_url}")
        webbrowser.open(frontend_url)
    except Exception as e:
        print(f"无法打开浏览器: {e}")
        print(f"请手动访问: http://127.0.0.1:5000")

def print_usage():
    """打印使用说明"""
    usage = """
    使用说明:
    1. 首次运行时，脚本会自动安装所需依赖并创建必要的目录结构
    2. 请根据需要修改 config/config.env 文件中的配置
    3. 浏览器将自动打开前端界面，默认访问地址: http://127.0.0.1:5000
    4. 默认登录账号: admin / password
    
    注意事项:
    - 确保Python版本 >= 3.7
    - 确保80端口未被占用
    - 首次使用时请配置亚马逊API凭证
    """
    print(usage)

def main():
    """主函数"""
    print_header()
    
    # 检查Python版本
    if not check_python_version():
        return 1
    
    # 创建目录结构
    create_directory_structure()
    
    # 创建配置文件
    create_config_file()
    
    # 创建requirements.txt
    create_requirements_file()
    
    # 安装依赖
    if not install_dependencies():
        print("依赖安装失败，程序可能无法正常运行")
    
    # 启动后端服务
    if start_backend_server():
        print_usage()
        # 打开浏览器
        open_browser()
        
        print("\n程序已成功启动!")
        print("按 Ctrl+C 停止服务")
        
        try:
            # 保持程序运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止服务...")
    else:
        print("启动失败，请检查错误信息并尝试解决问题")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())