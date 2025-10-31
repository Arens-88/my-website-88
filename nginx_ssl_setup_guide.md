# Nginx SSL配置指南

本指南将帮助您使用SSL证书配置Nginx服务器，以便为FBA费用计算器提供安全的HTTPS访问。

## 步骤1：准备SSL证书

1. 将您申请的SSL证书文件保存到安全的位置，建议在D盘创建一个专门的目录：
   - 创建目录：`D:\ssl_certs`
   - 复制证书文件到该目录：
     - 证书文件：`fullchain.pem` (或您的证书文件名)
     - 私钥文件：`privkey.pem` (或您的私钥文件名)

2. 确保证书文件具有正确的权限，Nginx进程需要能够读取这些文件。

## 步骤2：安装Nginx（如未安装）

如果您还没有安装Nginx，请按照以下步骤进行安装：

1. 访问[Nginx官方网站](http://nginx.org/en/download.html)下载Windows版本的Nginx
2. 将下载的压缩包解压到合适的位置，如 `D:\nginx`
3. 解压后应该有以下主要目录：
   - `conf`: 配置文件目录
   - `logs`: 日志文件目录
   - `html`: 默认网页目录
   - `nginx.exe`: Nginx可执行文件

## 步骤3：配置Nginx

1. 我们已经创建了SSL配置文件：`nginx_ssl.conf`
2. 将此配置文件复制到Nginx的配置目录：
   - 复制 `d:\FBA\fba\FBA\nginx_ssl.conf` 到 `D:\nginx\conf\conf.d\`
   - 如果 `conf.d` 目录不存在，请创建它

3. 修改主配置文件 `D:\nginx\conf\nginx.conf`，在 `http` 块中添加以下行来包含我们的SSL配置：
   ```nginx
   include conf/conf.d/*.conf;
   ```
   确保它在 `server` 块之前添加。

4. （可选）调整Nginx配置文件中的证书路径：
   - 打开 `D:\nginx\conf\conf.d\nginx_ssl.conf`
   - 修改 `ssl_certificate` 和 `ssl_certificate_key` 路径以匹配您实际的证书文件位置

## 步骤4：启动Python更新服务器

在启动Nginx之前，请确保Python更新服务器已经在运行：

1. 打开命令提示符
2. 切换到FBA目录：`cd d:\FBA\fba\FBA`
3. 运行启动脚本：`simple_start.bat`
4. 确保服务器在端口8081上成功启动

## 步骤5：启动Nginx服务

1. 以管理员身份打开命令提示符
2. 切换到Nginx目录：`cd D:\nginx`
3. 启动Nginx：`start nginx.exe`

## 步骤6：验证配置

1. 打开浏览器，访问：`https://tomarens.xyz`
2. 浏览器应该显示安全的连接，并且能够访问您的FBA费用计算器更新页面
3. 检查SSL证书是否有效（通常在浏览器地址栏的锁图标中可以查看）

## 常见问题排查

### Nginx无法启动
- 检查端口80和443是否被其他程序占用：`netstat -ano | findstr :80` 和 `netstat -ano | findstr :443`
- 查看错误日志：`D:\nginx\logs\error.log`

### SSL证书错误
- 确保证书文件路径正确且Nginx有读取权限
- 验证证书是否已过期
- 检查私钥是否与证书匹配

### 无法访问网站
- 确保Windows防火墙允许Nginx通过端口80和443
- 检查您的域名DNS配置是否正确指向服务器IP
- 验证Python更新服务器是否正在端口8081上运行

## 管理Nginx

- 停止Nginx：`nginx -s stop`
- 优雅停止Nginx：`nginx -s quit`
- 重新加载配置：`nginx -s reload`
- 测试配置是否正确：`nginx -t`

## 注意事项

1. 请定期更新您的SSL证书以确保安全性
2. 建议配置自动证书更新（如果您的证书颁发商支持）
3. 保持Nginx和Python服务器的定期更新
4. 定期检查日志文件以监控服务器状态和潜在问题

如果您在配置过程中遇到任何问题，请参考Nginx官方文档或寻求专业技术支持。