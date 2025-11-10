// 增强版下载优化器 - 用于提升大文件下载速度

class DownloadOptimizer {
    constructor() {
        this.chunkSize = 10 * 1024 * 1024; // 10MB 块大小
        this.concurrency = 3; // 并发连接数
        this.activeDownloads = 0;
        this.completedChunks = 0;
        this.totalChunks = 0;
        this.fileChunks = [];
        this.fileSize = 0;
        this.fileName = '';
        this.fileUrl = '';
    }

    // 初始化下载过程
    async startDownload(fileUrl, fileName) {
        this.fileUrl = fileUrl;
        this.fileName = fileName;
        
        try {
            // 获取文件大小
            const response = await fetch(fileUrl, { method: 'HEAD' });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.fileSize = parseInt(response.headers.get('content-length') || '0', 10);
            this.totalChunks = Math.ceil(this.fileSize / this.chunkSize);
            
            console.log(`开始下载: ${fileName}, 大小: ${(this.fileSize / 1024 / 1024).toFixed(2)}MB, 分块数: ${this.totalChunks}`);
            
            // 初始化进度条
            this.initProgressBar();
            
            // 开始分块下载
            await this.downloadChunks();
            
            // 合并文件块
            await this.mergeChunks();
            
            console.log('下载完成!');
            this.showProgressMessage('下载完成!');
            
        } catch (error) {
            console.error('下载失败:', error);
            this.showProgressMessage('下载失败，请重试', 'error');
        }
    }

    // 初始化进度条
    initProgressBar() {
        // 移除已存在的进度条
        const existingProgress = document.querySelector('.download-progress');
        if (existingProgress) {
            existingProgress.remove();
        }
        
        // 创建进度容器
        const progressContainer = document.createElement('div');
        progressContainer.className = 'download-progress';
        progressContainer.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            max-width: 600px;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            z-index: 1000;
        `;
        
        // 创建文件名显示
        const fileNameElement = document.createElement('div');
        fileNameElement.textContent = `正在下载: ${this.fileName}`;
        fileNameElement.style.cssText = 'font-weight: bold; margin-bottom: 10px;';
        
        // 创建进度条容器
        const barContainer = document.createElement('div');
        barContainer.style.cssText = 'width: 100%; height: 20px; background: #eee; border-radius: 10px; overflow: hidden;';
        
        // 创建进度条
        this.progressBar = document.createElement('div');
        this.progressBar.style.cssText = `
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
        `;
        
        // 创建百分比显示
        this.progressText = document.createElement('div');
        this.progressText.textContent = '0%';
        this.progressText.style.cssText = 'text-align: center; margin-top: 10px; font-size: 14px;';
        
        // 组装DOM
        barContainer.appendChild(this.progressBar);
        progressContainer.appendChild(fileNameElement);
        progressContainer.appendChild(barContainer);
        progressContainer.appendChild(this.progressText);
        
        document.body.appendChild(progressContainer);
    }

    // 更新进度显示
    updateProgress() {
        const progress = Math.round((this.completedChunks / this.totalChunks) * 100);
        this.progressBar.style.width = `${progress}%`;
        this.progressText.textContent = `${progress}%`;
    }

    // 显示进度消息
    showProgressMessage(message, type = 'info') {
        this.progressText.textContent = message;
        if (type === 'error') {
            this.progressText.style.color = '#e74c3c';
        } else if (type === 'success') {
            this.progressText.style.color = '#2ecc71';
        }
    }

    // 下载所有分块
    async downloadChunks() {
        const downloadPromises = [];
        
        for (let i = 0; i < this.totalChunks; i++) {
            // 控制并发数
            if (this.activeDownloads >= this.concurrency) {
                await new Promise(resolve => {
                    const checkInterval = setInterval(() => {
                        if (this.activeDownloads < this.concurrency) {
                            clearInterval(checkInterval);
                            resolve();
                        }
                    }, 100);
                });
            }
            
            downloadPromises.push(this.downloadChunk(i));
        }
        
        // 等待所有下载完成
        await Promise.all(downloadPromises);
    }

    // 下载单个分块
    async downloadChunk(chunkIndex) {
        this.activeDownloads++;
        
        const start = chunkIndex * this.chunkSize;
        const end = Math.min(start + this.chunkSize - 1, this.fileSize - 1);
        
        try {
            const response = await fetch(this.fileUrl, {
                method: 'GET',
                headers: {
                    'Range': `bytes=${start}-${end}`
                }
            });
            
            if (!response.ok && response.status !== 206) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const blob = await response.blob();
            this.fileChunks[chunkIndex] = blob;
            
            this.completedChunks++;
            this.updateProgress();
            
        } catch (error) {
            console.error(`下载块 ${chunkIndex} 失败:`, error);
            // 重试机制 - 最多重试3次
            for (let retry = 0; retry < 3; retry++) {
                try {
                    await new Promise(resolve => setTimeout(resolve, 1000 * (retry + 1)));
                    const response = await fetch(this.fileUrl, {
                        method: 'GET',
                        headers: {
                            'Range': `bytes=${start}-${end}`
                        }
                    });
                    
                    if (response.ok || response.status === 206) {
                        const blob = await response.blob();
                        this.fileChunks[chunkIndex] = blob;
                        
                        this.completedChunks++;
                        this.updateProgress();
                        break;
                    }
                } catch (retryError) {
                    console.error(`重试 ${retry + 1} 失败:`, retryError);
                }
            }
        } finally {
            this.activeDownloads--;
        }
    }

    // 合并文件块
    async mergeChunks() {
        this.showProgressMessage('正在合并文件...');
        
        // 创建一个新的Blob，包含所有下载的块
        const mergedBlob = new Blob(this.fileChunks, { type: 'application/octet-stream' });
        
        // 创建下载链接
        const url = URL.createObjectURL(mergedBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = this.fileName;
        
        // 触发下载
        document.body.appendChild(a);
        a.click();
        
        // 清理
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            // 移除进度条
            const progressContainer = document.querySelector('.download-progress');
            if (progressContainer) {
                progressContainer.remove();
            }
        }, 100);
    }
}

// 导出单例实例
export const downloadOptimizer = new DownloadOptimizer();