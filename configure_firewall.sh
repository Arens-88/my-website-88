#!/bin/bash

# FBA费用计算器 - 防火墙配置脚本
# 适用于Ubuntu (ufw) 和 CentOS (firewalld)

echo "========================================"
echo "FBA费用计算器 - 防火墙配置"
echo "========================================"

# 检测操作系统
echo "正在检测操作系统..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo "警告：无法检测操作系统"
    exit 1
fi

# 配置Ubuntu的ufw防火墙
if [[ "$OS" == *"Ubuntu"* ]]; then
    echo "检测到Ubuntu系统，使用ufw配置防火墙"
    
    # 检查ufw是否已安装
    if ! command -v ufw &> /dev/null; then
        echo "安装ufw..."
        sudo apt-get update
        sudo apt-get install -y ufw
    fi
    
    # 允许SSH连接
    echo "允许SSH连接（端口22）"
    sudo ufw allow 22/tcp
    
    # 允许HTTP连接
    echo "允许HTTP连接（端口80）"
    sudo ufw allow 80/tcp
    
    # 允许HTTPS连接
    echo "允许HTTPS连接（端口443）"
    sudo ufw allow 443/tcp
    
    # 允许Python服务器端口
    echo "允许Python服务器连接（端口8081）"
    sudo ufw allow 8081/tcp
    
    # 启用防火墙
    echo "启用防火墙..."
    sudo ufw --force enable
    
    # 显示状态
    echo "防火墙配置完成，当前状态："
    sudo ufw status

# 配置CentOS的firewalld防火墙
elif [[ "$OS" == *"CentOS"* || "$OS" == *"Red Hat"* ]]; then
    echo "检测到CentOS/Red Hat系统，使用firewalld配置防火墙"
    
    # 检查firewalld是否已安装
    if ! command -v firewall-cmd &> /dev/null; then
        echo "安装firewalld..."
        sudo yum install -y firewalld
    fi
    
    # 启动并启用firewalld服务
    sudo systemctl start firewalld
    sudo systemctl enable firewalld
    
    # 允许SSH连接
    echo "允许SSH连接（端口22）"
    sudo firewall-cmd --permanent --add-service=ssh
    
    # 允许HTTP连接
    echo "允许HTTP连接（端口80）"
    sudo firewall-cmd --permanent --add-service=http
    
    # 允许HTTPS连接
    echo "允许HTTPS连接（端口443）"
    sudo firewall-cmd --permanent --add-service=https
    
    # 允许Python服务器端口
    echo "允许Python服务器连接（端口8081）"
    sudo firewall-cmd --permanent --add-port=8081/tcp
    
    # 重新加载防火墙规则
    echo "重新加载防火墙规则..."
    sudo firewall-cmd --reload
    
    # 显示状态
    echo "防火墙配置完成，当前状态："
    sudo firewall-cmd --list-all

# 未知操作系统
else
    echo "不支持的操作系统：$OS"
    echo "请手动配置防火墙，确保以下端口可用："
    echo "- 22 (SSH)"
    echo "- 80 (HTTP)"
    echo "- 443 (HTTPS)"
    echo "- 8081 (Python服务器)"
    exit 1
fi

echo "========================================"
echo "防火墙配置脚本执行完成"
echo "========================================"
