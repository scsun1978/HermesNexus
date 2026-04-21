/**
 * HermesNexus Task Management JavaScript
 * 任务管理前端逻辑
 */

// API 基础URL
const API_BASE = '/api/v1';

// HTML转义函数 - 防止XSS攻击
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) {
        return '';
    }
    return String(unsafe)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// 当前状态
let currentPage = 1;
let pageSize = 20;
let totalPages = 1;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTasks();
    setupFormHandlers();
});

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/tasks/stats`);
        const stats = await response.json();

        document.getElementById('total-tasks').textContent = stats.total_tasks || 0;
        document.getElementById('running-tasks').textContent = stats.running_tasks || 0;
        document.getElementById('pending-tasks').textContent = stats.pending_tasks || 0;
        document.getElementById('success-rate').textContent = (stats.success_rate || 0) + '%';
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// 加载任务列表
async function loadTasks() {
    const filterType = document.getElementById('filter-type').value;
    const filterStatus = document.getElementById('filter-status').value;
    const filterPriority = document.getElementById('filter-priority').value;
    const filterSearch = document.getElementById('filter-search').value;

    let url = `${API_BASE}/tasks?page=${currentPage}&page_size=${pageSize}`;

    if (filterType) url += `&task_type=${filterType}`;
    if (filterStatus) url += `&status=${filterStatus}`;
    if (filterPriority) url += `&priority=${filterPriority}`;
    if (filterSearch) url += `&search=${encodeURIComponent(filterSearch)}`;

    const isFirstLoad = document.querySelector('.loading-indicator');
    const loadingId = isFirstLoad ? showLoading('正在加载任务列表...') : null;

    try {
        const response = await fetch(url);
        const data = await response.json();

        displayTasks(data.tasks || []);
        updatePagination(data);

        if (loadingId) hideLoading(loadingId);
    } catch (error) {
        console.error('Failed to load tasks:', error);
        if (loadingId) hideLoading(loadingId);
        showError('加载任务列表失败');
    }
}

// 显示任务列表
function displayTasks(tasks) {
    const tbody = document.getElementById('tasks-tbody');

    if (tasks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = tasks.map(task => `
        <tr>
            <td><code>${escapeHtml(task.task_id)}</code></td>
            <td><strong>${escapeHtml(task.name)}</strong></td>
            <td>${getTaskTypeLabel(task.task_type)}</td>
            <td>${getStatusBadge(task.status)}</td>
            <td>${getPriorityBadge(task.priority)}</td>
            <td><code>${escapeHtml(task.target_asset_id)}</code></td>
            <td>${task.target_node_id ? `<code>${escapeHtml(task.target_node_id)}</code>` : '-'}</td>
            <td>${formatDate(task.created_at)}</td>
            <td>
                <button class="btn btn-sm" onclick="viewTask('${escapeHtml(task.task_id)}')">查看</button>
                ${task.status === 'pending' || task.status === 'assigned' ? `
                    <button class="btn btn-sm btn-warning" onclick="cancelTask('${escapeHtml(task.task_id)}')">取消</button>
                ` : ''}
                ${task.status === 'succeeded' || task.status === 'failed' ? `
                    <button class="btn btn-sm btn-primary" onclick="viewResult('${escapeHtml(task.task_id)}')">结果</button>
                ` : ''}
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
        loadTasks();
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        loadTasks();
    }
}

// 过滤任务
function filterTasks() {
    currentPage = 1;
    loadTasks();
}

// 刷新任务列表
function refreshTasks() {
    loadStats();
    loadTasks();
}

// 显示创建模态框
function showCreateModal() {
    document.getElementById('modal-title').textContent = '新增任务';
    document.getElementById('task-form').reset();
    document.getElementById('task-id').value = '';
    document.getElementById('task-modal').style.display = 'block';
}

// 查看任务详情
async function viewTask(taskId) {
    try {
        const response = await fetch(`${API_BASE}/tasks/${taskId}`);
        const task = await response.json();

        const detailHtml = `
            <div class="detail-section">
                <h3>基本信息</h3>
                <table class="detail-table">
                    <tr><th>任务ID:</th><td><code>${task.task_id}</code></td></tr>
                    <tr><th>名称:</th><td>${task.name}</td></tr>
                    <tr><th>类型:</th><td>${getTaskTypeLabel(task.task_type)}</td></tr>
                    <tr><th>状态:</th><td>${getStatusBadge(task.status)}</td></tr>
                    <tr><th>优先级:</th><td>${getPriorityBadge(task.priority)}</td></tr>
                    <tr><th>描述:</th><td>${task.description || '-'}</td></tr>
                    <tr><th>创建者:</th><td>${task.created_by}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>目标信息</h3>
                <table class="detail-table">
                    <tr><th>目标资产:</th><td><code>${task.target_asset_id}</code></td></tr>
                    <tr><th>目标节点:</th><td>${task.target_node_id ? `<code>${task.target_node_id}</code>` : '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>执行配置</h3>
                <table class="detail-table">
                    <tr><th>命令:</th><td><code>${task.command}</code></td></tr>
                    <tr><th>参数:</th><td>${task.arguments.join(' ') || '-'}</td></tr>
                    <tr><th>工作目录:</th><td>${task.working_dir || '-'}</td></tr>
                    <tr><th>超时时间:</th><td>${task.timeout}秒</td></tr>
                    <tr><th>重试次数:</th><td>${task.retry_count}</td></tr>
                    <tr><th>重试延迟:</th><td>${task.retry_delay}秒</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>时间信息</h3>
                <table class="detail-table">
                    <tr><th>创建时间:</th><td>${formatDate(task.created_at)}</td></tr>
                    <tr><th>计划执行时间:</th><td>${task.scheduled_at ? formatDate(task.scheduled_at) : '-'}</td></tr>
                    <tr><th>分配时间:</th><td>${task.assigned_at ? formatDate(task.assigned_at) : '-'}</td></tr>
                    <tr><th>开始时间:</th><td>${task.started_at ? formatDate(task.started_at) : '-'}</td></tr>
                    <tr><th>完成时间:</th><td>${task.completed_at ? formatDate(task.completed_at) : '-'}</td></tr>
                </table>
            </div>

            <div class="detail-section">
                <h3>标签</h3>
                <div class="tags">
                    ${(task.tags || []).map(tag => `<span class="tag">${tag}</span>`).join('') || '-'}
                </div>
            </div>
        `;

        document.getElementById('detail-content').innerHTML = detailHtml;
        document.getElementById('detail-modal').style.display = 'block';
    } catch (error) {
        console.error('Failed to load task details:', error);
        showError('加载任务详情失败');
    }
}

// 查看任务结果
async function viewResult(taskId) {
    try {
        const response = await fetch(`${API_BASE}/tasks/${taskId}`);
        const task = await response.json();

        if (!task.result) {
            showError('该任务没有执行结果');
            return;
        }

        const result = task.result;
        const resultHtml = `
            <div class="result-section">
                <h3>执行结果</h3>
                <table class="detail-table">
                    <tr><th>退出码:</th><td>${result.exit_code !== null ? `<span class="${result.exit_code === 0 ? 'text-success' : 'text-danger'}">${result.exit_code}</span>` : '-'}</td></tr>
                    <tr><th>执行时间:</th><td>${result.execution_time ? result.execution_time.toFixed(2) + '秒' : '-'}</td></tr>
                    <tr><th>输出大小:</th><td>${result.output_size ? result.output_size + '字节' : '-'}</td></tr>
                    <tr><th>开始时间:</th><td>${result.started_at ? formatDate(result.started_at) : '-'}</td></tr>
                    <tr><th>完成时间:</th><td>${result.completed_at ? formatDate(result.completed_at) : '-'}</td></tr>
                </table>
            </div>

            ${result.error_message ? `
                <div class="result-section">
                    <h3>错误信息</h3>
                    <div class="error-message">
                        <strong>错误类型:</strong> ${result.error_type || 'Unknown'}<br>
                        <strong>错误消息:</strong> ${result.error_message}
                    </div>
                </div>
            ` : ''}

            <div class="result-section">
                <h3>标准输出</h3>
                <pre class="output-stdout">${result.stdout || '(空)'}</pre>
            </div>

            <div class="result-section">
                <h3>标准错误</h3>
                <pre class="output-stderr">${result.stderr || '(空)'}</pre>
            </div>
        `;

        document.getElementById('result-content').innerHTML = resultHtml;
        document.getElementById('result-modal').style.display = 'block';
    } catch (error) {
        console.error('Failed to load task result:', error);
        showError('加载任务结果失败');
    }
}

// 取消任务
async function cancelTask(taskId) {
    if (!confirm('确定要取消此任务吗？')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
            method: 'POST'
        });

        if (response.ok) {
            showSuccess('任务取消成功');
            loadTasks();
        } else {
            const error = await response.json();
            showError(error.error?.message || '取消失败');
        }
    } catch (error) {
        console.error('Failed to cancel task:', error);
        showError('取消任务失败');
    }
}

// 设置表单处理
function setupFormHandlers() {
    document.getElementById('task-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const data = {
            name: document.getElementById('task-name').value,
            task_type: document.getElementById('task-type').value,
            priority: document.getElementById('task-priority').value,
            target_asset_id: document.getElementById('target-asset').value,
            command: document.getElementById('task-command').value,
            arguments: document.getElementById('task-arguments').value.split(' ').filter(arg => arg),
            working_dir: document.getElementById('task-workdir').value || null,
            timeout: parseInt(document.getElementById('task-timeout').value) || 300,
            retry_count: parseInt(document.getElementById('task-retry').value) || 0,
            description: document.getElementById('task-description').value || null,
            tags: document.getElementById('task-tags').value.split(',').map(tag => tag.trim()).filter(tag => tag)
        };

        // Show loading notification
        const loadingId = showLoading('正在创建任务...');

        try {
            const response = await fetch(`${API_BASE}/tasks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                hideLoading(loadingId);
                showSuccess('任务创建成功');
                closeModal();
                loadTasks();
            } else {
                hideLoading(loadingId);
                const error = await response.json();
                showError(error.error?.message || '创建失败');
            }
        } catch (error) {
            console.error('Failed to create task:', error);
            hideLoading(loadingId);
            showError('创建任务失败');
        }
    });
}

// 关闭模态框
function closeModal() {
    document.getElementById('task-modal').style.display = 'none';
}

function closeDetailModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

function closeResultModal() {
    document.getElementById('result-modal').style.display = 'none';
}

// 工具函数
function getTaskTypeLabel(type) {
    const labels = {
        'basic_exec': '基础命令',
        'script_transfer': '脚本传输',
        'file_transfer': '文件传输',
        'system_info': '系统信息',
        'custom': '自定义'
    };
    return labels[type] || type;
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge badge-secondary">待处理</span>',
        'assigned': '<span class="badge badge-info">已分配</span>',
        'running': '<span class="badge badge-primary">运行中</span>',
        'succeeded': '<span class="badge badge-success">成功</span>',
        'failed': '<span class="badge badge-danger">失败</span>',
        'timeout': '<span class="badge badge-warning">超时</span>',
        'cancelled': '<span class="badge badge-dark">已取消</span>'
    };
    return badges[status] || status;
}

function getPriorityBadge(priority) {
    const badges = {
        'urgent': '<span class="badge badge-danger">紧急</span>',
        'high': '<span class="badge badge-warning">高</span>',
        'normal': '<span class="badge badge-info">普通</span>',
        'low': '<span class="badge badge-secondary">低</span>'
    };
    return badges[priority] || priority;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function showSuccess(message) {
    return notificationSystem.success(message);
}

function showError(message) {
    return notificationSystem.error(message);
}
