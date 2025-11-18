// 初始化应用
window.onload = initApp;

function initApp() {
    // 初始化应用程序的基本功能
    console.log('应用初始化中...');
    
    // 加载备份列表
    loadBackupList();
    
    // 初始化报表页面标签切换
    initReportTabs();
    
    // 初始化配置页面标签切换
    initConfigTabs();
    
    // 初始化自定义指标
    initCustomMetrics();
    
    // 初始化微信配置
    initWechatConfig();
    
    // 为应用筛选按钮绑定事件
    const applyFiltersBtn = document.getElementById('apply-filters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    // 为重置筛选按钮绑定事件
    const resetFiltersBtn = document.getElementById('reset-filters');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // 为导出报表按钮绑定事件
    const exportBtn = document.getElementById('export-profit-report');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportProfitReport);
    }
}

// 显示消息的辅助函数
function showMessage(message) {
    alert(message);
}

// 加载备份列表
function loadBackupList() {
    showMessage('正在加载备份列表...');
    fetch('/api/backups')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('backup-list-body');
            tbody.innerHTML = '';
            
            if (data.status === 'success' && data.data && data.data.length > 0) {
                data.data.forEach(backup => {
                    // 格式化时间戳显示
                    const date = new Date(backup.timestamp);
                    const formattedTime = date.toLocaleString('zh-CN', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    });
                    
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${backup.backup_file}</td>
                        <td>${backup.size_human || '未知'}</td>
                        <td>${formattedTime}</td>
                        <td>${backup.description || '自动备份'}</td>
                        <td>
                            <button class="btn-secondary" onclick="restoreBackup('${backup.backup_file}')">恢复</button>
                            <button class="btn-secondary" onclick="deleteBackup('${backup.backup_file}')">删除</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                const tr = document.createElement('tr');
                tr.innerHTML = '<td colspan="5" class="no-data">暂无备份</td>';
                tbody.appendChild(tr);
            }
        })
        .catch(error => {
            console.error('加载备份列表失败:', error);
            showMessage('加载备份列表失败');
        });
}

// 初始化系统配置页面的标签切换
function initConfigTabs() {
    const tabBtns = document.querySelectorAll('.config-tabs .tab-btn');
    if (tabBtns.length > 0) {
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                // 移除所有标签按钮的激活状态
                tabBtns.forEach(b => b.classList.remove('active'));
                // 添加当前标签按钮的激活状态
                this.classList.add('active');
                
                // 隐藏所有标签内容
                const tabContents = document.querySelectorAll('.tab-content');
                tabContents.forEach(content => content.style.display = 'none');
                
                // 显示对应标签内容
                const tabId = this.getAttribute('data-tab');
                const tabContent = document.getElementById(tabId);
                if (tabContent) {
                    tabContent.style.display = 'block';
                    
                    // 如果是高级报表配置标签，加载配置
                    if (tabId === 'report-config') {
                        loadReportConfigurations();
                    }
                }
            });
        });
    }
}

// 加载报表配置
function loadReportConfigurations() {
    fetch('/api/configs/report_settings')
        .then(response => {
            if (!response.ok) {
                // 如果没有找到配置，返回默认配置
                return Promise.resolve({ 
                    report_templates: [],
                    profit_calculation_method: 'gross',
                    default_chart_type: 'bar',
                    decimal_precision: 2
                });
            }
            return response.json();
        })
        .then(config => {
            // 设置利润计算方法
            const methodSelect = document.getElementById('profit_calculation_method');
            if (methodSelect && config.profit_calculation_method) {
                methodSelect.value = config.profit_calculation_method;
                toggleCustomFormulaInput();
            }
            
            // 设置默认图表类型
            const chartSelect = document.getElementById('default_chart_type');
            if (chartSelect && config.default_chart_type) {
                chartSelect.value = config.default_chart_type;
            }
            
            // 设置数值精度
            const precisionInput = document.getElementById('decimal_precision');
            if (precisionInput && config.decimal_precision) {
                precisionInput.value = config.decimal_precision;
            }
        })
        .catch(error => {
            console.error('加载报表配置失败:', error);
            showMessage('加载报表配置失败: ' + error.message);
        });
}

// 保存报表配置
function saveReportConfigurations() {
    const reportSettings = {
        profit_calculation_method: document.getElementById('profit_calculation_method').value,
        custom_profit_formula: document.getElementById('custom_profit_formula').value,
        include_adjustments: document.getElementById('include_adjustments').checked,
        apply_exchange_rate: document.getElementById('apply_exchange_rate').checked,
        default_chart_type: document.getElementById('default_chart_type').value,
        show_comparison: document.getElementById('show_comparison').checked,
        show_trend_lines: document.getElementById('show_trend_lines').checked,
        decimal_precision: parseInt(document.getElementById('decimal_precision').value),
        // 数据源配置
        data_sources: {
            sales: {
                enabled: document.getElementById('include_sales_data').checked,
                refresh_interval: parseInt(document.getElementById('sales_data_refresh_interval').value)
            },
            inventory: {
                enabled: document.getElementById('include_inventory_data').checked,
                refresh_interval: parseInt(document.getElementById('inventory_data_refresh_interval').value)
            },
            cost: {
                enabled: document.getElementById('include_cost_data').checked,
                source: document.getElementById('cost_data_source').value
            }
        }
    };
    
    fetch('/api/configs/report_settings', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(reportSettings)
    })
    .then(response => {
        if (!response.ok) throw new Error('保存报表配置失败');
        return response.json();
    })
    .then(result => {
        showMessage('报表配置保存成功');
    })
    .catch(error => {
        console.error('保存报表配置失败:', error);
        showMessage('保存报表配置失败: ' + error.message);
    });
}

// 重置报表配置为默认值
function resetReportConfigurations() {
    if (confirm('确定要将报表配置重置为默认值吗？这将丢失您所有的自定义设置。')) {
        // 重置表单元素
        document.getElementById('profit_calculation_method').value = 'gross';
        document.getElementById('custom_profit_formula').value = '';
        document.getElementById('include_adjustments').checked = true;
        document.getElementById('apply_exchange_rate').checked = true;
        document.getElementById('default_chart_type').value = 'bar';
        document.getElementById('show_comparison').checked = true;
        document.getElementById('show_trend_lines').checked = true;
        document.getElementById('decimal_precision').value = 2;
        
        // 重置数据源配置
        document.getElementById('include_sales_data').checked = true;
        document.getElementById('sales_data_refresh_interval').value = 1;
        document.getElementById('include_inventory_data').checked = true;
        document.getElementById('inventory_data_refresh_interval').value = 6;
        document.getElementById('include_cost_data').checked = true;
        document.getElementById('cost_data_source').value = 'erp';
        
        // 禁用自定义公式输入
        toggleCustomFormulaInput();
        
        showMessage('报表配置已重置为默认值');
    }
}

// 切换自定义公式输入框的启用状态
function toggleCustomFormulaInput() {
    const method = document.getElementById('profit_calculation_method').value;
    const formulaInput = document.getElementById('custom_profit_formula');
    if (formulaInput) {
        formulaInput.disabled = method !== 'custom';
    }
}

// 编辑报表模板
function editReportTemplate(templateId) {
    alert(`编辑报表模板: ${templateId}`);
    // 这里可以实现打开编辑模态框的逻辑
}

// 复制报表模板
function duplicateReportTemplate(templateId) {
    alert(`复制报表模板: ${templateId}`);
    // 这里可以实现复制模板的逻辑
}

// 创建新的报表模板
function createNewReportTemplate() {
    alert('创建新报表模板');
    // 这里可以实现打开创建模态框的逻辑
}

// 在页面加载时初始化配置标签
if (typeof initApp === 'function') {
    const originalInitApp = initApp;
    initApp = function() {
        originalInitApp();
        // 初始化标签切换
        setTimeout(initConfigTabs, 100);
        
        // 为利润计算方法选择框添加事件监听
        const methodSelect = document.getElementById('profit_calculation_method');
        if (methodSelect) {
            methodSelect.addEventListener('change', toggleCustomFormulaInput);
        }
    };
}

// 创建备份
function createBackup() {
    showMessage('正在创建备份...');
    fetch('/api/backups', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ description: '手动创建的备份' })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage('备份创建成功');
            loadBackupList();
        } else {
            showMessage('备份创建失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('创建备份失败:', error);
        showMessage('创建备份失败');
    });
}

// 清理旧备份
function cleanupBackups() {
    const daysToKeep = document.getElementById('backup-days-to-keep').value;
    showMessage(`正在清理 ${daysToKeep} 天前的备份...`);
    fetch('/api/backups/cleanup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ days_to_keep: parseInt(daysToKeep) })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage('旧备份清理完成，共删除 ' + data.deleted_count + ' 个备份');
            loadBackupList();
        } else {
            showMessage('清理旧备份失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('清理旧备份失败:', error);
        showMessage('清理旧备份失败');
    });
}

// 恢复备份
function restoreBackup(backupFilename) {
    if (confirm('确定要恢复此备份吗？这将会覆盖当前数据。')) {
        showMessage('正在恢复备份...');
        fetch(`/api/backups/restore`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ backup_filename: backupFilename })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showMessage('备份恢复成功，请刷新页面');
                // 可选：恢复成功后刷新页面或重新加载数据
            } else {
                showMessage('恢复备份失败: ' + (data.message || '未知错误'));
            }
        })
        .catch(error => {
            console.error('恢复备份失败:', error);
            showMessage('恢复备份失败');
        });
    }
}

// 删除备份
function deleteBackup(backupFilename) {
    if (confirm('确定要删除此备份吗？此操作不可撤销。')) {
        showMessage('正在删除备份...');
        fetch(`/api/backups/${encodeURIComponent(backupFilename)}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showMessage('备份删除成功');
                loadBackupList();
            } else {
                showMessage('删除备份失败: ' + (data.message || '未知错误'));
            }
        })
        .catch(error => {
            console.error('删除备份失败:', error);
            showMessage('删除备份失败');
        });
    }
}

// 自定义指标相关功能
function loadCustomMetrics() {
    fetch('/api/custom-metrics')
        .then(response => {
            if (!response.ok) throw new Error('加载自定义指标失败');
            return response.json();
        })
        .then(metrics => {
            const metricList = document.querySelector('.custom-metric-list');
            metricList.innerHTML = '';
            
            if (metrics.length === 0) {
                metricList.innerHTML = '<p class="no-metrics">暂无自定义指标，请点击"添加自定义指标"按钮创建</p>';
                return;
            }
            
            metrics.forEach(metric => {
                const metricItem = document.createElement('div');
                metricItem.className = 'custom-metric-item';
                metricItem.innerHTML = `
                    <div class="metric-header">
                        <span class="metric-name">${metric.metric_name}</span>
                        <div class="metric-actions">
                            <button class="btn-small btn-edit" onclick="editCustomMetric(${metric.id})">编辑</button>
                            <button class="btn-small btn-delete" onclick="deleteCustomMetric(${metric.id})">删除</button>
                        </div>
                    </div>
                    <div class="metric-details">
                        <p><strong>指标编码：</strong>${metric.metric_code}</p>
                        <p><strong>计算公式：</strong>${metric.formula}</p>
                        <p><strong>数据类型：</strong>${metric.data_type}</p>
                        <p><strong>小数位数：</strong>${metric.precision}</p>
                        <p><strong>状态：</strong>${metric.is_active ? '启用' : '禁用'}</p>
                    </div>
                `;
                metricList.appendChild(metricItem);
            });
        })
        .catch(error => {
            console.error('加载自定义指标失败:', error);
            showMessage('加载自定义指标失败');
        });
}

function openAddCustomMetricModal() {
    // 确保模态框HTML存在
    let modal = document.getElementById('custom-metric-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'custom-metric-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3 id="modal-title">添加自定义指标</h3>
                    <button class="close-modal" onclick="closeCustomMetricModal()">×</button>
                </div>
                <div class="modal-body">
                    <form id="custom-metric-form">
                        <input type="hidden" id="metric-id" value="">
                        <div class="form-group">
                            <label for="metric-name">指标名称</label>
                            <input type="text" id="metric-name" required placeholder="例如：利润率">
                        </div>
                        <div class="form-group">
                            <label for="metric-code">指标编码</label>
                            <input type="text" id="metric-code" required placeholder="例如：profit_rate" readonly>
                        </div>
                        <!-- 移除显示名称，后端模型中没有此字段 -->
                        <div class="form-group">
                            <label for="formula">计算公式</label>
                            <input type="text" id="formula" required placeholder="例如：(revenue - cost) / revenue * 100">
                            <div class="hint">支持基本算术运算，可以使用现有的字段名作为变量</div>
                        </div>
                        <div class="form-group">
                            <label for="data-type">数据类型</label>
                            <select id="data-type">
                                <option value="float">数值</option>
                                <option value="int">整数</option>
                                <option value="percentage">百分比</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="checkbox-label">
                                <input type="checkbox" id="is-active" checked>
                                启用此指标
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="decimal-places">小数位数</label>
                            <input type="number" id="decimal-places" min="0" max="6" value="2">
                        </div>
                        <div class="form-group">
                            <label for="description">描述</label>
                            <textarea id="description" rows="3" placeholder="可选，描述此指标的用途或计算逻辑"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="closeCustomMetricModal()">取消</button>
                    <button class="btn-primary" onclick="saveCustomMetric()">保存</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    // 重置表单
    document.getElementById('custom-metric-form').reset();
    document.getElementById('modal-title').textContent = '添加自定义指标';
    document.getElementById('metric-id').value = '';
    document.getElementById('metric-code').readOnly = false;
    
    // 显示模态框
    modal.style.display = 'block';
    
    // 监听指标名称变化，自动生成编码
    document.getElementById('metric-name').oninput = function() {
        const name = this.value;
        const code = name.toLowerCase()
            .replace(/[^a-z0-9\s]/g, '')
            .replace(/\s+/g, '_');
        document.getElementById('metric-code').value = code;
    };
}

function editCustomMetric(metricId) {
    fetch(`/api/custom-metrics/${metricId}`)
        .then(response => {
            if (!response.ok) throw new Error('获取指标信息失败');
            return response.json();
        })
        .then(metric => {
            // 打开模态框
            document.getElementById('modal-title').textContent = '编辑自定义指标';
            document.getElementById('metric-id').value = metric.id;
            document.getElementById('metric-name').value = metric.metric_name;
            document.getElementById('metric-code').value = metric.metric_code;
            document.getElementById('metric-code').readOnly = true; // 编辑时不能修改编码
            // 移除显示名称相关代码
            document.getElementById('formula').value = metric.formula;
            document.getElementById('data-type').value = metric.data_type;
            document.getElementById('decimal-places').value = metric.precision;
            document.getElementById('is-active').checked = metric.is_active;
            document.getElementById('description').value = metric.description || '';
            
            document.getElementById('custom-metric-modal').style.display = 'block';
        })
        .catch(error => {
            console.error('获取指标信息失败:', error);
            showMessage('获取指标信息失败: ' + error.message);
        });
}

function saveCustomMetric() {
    const form = document.getElementById('custom-metric-form');
    const metricId = document.getElementById('metric-id').value;
    const isEdit = !!metricId;
    
    const metricData = {
        metric_name: document.getElementById('metric-name').value,
        metric_code: document.getElementById('metric-code').value,
        formula: document.getElementById('formula').value,
        data_type: document.getElementById('data-type').value,
        precision: parseInt(document.getElementById('decimal-places').value),
        is_active: document.getElementById('is-active').checked,
        description: document.getElementById('description').value || ''
    };
    
    const url = isEdit ? `/api/custom-metrics/${metricId}` : '/api/custom-metrics';
    const method = isEdit ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(metricData)
    })
    .then(response => {
        if (!response.ok) throw new Error(isEdit ? '更新指标失败' : '创建指标失败');
        return response.json();
    })
    .then(data => {
        showMessage(isEdit ? '指标更新成功' : '指标创建成功');
        closeCustomMetricModal();
        loadCustomMetrics();
    })
    .catch(error => {
        console.error('保存指标失败:', error);
        showMessage(error.message);
    });
}

function deleteCustomMetric(metricId) {
    if (confirm('确定要删除此自定义指标吗？此操作不可撤销。')) {
        fetch(`/api/custom-metrics/${metricId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('删除指标失败');
            return response.json();
        })
        .then(data => {
            showMessage('指标删除成功');
            loadCustomMetrics();
        })
        .catch(error => {
            console.error('删除指标失败:', error);
            showMessage('删除指标失败: ' + error.message);
        });
    }
}

function closeCustomMetricModal() {
    document.getElementById('custom-metric-modal').style.display = 'none';
}

// 初始化自定义指标功能
function initCustomMetrics() {
    // 绑定添加按钮点击事件
    const addButton = document.getElementById('add-custom-metric-btn');
    if (addButton) {
        addButton.addEventListener('click', openAddCustomMetricModal);
    }
    
    // 当切换到自定义指标标签页时加载数据
    const customTab = document.getElementById('custom-tab');
    if (customTab) {
        customTab.addEventListener('click', function() {
            // 确保是在显示时加载
            if (this.style.display !== 'none') {
                loadCustomMetrics();
            }
        });
    }
}

// 在initApp函数中添加自定义指标初始化
if (typeof initApp === 'function') {
    const originalInitApp = initApp;
    initApp = function() {
        originalInitApp();
        // 等待DOM加载完成后初始化自定义指标功能
        document.addEventListener('DOMContentLoaded', function() {
            initCustomMetrics();
            initWechatConfig();
        });
    };
}

// 企业微信配置相关功能
function initWechatConfig() {
    // 绑定标签页点击事件
    const wechatTabBtn = document.querySelector('.menu-item[data-page="config"]');
    if (wechatTabBtn) {
        wechatTabBtn.addEventListener('click', function() {
            // 确保在系统配置页面加载微信配置
            setTimeout(() => {
                const configTab = document.getElementById('wechat-tab');
                if (configTab) {
                    configTab.addEventListener('click', function() {
                        loadWechatConfig();
                    });
                }
            }, 100);
        });
    }
    
    // 绑定表单提交事件
    const wechatForm = document.getElementById('wechat-config-form');
    if (wechatForm) {
        wechatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveWechatConfig();
        });
    }
    
    // 绑定推送开关事件，控制时间输入框的可用性
    const enableCheckbox = document.getElementById('enable_wechat_push');
    const pushHour = document.getElementById('push_hour');
    const pushMinute = document.getElementById('push_minute');
    
    if (enableCheckbox && pushHour && pushMinute) {
        enableCheckbox.addEventListener('change', function() {
            const isEnabled = this.checked;
            pushHour.disabled = !isEnabled;
            pushMinute.disabled = !isEnabled;
        });
    }
}

function loadWechatConfig() {
    fetch('/api/wechat/config')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应失败');
            }
            return response.json();
        })
        .then(data => {
            const webhookInput = document.getElementById('wechat_webhook_url');
            const enableCheckbox = document.getElementById('enable_wechat_push');
            const pushHour = document.getElementById('push_hour');
            const pushMinute = document.getElementById('push_minute');
            
            if (webhookInput && enableCheckbox && pushHour && pushMinute) {
                // 设置配置值，处理后端返回的可能不同的字段名
                webhookInput.value = data.config?.wechat_webhook_url || data.config?.webhook_url || '';
                enableCheckbox.checked = (data.config?.enable_wechat_push || 'false').toLowerCase() === 'true';
                pushHour.value = data.config?.push_hour || data.config?.wechat_push_hour || 8;
                pushMinute.value = data.config?.push_minute || data.config?.wechat_push_minute || 0;
                
                // 更新时间输入框的可用性
                const isEnabled = enableCheckbox.checked;
                pushHour.disabled = !isEnabled;
                pushMinute.disabled = !isEnabled;
            }
        })
        .catch(error => {
            console.error('加载微信配置失败:', error);
            showMessage('error', '加载微信配置失败: ' + error.message);
            
            // 设置默认值
            const pushHour = document.getElementById('push_hour');
            const pushMinute = document.getElementById('push_minute');
            if (pushHour && pushMinute) {
                pushHour.value = 8;
                pushMinute.value = 0;
            }
        });
}

function saveWechatConfig() {
    const webhookUrl = document.getElementById('wechat_webhook_url').value;
    const enablePush = document.getElementById('enable_wechat_push').checked;
    const pushHour = parseInt(document.getElementById('push_hour').value) || 8;
    const pushMinute = parseInt(document.getElementById('push_minute').value) || 0;
    
    // 验证Webhook URL格式
    if (enablePush && (!webhookUrl || !webhookUrl.startsWith('https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key='))) {
        showMessage('error', '请输入有效的企业微信机器人Webhook URL');
        return;
    }
    
    // 验证时间范围
    if (pushHour < 0 || pushHour > 23 || pushMinute < 0 || pushMinute > 59) {
        showMessage('error', '请输入有效的推送时间');
        return;
    }
    
    const config = {
        wechat_webhook_url: webhookUrl,
        enable_wechat_push: enablePush,
        wechat_push_hour: pushHour,
        wechat_push_minute: pushMinute
    };
    
    fetch('/api/wechat/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应失败');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            showMessage('success', '保存配置成功');
            // 如果启用了推送，提示用户将在指定时间收到推送
            if (enablePush) {
                setTimeout(() => {
                    showMessage('info', `已设置每日${pushHour.toString().padStart(2, '0')}:${pushMinute.toString().padStart(2, '0')}自动推送报表到企业微信`);
                }, 2000);
            }
        } else {
            showMessage('error', '保存配置失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('保存微信配置失败:', error);
        showMessage('error', '保存配置失败: ' + error.message);
    });
}

// 测试企业微信推送功能
function testWechatPush() {
    const webhookUrl = document.getElementById('wechat_webhook_url').value;
    
    // 验证Webhook URL
    if (!webhookUrl || !webhookUrl.startsWith('https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=')) {
        showMessage('error', '请先输入有效的企业微信机器人Webhook URL');
        return;
    }
    
    showMessage('info', '正在发送测试消息...');
    
    fetch('/api/wechat/test-push', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ webhook_url: webhookUrl })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应失败');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            showMessage('success', '测试消息发送成功，请检查企业微信');
        } else {
            showMessage('error', '测试消息发送失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('测试微信推送失败:', error);
        showMessage('error', '测试消息发送失败，可能是网络问题或Webhook URL错误');
    });
}

// 初始化报表页面标签切换
function initReportTabs() {
    const reportTabBtns = document.querySelectorAll('.report-tabs .tab-btn');
    if (reportTabBtns.length > 0) {
        reportTabBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                // 移除所有标签按钮的激活状态
                reportTabBtns.forEach(b => b.classList.remove('active'));
                // 添加当前标签按钮的激活状态
                this.classList.add('active');
                
                // 隐藏所有标签内容
                const tabContents = document.querySelectorAll('.tab-content');
                tabContents.forEach(content => content.style.display = 'none');
                
                // 显示对应标签内容
                const tabId = this.getAttribute('data-tab') + '-tab';
                const tabContent = document.getElementById(tabId);
                if (tabContent) {
                    tabContent.style.display = 'block';
                }
            });
        });
    }
}

// 应用筛选条件加载利润报表数据
function applyFilters() {
    // 显示加载中状态
    const tbody = document.getElementById('profit-report-body');
    tbody.innerHTML = '<tr><td colspan="9" class="loading">加载中...</td></tr>';
    
    // 获取筛选条件
    const filters = {
        start_date: document.getElementById('date-range-start').value,
        end_date: document.getElementById('date-range-end').value,
        marketplace: document.getElementById('marketplace').value,
        asin: document.getElementById('asin-filter').value,
        product_name: document.getElementById('product-name').value
    };
    
    // 发送请求获取利润报表数据
    fetch('/api/reports/profit?' + new URLSearchParams(filters))
        .then(response => {
            if (!response.ok) throw new Error('获取报表数据失败');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // 渲染报表数据
                renderProfitReport(data.data);
                
                // 更新汇总统计
                updateSummaryStatistics(data.summary);
            } else {
                tbody.innerHTML = '<tr><td colspan="9" class="no-data">' + (data.message || '暂无数据') + '</td></tr>';
            }
        })
        .catch(error => {
            console.error('加载利润报表失败:', error);
            tbody.innerHTML = '<tr><td colspan="9" class="error">加载数据失败，请重试</td></tr>';
        });
}

// 重置筛选条件
function resetFilters() {
    document.getElementById('date-range-start').value = '';
    document.getElementById('date-range-end').value = '';
    document.getElementById('marketplace').value = '';
    document.getElementById('asin-filter').value = '';
    document.getElementById('product-name').value = '';
}

// 渲染利润报表表格
function renderProfitReport(data) {
    const tbody = document.getElementById('profit-report-body');
    tbody.innerHTML = '';
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-data">暂无数据</td></tr>';
        return;
    }
    
    // 加载自定义指标，用于后续集成到报表中
    loadCustomMetricsIntoReports().then(customMetrics => {
        data.forEach(item => {
            const tr = document.createElement('tr');
            
            // 基础字段
            const baseColumns = `
                <td>${item.asin || '-'}</td>
                <td>${item.product_name || '-'}</td>
                <td>${item.marketplace || '-'}</td>
                <td>${item.order_count || 0}</td>
                <td>${formatCurrency(item.sales || 0)}</td>
                <td>${formatCurrency(item.cost || 0)}</td>
                <td>${formatCurrency(item.profit || 0)}</td>
                <td>${formatPercentage(item.profit_rate || 0)}</td>
            `;
            
            // 处理自定义指标
            let customColumns = '';
            const customMetricValues = calculateCustomMetrics(item, customMetrics);
            
            customMetricValues.forEach((value, metricCode) => {
                const metric = customMetrics.find(m => m.metric_code === metricCode);
                if (metric) {
                    if (metric.data_type === 'percentage') {
                        customColumns += `<td>${formatPercentage(value)}</td>`;
                    } else {
                        customColumns += `<td>${formatCurrency(value)}</td>`;
                    }
                }
            });
            
            // 操作列
            const actionColumn = '<td><button class="btn-small btn-secondary">详情</button></td>';
            
            tr.innerHTML = baseColumns + customColumns + actionColumn;
            tbody.appendChild(tr);
        });
        
        // 更新表格头部，添加自定义指标列
        updateReportTableHeader(customMetrics);
    });
}

// 加载自定义指标并集成到报表系统
function loadCustomMetricsIntoReports() {
    return new Promise((resolve) => {
        fetch('/api/custom-metrics')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.data) {
                    // 只返回启用状态的自定义指标
                    const enabledMetrics = data.data.filter(m => m.is_active);
                    resolve(enabledMetrics);
                } else {
                    resolve([]);
                }
            })
            .catch(error => {
                console.error('加载自定义指标失败:', error);
                resolve([]);
            });
    });
}

// 计算自定义指标值
function calculateCustomMetrics(item, customMetrics) {
    const results = {};
    
    customMetrics.forEach(metric => {
        try {
            // 使用Function构造器安全地计算自定义公式
            // 在实际生产环境中，应该使用更安全的表达式解析库
            const formulaFunction = new Function(
                'item', 
                `return ${metric.formula.replace(/\b(revenue|cost|profit|sales|order_count|profit_rate)\b/g, 'item.$1')}`
            );
            
            const result = formulaFunction(item);
            
            // 根据数据类型和精度进行格式化
            if (typeof result === 'number') {
                if (metric.precision !== undefined && metric.precision !== null) {
                    results[metric.metric_code] = parseFloat(result.toFixed(metric.precision));
                } else {
                    results[metric.metric_code] = result;
                }
            }
        } catch (error) {
            console.error(`计算自定义指标 ${metric.metric_code} 失败:`, error);
            results[metric.metric_code] = 0;
        }
    });
    
    return results;
}

// 更新报表表格头部，添加自定义指标列
function updateReportTableHeader(customMetrics) {
    const thead = document.querySelector('#profit-report-table thead');
    
    // 保存排序事件处理器
    const sortHandlers = [];
    const existingHeaders = thead.querySelectorAll('.sortable-header');
    existingHeaders.forEach(header => {
        const handlers = getEventListeners(header);
        if (handlers.click) {
            sortHandlers.push({ element: header, handlers: handlers.click });
        }
    });
    
    // 创建新的表头行
    const newHeaderRow = document.createElement('tr');
    
    // 基础表头
    newHeaderRow.innerHTML = `
        <th class="sortable-header" data-sort="asin">ASIN <span class="sort-icon"></span></th>
        <th class="sortable-header" data-sort="product_name">产品名称 <span class="sort-icon"></span></th>
        <th class="sortable-header" data-sort="marketplace">市场 <span class="sort-icon"></span></th>
        <th class="sortable-header" data-sort="order_count">订单数 <span class="sort-icon"></span></th>
        <th class="sortable-header" data-sort="sales">销售额 <span class="sort-icon"></span></th>
        <th class="sortable-header" data-sort="cost">成本 <span class="sort-icon"></span></th>
        <th class="sortable-header" data-sort="profit">利润 <span class="sort-icon"></span></th>
        <th class="sortable-header" data-sort="profit_rate">利润率 <span class="sort-icon"></span></th>
    `;
    
    // 添加自定义指标表头
    customMetrics.forEach(metric => {
        const th = document.createElement('th');
        th.className = 'sortable-header';
        th.setAttribute('data-sort', metric.metric_code);
        th.innerHTML = `${metric.metric_name} <span class="sort-icon"></span>`;
        newHeaderRow.appendChild(th);
    });
    
    // 添加操作列
    const actionTh = document.createElement('th');
    actionTh.textContent = '操作';
    newHeaderRow.appendChild(actionTh);
    
    // 替换表头
    thead.innerHTML = '';
    thead.appendChild(newHeaderRow);
    
    // 重新绑定排序事件
    const newHeaders = thead.querySelectorAll('.sortable-header');
    newHeaders.forEach(header => {
        header.addEventListener('click', handleSort);
    });
}

// 处理表格排序
function handleSort(event) {
    const sortField = this.getAttribute('data-sort');
    
    // 切换排序方向
    const currentDirection = this.getAttribute('data-direction') || 'asc';
    const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
    
    // 移除其他列的排序状态
    document.querySelectorAll('.sortable-header').forEach(header => {
        header.removeAttribute('data-direction');
        header.querySelector('.sort-icon').textContent = '';
    });
    
    // 设置当前列的排序状态
    this.setAttribute('data-direction', newDirection);
    this.querySelector('.sort-icon').textContent = newDirection === 'asc' ? '↑' : '↓';
    
    // 重新应用筛选，带上排序参数
    const filters = {
        start_date: document.getElementById('date-range-start').value,
        end_date: document.getElementById('date-range-end').value,
        marketplace: document.getElementById('marketplace').value,
        asin: document.getElementById('asin-filter').value,
        product_name: document.getElementById('product-name').value,
        sort_by: sortField,
        sort_direction: newDirection
    };
    
    // 显示加载中状态
    const tbody = document.getElementById('profit-report-body');
    tbody.innerHTML = '<tr><td colspan="9" class="loading">加载中...</td></tr>';
    
    // 发送请求获取排序后的数据
    fetch('/api/reports/profit?' + new URLSearchParams(filters))
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                renderProfitReport(data.data);
            }
        })
        .catch(error => {
            console.error('排序数据失败:', error);
        });
}

// 更新汇总统计信息
function updateSummaryStatistics(summary) {
    if (!summary) return;
    
    document.getElementById('total-asins').textContent = summary.total_asins || 0;
    document.getElementById('total-orders').textContent = summary.total_orders || 0;
    document.getElementById('total-sales').textContent = formatCurrency(summary.total_sales || 0);
    document.getElementById('total-profit').textContent = formatCurrency(summary.total_profit || 0);
    document.getElementById('avg-profit-rate').textContent = formatPercentage(summary.avg_profit_rate || 0);
}

// 导出利润报表
function exportProfitReport() {
    // 获取当前筛选条件
    const filters = {
        start_date: document.getElementById('date-range-start').value,
        end_date: document.getElementById('date-range-end').value,
        marketplace: document.getElementById('marketplace').value,
        asin: document.getElementById('asin-filter').value,
        product_name: document.getElementById('product-name').value,
        format: 'excel'
    };
    
    // 构建导出URL
    const exportUrl = '/api/reports/profit/export?' + new URLSearchParams(filters);
    
    // 打开新窗口下载文件
    window.open(exportUrl, '_blank');
}

// 格式化货币
function formatCurrency(value) {
    return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: 'CNY',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// 格式化百分比
function formatPercentage(value) {
    return new Intl.NumberFormat('zh-CN', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

// 获取元素的事件监听器
function getEventListeners(element) {
    const listeners = {};
    const events = ['click', 'change', 'input', 'submit', 'keydown', 'keyup'];
    
    events.forEach(event => {
        const listenersList = getEventListenersForEvent(element, event);
        if (listenersList.length > 0) {
            listeners[event] = listenersList;
        }
    });
    
    return listeners;
}

// 获取特定事件的监听器
function getEventListenersForEvent(element, event) {
    const listeners = [];
    // 这是一个简化版本，实际生产环境中可能需要更复杂的实现
    // 或者使用浏览器调试API
    return listeners;
}
