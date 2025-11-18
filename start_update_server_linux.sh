#!/bin/bash

# FBA费用计算器 - Linux版更新服务器启动脚本
# 用于在云服务器ECS上启动更新服务器

# 设置环境变量
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# 服务器配置
PORT=8081
HTTPS_PORT=8443

# SSL证书配置（Linux路径）
SSL_DIR="/etc/ssl/certs/fba"

# 创建SSL目录（如果不存在）
sudo mkdir -p $SSL_DIR
sudo chmod 755 $SSL_DIR

# 显示启动信息
echo "============================================================"
echo "FBA费用计算器更新服务器 - Linux版本"
echo "============================================================"
echo "服务地址: http://localhost:$PORT"
echo "更新信息: http://localhost:$PORT/update_info.json"
echo "可执行文件: http://localhost:$PORT/downloads/FBA费用计算器.exe"
echo "============================================================"
echo "重要提示:"
echo "1. 请确保防火墙允许端口$PORT的访问"
echo "2. 外部用户需要使用您的IP地址访问"
echo "3. 使用 Ctrl+C 停止服务器"
echo "============================================================"

# 检查端口是否被占用
check_port() {
    lsof -i:$1 > /dev/null 2>&1
    return $?
}

# 如果端口被占用，尝试其他端口
if check_port $PORT; then
    echo "警告: 端口 $PORT 已被占用，尝试使用端口 $((PORT+1))"
    PORT=$((PORT+1))
    if check_port $PORT; then
        echo "警告: 端口 $PORT 也被占用，尝试使用端口 $((PORT+1))"
        PORT=$((PORT+1))
    fi
fi

# 在后台启动Python服务器，并将输出重定向到日志文件
echo "正在启动Python服务器..."
nohup python3 -m http.server $PORT --bind 0.0.0.0 > server_output.log 2>&1 &

SERVER_PID=$!
echo "服务器进程ID: $SERVER_PID"
echo "服务器已在端口 $PORT 上启动"
echo "日志文件: server_output.log"
echo "使用 'kill $SERVER_PID' 可以停止服务器"
echo "============================================================"
