# Windows环境下FBA网站性能优化手动部署指南

本文档提供了在Windows环境下手动上传和部署FBA网站性能优化文件的详细步骤。

## 准备工作

### 1. 安装必要工具

在Windows上手动部署，您需要以下工具：

- **WinSCP或FileZilla**（推荐）：图形界面的SFTP客户端，用于文件上传
- **Windows Terminal或PuTTY**：用于SSH连接服务器执行命令

您可以从官网下载这些工具：
- WinSCP：https://winscp.net/download/WinSCP-5.21.8-Setup.exe
- PuTTY：https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html

### 2. 准备优化文件

确保您已经准备好以下优化文件：
- `optimized_fba_app.conf`（Nginx优化配置）
- `optimized_run_server.py`（优化版Python服务器）

## 第一步：连接到服务器检查配置

### 使用PuTTY连接服务器：

1. 打开PuTTY
2. 在"Host Name"中输入服务器IP：`47.98.248.238`
3. 端口保持默认的`22`
4. 点击"Open"
5. 在弹窗中输入用户名`root`，然后输入密码

### 检查当前服务器配置：

连接成功后，执行以下命令检查服务器配置：

```bash
# 查找Nginx配置文件
find /etc/nginx -type f -name "*.conf"

# 列出启用的配置
ls -l /etc/nginx/sites-enabled/

# 查看网站目录结构
ls -la /var/www/

# 检查是否存在原始服务器脚本
if [ -f '/var/www/fba_app/run_server.py' ]; then
    echo "原始服务器脚本存在，准备备份"
    cp /var/www/fba_app/run_server.py /var/www/fba_app/run_server.py.bak
    echo "服务器脚本已备份"
else
    echo "原始服务器脚本不存在，无需备份"
fi
```

## 第二步：手动上传优化文件

### 使用WinSCP上传文件（图形界面方式）：

1. 打开WinSCP
2. 配置连接：
   - 协议：SFTP
   - 主机名：47.98.248.238
   - 端口：22
   - 用户名：root
   - 密码：您的服务器密码
3. 点击"登录"
4. 登录成功后，您会看到左右两个面板：
   - 左边：您的Windows本地文件
   - 右边：服务器上的文件
5. 在本地找到`optimized_fba_app.conf`文件，将其拖拽到右边的`/etc/nginx/sites-available/`目录
6. 找到`optimized_run_server.py`文件，将其拖拽到右边的`/var/www/fba_app/`目录

### 使用Windows命令提示符上传（命令行方式）：

如果您已安装OpenSSH客户端，可以使用以下命令上传文件：

1. 打开Windows命令提示符（Win+R，输入cmd，回车）
2. 导航到包含优化文件的目录
3. 执行以下命令：

```cmd
:: 上传Nginx配置文件
scp optimized_fba_app.conf root@47.98.248.238:/etc/nginx/sites-available/

:: 上传优化的Python服务器脚本
scp optimized_run_server.py root@47.98.248.238:/var/www/fba_app/
```

上传过程中，可能会提示您输入服务器密码。

## 第三步：应用Nginx优化配置

回到PuTTY或Windows Terminal的SSH连接，执行以下命令：

```bash
# 确保Nginx配置目录存在
mkdir -p /etc/nginx/sites-available
mkdir -p /etc/nginx/sites-enabled

# 清理旧的启用配置
rm -f /etc/nginx/sites-enabled/*

# 启用优化配置
ln -s /etc/nginx/sites-available/optimized_fba_app.conf /etc/nginx/sites-enabled/

# 测试配置是否正确
nginx -t

# 重启Nginx服务
service nginx restart

# 检查Nginx服务状态
service nginx status
```

## 第四步：部署优化版Python服务器

继续在SSH连接中执行以下命令：

```bash
# 设置执行权限
chmod +x /var/www/fba_app/optimized_run_server.py

# 停止当前运行的服务器（如果有）
pkill -f run_server.py 2>/dev/null || echo "没有运行的服务器进程"

# 在后台运行优化版服务器
cd /var/www/fba_app
nohup python optimized_run_server.py > server_optimized.log 2>&1 &
echo $! > server.pid

# 检查服务器是否成功启动
ps aux | grep optimized_run_server.py
```

## 第五步：验证部署

完成上述步骤后，验证部署是否成功：

1. **检查服务状态**：
   ```bash
   # 检查Nginx状态
   service nginx status
   
   # 检查Python服务器进程
   ps aux | grep optimized_run_server.py
   ```

2. **测试网站访问**：
   - 打开浏览器访问：http://www.tomtarens.xyz/
   - 测试网页加载速度和文件下载功能

3. **检查日志**（如有问题）：
   ```bash
   # 查看Nginx错误日志
   tail -f /var/log/nginx/error.log
   
   # 查看优化版服务器日志
   tail -f /var/www/fba_app/server_optimized.log
   ```

## 故障排除（Windows用户专用）

### WinSCP连接失败

- 确认服务器IP地址正确：47.98.248.238
- 检查服务器端口22是否开放
- 验证用户名和密码是否正确
- 尝试使用PuTTY测试SSH连接

### Nginx配置错误

如果Nginx重启失败，检查配置：

```bash
nginx -t
```

查看错误日志：

```bash
cat /var/log/nginx/error.log
```

### Python服务器启动问题

检查服务器日志：

```bash
tail -f /var/www/fba_app/server_optimized.log
```

确保Python已正确安装：

```bash
python --version
```

## 使用Windows批处理脚本辅助部署

为了简化Windows环境下的部署流程，我们提供了`windows_manual_deploy_helper.bat`批处理脚本，该脚本包含了所有部署步骤的自动化操作。

### 使用方法：

1. 确保您已安装OpenSSH客户端（Windows 10/11用户可在"设置 > 应用 > 可选功能"中添加）
2. 双击运行`windows_manual_deploy_helper.bat`
3. 在菜单中选择您需要执行的操作：
   - [1] 查看服务器配置信息
   - [2] 上传优化文件
   - [3] 备份当前服务器配置
   - [4] 应用Nginx优化配置
   - [5] 部署优化版Python服务器
   - [6] 检查服务状态
   - [7] 查看日志文件
   - [8] 执行回滚操作
   - [9] 退出

### 脚本优势：

- 无需记忆复杂的SSH/SCP命令
- 提供交互式菜单，操作简单直观
- 包含文件检查和错误处理逻辑
- 自动显示执行命令和结果

## 常见错误处理指南

### 1. 批处理脚本执行错误

如果脚本运行时出现命令无法识别的错误：

- **错误信息**："'ssh' 不是内部或外部命令，也不是可运行的程序或批处理文件"
  - **解决方法**：确保已安装OpenSSH客户端，并已将其添加到系统PATH中
  - **安装步骤**：设置 > 应用 > 可选功能 > 添加功能 > 搜索并安装"OpenSSH客户端"
  - **验证安装**：在命令提示符中运行`ssh -V`，应显示版本信息

- **错误信息**：脚本显示乱码
  - **解决方法**：确保命令提示符使用UTF-8编码
  - **设置方法**：在命令提示符窗口中，右键标题栏 > 属性 > 选项 > 勾选"使用旧版控制台"

### 2. 文件上传问题

- **错误信息**："optimized_fba_app.conf 文件不存在！"
  - **解决方法**：确保优化文件与批处理脚本在同一目录中
  - **检查文件名**：确认文件名完全一致，包括大小写

- **SCP上传失败**：
  - **解决方法**：检查网络连接和防火墙设置
  - **替代方案**：使用WinSCP图形界面上传文件

### 3. SSH连接问题

- **连接被拒绝**：
  - 检查服务器IP地址是否正确
  - 确认SSH服务正在运行（端口22）
  - 检查防火墙设置，确保端口22开放

- **权限被拒绝**：
  - 验证用户名和密码是否正确
  - 确认root用户允许SSH登录

## 回滚步骤

如果优化后出现问题，可按以下步骤回滚：

```bash
# 恢复原始配置（如果有备份）
if [ -f '/etc/nginx/sites-available/fba_app.conf.bak' ]; then
    rm -f /etc/nginx/sites-enabled/*
    ln -s /etc/nginx/sites-available/fba_app.conf.bak /etc/nginx/sites-enabled/fba_app.conf
    nginx -t && service nginx restart
fi

# 恢复原始服务器脚本（如果有备份）
if [ -f '/var/www/fba_app/run_server.py.bak' ]; then
    pkill -f optimized_run_server.py
    cd /var/www/fba_app
    python run_server.py.bak > server.log 2>&1 &
    echo $! > server.pid
fi
```

## 注意事项

1. 所有命令都需要在SSH连接中执行
2. 确保您有足够的权限（使用root用户）
3. 上传文件时注意目标路径是否正确
4. 执行关键操作前最好备份相关文件
5. 遇到权限问题时，可以使用`chmod`命令修改权限
6. 批处理脚本执行时会显示详细的命令和执行结果
7. 对于初次部署，建议先使用脚本的[1]选项检查服务器配置

## 性能监控

部署完成后，建议定期监控服务器性能：

```bash
# 查看CPU和内存使用情况
ssh root@47.98.248.238 "top -b -n 1"

# 监控网络流量
ssh root@47.98.248.238 "iftop -t -s 10"
```

---

按照以上步骤，您可以在Windows环境下手动完成FBA网站性能优化文件的上传和部署。我们提供了详细的手动操作步骤和自动化批处理脚本，使部署过程更加简单和可靠。如有任何问题，请参考本文档的故障排除部分。