// FBA费用计算器 - 前端交互脚本

// 页面加载完成后执行
window.addEventListener('DOMContentLoaded', function() {
    // 初始化页面功能
    initPage();
});

// 初始化页面函数
function initPage() {
    // 为按钮添加事件监听器
    setupButtonListeners();
    
    // 检查并显示版本信息
    checkVersionInfo();
    
    // 添加平滑滚动效果
    enableSmoothScroll();
}

// 设置按钮事件监听器
function setupButtonListeners() {
    // 获取所有按钮元素
    const buttons = document.querySelectorAll('.btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // 记录点击事件
            console.log('Button clicked:', this.textContent.trim());
            
            // 下载按钮的特殊处理
            if (this.classList.contains('download-btn')) {
                handleDownload(this.dataset.version);
            }
        });
    });
}

// 检查版本信息
function checkVersionInfo() {
    // 这里可以通过AJAX请求获取最新版本信息
    // 目前使用模拟数据
    const versionInfo = {
        latestVersion: '1.1.1',
        releaseDate: '2023-10-15',
        description: '修复了部分计算错误，优化了用户界面'
    };
    
    // 更新页面上的版本信息
    updateVersionDisplay(versionInfo);
}

// 更新版本显示
function updateVersionDisplay(info) {
    const versionElement = document.querySelector('.latest-version');
    const dateElement = document.querySelector('.release-date');
    const descElement = document.querySelector('.version-description');
    
    if (versionElement) versionElement.textContent = info.latestVersion;
    if (dateElement) dateElement.textContent = info.releaseDate;
    if (descElement) descElement.textContent = info.description;
}

// 处理下载操作
function handleDownload(version) {
    // 显示下载提示
    showNotification(`正在准备下载版本 ${version}...`);
    
    // 这里可以添加下载统计等功能
    // 模拟下载延迟
    setTimeout(() => {
        showNotification('下载即将开始', 'success');
    }, 1000);
}

// 显示通知
function showNotification(message, type = 'info') {
    // 检查是否已有通知元素
    let notification = document.getElementById('notification');
    
    if (!notification) {
        // 创建通知元素
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s ease;
        `;
        document.body.appendChild(notification);
    }
    
    // 设置通知样式和内容
    notification.textContent = message;
    
    // 根据类型设置背景色
    switch(type) {
        case 'success':
            notification.style.backgroundColor = '#2ecc71';
            break;
        case 'error':
            notification.style.backgroundColor = '#e74c3c';
            break;
        case 'warning':
            notification.style.backgroundColor = '#f39c12';
            break;
        default:
            notification.style.backgroundColor = '#3498db';
    }
    
    // 显示通知
    notification.style.transform = 'translateY(0)';
    notification.style.opacity = '1';
    
    // 3秒后隐藏通知
    setTimeout(() => {
        notification.style.transform = 'translateY(100px)';
        notification.style.opacity = '0';
    }, 3000);
}

// 启用平滑滚动
function enableSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ 
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// 检测用户浏览器
function detectBrowser() {
    const userAgent = navigator.userAgent;
    let browser = 'Unknown';
    
    if (userAgent.includes('Chrome')) browser = 'Chrome';
    else if (userAgent.includes('Firefox')) browser = 'Firefox';
    else if (userAgent.includes('Safari')) browser = 'Safari';
    else if (userAgent.includes('MSIE') || userAgent.includes('Trident/')) browser = 'Internet Explorer';
    else if (userAgent.includes('Edge')) browser = 'Edge';
    
    return browser;
}

// 记录访问信息（可选功能）
function logVisitInfo() {
    const info = {
        timestamp: new Date().toISOString(),
        browser: detectBrowser(),
        screenSize: `${window.screen.width}x${window.screen.height}`,
        language: navigator.language
    };
    
    console.log('访问信息:', info);
    
    // 这里可以添加代码将信息发送到服务器（如果需要）
}