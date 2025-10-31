# GitHub Pages 设置详细指南

本文档详细介绍如何将您的静态网站部署到 GitHub Pages，作为无法配置路由器端口映射时的替代方案。

## 什么是 GitHub Pages？

GitHub Pages 是 GitHub 提供的静态网站托管服务，允许您直接从 GitHub 仓库托管静态网站，无需配置服务器或处理端口映射问题。

## 前提条件

- GitHub 账号
- 基本的 Git 知识
- 您的静态网站文件（HTML, CSS, JavaScript 等）

## 步骤一：准备您的静态网站文件

确保您的项目是静态网站（不包含服务端代码）：

1. 确保有一个 `index.html` 文件作为网站主页
2. 整理好 CSS、JavaScript 和图片等资源文件
3. 确保所有链接都是相对路径

## 步骤二：创建 GitHub 仓库

1. 登录您的 GitHub 账号
2. 点击右上角的 `+` 图标，选择 "New repository"
3. 为仓库命名（例如：`my-website`）
4. 可选：添加仓库描述
5. 选择公开或私有仓库（免费用户只能为公开仓库启用 GitHub Pages）
6. 勾选 "Add a README file" 或不勾选，根据您的需要
7. 点击 "Create repository"

## 步骤三：上传您的网站文件

有两种方式可以上传文件：

### 方法 A：通过 GitHub 网页界面上传

1. 在新创建的仓库页面，点击 "Add file" > "Upload files"
2. 拖拽您的静态网站文件到上传区域，或点击 "choose your files" 选择文件
3. 添加提交信息（如："Initial commit: Upload website files"）
4. 点击 "Commit changes"

### 方法 B：使用 Git 命令行上传（推荐）

1. 安装 Git（如未安装）
2. 在您的本地项目文件夹中打开命令行
3. 初始化 Git 仓库：
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Upload website files"
   ```
4. 连接到 GitHub 仓库：
   ```bash
   git remote add origin https://github.com/您的用户名/仓库名.git
   ```
5. 推送文件到 GitHub：
   ```bash
   git push -u origin master
   # 或者如果是 main 分支：
   git push -u origin main
   ```

## 步骤四：启用 GitHub Pages

1. 进入您的 GitHub 仓库
2. 点击 "Settings" 选项卡
3. 向下滚动找到 "Pages" 部分
4. 在 "Source" 下拉菜单中：
   - 选择要部署的分支（通常是 `main` 或 `master`）
   - 选择要部署的文件夹（通常是 `/root` 或 `/docs`）
5. 点击 "Save"
6. 页面会自动刷新，您将看到一个绿色提示框，显示您的网站已成功发布，以及访问 URL

## 步骤五：配置域名（可选）

如果您想使用自定义域名（如 tomarens.xyz）：

1. 在 GitHub Pages 设置中，找到 "Custom domain" 部分
2. 输入您的域名（如：`tomarens.xyz`）
3. 点击 "Save"
4. 前往您的域名注册商的 DNS 设置
5. 添加以下 DNS 记录：
   - A 记录：`@` 指向 GitHub Pages 的 IP 地址（185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153）
   - 或者 CNAME 记录：`www` 指向 `您的用户名.github.io`
6. 等待 DNS 记录生效（通常需要几分钟到几小时）
7. 可选：在仓库根目录创建一个 `CNAME` 文件，内容为您的域名

## 步骤六：启用 HTTPS（推荐）

1. 在 GitHub Pages 设置中，找到 "Enforce HTTPS" 选项
2. 勾选该选项
3. 点击 "Save"

## 为 FBA 项目创建静态网站版本

根据您的 FBA 项目，您可能需要：

1. 创建一个简单的静态 HTML 页面，展示您的 FBA 费用计算器信息
2. 如果您有 `.exe` 文件需要分享，可以将它们放在仓库中，并在网页上提供下载链接
3. 您可以使用 GitHub Actions 自动构建和部署更新

## 示例静态网站结构

```
my-website/
├── index.html        # 主页
├── css/              # CSS 文件夹
│   └── styles.css
├── js/               # JavaScript 文件夹
│   └── scripts.js
├── images/           # 图片文件夹
├── downloads/        # 下载文件夹（存放 .exe 文件）
│   └── FBA费用计算器.exe
└── README.md         # 项目说明
```

## 注意事项

1. GitHub Pages 仅支持静态网站，不支持服务器端代码（如 PHP、Python 等）
2. 免费版有带宽限制（每月约 100GB）
3. 单个文件大小限制为 100MB
4. 网站内容需要符合 GitHub 的服务条款

## 高级功能

### 使用 GitHub Actions 自动部署

如果您的项目需要构建步骤，可以使用 GitHub Actions 实现自动部署：

1. 在仓库中创建 `.github/workflows/deploy.yml` 文件
2. 配置自动化工作流来构建和部署您的网站

### 使用主题

GitHub Pages 支持多种主题：

1. 在仓库的 Settings 中的 Pages 部分，点击 "Choose a theme"
2. 浏览并选择一个适合您网站的主题

## 故障排除

如果您的网站没有正确显示：

1. 检查您的 `index.html` 文件是否存在且命名正确
2. 确保所有链接都是相对路径
3. 等待几分钟，因为 GitHub Pages 部署可能需要一些时间
4. 检查 GitHub Actions 日志（如果使用）查找构建错误
5. 清除浏览器缓存后重试

## 下一步

部署完成后，您可以：

1. 分享您的 GitHub Pages URL 或自定义域名给访问者
2. 定期更新您的仓库以更新网站内容
3. 考虑添加 Google Analytics 跟踪网站访问情况

---

通过这种方式，您可以在不配置路由器端口映射的情况下，让任何人都能访问您的网站！