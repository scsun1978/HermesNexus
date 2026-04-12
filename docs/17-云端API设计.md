# 17 云端 API 设计

## 目标

给云端控制平面定义稳定、可审计、可扩展的 API。

## API 分层

### 1. 管理类 API
- 设备注册
- 区域管理
- 节点管理
- 策略管理
- 权限管理

### 2. 任务类 API
- 创建任务
- 查询任务
- 取消任务
- 重试任务
- 查看步骤结果

### 3. 观测类 API
- 查询心跳
- 查询事件
- 查询审计
- 查询告警

### 4. 记忆类 API
- 拉取站点记忆摘要
- 查询故障知识
- 同步经验条目

## 推荐接口风格

- 内部服务优先 gRPC
- 外部控制台优先 REST
- 设备边缘通信优先长连接 / HTTP

## REST 资源建议

- /tenants
- /regions
- /nodes
- /devices
- /policies
- /jobs
- /job-steps
- /events
- /audit-records

## API 设计原则

1. 幂等：创建任务要支持 idempotency key。
2. 可分页：所有列表都支持分页。
3. 可过滤：按 region / device / status / time 查询。
4. 可追踪：每个请求带 trace_id。
5. 可审计：高危操作必须留痕。

## Hermes 如何参与

Hermes 可以作为 API 的智能使用者：
- 读接口帮助理解环境
- 写接口创建任务草案
- 查询接口追踪执行状态
- 失败时自动补充上下文并重试
