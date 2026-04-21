/**
 * HermesNexus Node Status JavaScript
 * 节点状态监控前端逻辑
 */

// API 基础URL
const API_BASE = '/api/v1';

// 节点数据缓存
let nodesData = [];
let filteredNodes = [];

// 分页和排序状态
let currentPage = 1;
let pageSize = 20;
let sortField = 'last_heartbeat';
let sortOrder = 'desc';
let totalPages = 1;

// 筛选条件
let filters = {
    status: '',
    nodeType: '',
    search: '',
    location: '',
    tags: []
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadNodes();
    // 自动刷新（每30秒）
    setInterval(loadNodes, 30000);
});

// 加载节点数据
async function loadNodes() {
    try {
        showLoading();

        const filterStatus = document.getElementById('filter-status').value;
        const filterSearch = document.getElementById('filter-search').value.trim();

        filters.status = filterStatus;
        filters.search = filterSearch;

        // 使用v1.2增强节点查询API
        const requestBody = {
            page: currentPage,
            page_size: pageSize,
            sort_by: sortField,
            sort_order: sortOrder,
            include_heartbeat_stats: true,
            include_task_summary: true,
            include_audit_summary: true
        };

        // 添加筛选参数
        if (filters.status) {
            requestBody.status = [filters.status];
        }
        if (filters.nodeType) {
            requestBody.node_type = filters.nodeType;
        }
        if (filters.search) {
            requestBody.search = filters.search;
        }

        const response = await fetch(`${API_BASE}/nodes/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // 处理节点数据
        processNodesDataV2(data);

        hideLoading();
    } catch (error) {
        console.error('Failed to load nodes:', error);
        showError('加载节点数据失败');
        hideLoading();
    }
}

// 处理节点数据 (v1.2新版本)
function processNodesDataV2(data) {
    // 更新分页信息
    currentPage = data.page || 1;
    totalPages = data.total_pages || 1;
    nodesData = data.nodes || [];

    // 更新统计信息
    document.getElementById('total-nodes').textContent = data.total || 0;

    // 从健康状态摘要中统计
    const healthSummary = data.health_summary || {};
    document.getElementById('online-nodes').textContent = healthSummary.healthy || 0;
    document.getElementById('offline-nodes').textContent = healthSummary.unknown || 0;
    document.getElementById('busy-nodes').textContent = healthSummary.degraded || 0;

    filteredNodes = nodesData;
    renderNodes();

    // 更新分页控件
    updatePaginationControls();
}

// 过滤节点
function filterNodes() {
    currentPage = 1;
    loadNodes();
}

// 渲染节点
function renderNodes() {
    const viewMode = document.getElementById('view-mode').value;

    if (viewMode === 'cards') {
        renderCardsView();
        document.getElementById('nodes-cards-view').style.display = 'grid';
        document.getElementById('nodes-table-view').style.display = 'none';
    } else {
        renderTableView();
        document.getElementById('nodes-cards-view').style.display = 'none';
        document.getElementById('nodes-table-view').style.display = 'block';
    }
}

// 渲染卡片视图
function renderCardsView() {
    const container = document.getElementById('nodes-cards-view');

    if (filteredNodes.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无节点数据</div>';
        return;
    }

    container.innerHTML = filteredNodes.map(node => {
        const statusSummary = node.status_summary || {};
        const taskSummary = node.task_summary || {};
        const healthStatus = statusSummary.health_status || 'unknown';
        const isOnline = statusSummary.is_online || false;
        const canAcceptTasks = statusSummary.can_accept_tasks || false;
        const nodeId = JSON.stringify(node.node_id || '');

        return `
        <div class="node-card" onclick="viewNodeDetail(${nodeId})">
            <div class="node-card-header">
                <div class="node-status ${getHealthStatusClass(healthStatus)}">
                    ${getHealthStatusText(healthStatus)}
                </div>
                <div class="node-actions">
                    <button class="btn btn-icon" onclick="event.stopPropagation(); viewNodeDetail(${nodeId})">
                        <i class="fas fa-info-circle"></i>
                    </button>
                </div>
            </div>

            <div class="node-card-body">
                <div class="node-name">${escapeHtml(node.node_name)}</div>
                <div class="node-id"><code>${escapeHtml(node.node_id)}</code></div>

                <div class="node-info">
                    <div class="info-item">
                        <i class="fas fa-server"></i>
                        <span>${getNodeTypeLabel(node.node_type)}</span>
                    </div>
                    ${node.location ? `
                        <div class="info-item">
                            <i class="fas fa-map-marker-alt"></i>
                            <span>${escapeHtml(node.location)}</span>
                        </div>
                    ` : ''}
                </div>

                <div class="node-status-info">
                    <div class="status-item">
                        <i class="fas fa-heartbeat ${isOnline ? 'text-success' : 'text-danger'}"></i>
                        <span>${isOnline ? '在线' : '离线'}</span>
                    </div>
                    <div class="status-item">
                        <i class="fas fa-tasks ${canAcceptTasks ? 'text-success' : 'text-warning'}"></i>
                        <span>${taskSummary.running_tasks || 0}/${taskSummary.max_concurrent_tasks || 3} 任务</span>
                    </div>
                </div>

                ${node.last_heartbeat ? `
                    <div class="node-heartbeat">
                        <i class="fas fa-clock"></i>
                        <span>最后心跳: ${formatDateTime(node.last_heartbeat)}</span>
                    </div>
                ` : ''}
            </div>

            <div class="node-card-footer">
                <div class="node-tags">
                    ${(node.tags || []).slice(0, 3).map(tag =>
                        `<span class="tag tag-small">${escapeHtml(tag)}</span>`
                    ).join('')}
                </div>
            </div>
        </div>
    `}).join('');
}

// 渲染表格视图
function renderTableView() {
    const tbody = document.getElementById('nodes-table-body');

    if (filteredNodes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">暂无节点数据</td></tr>';
        return;
    }

    tbody.innerHTML = filteredNodes.map(node => {
        const statusSummary = node.status_summary || {};
        const taskSummary = node.task_summary || {};
        const healthStatus = statusSummary.health_status || 'unknown';
        const isOnline = statusSummary.is_online || false;
        const nodeId = JSON.stringify(node.node_id || '');

        return `
        <tr>
            <td><code>${escapeHtml(node.node_id)}</code></td>
            <td><strong>${escapeHtml(node.node_name)}</strong></td>
            <td>${getHealthStatusBadge(healthStatus)}</td>
            <td>${getNodeTypeLabel(node.node_type)}</td>
            <td>${taskSummary.running_tasks || 0}/${taskSummary.max_concurrent_tasks || 3}</td>
            <td>${isOnline ? '<span class="badge badge-success">在线</span>' : '<span class="badge badge-danger">离线</span>'}</td>
            <td>${node.last_heartbeat ? formatDateTime(node.last_heartbeat) : '-'}</td>
            <td>
                <button class="btn btn-sm" onclick="viewNodeDetail(${nodeId})">查看</button>
            </td>
        </tr>
    `}).join('');
}

// 查看节点详情
async function viewNodeDetail(nodeId) {
    try {
        // 使用新的增强节点详情API
        const response = await fetch(`${API_BASE}/nodes/${encodeURIComponent(nodeId)}?include_details=true`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const node = await response.json();
        const statusSummary = node.status_summary || {};
        const taskSummary = node.task_summary || {};
        const heartbeatStats = node.heartbeat_stats || {};
        const auditSummary = node.audit_summary || {};

        const detailHtml = `
            <div class="detail-section">
                <h3>基本信息</h3>
                <table class="detail-table">
                    <tr><th>节点ID:</th><td><code>${escapeHtml(node.node_id)}</code></td></tr>
                    <tr><th>节点名称:</th><td>${escapeHtml(node.node_name)}</td></tr>
                    <tr><th>节点类型:</th><td>${getNodeTypeLabel(node.node_type)}</td></tr>
                    <tr><th>状态:</th><td>${getHealthStatusBadge(statusSummary.health_status || 'unknown')}</td></tr>
                    <tr><th>位置:</th><td>${node.location ? escapeHtml(node.location) : '-'}</td></tr>
                    <tr><th>描述:</th><td>${node.description ? escapeHtml(node.description) : '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>状态摘要</h3>
                <table class="detail-table">
                    <tr><th>在线状态:</th><td>${statusSummary.is_online ? '<span class="badge badge-success">在线</span>' : '<span class="badge badge-danger">离线</span>'}</td></tr>
                    <tr><th>活跃状态:</th><td>${statusSummary.is_active ? '<span class="badge badge-success">活跃</span>' : '<span class="badge badge-secondary">非活跃</span>'}</td></tr>
                    <tr><th>可接受任务:</th><td>${statusSummary.can_accept_tasks ? '<span class="badge badge-success">是</span>' : '<span class="badge badge-warning">否</span>'}</td></tr>
                    <tr><th>健康状态:</th><td>${getHealthStatusBadge(statusSummary.health_status || 'unknown')}</td></tr>
                    <tr><th>最后心跳:</th><td>${node.last_heartbeat ? formatDateTime(node.last_heartbeat) : '-'}</td></tr>
                    ${statusSummary.last_heartbeat_age_seconds ? `
                        <tr><th>心跳距现在:</th><td>${formatDuration(statusSummary.last_heartbeat_age_seconds)}前</td></tr>
                    ` : ''}
                </table>
            </div>

            <div class="detail-section">
                <h3>任务摘要</h3>
                <table class="detail-table">
                    <tr><th>总任务数:</th><td>${taskSummary.total_tasks || 0}</td></tr>
                    <tr><th>运行中:</th><td>${taskSummary.running_tasks || 0}</td></tr>
                    <tr><th>已完成:</th><td>${taskSummary.completed_tasks || 0}</td></tr>
                    <tr><th>失败:</th><td>${taskSummary.failed_tasks || 0}</td></tr>
                    <tr><th>当前负载:</th><td>${taskSummary.current_task_load || 0}/${taskSummary.max_concurrent_tasks || 3}</td></tr>
                    <tr><th>任务利用率:</th><td>${taskSummary.task_utilization_percent || 0}%</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>心跳统计</h3>
                <table class="detail-table">
                    <tr><th>总心跳次数:</th><td>${heartbeatStats.total_heartbeats || 0}</td></tr>
                    <tr><th>成功心跳:</th><td>${heartbeatStats.successful_heartbeats || 0}</td></tr>
                    <tr><th>失败心跳:</th><td>${heartbeatStats.failed_heartbeats || 0}</td></tr>
                    <tr><th>平均间隔:</th><td>${heartbeatStats.avg_heartbeat_interval_seconds ? Math.round(heartbeatStats.avg_heartbeat_interval_seconds) + '秒' : '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>能力信息</h3>
                <table class="detail-table">
                    <tr><th>最大并发任务:</th><td>${node.max_concurrent_tasks || 3}</td></tr>
                    <tr><th>支持的协议:</th><td>${(node.capabilities?.protocols || []).map(escapeHtml).join(', ') || '-'}</td></tr>
                    <tr><th>支持的任务类型:</th><td>${(node.capabilities?.supported_task_types || []).map(escapeHtml).join(', ') || '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>标签</h3>
                <div class="tags">
                    ${(node.tags || []).map(tag =>
                        `<span class="tag">${escapeHtml(tag)}</span>`
                    ).join('') || '<span class="no-tags">无标签</span>'}
                </div>
            </div>
        `;

        document.getElementById('node-detail-content').innerHTML = detailHtml;
        document.getElementById('node-detail-modal').style.display = 'block';
    } catch (error) {
        console.error('Failed to load node details:', error);
        showError('加载节点详情失败');
    }
}

// 关闭详情模态框
function closeNodeDetailModal() {
    document.getElementById('node-detail-modal').style.display = 'none';
}

// 切换视图模式
function changeViewMode() {
    renderNodes();
}

// 刷新节点数据
function refreshNodes() {
    loadNodes();
}

// 导出节点数据
function exportNodes() {
    // 简化实现：导出为JSON
    const dataStr = JSON.stringify(filteredNodes, null, 2);
    const blob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nodes_export_${new Date().toISOString()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 工具函数
function getHealthStatusClass(healthStatus) {
    const statusMap = {
        'healthy': 'success',
        'degraded': 'warning',
        'error': 'danger',
        'unknown': 'secondary',
        'inactive': 'dark'
    };
    return statusMap[healthStatus] || 'secondary';
}

function getHealthStatusText(healthStatus) {
    const statusMap = {
        'healthy': '健康',
        'degraded': '降级',
        'error': '错误',
        'unknown': '未知',
        'inactive': '非活跃'
    };
    return statusMap[healthStatus] || escapeHtml(healthStatus);
}

function getHealthStatusBadge(healthStatus) {
    const badges = {
        'healthy': '<span class="badge badge-success">健康</span>',
        'degraded': '<span class="badge badge-warning">降级</span>',
        'error': '<span class="badge badge-danger">错误</span>',
        'unknown': '<span class="badge badge-secondary">未知</span>',
        'inactive': '<span class="badge badge-dark">非活跃</span>'
    };
    return badges[healthStatus] || escapeHtml(healthStatus);
}

function getNodeTypeLabel(nodeType) {
    const labels = {
        'physical': '物理机',
        'vm': '虚拟机',
        'container': '容器',
        'edge': '边缘设备'
    };
    return labels[nodeType] || escapeHtml(nodeType);
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds}秒`;
    } else if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}分钟`;
    } else if (seconds < 86400) {
        return `${Math.floor(seconds / 3600)}小时`;
    } else {
        return `${Math.floor(seconds / 86400)}天`;
    }
}

function updatePaginationControls() {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    if (pageInfo) {
        pageInfo.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;
    }
    if (prevBtn) {
        prevBtn.disabled = currentPage <= 1;
    }
    if (nextBtn) {
        nextBtn.disabled = currentPage >= totalPages;
    }
}

// 分页导航函数
function goToPage(page) {
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        loadNodes();
    }
}

function previousPage() {
    goToPage(currentPage - 1);
}

function nextPage() {
    goToPage(currentPage + 1);
}

function getAssetTypeLabel(type) {
    const labels = {
        'edge_node': '边缘节点',
        'linux_host': 'Linux 主机',
        'network_device': '网络设备',
        'iot_device': 'IoT 设备'
    };
    return labels[type] || escapeHtml(type);
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading() {
    // 显示加载状态
}

function hideLoading() {
    // 隐藏加载状态
}

function showError(message) {
    alert('错误: ' + message);
}