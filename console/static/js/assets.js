/**
 * HermesNexus Asset Management JavaScript
 * 资产管理前端逻辑
 */

// API 基础URL
const API_BASE = '/api/v1';

// 当前状态
let currentPage = 1;
let pageSize = 20;
let totalPages = 1;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadAssets();
    setupFormHandlers();
});

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/assets/stats`);
        const stats = await response.json();

        document.getElementById('total-assets').textContent = stats.total_assets || 0;
        document.getElementById('active-nodes').textContent = stats.active_nodes || 0;
        document.getElementById('inactive-nodes').textContent = stats.inactive_nodes || 0;
        document.getElementById('edge-nodes').textContent = stats.by_type?.edge_node || 0;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// 加载资产列表
async function loadAssets() {
    const filterType = document.getElementById('filter-type').value;
    const filterStatus = document.getElementById('filter-status').value;
    const filterSearch = document.getElementById('filter-search').value;

    let url = `${API_BASE}/assets?page=${currentPage}&page_size=${pageSize}`;

    if (filterType) url += `&asset_type=${filterType}`;
    if (filterStatus) url += `&status=${filterStatus}`;
    if (filterSearch) url += `&search=${encodeURIComponent(filterSearch)}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        displayAssets(data.assets || []);
        updatePagination(data);
    } catch (error) {
        console.error('Failed to load assets:', error);
        showError('加载资产列表失败');
    }
}

// 显示资产列表
function displayAssets(assets) {
    const tbody = document.getElementById('assets-tbody');

    if (assets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = assets.map(asset => `
        <tr>
            <td><code>${asset.asset_id}</code></td>
            <td><strong>${asset.name}</strong></td>
            <td>${getAssetTypeLabel(asset.asset_type)}</td>
            <td>${getStatusBadge(asset.status)}</td>
            <td>${asset.metadata?.ip_address || '-'}</td>
            <td>${asset.associated_node_id ? `<code>${asset.associated_node_id}</code>` : '-'}</td>
            <td>${asset.last_heartbeat ? formatDate(asset.last_heartbeat) : '-'}</td>
            <td>
                <button class="btn btn-sm" onclick="viewAsset('${asset.asset_id}')">查看</button>
                <button class="btn btn-sm" onclick="editAsset('${asset.asset_id}')">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteAsset('${asset.asset_id}')">删除</button>
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
        loadAssets();
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        loadAssets();
    }
}

// 过滤资产
function filterAssets() {
    currentPage = 1;
    loadAssets();
}

// 刷新资产列表
function refreshAssets() {
    loadStats();
    loadAssets();
}

// 显示创建模态框
function showCreateModal() {
    document.getElementById('modal-title').textContent = '新增资产';
    document.getElementById('asset-form').reset();
    document.getElementById('asset-id').value = '';
    document.getElementById('asset-modal').style.display = 'block';
}

// 编辑资产
async function editAsset(assetId) {
    try {
        const response = await fetch(`${API_BASE}/assets/${assetId}`);
        const asset = await response.json();

        document.getElementById('modal-title').textContent = '编辑资产';
        document.getElementById('asset-id').value = asset.asset_id;
        document.getElementById('asset-name').value = asset.name;
        document.getElementById('asset-type').value = asset.asset_type;
        document.getElementById('asset-description').value = asset.description || '';
        document.getElementById('asset-ip').value = asset.metadata?.ip_address || '';
        document.getElementById('asset-hostname').value = asset.metadata?.hostname || '';
        document.getElementById('asset-ssh-port').value = asset.metadata?.ssh_port || 22;
        document.getElementById('asset-ssh-user').value = asset.metadata?.ssh_username || '';

        document.getElementById('asset-modal').style.display = 'block';
    } catch (error) {
        console.error('Failed to load asset:', error);
        showError('加载资产详情失败');
    }
}

// 查看资产详情
async function viewAsset(assetId) {
    try {
        const response = await fetch(`${API_BASE}/assets/${assetId}`);
        const asset = await response.json();

        const detailHtml = `
            <div class="detail-section">
                <h3>基本信息</h3>
                <table class="detail-table">
                    <tr><th>资产ID:</th><td><code>${asset.asset_id}</code></td></tr>
                    <tr><th>名称:</th><td>${asset.name}</td></tr>
                    <tr><th>类型:</th><td>${getAssetTypeLabel(asset.asset_type)}</td></tr>
                    <tr><th>状态:</th><td>${getStatusBadge(asset.status)}</td></tr>
                    <tr><th>描述:</th><td>${asset.description || '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>网络信息</h3>
                <table class="detail-table">
                    <tr><th>IP地址:</th><td>${asset.metadata?.ip_address || '-'}</td></tr>
                    <tr><th>主机名:</th><td>${asset.metadata?.hostname || '-'}</td></tr>
                    <tr><th>MAC地址:</th><td>${asset.metadata?.mac_address || '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>SSH配置</h3>
                <table class="detail-table">
                    <tr><th>SSH端口:</th><td>${asset.metadata?.ssh_port || '-'}</td></tr>
                    <tr><th>SSH用户名:</th><td>${asset.metadata?.ssh_username || '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>系统信息</h3>
                <table class="detail-table">
                    <tr><th>操作系统:</th><td>${asset.metadata?.os_type || '-'} ${asset.metadata?.os_version || ''}</td></tr>
                    <tr><th>CPU核心:</th><td>${asset.metadata?.cpu_cores || '-'}</td></tr>
                    <tr><th>内存:</th><td>${asset.metadata?.memory_gb || '-'} GB</td></tr>
                    <tr><th>磁盘:</th><td>${asset.metadata?.disk_gb || '-'} GB</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>关联信息</h3>
                <table class="detail-table">
                    <tr><th>关联节点:</th><td>${asset.associated_node_id ? `<code>${asset.associated_node_id}</code>` : '-'}</td></tr>
                    <tr><th>最后心跳:</th><td>${asset.last_heartbeat ? formatDate(asset.last_heartbeat) : '-'}</td></tr>
                    <tr><th>创建时间:</th><td>${formatDate(asset.created_at)}</td></tr>
                    <tr><th>更新时间:</th><td>${formatDate(asset.updated_at)}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>标签和分组</h3>
                <div class="tags">
                    ${(asset.metadata?.tags || []).map(tag => `<span class="tag">${tag}</span>`).join('') || '-'}
                </div>
                <div class="groups">
                    <strong>分组:</strong>
                    ${(asset.metadata?.groups || []).join(', ') || '-'}
                </div>
            </div>
        `;

        document.getElementById('detail-content').innerHTML = detailHtml;
        document.getElementById('detail-modal').style.display = 'block';
    } catch (error) {
        console.error('Failed to load asset details:', error);
        showError('加载资产详情失败');
    }
}

// 删除资产
async function deleteAsset(assetId) {
    if (!confirm('确定要删除此资产吗？')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/assets/${assetId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showSuccess('资产删除成功');
            loadAssets();
        } else {
            const error = await response.json();
            showError(error.error?.message || '删除失败');
        }
    } catch (error) {
        console.error('Failed to delete asset:', error);
        showError('删除资产失败');
    }
}

// 设置表单处理
function setupFormHandlers() {
    document.getElementById('asset-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const assetId = document.getElementById('asset-id').value;
        const isEdit = !!assetId;

        const data = {
            name: document.getElementById('asset-name').value,
            asset_type: document.getElementById('asset-type').value,
            description: document.getElementById('asset-description').value || null,
            metadata: {
                ip_address: document.getElementById('asset-ip').value || null,
                hostname: document.getElementById('asset-hostname').value || null,
                ssh_port: parseInt(document.getElementById('asset-ssh-port').value) || 22,
                ssh_username: document.getElementById('asset-ssh-user').value || null
            }
        };

        try {
            const url = isEdit ? `${API_BASE}/assets/${assetId}` : `${API_BASE}/assets`;
            const method = isEdit ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                showSuccess(isEdit ? '资产更新成功' : '资产创建成功');
                closeModal();
                loadAssets();
            } else {
                const error = await response.json();
                showError(error.error?.message || '操作失败');
            }
        } catch (error) {
            console.error('Failed to save asset:', error);
            showError('保存资产失败');
        }
    });
}

// 关闭模态框
function closeModal() {
    document.getElementById('asset-modal').style.display = 'none';
}

function closeDetailModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// 工具函数
function getAssetTypeLabel(type) {
    const labels = {
        'edge_node': '边缘节点',
        'linux_host': 'Linux 主机',
        'network_device': '网络设备',
        'iot_device': 'IoT 设备'
    };
    return labels[type] || type;
}

function getStatusBadge(status) {
    const badges = {
        'registered': '<span class="badge badge-info">已注册</span>',
        'active': '<span class="badge badge-success">活跃</span>',
        'inactive': '<span class="badge badge-warning">非活跃</span>',
        'decommissioned': '<span class="badge badge-danger">已退役</span>'
    };
    return badges[status] || status;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function showSuccess(message) {
    alert(message); // 简化实现，生产环境应使用更好的通知组件
}

function showError(message) {
    alert('错误: ' + message);
}
