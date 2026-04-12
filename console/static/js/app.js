// HermesNexus Console JavaScript

const API_BASE = 'http://localhost:8080/api/v1';

// 状态管理
let currentTab = 'overview';
let nodes = [];
let tasks = [];
let events = [];

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeFilters();
    initializeRefreshButtons();
    loadAllData();
    // 每30秒自动刷新数据
    setInterval(loadAllData, 30000);
});

// 标签页切换
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // 更新标签按钮状态
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-tab') === tabName) {
            btn.classList.add('active');
        }
    });

    // 更新内容显示
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
        if (content.id === `${tabName}-tab`) {
            content.classList.add('active');
        }
    });

    currentTab = tabName;
}

// 初始化过滤器
function initializeFilters() {
    // 任务状态过滤器
    const taskStatusFilter = document.getElementById('task-status-filter');
    taskStatusFilter.addEventListener('change', function() {
        filterTasks(this.value);
    });

    // 事件级别过滤器
    const eventLevelFilter = document.getElementById('event-level-filter');
    eventLevelFilter.addEventListener('change', function() {
        filterEvents(this.value);
    });
}

// 初始化刷新按钮
function initializeRefreshButtons() {
    document.getElementById('refresh-nodes').addEventListener('click', loadNodes);
    document.getElementById('refresh-tasks').addEventListener('click', loadTasks);
    document.getElementById('refresh-events').addEventListener('click', loadEvents);
}

// 加载所有数据
async function loadAllData() {
    try {
        await Promise.all([
            loadNodes(),
            loadTasks(),
            loadEvents()
        ]);
        updateOverview();
        updateHeaderStats();
    } catch (error) {
        console.error('加载数据失败:', error);
    }
}

// 加载节点数据
async function loadNodes() {
    try {
        const response = await fetch(`${API_BASE}/nodes`);
        const data = await response.json();
        nodes = data.nodes || [];
        renderNodes();
        updateOverview();
        updateHeaderStats();
    } catch (error) {
        console.error('加载节点失败:', error);
        showErrorMessage('nodes-list', '加载节点数据失败');
    }
}

// 加载任务数据
async function loadTasks() {
    try {
        const response = await fetch(`${API_BASE}/jobs`);
        const data = await response.json();
        tasks = data.jobs || [];
        renderTasks();
        updateOverview();
        updateHeaderStats();
    } catch (error) {
        console.error('加载任务失败:', error);
        showErrorMessage('tasks-list', '加载任务数据失败');
    }
}

// 加载事件数据
async function loadEvents() {
    try {
        const response = await fetch(`${API_BASE}/events`);
        const data = await response.json();
        events = data.events || [];
        renderEvents();
        updateOverview();
        updateHeaderStats();
    } catch (error) {
        console.error('加载事件失败:', error);
        showErrorMessage('events-list', '加载事件数据失败');
    }
}

// 渲染节点列表
function renderNodes() {
    const container = document.getElementById('nodes-list');

    if (nodes.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📡</div>
                <p>暂无节点</p>
            </div>
        `;
        return;
    }

    const html = nodes.map(node => `
        <div class="node-card">
            <div class="node-header">
                <div class="node-id">${escapeHtml(node.node_id || 'Unknown')}</div>
                <div class="node-status ${node.status || 'offline'}">
                    ${node.status === 'online' ? '在线' : '离线'}
                </div>
            </div>
            <div class="node-stats">
                <div class="node-stat">
                    <span class="stat-label">CPU使用率:</span>
                    <span class="stat-value">${(node.cpu_usage || 0).toFixed(1)}%</span>
                </div>
                <div class="node-stat">
                    <span class="stat-label">内存使用率:</span>
                    <span class="stat-value">${(node.memory_usage || 0).toFixed(1)}%</span>
                </div>
                <div class="node-stat">
                    <span class="stat-label">活跃任务:</span>
                    <span class="stat-value">${node.active_tasks || 0}</span>
                </div>
                <div class="node-stat">
                    <span class="stat-label">最后心跳:</span>
                    <span class="stat-value">${formatTime(node.last_heartbeat)}</span>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

// 渲染任务列表
function renderTasks(filteredTasks = null) {
    const container = document.getElementById('tasks-list');
    const tasksToRender = filteredTasks || tasks;

    if (tasksToRender.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <p>暂无任务</p>
            </div>
        `;
        return;
    }

    const html = tasksToRender.map(task => `
        <div class="task-card">
            <div class="task-header">
                <div class="task-id">${escapeHtml(task.job_id || 'Unknown')}</div>
                <div class="task-status ${task.status || 'pending'}">
                    ${getStatusText(task.status)}
                </div>
            </div>
            <div class="task-details">
                <div>
                    <span class="stat-label">名称:</span>
                    <span class="stat-value">${escapeHtml(task.name || '未命名')}</span>
                </div>
                <div>
                    <span class="stat-label">目标设备:</span>
                    <span class="stat-value">${escapeHtml(task.target_device_id || 'Unknown')}</span>
                </div>
                <div>
                    <span class="stat-label">分配节点:</span>
                    <span class="stat-value">${escapeHtml(task.node_id || 'Unassigned')}</span>
                </div>
                <div>
                    <span class="stat-label">创建时间:</span>
                    <span class="stat-value">${formatTime(task.created_at)}</span>
                </div>
            </div>
            ${task.command ? `
                <div class="task-command">
                    ${escapeHtml(task.command)}
                </div>
            ` : ''}
        </div>
    `).join('');

    container.innerHTML = html;
}

// 渲染事件列表
function renderEvents(filteredEvents = null) {
    const container = document.getElementById('events-list');
    const eventsToRender = filteredEvents || events;

    if (eventsToRender.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📡</div>
                <p>暂无事件</p>
            </div>
        `;
        return;
    }

    const html = eventsToRender.map(event => `
        <div class="event-card ${event.level || 'info'}">
            <div class="event-header">
                <div class="event-type">${escapeHtml(event.type || 'Unknown')}</div>
                <div class="event-time">${formatTime(event.timestamp)}</div>
            </div>
            <div class="event-message">
                ${escapeHtml(event.message || event.title || 'No message')}
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

// 更新概览页面
function updateOverview() {
    // 节点概览
    const nodesOverview = document.getElementById('overview-nodes');
    if (nodes.length > 0) {
        const onlineCount = nodes.filter(n => n.status === 'online').length;
        nodesOverview.innerHTML = `
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 3rem; margin-bottom: 10px;">
                    ${onlineCount}/${nodes.length}
                </div>
                <div style="color: var(--text-secondary);">
                    在线节点
                </div>
            </div>
        `;
    } else {
        nodesOverview.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📡</div>
                <p>暂无节点</p>
            </div>
        `;
    }

    // 任务概览
    const tasksOverview = document.getElementById('overview-tasks');
    if (tasks.length > 0) {
        const successCount = tasks.filter(t => t.status === 'success').length;
        const runningCount = tasks.filter(t => t.status === 'running').length;
        const pendingCount = tasks.filter(t => t.status === 'pending').length;

        tasksOverview.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center;">
                <div>
                    <div style="font-size: 1.5rem; color: var(--success-color);">${successCount}</div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">成功</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; color: var(--info-color);">${runningCount}</div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">运行中</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; color: var(--warning-color);">${pendingCount}</div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">等待中</div>
                </div>
            </div>
        `;
    } else {
        tasksOverview.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <p>暂无任务</p>
            </div>
        `;
    }

    // 事件概览
    const eventsOverview = document.getElementById('overview-events');
    if (events.length > 0) {
        const recentEvents = events.slice(0, 5);
        eventsOverview.innerHTML = recentEvents.map(event => `
            <div class="event-card ${event.level || 'info'}" style="margin-bottom: 8px;">
                <div class="event-header" style="margin-bottom: 3px;">
                    <div class="event-type" style="font-size: 0.85rem;">${escapeHtml(event.type || 'Unknown')}</div>
                    <div class="event-time" style="font-size: 0.75rem;">${formatTime(event.timestamp)}</div>
                </div>
                <div class="event-message" style="font-size: 0.85rem;">
                    ${escapeHtml(event.message || event.title || '').substring(0, 60)}...
                </div>
            </div>
        `).join('');
    } else {
        eventsOverview.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📡</div>
                <p>暂无事件</p>
            </div>
        `;
    }
}

// 更新头部统计
function updateHeaderStats() {
    // 节点状态
    const nodeStatus = document.getElementById('node-status');
    const onlineNodes = nodes.filter(n => n.status === 'online').length;
    nodeStatus.textContent = `${onlineNodes}/${nodes.length} 在线`;
    nodeStatus.style.color = onlineNodes > 0 ? 'var(--success-color)' : 'var(--error-color)';

    // 活跃任务
    const activeTasks = document.getElementById('active-tasks');
    const activeCount = tasks.filter(t => t.status === 'running' || t.status === 'pending').length;
    activeTasks.textContent = activeCount;

    // 最近事件
    const recentEvents = document.getElementById('recent-events');
    const today = new Date().toDateString();
    const todayEvents = events.filter(e => new Date(e.timestamp).toDateString() === today);
    recentEvents.textContent = todayEvents.length;
}

// 过滤任务
function filterTasks(status) {
    if (!status) {
        renderTasks(tasks);
        return;
    }
    const filtered = tasks.filter(task => task.status === status);
    renderTasks(filtered);
}

// 过滤事件
function filterEvents(level) {
    if (!level) {
        renderEvents(events);
        return;
    }
    const filtered = events.filter(event => event.level === level);
    renderEvents(filtered);
}

// 工具函数
function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`;
    return date.toLocaleDateString('zh-CN');
}

function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'running': '运行中',
        'success': '成功',
        'failed': '失败',
        'cancelled': '已取消'
    };
    return statusMap[status] || status;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showErrorMessage(containerId, message) {
    const container = document.getElementById(containerId);
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">⚠️</div>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}