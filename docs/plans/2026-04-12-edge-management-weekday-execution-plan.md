# Hermes 分布式边缘设备管理系统 Week/Day 执行计划

Date: 2026-04-12
Version: 1.0.1

## 结论先行

当前规划没有偏离主线。下一步应继续围绕“最小可验证闭环”推进：设备注册 → 心跳 → 任务下发 → 结果回传 → 断线重连。

本计划刻意不引入以下内容：
- 多机房
- 高可用集群
- 复杂权限体系
- 大规模调度优化
- 完整监控平台

目标不是把系统做“大”，而是先把系统做“可管、可验、可恢复”。

## 总目标

在 2 个工作周内，完成一个最小可验证的云-边闭环，让开发服务器上能够稳定演示：
1. 节点注册成功
2. 节点持续心跳
3. 云端能下发任务
4. 边缘节点能执行并回传结果
5. 节点断线后可重新接入并恢复状态

## 规划边界

### 本轮必须完成
- 最小控制面协议冻结
- 节点注册和心跳
- 任务创建、下发、结果回传
- 断线与重连处理
- 开发服务器部署方式
- 最小集成测试
- 最小运维文档

### 本轮不做
- 多地域/多机房
- HA/主备切换
- RBAC/审批流
- 复杂调度策略
- 全量告警和可观测平台

## 代码与文档落点

建议优先触达的文件：

- 新建协议与模型：
  - `shared/models/protocol.py`
  - `shared/models/node.py`
  - `shared/models/task.py`
- 复用和调整的数据访问层：
  - `shared/dao/task_dao.py`
  - `shared/dao/node_dao.py`（如不存在则创建）
- 云端服务入口与接口：
  - `cloud/__init__.py`
  - `cloud/app.py`（如不存在则创建）
  - `cloud/api.py`（如需要拆分则创建）
- 边缘节点入口与执行器：
  - `edge/__init__.py`
  - `edge/agent.py`（如不存在则创建）
  - `edge/transport.py`（如需要拆分则创建）
- 测试：
  - `tests/test_edge_protocol.py`
  - `tests/test_edge_registration.py`
  - `tests/test_edge_heartbeat.py`
  - `tests/test_edge_task_flow.py`
  - `tests/integration/test_edge_e2e.py`
- 文档：
  - `docs/specs/edge-control-protocol.md`
  - `docs/plans/2026-04-12-edge-management-weekday-execution-plan.md`
  - `docs/runbooks/edge-management-ops.md`（如不存在则创建）

## Week 1：协议、注册、心跳

### Day 1：冻结最小控制面协议

**目标**：先把云端和边缘节点“最少要说清楚的话”定下来，避免后续接口反复改。

**要产出**：
- 协议说明文档
- 最小 JSON 示例
- 错误码约定
- 字段约束说明

**文件**：
- 新建：`docs/specs/edge-control-protocol.md`
- 新建：`shared/models/protocol.py`
- 新建：`tests/test_edge_protocol.py`

**本机验证**：
- `python -m pytest tests/test_edge_protocol.py -q`
- 确认注册、心跳、任务、结果、离线/重连消息的 JSON 样例都能通过序列化/反序列化测试

**服务器验证**：
- 在开发服务器上打开协议文档，确认云端和边缘端对字段含义一致
- 用真实配置跑一次样例请求，确认日志中的字段和文档一致

### Day 2：实现共享消息模型

**目标**：把协议落成可复用的数据结构，后续云端和边缘端都从这里读写。

**文件**：
- 新建：`shared/models/node.py`
- 新建：`shared/models/task.py`
- 修改：`shared/models/protocol.py`
- 新建：`tests/test_edge_model_serialization.py`

**本机验证**：
- `python -m pytest tests/test_edge_model_serialization.py -q`
- 确认模型字段、默认值、必填项、错误字段输出都正确

**服务器验证**：
- 在开发服务器上跑一个最小的序列化样例，确认日志、API payload、数据库字段没有命名偏差

### Day 3：建立云端节点注册与状态存储

**目标**：让云端知道节点是谁、是否在线、最后一次心跳是什么时候。

**文件**：
- 新建：`cloud/app.py`
- 新建：`cloud/node_registry.py`
- 修改：`shared/dao/task_dao.py`
- 新建：`shared/dao/node_dao.py`
- 新建：`tests/test_edge_registration.py`

**本机验证**：
- `python -m pytest tests/test_edge_registration.py -q`
- 确认注册接口能生成或确认 `node_id`
- 确认节点状态能落库

**服务器验证**：
- 在开发服务器启动云端服务后，手动注册一个模拟节点
- 检查节点列表、在线状态、最后心跳时间是否正确显示

### Day 4：实现边缘节点自动注册与心跳

**目标**：让边缘节点启动后自动接入，并持续保持在线。

**文件**：
- 新建：`edge/agent.py`
- 新建：`edge/heartbeat.py`
- 新建：`edge/config.py`
- 新建：`tests/test_edge_heartbeat.py`

**本机验证**：
- `python -m pytest tests/test_edge_heartbeat.py -q`
- 确认启动后自动注册
- 确认心跳定时器按间隔发送
- 确认心跳失败会进入重试逻辑

**服务器验证**：
- 在开发服务器上启动一个模拟边缘节点
- 确认云端能持续看到心跳刷新
- 停掉节点后，确认云端在线状态切到离线

### Day 5：断线重连与状态恢复

**目标**：节点掉线后能重新接入，且云端状态不会长期脏掉。

**文件**：
- 修改：`edge/agent.py`
- 修改：`edge/heartbeat.py`
- 修改：`cloud/node_registry.py`
- 新建：`tests/test_edge_reconnect.py`

**本机验证**：
- `python -m pytest tests/test_edge_reconnect.py -q`
- 确认断线后自动重连
- 确认重连后可复用原节点身份或按规则重新注册

**服务器验证**：
- 在开发服务器上手动断开模拟节点网络
- 恢复网络后确认节点自动回连
- 检查离线/在线切换记录是否正确

## Week 2：任务闭环、部署、测试

### Day 6：定义任务模型与下发接口

**目标**：云端可以创建任务，并明确下发到指定节点。

**文件**：
- 新建：`shared/models/task_command.py`
- 修改：`shared/models/task.py`
- 新建：`cloud/task_service.py`
- 新建：`tests/test_edge_task_dispatch.py`

**本机验证**：
- `python -m pytest tests/test_edge_task_dispatch.py -q`
- 确认任务对象字段完整
- 确认下发接口能定位目标节点

**服务器验证**：
- 在开发服务器上创建一个测试任务
- 确认目标节点能收到任务元数据

### Day 7：边缘节点执行任务并回传结果

**目标**：节点不只是“在线”，而是真的能“干活”。

**文件**：
- 新建：`edge/task_worker.py`
- 修改：`edge/agent.py`
- 新建：`tests/test_edge_task_result.py`

**本机验证**：
- `python -m pytest tests/test_edge_task_result.py -q`
- 确认任务执行成功会回传结果
- 确认执行失败会回传 error 和状态码

**服务器验证**：
- 在开发服务器上让节点执行一个测试任务
- 确认结果回传到云端
- 确认云端任务状态从 pending/running 变为 success/failed

### Day 8：补齐任务状态跟踪与失败处理

**目标**：云端能准确知道任务生命周期，而不是只知道“发过了”。

**文件**：
- 修改：`cloud/task_service.py`
- 修改：`shared/dao/task_dao.py`
- 新建：`tests/test_edge_task_lifecycle.py`

**本机验证**：
- `python -m pytest tests/test_edge_task_lifecycle.py -q`
- 确认任务状态流转符合预期
- 确认重复回传、超时回传、失败回传不会污染状态

**服务器验证**：
- 在开发服务器上模拟超时和失败任务
- 检查任务列表是否正确标记为超时或失败

### Day 9：建立开发服务器部署方式

**目标**：把云端和边缘模拟器变成可重复启动、可重复清理的环境。

**文件**：
- 新建：`scripts/dev_start_cloud.sh`
- 新建：`scripts/dev_start_edge.sh`
- 新建：`scripts/dev_reset_edge_state.sh`
- 新建：`docs/runbooks/edge-management-ops.md`

**本机验证**：
- `bash scripts/dev_start_cloud.sh --dry-run`
- `bash scripts/dev_start_edge.sh --dry-run`
- 确认脚本能正确打印配置、日志和数据目录

**服务器验证**：
- 在开发服务器上一键启动云端与模拟节点
- 重启后确认状态可恢复
- 确认日志路径固定且可直接定位问题

### Day 10：最小集成测试与收尾文档

**目标**：把核心链路固化成自动测试，并把操作方式写清楚。

**文件**：
- 新建：`tests/integration/test_edge_e2e.py`
- 新建：`tests/integration/test_edge_restart_recovery.py`
- 新建：`docs/runbooks/edge-management-ops.md`
- 新建：`docs/plans/2026-04-12-edge-management-weekday-execution-plan.md`（如需迭代更新）

**本机验证**：
- `python -m pytest tests/integration/test_edge_e2e.py -q`
- `python -m pytest tests/integration/test_edge_restart_recovery.py -q`
- 确认本机单测和集成测试都能跑通

**服务器验证**：
- 在开发服务器上完整跑一遍注册、心跳、任务下发、结果回传、断线重连
- 失败时能从日志快速定位到具体步骤

## 验收标准

满足以下条件时，可认为这一轮没有跑偏：
- 本机可开发、可单测
- 开发服务器可部署、可联调
- 节点可注册、可心跳
- 服务端可下发任务
- 节点可回传结果
- 断线后可恢复
- 测试失败时能定位到具体环节

## 推荐推进顺序

严格按顺序执行：
1. 协议
2. 注册/心跳
3. 断线重连
4. 任务闭环
5. 部署脚本
6. 集成测试
7. 运维文档

## 风险提示

- 如果协议没冻结就开写实现，后面会反复返工
- 如果只做云端不做边缘端，系统仍然不完整
- 如果先做 HA、监控、权限扩展，会把主线拖偏
- 如果没有开发服务器验证，本机通过不代表链路可用

## 下一步建议

先执行 Day 1 和 Day 2，尽快把协议与模型定死，然后再往注册/心跳推进。

