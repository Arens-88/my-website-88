# FBA费用计算器 - 阿里云ECS部署指南

## 1. 准备工作

### 1.1 服务器环境
- 推荐使用Ubuntu 20.04 LTS或CentOS 7/8
- 确保服务器安全组已开放以下端口：
  - 80 (HTTP)
  - 443 (HTTPS)
  - 8081 (Python服务器)
  - 22 (SSH连接)

### 1.2 域名准备
- 确保域名tomarens.xyz已解析到ECS服务器的公网IP

## 2. 安装必要软件

通过SSH连接到ECS服务器后，执行以下命令安装所需软件：

### Ubuntu系统
```bash
# 更新软件包列表
sudo apt update

# 安装Python3和pip
sudo apt install -y python3 python3-pip

# 安装Nginx
sudo apt install -y nginx

# 安装OpenSSL（用于证书管理）
sudo apt install -y openssl

# 安装Git（可选，用于代码管理）
sudo apt install -y git
```

### CentOS系统
```bash
# 更新软件包列表
sudo yum update -y

# 安装Python3和pip
sudo yum install -y python3 python3-pip

# 安装Nginx
sudo yum install -y nginx

# 安装OpenSSL
sudo yum install -y openssl

# 安装Git（可选）
sudo yum install -y git
```

## 3. 创建网站目录结构

```bash
# 创建主目录
sudo mkdir -p /var/www/fba

# 创建SSL证书目录
sudo mkdir -p /etc/ssl/certs/fba

# 创建日志目录
sudo mkdir -p /var/log/fba

# 设置目录权限
sudo chown -R $USER:$USER /var/www/fba
sudo chmod -R 755 /var/www/fba
```

## 4. 上传网站文件

**注意：SFTP和SCP不是代码工具，而是Linux/Unix系统中的安全文件传输协议工具**，用于在本地计算机和远程服务器之间传输文件。

使用SFTP或SCP工具上传以下文件到服务器：

```
# 将所有网站文件上传到 /var/www/fba 目录
# 主要文件包括：
# - index.html
# - css/
# - js/
# - images/
# - downloads/ (包含FBA费用计算器.exe)
# - start_update_server_linux.sh
```

### 使用SCP上传文件的示例命令：

```bash
# 在Windows上可以使用PowerShell或Git Bash运行SCP命令
# 上传单个文件
scp ./FBA/index.html root@your_server_ip:/var/www/fba/

# 上传整个目录（递归）
scp -r ./FBA/css root@your_server_ip:/var/www/fba/
scp -r ./FBA/js root@your_server_ip:/var/www/fba/
scp -r ./FBA/images root@your_server_ip:/var/www/fba/
scp -r ./FBA/downloads root@your_server_ip:/var/www/fba/

# 上传启动脚本
scp ./FBA/start_update_server_linux.sh root@your_server_ip:/var/www/fba/
```

### 使用SFTP上传文件的示例：

```bash
# 连接到远程服务器
sftp root@your_server_ip

# 切换到本地FBA目录
lcd d:/FBA/fba/FBA

# 切换到远程目标目录
cd /var/www/fba

# 上传单个文件
put index.html

# 上传目录（递归）
put -r css
put -r js
put -r images
put -r downloads
put start_update_server_linux.sh

# 退出SFTP会话
exit
```

Windows用户也可以使用图形化工具如WinSCP或FileZilla进行文件传输，操作更直观。

## 4.1 常见连接问题及故障排除

如果您在使用SCP或SFTP时遇到连接问题（如超时、拒绝连接等），请检查以下几点：

### 1. 连接超时问题
```
ssh: connect to host your_server_ip port 22: Connection timed out
```

**可能的原因和解决方案：**
- **防火墙限制**：检查服务器的防火墙是否允许22端口（SSH）的入站连接
- **安全组规则**：在云服务器控制台检查安全组配置，确保22端口已开放
- **IP地址错误**：确认您使用的服务器IP地址正确无误
- **SSH服务未启动**：确保服务器上的SSH服务正在运行
- **网络连接问题**：检查本地网络连接和路由设置
- **内网/外网IP混用**：确认您使用的是正确的网络类型（内网或外网）IP地址

### 2. 如何查看22端口是否开放

#### 从本地计算机检查端口是否开放：
```bash
# Windows PowerShell中使用Test-NetConnection
Test-NetConnection -ComputerName your_server_ip -Port 22

# 或使用telnet（需要先启用telnet客户端功能）
telnet your_server_ip 22
```

如果连接成功，Test-NetConnection会显示"TcpTestSucceeded : True"，telnet会显示SSH服务的欢迎信息。

#### 在Linux服务器上检查端口状态：
```bash
# 检查22端口是否正在监听
ss -tuln | grep 22

# 或使用netstat（如果已安装）
netstat -tuln | grep 22

# 检查防火墙规则
# Ubuntu/Debian系统(ufw)
sudo ufw status

# CentOS/RHEL系统(firewalld)
sudo firewall-cmd --list-ports
```

### 3. 如何开放22端口

#### 在Ubuntu/Debian系统上开放22端口：
```bash
# 使用ufw防火墙开放22端口
sudo ufw allow 22/tcp
sudo ufw enable
```

#### 在CentOS/RHEL系统上开放22端口：
```bash
# 使用firewalld开放22端口
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --reload
```

### 4. 检查云服务器安全组配置

在ECS管理控制台中开放22端口：

1. 登录云服务器管理控制台
2. 找到目标实例，点击进入实例详情页
3. 找到"安全组"配置部分
4. 点击关联的安全组ID
5. 点击"配置规则" > "添加安全组规则"
6. 添加以下规则：
   - 协议类型：SSH(22)
   - 授权类型：地址段访问
   - 授权对象：0.0.0.0/0（允许所有IP访问，或根据需要设置特定IP范围）
   - 优先级：1-100（数字越小优先级越高）
7. 点击确定保存规则

### 5. 替代上传方案

如果SSH连接持续失败，可以考虑以下替代方案：

#### 使用云服务器控制台的Web SSH
1. 登录云服务器ECS控制台
2. 找到目标实例，点击"远程连接"
3. 使用Web SSH登录服务器
4. 使用wget或curl从网络下载文件：
   ```bash
   # 假设文件已上传到临时存储服务
   wget https://your-temp-storage.com/files.zip -O /var/www/fba/files.zip
   unzip /var/www/fba/files.zip -d /var/www/fba/
   rm /var/www/fba/files.zip
   ```

#### 使用图形化FTP工具的被动模式
- 在WinSCP或FileZilla中，尝试使用被动模式连接
- 在FileZilla中：编辑 > 设置 > 连接 > FTP > 被动模式
- 在WinSCP中：选项 > 首选项 > 连接 > FTP > 被动模式

### 6. 测试SSH连接

在尝试文件传输前，先测试SSH连接是否正常：
```bash
# Windows PowerShell中
ssh -v root@your_server_ip
```

-v参数会显示详细的连接日志，有助于诊断问题。

#### 解决Windows PowerShell中无法输入"yes"的问题

在Windows PowerShell中连接新服务器时，可能会遇到无法输入"yes"确认SSH密钥的情况。这通常是由于PowerShell的交互模式问题。以下是解决方案：

```powershell
# 方法1：使用-o参数直接接受新主机密钥
ssh -o StrictHostKeyChecking=no root@your_server_ip

# 方法2：使用echo和管道自动输入yes
(echo yes) | ssh root@your_server_ip

# 方法3：手动将主机密钥添加到known_hosts文件
# 首先使用命令获取主机密钥
ssh-keyscan -H your_server_ip >> ~/.ssh/known_hosts
# 然后再连接
ssh root@your_server_ip
```

对于SCP命令，也可以使用类似的方法：

```powershell
# 使用-o参数避免主机密钥确认提示
scp -o StrictHostKeyChecking=no your_file.txt root@your_server_ip:/path/to/destination/
```

这些方法可以帮助您在Windows PowerShell中解决无法输入"yes"的问题，特别是在自动化脚本或某些受限环境中非常有用。

#### SSH连接成功后的下一步操作

当您成功连接到服务器后（看到类似"root@Arens:~#"的提示符），可以继续执行以下操作：

1. **检查服务器环境**：
   ```bash
   # 查看服务器基本信息
   uname -a
   
   # 检查磁盘空间
   df -h
   
   # 检查内存使用情况
   free -h
   ```

2. **创建必要的目录**：
   ```bash
   # 创建应用程序部署目录
   mkdir -p /var/www/fba_app
   
   # 设置目录权限
   chmod -R 755 /var/www/fba_app
   ```

3. **从本地传输文件到服务器**：
   ```powershell
   # 在另一个PowerShell窗口中执行
   scp -o StrictHostKeyChecking=no -r d:/FBA/fba/FBA/* root@47.98.248.238:/var/www/fba_app/
   ```

4. **安装必要的依赖**（根据应用程序需求）：
   ```bash
   # 更新软件包列表
   apt update
   
   # 安装常用依赖
   apt install -y python3 python3-pip nginx
   ```

注意：根据截图显示，您已成功使用公网IP 47.98.248.238连接到服务器，而服务器的内网IP为172.28.47.29。在后续操作中，请使用已验证有效的公网IP地址进行连接和文件传输。

### 8. 文件上传成功后的网站对接配置

当您成功将文件上传到服务器后，需要进行以下配置才能让您的网站正常访问：

#### 8.1 Nginx配置

1. **创建Nginx配置文件**：
   ```bash
   # 创建网站配置文件
   nano /etc/nginx/sites-available/fba_app
   ```

2. **编辑配置内容**（根据您的应用程序调整）：
   ```nginx
   server {
       listen 80;
       server_name your_domain.com 47.98.248.238;  # 替换为您的域名或直接使用IP
       
       root /var/www/fba_app;
       index index.html index.htm;
       
       location / {
           try_files $uri $uri/ =404;
       }
       
       # 如果您的应用有API服务，添加如下配置
       location /api {
           proxy_pass http://localhost:8000;  # 假设您的API服务运行在8000端口
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **启用配置文件**：
   ```bash
   # 创建符号链接
   ln -s /etc/nginx/sites-available/fba_app /etc/nginx/sites-enabled/
   
   # 删除默认配置
   rm /etc/nginx/sites-enabled/default
   
   # 测试配置是否正确
   nginx -t
   
   # 重新加载Nginx
   systemctl reload nginx
   ```

#### 8.2 启动您的应用服务

根据您的应用类型，启动相应的服务：

1. **对于Python应用**（如果您的应用有run_server.py）：
   ```bash
   # 创建Python虚拟环境（推荐）
   cd /var/www/fba_app
   python3 -m venv venv
   
   # 激活虚拟环境
   source venv/bin/activate
   
   # 安装应用依赖
   pip install -r requirements.txt  # 如果有requirements.txt文件
   
   # 启动Python服务器（在虚拟环境中）
   python run_server.py &
   ```
   
   **注意**：现代Linux发行版（如Ubuntu 23.04+、Debian 12+）默认采用PEP 668规范，禁止在系统Python环境中直接安装包。使用虚拟环境可以避免此问题，并确保应用依赖的隔离。

2. **对于静态网站**：
   Nginx已经配置好直接服务静态文件，无需额外操作。

#### 8.3 配置域名（可选）

如果您有域名，请按照以下步骤配置：

1. **在域名注册商处设置DNS记录**：
   - 添加A记录：指向您的服务器IP 47.98.248.238
   - 添加CNAME记录（如果需要）

2. **配置SSL证书（推荐）**：
   ```bash
   # 安装Certbot
   apt install -y certbot python3-certbot-nginx
   
   # 获取并配置SSL证书
   certbot --nginx -d your_domain.com
   ```

#### 8.4 防火墙配置

确保防火墙允许HTTP和HTTPS流量：

```bash
# 检查防火墙状态
ufw status

# 如果防火墙开启，允许HTTP和HTTPS
ufw allow 'Nginx Full'

# 重新加载防火墙规则
ufw reload
```

#### 8.5 测试网站访问

完成以上配置后，您可以通过以下方式访问您的网站：

1. 使用服务器IP：http://47.98.248.238
2. 如果配置了域名：http://your_domain.com

如果遇到访问问题，请检查以下几点：
- Nginx服务是否正常运行：`systemctl status nginx`
- 应用服务是否正常运行
- 防火墙规则是否正确配置
- 域名DNS解析是否生效

### 7. Windows环境下的内网连接故障排除

#### 7.1 连接问题诊断

如果您在Windows环境下遇到内网连接问题，可以使用以下PowerShell命令进行诊断：

```powershell
# 检查IP配置
Get-NetIPConfiguration

# 检查防火墙状态
Get-NetFirewallProfile | Select-Object Name, Enabled

# 测试连接到服务器
Test-NetConnection -ComputerName your_server_ip -Port 22
```

#### 7.2 常见问题解决方案

1. **防火墙阻止**：
   ```powershell
   # 临时禁用Windows防火墙（仅用于测试）
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   
   # 允许SSH连接通过防火墙
   New-NetFirewallRule -DisplayName "SSH" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22
   
   # 重新启用防火墙
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
   ```

2. **IP地址冲突**：
   ```powershell
   # 检查网络适配器状态
   Get-NetAdapter | Where-Object {$_.Status -eq "Up"}
   
   # 刷新DNS缓存
   ipconfig /flushdns
   ```

3. **代理设置问题**：
   ```powershell
   # 检查代理设置
   Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" | Select-Object ProxyServer, ProxyEnable
   ```

#### 7.3 企业环境中的特殊情况

如果您在企业环境中，可能需要联系IT部门处理以下问题：

1. 企业防火墙策略限制
2. 内网网段隔离
3. 安全软件阻止

#### 7.4 使用诊断脚本

您可以使用以下PowerShell脚本来执行全面的网络诊断：

```powershell
# 创建并保存为network_diagnostics.ps1
Write-Host "=== 网络连接诊断工具 ===" -ForegroundColor Cyan

# 检查IP配置
Write-Host "\n[1] IP配置信息:" -ForegroundColor Yellow
Get-NetIPConfiguration | Format-List

# 检查连通性
Write-Host "\n[2] 检查网络连通性:" -ForegroundColor Yellow
Test-NetConnection -ComputerName 8.8.8.8 -InformationLevel Detailed

# 检查端口22
Write-Host "\n[3] 检查SSH端口(22):" -ForegroundColor Yellow
Test-NetConnection -ComputerName your_server_ip -Port 22

# 检查防火墙状态
Write-Host "\n[4] 防火墙状态:" -ForegroundColor Yellow
Get-NetFirewallProfile | Select-Object Name, Enabled

# 检查网络路由
Write-Host "\n[5] 网络路由表:" -ForegroundColor Yellow
Get-NetRoute | Where-Object {$_.DestinationPrefix -eq '0.0.0.0/0'} | Format-List

# 检查SSH客户端
Write-Host "\n[6] 检查SSH客户端:" -ForegroundColor Yellow
try {
    ssh -V
} catch {
    Write-Host "SSH客户端可能未安装" -ForegroundColor Red
}

# 提供故障排除建议
Write-Host "\n[7] 故障排除建议:" -ForegroundColor Green
Write-Host "1. 如果无法连接到服务器，请检查网络连接和防火墙设置"
Write-Host "2. 确保服务器已启动且SSH服务正在运行"
Write-Host "3. 验证您的IP地址和端口号是否正确"
Write-Host "4. 检查您的用户名和密码/密钥是否正确"
Write-Host "5. 企业环境中可能需要联系IT部门开放端口"
Write-Host "6. 尝试使用不同的网络环境连接"
Write-Host "7. 检查服务器负载是否过高导致连接超时"

# 替代解决方案
Write-Host "\n[8] 替代部署方案:" -ForegroundColor Magenta
Write-Host "1. 使用云存储服务(如阿里云OSS)作为中转"
Write-Host "2. 配置FTP服务作为替代传输方式"
Write-Host "3. 使用团队协作工具共享部署包"
Write-Host "4. 考虑使用容器化部署技术(Docker)简化过程"
```

将脚本保存为`network_diagnostics.ps1`，然后右键点击以管理员身份运行。脚本将提供详细的网络诊断信息和故障排除建议。

#### 7.5 基于诊断结果的解决方案

根据网络诊断脚本的输出，您可能会遇到以下情况：

1. **服务器无法ping通**：
   - 检查网络连接是否正常
   - 验证服务器IP地址是否正确
   - 确认服务器防火墙是否允许ping（ICMP协议）
   - 检查网络设备（如路由器、交换机）是否正常工作

2. **防火墙状态问题**：
   如果诊断脚本显示Windows防火墙已启用，您可以执行以下命令来临时禁用防火墙或创建规则：
   ```powershell
   # 临时禁用Windows防火墙
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   
   # 创建允许SSH连接的防火墙规则
   New-NetFirewallRule -DisplayName "允许SSH连接" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow
   
   # 重新启用防火墙
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
   ```

#### 7.6 简易部署替代方案

如果SSH连接持续存在问题，您可以考虑以下替代方案：

1. **USB传输部署**：
   - 将应用程序打包到USB设备
   - 物理连接USB设备到服务器
   - 手动复制文件到服务器目录

2. **云盘同步部署**：
   - 将应用程序文件上传到云盘服务（如阿里云盘、百度网盘）
   - 在服务器上安装相应的云盘客户端
   - 下载应用程序文件到服务器

3. **自解压包部署**：
   - 使用IExpress或7-Zip创建自解压可执行文件
   - 通过邮件或其他方式发送给服务器管理员
   - 在服务器上执行自解压包自动部署

这些替代方法虽然不如SSH传输方便，但在特殊情况下可以作为有效的备选方案。

### 8. 文件上传成功后的网站对接配置

当您成功将文件上传到服务器后，需要进行以下配置才能让您的网站正常访问：

#### 8.1 Nginx配置

1. **创建Nginx配置文件**：
   ```bash
   # 创建网站配置文件
   nano /etc/nginx/sites-available/fba_app
   ```

2. **编辑配置内容**（根据您的应用程序调整）：
   ```nginx
   server {
       listen 80;
       server_name your_domain.com 47.98.248.238;  # 替换为您的域名或直接使用IP
       
       root /var/www/fba_app;
       index index.html index.htm;
       
       location / {
           try_files $uri $uri/ =404;
       }
       
       # 如果您的应用有API服务，添加如下配置
       location /api {
           proxy_pass http://localhost:8000;  # 假设您的API服务运行在8000端口
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **启用配置文件**：
   ```bash
   # 创建符号链接
   ln -s /etc/nginx/sites-available/fba_app /etc/nginx/sites-enabled/
   
   # 删除默认配置
   rm /etc/nginx/sites-enabled/default
   
   # 测试配置是否正确
   nginx -t
   
   # 重新加载Nginx
   systemctl reload nginx
   ```

#### 8.2 启动您的应用服务

根据您的应用类型，启动相应的服务：

1. **对于Python应用**（如果您的应用有run_server.py）：
   ```bash
   # 安装应用依赖
   cd /var/www/fba_app
   pip install -r requirements.txt  # 如果有requirements.txt文件
   
   # 启动Python服务器
   python3 run_server.py &
   ```

2. **对于静态网站**：
   Nginx已经配置好直接服务静态文件，无需额外操作。

#### 8.3 配置域名（可选）

如果您有域名，请按照以下步骤配置：

1. **在域名注册商处设置DNS记录**：
   - 添加A记录：指向您的服务器IP 47.98.248.238
   - 添加CNAME记录（如果需要）

2. **配置SSL证书（推荐）**：
   ```bash
   # 安装Certbot
   apt install -y certbot python3-certbot-nginx
   
   # 获取并配置SSL证书
   certbot --nginx -d your_domain.com
   ```

#### 8.4 防火墙配置

确保防火墙允许HTTP和HTTPS流量：

```bash
# 检查防火墙状态
ufw status

# 如果防火墙开启，允许HTTP和HTTPS
ufw allow 'Nginx Full'

# 重新加载防火墙规则
ufw reload
```

#### 8.5 测试网站访问

完成以上配置后，您可以通过以下方式访问您的网站：

1. 使用服务器IP：http://47.98.248.238
2. 如果配置了域名：http://your_domain.com

如果遇到访问问题，请检查以下几点：
- Nginx服务是否正常运行：`systemctl status nginx`
- 应用服务是否正常运行
- 防火墙规则是否正确配置
- 域名DNS解析是否生效

### 9. 部署后维护

#### 9.1 监控服务状态

定期检查服务器和应用程序状态：

```bash
# 检查Nginx状态
systemctl status nginx

# 检查Python应用（如果运行在8000端口）
netstat -tlnp | grep 8000

# 查看系统负载
top
```

#### 9.2 日志管理

检查关键日志以排查问题：

```bash
# 查看Nginx错误日志
cat /var/log/nginx/error.log

# 查看Nginx访问日志
cat /var/log/nginx/access.log

# 如果有应用日志
cat /var/www/fba_app/app.log  # 根据您的应用日志位置调整
```

#### 9.3 自动启动设置

确保服务在服务器重启后自动启动：

```bash
# 设置Nginx自动启动
systemctl enable nginx

# 为Python应用创建systemd服务（可选）
nano /etc/systemd/system/fba_app.service
```

在service文件中添加以下内容：
```ini
[Unit]
Description=FBA Application
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/fba_app
ExecStart=/usr/bin/python3 run_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

然后启用服务：
```bash
systemctl daemon-reload
systemctl enable fba_app.service
systemctl start fba_app.service
```

#### 9.4 定期备份

设置定期备份以保护您的数据：

```bash
# 创建备份目录
mkdir -p /backup

# 创建简单的备份脚本
nano /root/backup.sh
```

脚本内容：
```bash
#!/bin/bash
BACKUP_DIR="/backup"
APP_DIR="/var/www/fba_app"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建备份
cd $APP_DIR && tar -czf "$BACKUP_DIR/fba_app_backup_$TIMESTAMP.tar.gz" *

# 保留最近10个备份，删除旧备份
ls -t "$BACKUP_DIR"/fba_app_backup_*.tar.gz | tail -n +11 | xargs rm -f
```

设置脚本权限并添加到定时任务：
```bash
chmod +x /root/backup.sh
crontab -e
```

添加以下行以每天执行备份：
```
0 0 * * * /root/backup.sh
```


## 5. 设置文件权限

```bash
# 为启动脚本添加执行权限
chmod +x /var/www/fba/start_update_server_linux.sh
chmod +x /var/www/fba/start_update_server.py

# 确保下载目录有正确权限
chmod -R 755 /var/www/fba/downloads/
```

## 6. 配置Nginx

1. 将Nginx配置文件复制到正确位置：

```bash
# 复制我们的Linux版本Nginx配置
sudo cp /var/www/fba/nginx_ssl_linux.conf /etc/nginx/sites-available/tomarens.xyz

# 创建符号链接到sites-enabled目录
sudo ln -s /etc/nginx/sites-available/tomarens.xyz /etc/nginx/sites-enabled/

# 移除默认配置（如果存在）
sudo rm /etc/nginx/sites-enabled/default
```

2. 测试Nginx配置：

```bash
sudo nginx -t
```

3. 重启Nginx服务：

```bash
sudo systemctl restart nginx
```

## 7. 配置SSL证书

### 方法1：使用Let's Encrypt（推荐）

安装Certbot并获取免费SSL证书：

```bash
# Ubuntu系统
sudo apt install -y certbot python3-certbot-nginx

# CentOS系统
sudo yum install -y certbot python3-certbot-nginx

# 自动获取和配置证书
sudo certbot --nginx -d tomarens.xyz
```

### 方法2：使用现有证书

如果您已有SSL证书，请将证书文件上传到服务器：

```bash
# 上传证书文件到SSL目录
sudo cp path/to/your_certificate.pem /etc/ssl/certs/fba/tomarens.xyz_certificate.pem
sudo cp path/to/your_private_key.pem /etc/ssl/certs/fba/tomarens.xyz_private_key.pem

# 设置正确的权限
sudo chmod 644 /etc/ssl/certs/fba/tomarens.xyz_certificate.pem
sudo chmod 600 /etc/ssl/certs/fba/tomarens.xyz_private_key.pem
```

## 8. 启动Python服务器

```bash
# 切换到网站目录
cd /var/www/fba

# 启动服务器（使用我们的Linux启动脚本）
./start_update_server_linux.sh
```

## 9. 设置系统服务（可选，但推荐）

创建系统服务文件以确保服务器在重启后自动启动：

```bash
sudo nano /etc/systemd/system/fba-update.service
```

添加以下内容：

```
[Unit]
Description=FBA Update Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/fba
ExecStart=/usr/bin/python3 /var/www/fba/start_update_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl enable fba-update.service
sudo systemctl start fba-update.service
```

## 10. 验证部署

1. 检查Nginx状态：
```bash
sudo systemctl status nginx
```

2. 检查Python服务器状态：
```bash
ps aux | grep python3
```

3. 在浏览器中访问您的网站：
   - HTTP: http://tomarens.xyz（应自动重定向到HTTPS）
   - HTTPS: https://tomarens.xyz

## 11. 定期维护

1. **自动更新SSL证书**（如果使用Let's Encrypt）：
```bash
# 创建证书自动续期的cron任务
echo "0 0,12 * * * root certbot renew --quiet" | sudo tee -a /etc/crontab > /dev/null
```

2. **定期备份网站数据**：
```bash
# 创建简单的备份脚本
sudo nano /usr/local/bin/backup_fba.sh
```

添加以下内容：
```bash
#!/bin/bash

BACKUP_DIR="/var/backups/fba"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf "$BACKUP_DIR/fba_backup_$TIMESTAMP.tar.gz" /var/www/fba
```

设置执行权限并添加cron任务：
```bash
chmod +x /usr/local/bin/backup_fba.sh
echo "0 1 * * * root /usr/local/bin/backup_fba.sh" | sudo tee -a /etc/crontab > /dev/null
```

## 12. 故障排除

### Nginx无法启动
- 检查端口是否被占用：`sudo netstat -tuln | grep 80` 或 `sudo netstat -tuln | grep 443`
- 检查Nginx错误日志：`sudo tail -f /var/log/nginx/error.log`

### SSL证书错误
- 确保证书路径正确且权限设置正确
- 检查证书是否已过期：`openssl x509 -enddate -noout -in /etc/ssl/certs/fba/tomarens.xyz_certificate.pem`

### 网站无法访问
- 检查防火墙设置：`sudo ufw status`（Ubuntu）或 `sudo firewall-cmd --list-all`（CentOS）
- 确保安全组规则已正确配置
- 验证域名解析：`ping tomarens.xyz`

---

完成以上步骤后，您的FBA费用计算器网站应该已经成功部署在阿里云ECS服务器上并可通过HTTPS安全访问。
