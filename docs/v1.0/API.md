# HermesNexus v1.0 API 接口文档

## 1. 总说明

本文件描述当前真实实现的 HTTP 契约。以下内容以 stable-cloud-api.py + final-edge-node.py 的行为为准。

- 默认 Base URL：http://localhost:8080
- 数据格式：JSON
- 任务派发模式：Edge Node 轮询任务列表并按 node_id 自筛选

## 2. 响应格式

### 成功响应

```json
{
  "status": "success",
  "message": "操作成功",
  "timestamp": "2026-04-11T12:00:00Z"
}
```

### 错误响应

```json
{
  "status": "error",
  "message": "错误描述",
  "timestamp": "2026-04-11T12:00:00Z"
}
```

## 3. 健康检查与统计

### GET /health

返回服务健康状态。

响应示例：

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-04-11T12:00:00Z",
  "deployment": "production-mvp",
  "build_date": "2026-04-11"
}
```

### GET /api/v1/stats

返回节点和任务统计。

响应示例：

```json
{
  "active_nodes": 1,
  "total_tasks": 12,
  "pending_tasks": 2,
  "completed_tasks": 9,
  "failed_tasks": 1,
  "system_status": "operational"
}
```

## 4. 设备接口

### POST /api/v1/devices

创建设备。当前实现会把设备写入 nodes 表，所以它既是设备注册接口，也是最小节点登记接口。

请求示例：

```json
{
  "device_id": "dev-edge-node-001",
  "name": "开发服务器边缘节点",
  "device_type": "edge_node"
}
```

响应示例：

```json
{
  "status": "success",
  "device_id": "dev-edge-node-001",
  "name": "开发服务器边缘节点",
  "device_type": "edge_node",
  "message": "Device created successfully",
  "created_at": "2026-04-11T12:00:00Z"
}
```

### GET /api/v1/devices

列出设备。

### GET /api/v1/nodes

列出节点。

### GET /api/v1/nodes/{node_id}

查询指定节点详情。

### POST /api/v1/nodes/{node_id}/heartbeat

接收节点心跳。

请求示例：

```json
{
  "name": "开发服务器边缘节点",
  "status": "active",
  "resources": {
    "cpu_usage": 12.5,
    "memory_usage": 48.2,
    "disk_usage": 61.0
  }
}
```

响应示例：

```json
{
  "status": "success",
  "timestamp": "2026-04-11T12:00:00Z",
  "node_id": "dev-edge-node-001"
}
```

## 5. 任务接口

### POST /api/v1/jobs
### POST /api/v1/tasks

创建任务。两条路径是别名。

必须字段：

- node_id：任务目标节点
- task_type：任务类型

推荐字段：

- task_id
- target
- command
- priority
- timeout
- created_by

请求示例：

```json
{
  "task_id": "task-20260411-120000",
  "node_id": "dev-edge-node-001",
  "task_type": "system_test",
  "target": {
    "test": "deployment_verification"
  },
  "created_by": "audit"
}
```

响应示例：

```json
{
  "status": "success",
  "task_id": "task-20260411-120000",
  "current_status": "pending",
  "message": "Task created successfully",
  "created_at": "2026-04-11T12:00:00Z"
}
```

注意：如果 node_id 缺失，任务会以 unknown 落库，Edge Node 不会主动处理。

### GET /api/v1/tasks
### GET /api/v1/jobs

列出任务。两条路径是别名。

响应示例：

```json
{
  "total": 1,
  "tasks": [
    {
      "task_id": "task-20260411-120000",
      "node_id": "dev-edge-node-001",
      "task_type": "system_test",
      "status": "pending",
      "created_at": "2026-04-11T12:00:00Z",
      "completed_at": null
    }
  ]
}
```

### GET /api/v1/tasks/{task_id}

查询任务详情。

响应示例：

```json
{
  "task_id": "task-20260411-120000",
  "node_id": "dev-edge-node-001",
  "task_type": "system_test",
  "target": {
    "test": "deployment_verification"
  },
  "status": "completed",
  "result": {
    "success": true,
    "output": null,
    "error": null,
    "return_code": null,
    "completed_at": "2026-04-11T12:00:05Z",
    "node_id": "dev-edge-node-001"
  },
  "created_at": "2026-04-11T12:00:00Z",
  "completed_at": "2026-04-11T12:00:05Z"
}
```

### POST /api/v1/nodes/{node_id}/tasks/{task_id}/result

接收任务结果回写。

请求示例：

```json
{
  "success": true,
  "output": "total 16...",
  "error": null,
  "return_code": 0,
  "completed_at": "2026-04-11T12:00:05Z",
  "node_id": "dev-edge-node-001"
}
```

响应示例：

```json
{
  "status": "success",
  "task_id": "task-20260411-120000",
  "node_id": "dev-edge-node-001",
  "updated_status": "completed",
  "result_received": true,
  "timestamp": "2026-04-11T12:00:06Z"
}
```

## 6. 事件与审计

### GET /api/v1/events

返回事件流。

常见事件类型：

- task_created
- task_completed
- task_failed

### GET /api/v1/audit_logs

返回审计日志。

常见 action：

- task_created
- task_result_completed
- task_result_failed

## 7. 当前实现约定

- /api/v1/jobs 与 /api/v1/tasks 都可创建任务
- /api/v1/jobs 与 /api/v1/tasks 都可列出任务
- Edge Node 当前轮询的是 /api/v1/tasks
- 任务回写必须走 /api/v1/nodes/{node_id}/tasks/{task_id}/result
- 当前实现没有把 node-specific task list 作为主流程接口
