# HermesNexus v1.0 架构设计

## 1. 系统目标

HermesNexus v1.0 采用云边协同架构，目标是先跑通一个可验证、可回归的最小闭环：

- 云端负责设备、任务、事件和审计日志管理
- 边缘节点负责注册、心跳、轮询任务、执行任务、回写结果
- SQLite 负责轻量持久化
- 开发服务器作为集成验证环境

## 2. 当前真实运行时

当前验证通过的运行时组合是：

- Cloud API：stable-cloud-api.py
- Edge Node：final-edge-node.py
- 默认数据库：/home/scsun/hermesnexus/data/hermesnexus.db
- 默认日志目录：/home/scsun/hermesnexus/logs/

说明：
complete-cloud-api.py 与 complete-edge-node.py 是更完整的参考实现，但当前 v1.0 文档以稳定通过验证的路径为准。

## 3. 组件职责

### 3.1 Cloud API

Cloud API 负责：

- 创建设备：POST /api/v1/devices
- 创建任务：POST /api/v1/jobs 或 POST /api/v1/tasks
- 提供任务查询：GET /api/v1/tasks/{task_id}
- 提供任务列表：GET /api/v1/tasks、GET /api/v1/jobs
- 接收节点心跳：POST /api/v1/nodes/{node_id}/heartbeat
- 接收任务结果回写：POST /api/v1/nodes/{node_id}/tasks/{task_id}/result
- 写入事件流和审计日志

### 3.2 Edge Node

Edge Node 负责：

- 使用 NODE_ID 和 NODE_NAME 向 Cloud API 注册
- 周期性发送心跳
- 轮询 GET /api/v1/tasks
- 只处理本节点 node_id 匹配的 pending 任务
- 执行 ssh_command / system_test / test
- 将结果写回 Cloud API

### 3.3 SQLite 存储

当前实现使用 SQLite 作为单机持久化层，主要表包括：

- nodes
- tasks
- devices
- events
- audit_logs

## 4. 运行时数据流

```text
设备创建
  -> /api/v1/devices
  -> nodes 表写入

任务创建
  -> /api/v1/jobs 或 /api/v1/tasks
  -> tasks 表写入 pending
  -> events 写入 task_created
  -> audit_logs 写入 task_created

节点注册/心跳
  -> /api/v1/nodes/{node_id}/heartbeat
  -> nodes 表更新 last_heartbeat

边缘轮询
  -> GET /api/v1/tasks
  -> Edge Node 本地按 node_id 过滤

结果回写
  -> POST /api/v1/nodes/{node_id}/tasks/{task_id}/result
  -> tasks 更新为 completed/failed
  -> events 写入 task_completed/task_failed
  -> audit_logs 写入 task_result_completed/task_result_failed
```

## 5. 当前约定

### 5.1 node_id 是任务派发关键字段

任务创建时必须带 node_id。若缺失，任务会以 unknown 存储，Edge Node 不会主动接收。

### 5.2 jobs 与 tasks 是别名

当前实现同时支持 /api/v1/jobs 和 /api/v1/tasks 作为任务创建入口；任务列表也同时支持 /api/v1/jobs 和 /api/v1/tasks。

### 5.3 devices 与 nodes 不是同一层概念

- devices：外部设备注册视图
- nodes：运行时节点视图

在当前稳定实现中，/api/v1/devices 会把设备记录映射进 nodes 表，以便最小闭环先跑通。

## 6. 非目标

v1.0 当前不把以下内容作为默认承诺：

- 多云部署
- 高可用集群
- 复杂权限体系
- 分布式调度器
- 节点侧复杂插件框架

## 7. 关键风险

- 运行路径对 /home/scsun/hermesnexus 有默认假设
- task 的目标节点必须明确
- 轮询模型是当前 MVP 的实现方式，不是最终调度方案
