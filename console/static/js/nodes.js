/**
 * HermesNexus Node Status JavaScript
 * 节点状态监控前端逻辑
 */

// API 基础URL
const API_BASE = '/api/v1';

// 节点数据缓存
let nodesData = [];
let filteredNodes = [];

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

        // 并行加载多个API
        const [assetsResponse, tasksResponse] = await Promise.all([
            fetch(`${API_BASE}/assets`),
            fetch(`${API_BASE}/tasks/stats`)
        ]);

        const assets = await assetsResponse.json();
        const taskStats = await tasksResponse.json();

        // 处理节点数据
        processNodesData(assets, taskStats);

        hideLoading();
    } catch (error) {
        console.error('Failed to load nodes:', error);
        showError('加载节点数据失败');
        hideLoading();
    }
}

// 处理节点数据
function processNodesData(assets, taskStats) {
    // 从资产数据中提取节点信息
    nodesData = assets.assets || [];

    // 统计节点运行任务数
    const runningTasks = taskStats.running_tasks || 0;
    const busyNodes = Math.min(runningTasks, nodesData.length);

    // 更新统计信息
    document.getElementById('total-nodes').textContent = nodesData.length;
    document.getElementById('online-nodes').textContent = assets.by_status?.active || 0;
    document.getElementById('offline-nodes').textContent = assets.by_status?.inactive || 0;
    document.getElementById('busy-nodes').textContent = busyNodes;

    // 应用当前过滤
    filterNodes();
}

// 过滤节点
function filterNodes() {
    const filterStatus = document.getElementById('filter-status').value;
    const filterSearch = document.getElementById('filter-search').value.toLowerCase();

    filteredNodes = nodesData.filter(node => {
        // 状态过滤
        if (filterStatus) {
            const statusMap = {
                'online': 'active',
                'offline': 'inactive',
                'busy': 'active' // 简化实现，实际需要检查任务状态
            };
            if (node.status !== statusMap[filterStatus]) {
                return false;
            }
        }

        // 搜索过滤
        if (filterSearch) {
            const searchText = filterSearch.toLowerCase();
            if (node.name && !node.name.toLowerCase().includes(searchText) &&
                node.asset_id && !node.asset_id.toLowerCase().includes(searchText)) {
                return false;
            }
        }

        return true;
    });

    renderNodes();
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

    container.innerHTML = filteredNodes.map(node => `
        <div class="node-card" onclick="viewNodeDetail('${node.asset_id}')">
            <div class="node-card-header">
                <div class="node-status ${getStatusClass(node.status)}">
                    ${getStatusText(node.status)}
                </div>
                <div class="node-actions">
                    <button class="btn btn-icon" onclick="event.stopPropagation(); viewNodeDetail('${node.asset_id}')">
                        <i class="fas fa-info-circle"></i>
                    </button>
                </div>
            </div>

            <div class="node-card-body">
                <div class="node-name">${escapeHtml(node.name)}</div>
                <div class="node-id"><code>${node.asset_id}</code></div>

                <div class="node-info">
                    <div class="info-item">
                        <i class="fas fa-box"></i>
                        <span>${getAssetTypeLabel(node.asset_type)}</span>
                    </div>
                    ${node.metadata?.ip_address ? `
                        <div class="info-item">
                            <i class="fas fa-network-wired"></i>
                            <span>${node.metadata.ip_address}</span>
                        </div>
                    ` : ''}
                </div>

                ${node.associated_node_id ? `
                    <div class="node-association">
                        <i class="fas fa-link"></i>
                        <span>关联节点: <code>${node.associated_node_id}</code></span>
                    </div>
                ` : ''}

                ${node.last_heartbeat ? `
                    <div class="node-heartbeat">
                        <i class="fas fa-heartbeat"></i>
                        <span>最后心跳: ${formatDateTime(node.last_heartbeat)}</span>
                    </div>
                ` : ''}
            </div>

            <div class="node-card-footer">
                <div class="node-tags">
                    ${(node.metadata?.tags || []).slice(0, 3).map(tag =>
                        `<span class="tag tag-small">${escapeHtml(tag)}</span>`
                    ).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

// 渲染表格视图
function renderTableView() {
    const tbody = document.getElementById('nodes-table-body');

    if (filteredNodes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">暂无节点数据</td></tr>';
        return;
    }

    tbody.innerHTML = filteredNodes.map(node => `
        <tr>
            <td><code>${node.asset_id}</code></td>
            <td><strong>${escapeHtml(node.name)}</strong></td>
            <td>${getStatusBadge(node.status)}</td>
            <td>${getAssetTypeLabel(node.asset_type)}</td>
            <td>${node.associated_node_id ? `<code>${node.associated_node_id}</code>` : '-'}</td>
            <td>${node.last_heartbeat ? formatDateTime(node.last_heartbeat) : '-'}</td>
            <td>${node.metadata?.os_version || '-'}</td>
            <td>
                <button class="btn btn-sm" onclick="viewNodeDetail('${node.asset_id}')">查看</button>
            </td>
        </tr>
    `).join('');
}

// 查看节点详情
async function viewNodeDetail(nodeId) {
    try {
        // 查找节点数据
        const node = nodesData.find(n => n.asset_id === nodeId);
        if (!node) {
            showError('未找到节点数据');
            return;
        }

        // 获取节点的审计日志
        const auditResponse = await fetch(`${API_BASE}/audit_logs/assets/${nodeId}?limit=10`);
        const auditLogs = await auditResponse.json();

        const detailHtml = `
            <div class="detail-section">
                <h3>基本信息</h3>
                <table class="detail-table">
                    <tr><th>节点ID:</th><td><code>${node.asset_id}</code></td></tr>
                    <tr><th>节点名称:</th><td>${escapeHtml(node.name)}</td></tr>
                    <tr><th>节点类型:</th><td>${getAssetTypeLabel(node.asset_type)}</td></tr>
                    <tr><th>状态:</th><td>${getStatusBadge(node.status)}</td></tr>
                    <tr><th>描述:</th><td>${node.description || '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>网络信息</h3>
                <table class="detail-table">
                    <tr><th>IP地址:</th><td>${node.metadata?.ip_address || '-'}</td></tr>
                    <tr><th>主机名:</th><td>${node.metadata?.hostname || '-'}</td></tr>
                    <tr><th>MAC地址:</th><td>${node.metadata?.mac_address || '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>系统信息</h3>
                <table class="detail-table">
                    <tr><th>操作系统:</th><td>${node.metadata?.os_type || '-'} ${node.metadata?.os_version || ''}</td></tr>
                    <tr><th>CPU核心:</th><td>${node.metadata?.cpu_cores || '-'}</td></tr>
                    <tr><th>内存:</th><td>${node.metadata?.memory_gb ? node.metadata.memory_gb + ' GB' : '-'}</td></tr>
                    <tr><th>磁盘:</th><td>${node.metadata?.disk_gb ? node.metadata.disk_gb + ' GB' : '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>关联信息</h3>
                <table class="detail-table">
                    <tr><th>关联节点:</th><td>${node.associated_node_id ? `<code>${node.associated_node_id}</code>` : '-'}</td></tr>
                    <tr><th>最后心跳:</th><td>${node.last_heartbeat ? formatDateTime(node.last_heartbeat) : '-'}</td></tr>
                    <tr><th>注册时间:</th><td>${formatDateTime(node.created_at)}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>最近活动</h3>
                <div class="activity-list">
                    ${auditLogs.length > 0 ? auditLogs.slice(0, 5).map(log => `
                        <div class="activity-item">
                            <i class="fas fa-circle status-dot-${log.level}"></i>
                            <div class="activity-content">
                                <div class="activity-message">${escapeHtml(log.message)}</div>
                                <div class="activity-time">${formatDateTime(log.timestamp)}</div>
                            </div>
                        </div>
                    `).join('') : '<div class="no-activity">暂无活动记录</div>'}
                </div>
            </div>

            <div class="detail-section">
                <h3>标签</h3>
                <div class="tags">
                    ${(node.metadata?.tags || []).map(tag =>
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
function getStatusClass(status) {
    const statusMap = {
        'active': 'success',
        'inactive': 'danger',
        'registered': 'info',
        'decommissioned': 'dark'
    };
    return statusMap[status] || 'secondary';
}

function getStatusText(status) {
    const statusMap = {
        'active': '在线',
        'inactive': '离线',
        'registered': '已注册',
        'decommissioned': '已退役'
    };
    return statusMap[status] || status;
}

function getStatusBadge(status) {
    const badges = {
        'active': '<span class="badge badge-success">在线</span>',
        'inactive': '<span class="badge badge-danger">离线</span>',
        'registered': '<span class="badge badge-info">已注册</span>',
        'decommissioned': '<span class="badge badge-dark">已退役</span>'
    };
    return badges[status] || status;
}

function getAssetTypeLabel(type) {
    const labels = {
        'edge_node': '边缘节点',
        'linux_host': 'Linux 主机',
        'network_device': '网络设备',
        'iot_device': 'IoT 设备'
    };
    return labels[type] || type;
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