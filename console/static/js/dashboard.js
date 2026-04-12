/**
 * HermesNexus Dashboard JavaScript
 * 仪表板前端逻辑
 */

// API 基础URL
const API_BASE = '/api/v1';

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    // 自动刷新（每60秒）
    setInterval(loadDashboard, 60000);
});

// 加载仪表板数据
async function loadDashboard() {
    try {
        // 并行加载所有统计数据
        const [assetsStats, tasksStats, auditStats] = await Promise.all([
            fetch(`${API_BASE}/assets/stats`),
            fetch(`${API_BASE}/tasks/stats`),
            fetch(`${API_BASE}/audit_logs/stats`)
        ]);

        const assets = await assetsStats.json();
        const tasks = await tasksStats.json();
        const audit = await auditStats.json();

        // 更新统计数据
        updateNodeStats(assets);
        updateTaskStats(tasks);
        updateAssetStats(assets);
        updateSuccessRate(tasks);

        // 更新头部统计
        updateHeaderStats(assets, tasks);

        // 加载最近活动
        loadRecentActivity();

        // 更新系统信息
        updateSystemInfo();

    } catch (error) {
        console.error('Failed to load dashboard:', error);
        showError('加载仪表板数据失败');
    }
}

// 更新节点统计
function updateNodeStats(assets) {
    const online = assets.active_nodes || 0;
    const offline = assets.inactive_nodes || 0;
    const total = assets.total_assets || 0;

    document.getElementById('nodes-online').textContent = online;
    document.getElementById('nodes-offline').textContent = offline;
    document.getElementById('nodes-total').textContent = total;
}

// 更新任务统计
function updateTaskStats(tasks) {
    const running = tasks.running_tasks || 0;
    const completed = tasks.completed_tasks || 0;
    const failed = tasks.failed_tasks || 0;

    document.getElementById('tasks-running').textContent = running;
    document.getElementById('tasks-completed').textContent = completed;
    document.getElementById('tasks-failed').textContent = failed;
}

// 更新资产统计
function updateAssetStats(assets) {
    const active = assets.active_nodes || 0;
    const inactive = assets.inactive_nodes || 0;
    const total = assets.total_assets || 0;

    document.getElementById('assets-active').textContent = active;
    document.getElementById('assets-inactive').textContent = inactive;
    document.getElementById('assets-total').textContent = total;
}

// 更新成功率
function updateSuccessRate(tasks) {
    const rate = tasks.success_rate || 0;
    document.getElementById('success-rate').textContent = rate.toFixed(1) + '%';
}

// 更新头部统计
function updateHeaderStats(assets, tasks) {
    document.getElementById('header-assets-count').textContent = assets.total_assets || 0;
    document.getElementById('header-tasks-count').textContent = tasks.total_tasks || 0;
    document.getElementById('header-nodes-count').textContent = assets.active_nodes || 0;
}

// 加载最近活动
async function loadRecentActivity() {
    try {
        const response = await fetch(`${API_BASE}/audit_logs?page=1&page_size=10&sort_by=timestamp&sort_order=desc`);
        const data = await response.json();

        const activityList = document.getElementById('activity-list');

        if (data.audit_logs.length === 0) {
            activityList.innerHTML = '<div class="no-activity">暂无最近活动</div>';
            return;
        }

        activityList.innerHTML = data.audit_logs.slice(0, 5).map(log => `
            <div class="activity-item">
                <i class="fas fa-circle status-dot-${log.level}"></i>
                <div class="activity-content">
                    <div class="activity-message">${escapeHtml(log.message)}</div>
                    <div class="activity-time">${formatDateTime(log.timestamp)} · ${log.actor}</div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load recent activity:', error);
    }
}

// 更新系统信息
function updateSystemInfo() {
    // 系统版本
    const version = 'Phase 2 v2.0.0';
    const environment = 'development';

    // 运行时间（简化实现）
    const now = new Date();
    const uptime = '0天 0小时 0分钟'; // 实际应从API获取

    // 最后更新时间
    const lastUpdate = now.toLocaleString('zh-CN');

    document.getElementById('uptime').textContent = uptime;
    document.getElementById('last-update').textContent = lastUpdate;
    document.getElementById('environment').textContent = environment;
}

// 刷新仪表板
function refreshDashboard() {
    loadDashboard();
    showSuccess('仪表板已刷新');
}

// 工具函数
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) {
        return '刚刚';
    } else if (diffMins < 60) {
        return `${diffMins}分钟前`;
    } else if (diffMins < 1440) {
        const hours = Math.floor(diffMins / 60);
        return `${hours}小时前`;
    } else {
        return date.toLocaleString('zh-CN');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccess(message) {
    // 简化实现
    console.log('Success:', message);
}

function showError(message) {
    alert('错误: ' + message);
}

// 通知面板
function showNotifications() {
    // TODO: 实现通知面板
    alert('通知功能开发中...');
}

function hideNotifications() {
    // TODO: 隐藏通知面板
}

function refreshAll() {
    loadDashboard();
    showSuccess('数据已刷新');
}