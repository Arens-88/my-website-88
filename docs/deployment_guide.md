# Amazon FBA报表工具部署指南

## 1. 环境准备

### 1.1 硬件要求
- CPU: 2核或以上
- 内存: 4GB或以上
- 存储: 50GB SSD硬盘
- 操作系统: Ubuntu 20.04 LTS 或 CentOS 8

### 1.2 软件要求
- Python 3.8+
- MySQL 8.0 或 PostgreSQL 12+
- Redis 6.0+（可选，用于缓存）
- Nginx 1.18+（用于前端部署）
- Supervisor（用于进程管理）

## 2. 数据库安装与配置

### 2.1 MySQL安装（以Ubuntu为例）

```bash
# 安装MySQL
apt update
apt install -y mysql-server

# 安全配置
mysql_secure_installation

# 创建数据库和用户
mysql -u root -p
CREATE DATABASE amazon_report_tool DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'amazon_user'@'localhost' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON amazon_report_tool.* TO 'amazon_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 3. 后端部署

### 3.1 克隆代码

```bash
mkdir -p /opt/amazon-report-tool
cd /opt/amazon-report-tool
git clone <repository_url> .
cd backend
```

### 3.2 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 3.3 安装依赖

```bash
pip install -r requirements.txt
```

### 3.4 配置文件设置

复制配置示例文件并根据环境修改：

```bash
cp config.example.py config.py
```

编辑 `config.py` 文件，修改以下配置：

```python
# 数据库配置
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://amazon_user:your_strong_password@localhost/amazon_report_tool'

# Redis配置（如果启用）
REDIS_URL = 'redis://localhost:6379/0'

# 密钥设置
SECRET_KEY = 'your_secure_secret_key'

# 环境配置
ENV = 'production'
DEBUG = False

# 定时任务配置
SCHEDULER_API_ENABLED = True
```

### 3.5 初始化数据库

```bash
python init_db.py
```

### 3.6 设置Supervisor管理服务

创建Supervisor配置文件：

```bash
nano /etc/supervisor/conf.d/amazon-report-tool.conf
```

配置内容：

```ini
[program:amazon-report-tool]
directory=/opt/amazon-report-tool/backend
command=/opt/amazon-report-tool/backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
autostart=true
autorestart=true
stderr_logfile=/var/log/amazon-report-tool.err.log
stdout_logfile=/var/log/amazon-report-tool.out.log
user=www-data
environment=PYTHONPATH=/opt/amazon-report-tool/backend
```

更新Supervisor配置：

```bash
supervisorctl reread
supervisorctl update
supervisorctl start amazon-report-tool
```

## 4. 前端部署

### 4.1 编译前端代码

在开发环境中编译前端：

```bash
cd /path/to/frontend
npm install
npm run build
```

将生成的 `dist` 目录复制到服务器：

```bash
scp -r dist/* user@server:/var/www/amazon-report-tool/
```

### 4.2 配置Nginx

创建Nginx配置文件：

```bash
nano /etc/nginx/sites-available/amazon-report-tool
```

配置内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/amazon-report-tool;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端API代理
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态资源缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
}
```

启用配置并重启Nginx：

```bash
ln -s /etc/nginx/sites-available/amazon-report-tool /etc/nginx/sites-enabled/
nginx -t
nginx -s reload
```

## 5. SSL证书配置（可选）

使用Let's Encrypt获取免费SSL证书：

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## 6. 定时任务配置

系统已内置APScheduler管理定时任务，主要任务包括：
- 数据同步
- 报表生成
- 推送通知

这些任务可以通过管理界面进行配置。

## 7. 备份策略

### 7.1 数据库备份

创建每日备份脚本：

```bash
nano /opt/backup-db.sh
```

内容：

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR
mysqldump -u amazon_user -p'your_strong_password' amazon_report_tool > $BACKUP_DIR/amazon_report_tool_$DATE.sql
gzip $BACKUP_DIR/amazon_report_tool_$DATE.sql
# 删除7天前的备份
find $BACKUP_DIR -name "amazon_report_tool_*.sql.gz" -mtime +7 -delete
```

设置可执行权限并添加到crontab：

```bash
chmod +x /opt/backup-db.sh
crontab -e
```

添加以下行（每天凌晨3点执行）：

```
0 3 * * * /opt/backup-db.sh
```

### 7.2 配置文件备份

定期备份配置文件：

```bash
cp /opt/amazon-report-tool/backend/config.py /opt/backups/config_$(date +%Y%m%d).py
```

## 8. 监控与维护

### 8.1 日志查看

- 应用日志：`/var/log/amazon-report-tool.out.log` 和 `/var/log/amazon-report-tool.err.log`
- Nginx日志：`/var/log/nginx/access.log` 和 `/var/log/nginx/error.log`
- 数据库日志：`/var/log/mysql/mysql.log`

### 8.2 常见问题排查

1. **服务无法启动**
   - 检查端口是否被占用
   - 检查数据库连接是否正常
   - 查看错误日志

2. **定时任务不执行**
   - 确认APScheduler是否正常运行
   - 检查任务配置是否正确
   - 验证系统时间是否准确

3. **内存占用过高**
   - 调整Gunicorn工作进程数量
   - 检查是否存在内存泄漏
   - 考虑增加服务器内存

## 9. 版本更新

### 9.1 后端更新

```bash
cd /opt/amazon-report-tool
git pull
source backend/venv/bin/activate
cd backend
pip install -r requirements.txt
python init_db.py  # 执行数据库迁移

# 重启服务
supervisorctl restart amazon-report-tool
```

### 9.2 前端更新

编译新的前端代码并部署到服务器：

```bash
cd /path/to/frontend
npm install
npm run build
scp -r dist/* user@server:/var/www/amazon-report-tool/
```

## 10. 性能优化

### 10.1 数据库优化
- 创建适当的索引
- 定期执行 `ANALYZE TABLE` 优化表统计信息
- 考虑使用读写分离架构

### 10.2 缓存优化
- 启用Redis缓存（修改配置文件）
- 增加缓存有效期
- 优化缓存键设计

### 10.3 服务器优化
- 调整Linux内核参数
- 优化MySQL配置
- 配置Nginx缓存

---

*本部署指南由Amazon FBA报表工具团队编写，最后更新日期：2024年7月*