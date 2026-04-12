/**
 * HermesNexus Audit Log JavaScript
 * 审计日志前端逻辑
 */

// API 基础URL
const API_BASE = '/api/v1';

// 当前状态
let currentPage = 1;
let pageSize = 50;
let totalPages = 1;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadLogs();
});

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/audit_logs/stats`);
        const stats = await response.json();

        document.getElementById('total-events').textContent = stats.total_events || 0;
        document.getElementById('error-events').textContent = stats.error_events || 0;
        document.getElementById('events-last-hour').textContent = stats.events_last_hour || 0;
        document.getElementById('events-last-day').textContent = stats.events_last_day || 0;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// 加载审计日志
async function loadLogs() {
    const filterCategory = document.getElementById('filter-category').value;
    const filterLevel = document.getElementById('filter-level').value;
    const filterActor = document.getElementById('filter-actor').value;
    const filterSearch = document.getElementById('filter-search').value;

    let url = `${API_BASE}/audit_logs?page=${currentPage}&page_size=${pageSize}`;

    if (filterCategory) url += `&category=${filterCategory}`;
    if (filterLevel) url += `&level=${filterLevel}`;
    if (filterActor) url += `&actor=${encodeURIComponent(filterActor)}`;
    if (filterSearch) url += `&search=${encodeURIComponent(filterSearch)}`;

    // 应用时间范围
    const timeRange = document.getElementById('filter-time-range').value;
    if (timeRange !== 'custom') {
        const {startTime, endTime} = getTimeRangeBounds(timeRange);
        if (startTime) url += `&start_time=${startTime.toISOString()}`;
        if (endTime) url += `&end_time=${endTime.toISOString()}`;
    } else {
        const customStart = document.getElementById('filter-start-time').value;
        const customEnd = document.getElementById('filter-end-time').value;
        if (customStart) url += `&start_time=${new Date(customStart).toISOString()}`;
        if (customEnd) url += `&end_time=${new Date(customEnd).toISOString()}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();

        displayLogs(data.audit_logs || []);
        updatePagination(data);
    } catch (error) {
        console.error('Failed to load audit logs:', error);
        showError('加载审计日志失败');
    }
}

// 显示审计日志
function displayLogs(logs) {
    const tbody = document.getElementById('audit-logs-tbody');

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr class="log-row log-row-${log.level}">
            <td>${formatDateTime(log.timestamp)}</td>
            <td>${getLevelBadge(log.level)}</td>
            <td>${getCategoryLabel(log.category)}</td>
            <td>${getActionLabel(log.action)}</td>
            <td>${log.actor}</td>
            <td>${formatTarget(log.target_type, log.target_id)}</td>
            <td>${escapeHtml(log.message)}</td>
            <td>
                <button class="btn btn-sm" onclick="viewDetail('${log.audit_id}')">详情</button>
            </td>
        </tr>
    `).join('');
}

// 更新分页信息
function updatePagination(data) {
    totalPages = data.total_pages || 1;

    document.getElementById('page-info').textContent = `第 ${data.page} 页 / 共 ${totalPages} 页`;
    document.getElementById('prev-btn').disabled = currentPage <= 1;
    document.getElementById('next-btn').disabled = currentPage >= totalPages;
}

// 分页操作
function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        loadLogs();
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        loadLogs();
    }
}

// 过滤审计日志
function filterLogs() {
    currentPage = 1;
    loadLogs();
}

// 应用时间范围
function applyTimeRange() {
    const timeRange = document.getElementById('filter-time-range').value;
    const customTimeRange = document.getElementById('custom-time-range');

    if (timeRange === 'custom') {
        customTimeRange.style.display = 'flex';
    } else {
        customTimeRange.style.display = 'none';
    }

    currentPage = 1;
    loadLogs();
}

// 获取时间范围边界
function getTimeRangeBounds(range) {
    const now = new Date();
    let startTime, endTime = now;

    switch (range) {
        case '1h':
            startTime = new Date(now.getTime() - 60 * 60 * 1000);
            break;
        case '24h':
            startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
            break;
        case '7d':
            startTime = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            break;
        case '30d':
            startTime = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
            break;
        default:
            startTime = null;
            endTime = null;
    }

    return { startTime, endTime };
}

// 刷新审计日志
function refreshLogs() {
    loadStats();
    loadLogs();
}

// 导出审计日志
async function exportLogs(format) {
    try {
        const filterCategory = document.getElementById('filter-category').value;
        const filterLevel = document.getElementById('filter-level').value;

        let requestBody = {
            format: format,
            limit: 10000
        };

        if (filterCategory) requestBody.category = filterCategory;
        if (filterLevel) requestBody.level = filterLevel;

        // 应用时间范围
        const timeRange = document.getElementById('filter-time-range').value;
        if (timeRange !== 'custom') {
            const {startTime, endTime} = getTimeRangeBounds(timeRange);
            if (startTime) requestBody.start_time = startTime.toISOString();
            if (endTime) requestBody.end_time = endTime.toISOString();
        } else {
            const customStart = document.getElementById('filter-start-time').value;
            const customEnd = document.getElementById('filter-end-time').value;
            if (customStart) requestBody.start_time = new Date(customStart).toISOString();
            if (customEnd) requestBody.end_time = new Date(customEnd).toISOString();
        }

        const response = await fetch(`${API_BASE}/audit_logs/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (response.ok) {
            // 获取文件名
            const disposition = response.headers.get('Content-Disposition');
            let filename = `audit_logs_${new Date().toISOString()}.${format}`;

            if (disposition && disposition.indexOf('filename=') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }

            // 下载文件
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            showSuccess(`审计日志已导出为 ${format.toUpperCase()} 格式`);
        } else {
            const error = await response.json();
            showError(error.error?.message || '导出失败');
        }
    } catch (error) {
        console.error('Failed to export audit logs:', error);
        showError('导出审计日志失败');
    }
}

// 查看审计日志详情
async function viewDetail(auditId) {
    try {
        // 这里简化实现，直接显示已加载的数据
        // 在实际应用中，可能需要调用专门的详情API
        const response = await fetch(`${API_BASE}/audit_logs?page=1&page_size=1000`);
        const data = await response.json();
        const log = data.audit_logs.find(l => l.audit_id === auditId);

        if (!log) {
            showError('未找到审计日志');
            return;
        }

        const detailHtml = `
            <div class="detail-section">
                <h3>基本信息</h3>
                <table class="detail-table">
                    <tr><th>审计ID:</th><td><code>${log.audit_id}</code></td></tr>
                    <tr><th>时间:</th><td>${formatDateTime(log.timestamp)}</td></tr>
                    <tr><th>级别:</th><td>${getLevelBadge(log.level)}</td></tr>
                    <tr><th>分类:</th><td>${getCategoryLabel(log.category)}</td></tr>
                    <tr><th>动作:</th><td>${getActionLabel(log.action)}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>操作信息</h3>
                <table class="detail-table">
                    <tr><th>操作者:</th><td>${log.actor} (${log.actor_type})</td></tr>
                    <tr><th>目标类型:</th><td>${log.target_type}</td></tr>
                    <tr><th>目标ID:</th><td>${log.target_id ? `<code>${log.target_id}</code>` : '-'}</td></tr>
                    <tr><th>消息:</th><td>${escapeHtml(log.message)}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>关联信息</h3>
                <table class="detail-table">
                    <tr><th>关联任务:</th><td>${log.related_task_id ? `<code>${log.related_task_id}</code>` : '-'}</td></tr>
                    <tr><th>关联节点:</th><td>${log.related_node_id ? `<code>${log.related_node_id}</code>` : '-'}</td></tr>
                    <tr><th>关联资产:</th><td>${log.related_asset_id ? `<code>${log.related_asset_id}</code>` : '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>详细信息</h3>
                <pre class="json-display">${JSON.stringify(log.details, null, 2)}</pre>
            </div>

            <div class="detail-section">
                <h3>上下文信息</h3>
                <table class="detail-table">
                    <tr><th>IP地址:</th><td>${log.ip_address || '-'}</td></tr>
                    <tr><th>用户代理:</th><td>${log.user_agent || '-'}</td></tr>
                    <tr><th>请求ID:</th><td>${log.request_id ? `<code>${log.request_id}</code>` : '-'}</td></tr>
                </table>
            </div>
        `;

        document.getElementById('detail-content').innerHTML = detailHtml;
        document.getElementById('detail-modal').style.display = 'block';
    } catch (error) {
        console.error('Failed to load audit log details:', error);
        showError('加载审计日志详情失败');
    }
}

// 关闭详情模态框
function closeDetailModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// 工具函数
function getLevelBadge(level) {
    const badges = {
        'debug': '<span class="badge badge-secondary">调试</span>',
        'info': '<span class="badge badge-info">信息</span>',
        'warning': '<span class="badge badge-warning">警告</span>',
        'error': '<span class="badge badge-danger">错误</span>',
        'critical': '<span class="badge badge-dark">严重</span>'
    };
    return badges[level] || level;
}

function getCategoryLabel(category) {
    const labels = {
        'task': '任务',
        'node': '节点',
        'asset': '资产',
        'system': '系统',
        'security': '安全',
        'user': '用户'
    };
    return labels[category] || category;
}

function getActionLabel(action) {
    const labels = {
        'task_created': '任务创建',
        'task_assigned': '任务分配',
        'task_started': '任务开始',
        'task_succeeded': '任务成功',
        'task_failed': '任务失败',
        'task_cancelled': '任务取消',
        'node_online': '节点上线',
        'node_offline': '节点离线',
        'node_heartbeat': '节点心跳',
        'asset_registered': '资产注册',
        'system_started': '系统启动',
        'system_error': '系统错误'
    };
    return labels[action] || action;
}

function formatTarget(targetType, targetId) {
    if (!targetType) return '-';
    if (!targetId) return targetType;
    return `${targetType}: <code>${targetId}</code>`;
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function escapeHtml(text) {
    if (!text) return '-';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccess(message) {
    alert(message);
}

function showError(message) {
    alert('错误: ' + message);
}
