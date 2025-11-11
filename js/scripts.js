// FBA费用计算器 - 前端交互脚本

// 页面加载完成后执行
window.addEventListener('DOMContentLoaded', function() {
    // 初始化页面功能
    initPage();
    
    // 添加页面进入动画
    animatePageElements();
});

// 初始化页面函数
function initPage() {
    // 为按钮添加事件监听器
    setupButtonListeners();
    
    // 检查并显示版本信息
    checkVersionInfo();
    
    // 添加平滑滚动效果
    enableSmoothScroll();
    
    // 记录访问信息
    logVisitInfo();
    
    // 添加功能卡片悬停效果
    setupFeatureCardEffects();
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
            // 版本历史按钮
            else if (this.textContent.includes('版本历史')) {
                showNotification('正在跳转到版本历史页面...');
            }
            // 查看更新信息按钮
            else if (this.textContent.includes('查看更新信息')) {
                showNotification('正在加载更新信息...');
            }
        });
        
        // 添加按钮按下效果
        button.addEventListener('mousedown', function() {
            this.style.transform = 'translateY(1px)';
        });
        
        button.addEventListener('mouseup', function() {
            this.style.transform = 'translateY(-3px)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// 检查版本信息
function checkVersionInfo() {
    // 这里可以通过AJAX请求获取最新版本信息
    // 使用正确的版本数据
    const versionInfo = {
        latestVersion: '1.2.4',
        releaseDate: '2025-11-01',
        description: '全新界面设计，提升用户体验，优化了FBA费用计算逻辑，提高准确性，修复了已知问题，增强程序稳定性，支持更多亚马逊站点的费用计算'
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
    
    // 更新版本信息区域中的当前版本
    const currentVersionElements = document.querySelectorAll('.version-info strong');
    currentVersionElements.forEach(element => {
        if (element.parentNode.textContent.includes('当前版本')) {
            element.nextSibling.textContent = ` ${info.latestVersion}`;
        } else if (element.parentNode.textContent.includes('更新日期')) {
            element.nextSibling.textContent = ` ${info.releaseDate}`;
        }
    });
}

// 处理下载操作
function handleDownload(version) {
    // 显示下载提示
    showNotification(`正在准备下载版本 ${version}...`);
    
    // 添加下载动画效果
    const downloadButton = document.querySelector('.download-btn');
    if (downloadButton) {
        downloadButton.style.animation = 'pulse 0.5s ease infinite';
    }
    
    // 模拟下载延迟
    setTimeout(() => {
        showNotification('下载即将开始', 'success');
        
        // 移除动画效果
        if (downloadButton) {
            downloadButton.style.animation = '';
        }
    }, 1000);
}

// 显示通知
function showNotification(message, type = 'info') {
    // 检查是否已有通知元素
    let notification = document.getElementById('notification');
    
    // 如果已有通知，先隐藏它
    if (notification) {
        notification.style.transform = 'translateY(100px)';
        notification.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(notification);
            createNewNotification(message, type);
        }, 300);
    } else {
        createNewNotification(message, type);
    }
}

// 创建新的通知
function createNewNotification(message, type) {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.id = 'notification';
    
    // 设置通知内容
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
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 强制重排以确保动画生效
    notification.offsetHeight;
    
    // 显示通知
    notification.style.transform = 'translateY(0)';
    notification.style.opacity = '1';
    
    // 3秒后隐藏通知
    setTimeout(() => {
        notification.style.transform = 'translateY(100px)';
        notification.style.opacity = '0';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
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

// 记录访问信息
function logVisitInfo() {
    const info = {
        timestamp: new Date().toISOString(),
        browser: detectBrowser(),
        screenSize: `${window.screen.width}x${window.screen.height}`,
        language: navigator.language
    };
    
    console.log('访问信息:', info);
}

// 页面元素动画
function animatePageElements() {
    // 为所有部分添加进入动画
    const sections = document.querySelectorAll('.feature-cards, .update-log, .version-info, .server-info');
    
    sections.forEach((section, index) => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        
        setTimeout(() => {
            section.style.opacity = '1';
            section.style.transform = 'translateY(0)';
        }, 300 + (index * 150));
    });
}

// 设置功能卡片效果
function setupFeatureCardEffects() {
    const cards = document.querySelectorAll('.feature-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
            this.style.boxShadow = '0 15px 30px rgba(0,0,0,0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
            this.style.boxShadow = '0 10px 30px rgba(0,0,0,0.1)';
        });
    });
}

// 添加响应式检测
function checkResponsive() {
    const isMobile = window.innerWidth <= 768;
    const isTablet = window.innerWidth > 768 && window.innerWidth <= 1024;
    
    return {
        isMobile,
        isTablet,
        isDesktop: !isMobile && !isTablet
    };
}

// 窗口大小改变时重新应用响应式调整
window.addEventListener('resize', function() {
    const responsive = checkResponsive();
    console.log('屏幕尺寸变化:', responsive);
    
    // 根据需要调整元素大小或位置
    const buttons = document.querySelectorAll('.btn');
    if (responsive.isMobile) {
        buttons.forEach(btn => {
            btn.style.width = '100%';
            btn.style.margin = '10px 0';
        });
    }
});