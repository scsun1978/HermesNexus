# 60 服务接口与 OpenAPI 清单

## 目标

把仓库中的服务接口提前列清楚，方便开发和联调时对齐。

## 核心服务接口

### Identity Service
- POST /auth/login
- POST /nodes/register
- POST /nodes/{id}/rotate-cert

### Asset Service
- GET /devices
- POST /devices
- GET /devices/{id}
- PATCH /devices/{id}
- GET /regions

### Task Service
- POST /jobs
- GET /jobs
- GET /jobs/{id}
- POST /jobs/{id}/cancel
- POST /jobs/{id}/retry

### Policy Service
- GET /policies
- POST /policies
- PATCH /policies/{id}
- POST /policies/{id}/approve

### Event Service
- POST /events
- GET /events
- GET /events/{id}

### Memory Service
- GET /memory/summaries
- GET /memory/skills
- POST /memory/entries

### Edge Gateway
- POST /nodes/{id}/heartbeat
- POST /nodes/{id}/messages
- GET /nodes/{id}/tasks

## OpenAPI 清单建议

每个服务都要有：
- openapi.yaml
- examples/
- error codes
- auth requirements

## 接口约定

- 所有创建类接口要支持幂等键
- 所有列表接口支持分页和过滤
- 所有写接口必须返回 trace_id
- 所有错误都要有 machine-readable code

## 联调优先顺序

1. 注册节点
2. 拉取任务
3. 上报事件
4. 查询资产
5. 创建任务
6. 审批策略

## 设计建议

- 先把接口冻结，再做前端
- 所有接口都要有 mock 响应
- 关键接口要有契约测试
