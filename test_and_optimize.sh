#!/bin/bash

# FBA费用计算器 - 测试和性能调优脚本
# 用于验证网站状态、检查端口占用和优化服务器性能

echo "========================================"
echo "FBA费用计算器 - 测试和性能调优工具"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查端口占用情况
check_ports() {
    echo -e "\n${YELLOW}检查端口占用情况...${NC}"
    
    # 检查80端口 (HTTP)
    if lsof -i:80 > /dev/null 2>&1; then
        echo -e "端口 80 (HTTP): ${GREEN}已占用${NC}"
        echo -e "进程信息:"
        lsof -i:80 | grep LISTEN
    else
        echo -e "端口 80 (HTTP): ${RED}未被占用${NC}"
    fi
    
    # 检查443端口 (HTTPS)
    if lsof -i:443 > /dev/null 2>&1; then
        echo -e "端口 443 (HTTPS): ${GREEN}已占用${NC}"
        echo -e "进程信息:"
        lsof -i:443 | grep LISTEN
    else
        echo -e "端口 443 (HTTPS): ${RED}未被占用${NC}"
    fi
    
    # 检查8081端口 (Python服务器)
    if lsof -i:8081 > /dev/null 2>&1; then
        echo -e "端口 8081 (Python服务器): ${GREEN}已占用${NC}"
        echo -e "进程信息:"
        lsof -i:8081 | grep LISTEN
    else
        echo -e "端口 8081 (Python服务器): ${RED}未被占用${NC}"
    fi
}

# 检查服务状态
check_services() {
    echo -e "\n${YELLOW}检查服务状态...${NC}"
    
    # 检查Nginx服务
    if command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet nginx; then
            echo -e "Nginx服务: ${GREEN}运行中${NC}"
        else
            echo -e "Nginx服务: ${RED}未运行${NC}"
        fi
        
        # 检查自定义FBA服务
        if systemctl is-active --quiet fba-update.service 2>/dev/null; then
            echo -e "FBA更新服务器: ${GREEN}运行中${NC}"
        else
            echo -e "FBA更新服务器: ${RED}未运行（系统服务未找到或未激活）${NC}"
        fi
    else
        echo -e "系统使用init.d，检查服务..."
        # 检查Nginx
        if service nginx status > /dev/null 2>&1; then
            echo -e "Nginx服务: ${GREEN}运行中${NC}"
        else
            echo -e "Nginx服务: ${RED}未运行${NC}"
        fi
    fi
    
    # 检查Python进程
    echo -e "Python服务器进程:"
    if pgrep -f "python.*8081" > /dev/null; then
        echo -e "${GREEN}运行中${NC}"
        ps aux | grep "python.*8081" | grep -v grep
    else
        echo -e "${RED}未找到Python服务器进程${NC}"
    fi
}

# 检查网站访问
check_website() {
    echo -e "\n${YELLOW}检查网站访问状态...${NC}"
    
    # 本地HTTP访问测试
    echo -e "测试本地HTTP访问:"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
    if [ "$HTTP_STATUS" -eq 301 ]; then
        echo -e "HTTP访问: ${GREEN}正常 (重定向到HTTPS)${NC}"
    elif [ "$HTTP_STATUS" -eq 200 ]; then
        echo -e "HTTP访问: ${YELLOW}正常 (未重定向到HTTPS)${NC}"
    else
        echo -e "HTTP访问: ${RED}失败 (状态码: $HTTP_STATUS)${NC}"
    fi
    
    # 本地HTTPS访问测试 (忽略证书验证)
    echo -e "测试本地HTTPS访问:"
    HTTPS_STATUS=$(curl -s -k -o /dev/null -w "%{http_code}" https://localhost)
    if [ "$HTTPS_STATUS" -eq 200 ]; then
        echo -e "HTTPS访问: ${GREEN}正常${NC}"
    else
        echo -e "HTTPS访问: ${RED}失败 (状态码: $HTTPS_STATUS)${NC}"
    fi
    
    # 检查更新信息文件
    echo -e "测试更新信息文件访问:"
    UPDATE_INFO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/update_info.json)
    if [ "$UPDATE_INFO_STATUS" -eq 200 ]; then
        echo -e "更新信息文件: ${GREEN}可访问${NC}"
    else
        echo -e "更新信息文件: ${RED}无法访问 (状态码: $UPDATE_INFO_STATUS)${NC}"
    fi
}

# 性能调优建议
offer_optimizations() {
    echo -e "\n${YELLOW}性能调优建议...${NC}"
    
    # 检查系统内存使用
    echo -e "系统内存使用情况:"
    free -h
    
    # 检查CPU使用
    echo -e "\nCPU使用情况:"
    top -bn1 | head -15
    
    # 提供Python服务器优化建议
    echo -e "\n${YELLOW}Python服务器优化建议:${NC}"
    echo -e "1. 考虑使用更高效的WSGI服务器如Gunicorn或uWSGI代替http.server"
    echo -e "2. 增加进程数以利用多核CPU: \`gunicorn -w 4 -b 0.0.0.0:8081 app:app\`"
    echo -e "3. 使用Python虚拟环境隔离依赖: \`python3 -m venv venv && source venv/bin/activate\`"
    
    # 提供Nginx优化建议
    echo -e "\n${YELLOW}Nginx优化建议:${NC}"
    echo -e "1. 根据服务器CPU核心数调整worker_processes: \`worker_processes $(nproc);\`"
    echo -e "2. 增加worker_connections: \`worker_connections 8192;\`"
    echo -e "3. 启用缓存以减轻Python服务器负担:"
    echo -e "   proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m use_temp_path=off;"
    echo -e "   # 在server块中添加: proxy_cache my_cache;"
    
    # 提供系统级优化建议
    echo -e "\n${YELLOW}系统级优化建议:${NC}"
    echo -e "1. 增加文件描述符限制: \`echo 'fs.file-max = 65535' >> /etc/sysctl.conf && sysctl -p\`"
    echo -e "2. 优化TCP参数:"
    echo -e "   echo 'net.core.somaxconn = 4096' >> /etc/sysctl.conf"
    echo -e "   echo 'net.ipv4.tcp_max_syn_backlog = 4096' >> /etc/sysctl.conf"
    echo -e "   echo 'net.ipv4.tcp_fin_timeout = 30' >> /etc/sysctl.conf"
    echo -e "   sysctl -p"
    echo -e "3. 考虑使用CDN加速静态文件访问"
}

# 检查磁盘空间
check_disk_space() {
    echo -e "\n${YELLOW}检查磁盘空间...${NC}"
    df -h
}

# 检查日志文件
check_logs() {
    echo -e "\n${YELLOW}检查日志文件...${NC}"
    
    # 检查Nginx错误日志
    if [ -f "/var/log/nginx/error.log" ]; then
        echo -e "\n最近的Nginx错误:"
        tail -n 10 /var/log/nginx/error.log
    else
        echo -e "Nginx错误日志未找到: /var/log/nginx/error.log"
    fi
    
    # 检查Python服务器日志
    if [ -f "/var/www/fba/server_output.log" ]; then
        echo -e "\n最近的Python服务器日志:"
        tail -n 10 /var/www/fba/server_output.log
    else
        echo -e "Python服务器日志未找到: /var/www/fba/server_output.log"
    fi
}

# 执行所有检查
check_ports
check_services
check_website
check_disk_space
check_logs
offer_optimizations

echo -e "\n========================================"
echo -e "测试和调优脚本执行完成"
echo -e "请根据以上信息进行必要的调整和优化"
echo -e "========================================\n"
