// 图表配置和响应式处理模块

// 全局图表实例缓存
const chartInstances = {};

// 初始化所有图表
function initCharts() {
    // 销售额趋势图
    initSalesChart();
    
    // TOP 5 ASIN 销售额图
    initTopAsinChart();
    
    // 市场表现对比图（如果存在）
    if (document.getElementById('marketplace-chart')) {
        initMarketplaceChart();
    }
    
    // 店铺表现对比图（如果存在）
    if (document.getElementById('store-comparison-chart')) {
        initStoreComparisonChart();
    }
    
    // 添加窗口大小变化监听
    window.addEventListener('resize', handleResize);
}

// 初始化销售额趋势图
function initSalesChart() {
    const chartDom = document.getElementById('sales-chart');
    if (!chartDom) return;
    
    const myChart = echarts.init(chartDom);
    chartInstances['sales-chart'] = myChart;
    
    const option = {
        title: {
            show: false
        },
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            borderColor: 'transparent',
            textStyle: {
                color: '#fff'
            },
            formatter: function(params) {
                let result = params[0].axisValue + '<br/>';
                params.forEach(item => {
                    result += `${item.marker} ${item.seriesName}: ${formatCurrency(item.value)}<br/>`;
                });
                return result;
            }
        },
        legend: {
            data: ['销售额', '净利润'],
            top: 0,
            textStyle: {
                fontSize: 12
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '10%',
            top: '20%',
            containLabel: true
        },
        toolbox: {
            feature: {
                saveAsImage: {
                    title: '保存为图片',
                    iconStyle: {
                        borderColor: '#999'
                    }
                }
            },
            top: 0,
            right: 0
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: [],
            axisLabel: {
                rotate: 45,
                fontSize: 11
            }
        },
        yAxis: {
            type: 'value',
            axisLabel: {
                formatter: function(value) {
                    return formatCurrencyShort(value);
                }
            }
        },
        series: [
            {
                name: '销售额',
                type: 'line',
                smooth: true,
                data: [],
                itemStyle: {
                    color: '#1890ff'
                },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [{
                            offset: 0, color: 'rgba(24, 144, 255, 0.3)'
                        }, {
                            offset: 1, color: 'rgba(24, 144, 255, 0.05)'
                        }]
                    }
                },
                emphasis: {
                    focus: 'series',
                    lineStyle: {
                        width: 3
                    }
                }
            },
            {
                name: '净利润',
                type: 'line',
                smooth: true,
                data: [],
                itemStyle: {
                    color: '#52c41a'
                },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [{
                            offset: 0, color: 'rgba(82, 196, 26, 0.3)'
                        }, {
                            offset: 1, color: 'rgba(82, 196, 26, 0.05)'
                        }]
                    }
                },
                emphasis: {
                    focus: 'series',
                    lineStyle: {
                        width: 3
                    }
                }
            }
        ],
        animation: true,
        animationDuration: 1000
    };
    
    myChart.setOption(option);
    
    // 添加交互事件
    myChart.on('click', function(params) {
        // 可以在这里添加点击事件处理，比如钻取到详细数据
        console.log('点击了销售额趋势图:', params);
    });
    
    // 加载数据
    loadSalesChartData(myChart);
}

// 初始化TOP 5 ASIN 销售额图
function initTopAsinChart() {
    const chartDom = document.getElementById('top-asin-chart');
    if (!chartDom) return;
    
    const myChart = echarts.init(chartDom);
    chartInstances['top-asin-chart'] = myChart;
    
    const option = {
        title: {
            show: false
        },
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            borderColor: 'transparent',
            textStyle: {
                color: '#fff'
            },
            axisPointer: {
                type: 'shadow'
            },
            formatter: function(params) {
                const data = params[0];
                return `${data.axisValue}<br/>${data.marker} 销售额: ${formatCurrency(data.value)}`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            top: '3%',
            containLabel: true
        },
        toolbox: {
            feature: {
                saveAsImage: {
                    title: '保存为图片'
                }
            },
            top: 0,
            right: 0
        },
        xAxis: {
            type: 'value',
            axisLabel: {
                formatter: function(value) {
                    return formatCurrencyShort(value);
                }
            }
        },
        yAxis: {
            type: 'category',
            data: [],
            axisLabel: {
                interval: 0,
                fontSize: 11,
                formatter: function(value) {
                    // 限制显示长度
                    if (value.length > 15) {
                        return value.substring(0, 15) + '...';
                    }
                    return value;
                }
            }
        },
        series: [
            {
                type: 'bar',
                data: [],
                itemStyle: {
                    color: function(params) {
                        // 渐变色彩
                        const colorList = ['#ff7875', '#ffa940', '#ffd43b', '#95de64', '#5cdbd3'];
                        return colorList[params.dataIndex % colorList.length];
                    },
                    borderRadius: [0, 4, 4, 0]
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                },
                barWidth: '60%',
                animationDelay: function(idx) {
                    return idx * 100;
                }
            }
        ],
        animation: true,
        animationDuration: 1000,
        animationEasing: 'elasticOut'
    };
    
    myChart.setOption(option);
    
    // 添加交互事件
    myChart.on('click', function(params) {
        // 点击ASIN可以跳转到详情页或筛选该ASIN
        console.log('点击了TOP ASIN:', params);
        // 示例：触发ASIN筛选
        filterByASIN(params.name);
    });
    
    // 加载数据
    loadTopAsinChartData(myChart);
}

// 初始化市场表现对比图
function initMarketplaceChart() {
    const chartDom = document.getElementById('marketplace-chart');
    if (!chartDom) return;
    
    const myChart = echarts.init(chartDom);
    chartInstances['marketplace-chart'] = myChart;
    
    const option = {
        title: {
            show: false
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            },
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            borderColor: 'transparent',
            textStyle: {
                color: '#fff'
            }
        },
        legend: {
            data: ['销售额', '订单数', '利润'],
            top: 0,
            textStyle: {
                fontSize: 12
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '20%',
            containLabel: true
        },
        toolbox: {
            feature: {
                saveAsImage: {}
            },
            top: 0,
            right: 0
        },
        xAxis: {
            type: 'category',
            data: [],
            axisLabel: {
                rotate: 45,
                fontSize: 11
            }
        },
        yAxis: [
            {
                type: 'value',
                name: '销售额/利润',
                axisLabel: {
                    formatter: function(value) {
                        return formatCurrencyShort(value);
                    }
                }
            },
            {
                type: 'value',
                name: '订单数',
                axisLabel: {
                    formatter: '{value}'
                }
            }
        ],
        series: [
            {
                name: '销售额',
                type: 'bar',
                data: [],
                itemStyle: {
                    color: '#1890ff'
                }
            },
            {
                name: '订单数',
                type: 'line',
                yAxisIndex: 1,
                data: [],
                itemStyle: {
                    color: '#ff7875'
                }
            },
            {
                name: '利润',
                type: 'bar',
                data: [],
                itemStyle: {
                    color: '#52c41a'
                }
            }
        ]
    };
    
    myChart.setOption(option);
    loadMarketplaceChartData(myChart);
}

// 初始化店铺对比图
function initStoreComparisonChart() {
    const chartDom = document.getElementById('store-comparison-chart');
    if (!chartDom) return;
    
    const myChart = echarts.init(chartDom);
    chartInstances['store-comparison-chart'] = myChart;
    
    const option = {
        title: {
            show: false
        },
        tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            borderColor: 'transparent',
            textStyle: {
                color: '#fff'
            },
            formatter: function(params) {
                return `${params.name}<br/>${params.marker} 销售额: ${formatCurrency(params.value)}<br/>占比: ${params.percent}%`;
            }
        },
        legend: {
            orient: 'vertical',
            left: 10,
            top: 'center',
            textStyle: {
                fontSize: 12
            }
        },
        series: [
            {
                name: '销售额',
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['60%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 4,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 16,
                        fontWeight: 'bold'
                    },
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                },
                labelLine: {
                    show: false
                },
                data: []
            }
        ],
        animationType: 'scale',
        animationEasing: 'elasticOut',
        animationDelay: function(idx) {
            return Math.random() * 200;
        }
    };
    
    myChart.setOption(option);
    loadStoreComparisonChartData(myChart);
}

// 加载销售额趋势图数据
function loadSalesChartData(chart) {
    // 获取日期范围
    const startDate = document.getElementById('dashboard-start-date')?.value || getDefaultStartDate();
    const endDate = document.getElementById('dashboard-end-date')?.value || getDefaultEndDate();
    const storeId = document.getElementById('store-selector')?.value || '';
    
    // 这里应该调用API获取实际数据
    // 暂时使用模拟数据
    const mockData = getMockSalesTrendData(startDate, endDate);
    
    chart.setOption({
        xAxis: {
            data: mockData.dates
        },
        series: [
            {
                data: mockData.sales
            },
            {
                data: mockData.profit
            }
        ]
    });
}

// 加载TOP ASIN图表数据
function loadTopAsinChartData(chart) {
    // 获取日期范围和店铺选择
    const startDate = document.getElementById('dashboard-start-date')?.value || getDefaultStartDate();
    const endDate = document.getElementById('dashboard-end-date')?.value || getDefaultEndDate();
    const storeId = document.getElementById('store-selector')?.value || '';
    
    // 模拟数据
    const mockData = getMockTopAsinData();
    
    chart.setOption({
        yAxis: {
            data: mockData.asins
        },
        series: [
            {
                data: mockData.sales
            }
        ]
    });
}

// 加载市场表现对比数据
function loadMarketplaceChartData(chart) {
    // 模拟数据
    const mockData = getMockMarketplaceData();
    
    chart.setOption({
        xAxis: {
            data: mockData.marketplaces
        },
        series: [
            {
                data: mockData.sales
            },
            {
                data: mockData.orders
            },
            {
                data: mockData.profit
            }
        ]
    });
}

// 加载店铺对比数据
function loadStoreComparisonChartData(chart) {
    // 模拟数据
    const mockData = getMockStoreComparisonData();
    
    chart.setOption({
        series: [
            {
                data: mockData
            }
        ]
    });
}

// 窗口大小变化处理
function handleResize() {
    // 遍历所有图表实例进行重绘
    Object.values(chartInstances).forEach(chart => {
        chart.resize();
    });
}

// 响应式调整图表配置
function updateChartResponsiveConfig() {
    const isMobile = window.innerWidth < 768;
    
    Object.entries(chartInstances).forEach(([chartId, chart]) => {
        const option = chart.getOption();
        
        if (isMobile) {
            // 移动端配置
            if (option.legend) {
                option.legend.show = false;
            }
            if (option.toolbox) {
                option.toolbox.show = false;
            }
            if (option.grid) {
                option.grid.top = '5%';
                option.grid.bottom = '15%';
            }
            if (option.xAxis && option.xAxis[0] && option.xAxis[0].axisLabel) {
                option.xAxis[0].axisLabel.fontSize = 9;
            }
            if (option.yAxis && option.yAxis[0] && option.yAxis[0].axisLabel) {
                option.yAxis[0].axisLabel.fontSize = 9;
            }
        } else {
            // 桌面端配置
            if (chartId === 'sales-chart' || chartId === 'marketplace-chart') {
                if (option.legend) {
                    option.legend.show = true;
                }
                if (option.toolbox) {
                    option.toolbox.show = true;
                }
                if (option.grid) {
                    option.grid.top = '20%';
                    option.grid.bottom = '10%';
                }
            }
            if (option.xAxis && option.xAxis[0] && option.xAxis[0].axisLabel) {
                option.xAxis[0].axisLabel.fontSize = 11;
            }
            if (option.yAxis && option.yAxis[0] && option.yAxis[0].axisLabel) {
                option.yAxis[0].axisLabel.fontSize = 11;
            }
        }
        
        chart.setOption(option);
    });
}

// 辅助函数：格式化货币（简短显示）
function formatCurrencyShort(value) {
    if (value >= 10000) {
        return (value / 10000).toFixed(1) + '万';
    } else if (value >= 1000) {
        return (value / 1000).toFixed(1) + 'k';
    }
    return value.toString();
}

// 辅助函数：格式化货币
function formatCurrency(value) {
    return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: 'CNY',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

// 辅助函数：获取默认开始日期（30天前）
function getDefaultStartDate() {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
}

// 辅助函数：获取默认结束日期（今天）
function getDefaultEndDate() {
    return new Date().toISOString().split('T')[0];
}

// 辅助函数：根据ASIN筛选数据
function filterByASIN(asin) {
    const asinFilter = document.getElementById('asin-filter');
    if (asinFilter) {
        asinFilter.value = asin;
        // 触发筛选事件（如果存在applyFilters函数）
        if (typeof applyFilters === 'function') {
            applyFilters();
        }
    }
}

// 模拟数据生成函数
function getMockSalesTrendData(startDate, endDate) {
    const dates = [];
    const sales = [];
    const profit = [];
    
    const start = new Date(startDate);
    const end = new Date(endDate);
    const daysDiff = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    
    for (let i = 0; i < daysDiff && i < 30; i++) { // 最多30天数据
        const date = new Date(start);
        date.setDate(date.getDate() + i);
        dates.push(date.toLocaleDateString('zh-CN'));
        
        // 生成随机销售额
        const saleValue = Math.floor(Math.random() * 50000) + 10000;
        sales.push(saleValue);
        
        // 利润为销售额的40%-60%
        const profitRate = Math.random() * 0.2 + 0.4;
        profit.push(Math.floor(saleValue * profitRate));
    }
    
    return { dates, sales, profit };
}

function getMockTopAsinData() {
    return {
        asins: ['B08X123456', 'B07Y654321', 'B09Z789012', 'B06A345678', 'B05B890123'],
        sales: [45000, 38000, 32000, 28000, 25000]
    };
}

function getMockMarketplaceData() {
    return {
        marketplaces: ['美国', '英国', '德国', '法国', '日本'],
        sales: [180000, 95000, 85000, 65000, 75000],
        orders: [1200, 750, 680, 520, 600],
        profit: [75000, 42000, 38000, 28000, 32000]
    };
}

function getMockStoreComparisonData() {
    return [
        { value: 320000, name: '主力店铺' },
        { value: 180000, name: '新店测试' },
        { value: 120000, name: '欧洲分店' },
        { value: 80000, name: '亚洲分店' }
    ];
}

// 在页面加载完成后初始化图表
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        // 延迟初始化，确保页面元素已经加载完成
        setTimeout(initCharts, 100);
    });
} else {
    setTimeout(initCharts, 100);
}

// 导出图表相关函数
export { 
    initCharts, 
    handleResize, 
    updateChartResponsiveConfig,
    loadSalesChartData,
    loadTopAsinChartData
};