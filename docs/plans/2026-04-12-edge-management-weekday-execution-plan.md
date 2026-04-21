# Hermes 分布式边缘设备管理系统 Week/Day 执行计划

Date: 2026-04-12
Version: 1.0.2

## 结论先行

当前规划已经从“从零开发”转入“核心已实现，补缺口、验收、固化流程”的阶段。

graphify-out 与源码核对后可以确认：
- 注册、心跳、任务下发、结果回传的核心链路已经存在
- 边缘执行面与云端控制面已经打通
- 现在的重点不是继续扩展大功能，而是把已实现能力补完整、测稳定、写清楚

本计划刻意不引入以下内容：
- 多机房
- 高可用集群
- 复杂权限体系
- 大规模调度优化
- 完整监控平台

目标不是把系统做“大”，而是把系统做“完整、可验、可恢复”。

## 总目标

在 2 个工作周内，完成“核心闭环验收 + 缺口补齐 + 部署与测试固化”，让开发服务器上能够稳定演示：
1. 节点注册成功
2. 节点持续心跳
3. 云端能下发任务
4. 边缘节点能执行并回传结果
5. 节点断线后可重新接入并恢复状态
6. 脚本类任务至少达到可用或明确降级状态

## 规划边界

### 本轮必须完成
- 复核当前核心实现
- 补齐明确缺口
- 统一状态流转与错误码
- 固化本机和开发服务器验证流程
- 固化最小集成测试
- 同步最小运维文档

### 本轮不做
- 多地域/多机房
- HA/主备切换
- RBAC/审批流
- 复杂调度策略
- 全量告警和可观测平台

## 代码与文档落点

建议优先触达的文件：

- 已有核心实现：
  - `cloud/api/main.py`
  - `cloud/database/db.py`
  - `edge/runtime/core.py`
  - `edge/cloud/client.py`
  - `edge/storage/storage.py`
  - `shared/protocol/messages.py`
  - `shared/protocol/error_codes.py`
  - `shared/schemas/models.py`
- 需要补齐/修正：
  - `edge/runtime/core.py`
  - `shared/models/*`（如有命名/结构不一致）
  - `cloud/api/*`（如有接口命名或状态字段不一致）
- 测试：
  - `tests/test_edge_protocol.py`
  - `tests/test_edge_registration.py`
  - `tests/test_edge_heartbeat.py`
  - `tests/test_edge_task_flow.py`
  - `tests/integration/test_edge_e2e.py`
  - `tests/e2e/test_complete_workflow.py`
- 文档：
  - `docs/specs/edge-control-protocol.md`
  - `docs/plans/2026-04-12-edge-management-next-steps.md`
  - `docs/runbooks/edge-management-ops.md`（如不存在则创建）

## Week 1：复核、补缺、对齐

### Day 1：复核当前实现与缺口

**目标**：确认哪些已经完成，哪些还需要补，避免重复开发。

**要产出**：
- 已完成清单
- 缺口清单
- 优先级清单

**文件**：
- 读取：`cloud/api/main.py`
- 读取：`edge/runtime/core.py`
- 读取：`shared/protocol/messages.py`
- 读取：`shared/schemas/models.py`
- 读取：`graphify-out/GRAPH_REPORT.md`

**本机验证**：
- 对照源码和 graphify 结果，列出“已存在 / 部分存在 / 未实现”三类项

**服务器验证**：
- 在开发服务器上确认当前版本能启动云端与边缘端
- 记录一次完整链路的启动日志

### Day 2：补脚本类任务执行缺口

**目标**：把当前明确未完成的脚本执行路径处理掉，或者明确降级策略。

**文件**：
- 修改：`edge/runtime/core.py`
- 新建或修改：`edge/executors/*`（如需统一执行接口）
- 新建：`tests/test_edge_script_task.py`

**本机验证**：
- `python -m pytest tests/test_edge_script_task.py -q`
- 确认脚本任务要么可执行，要么按明确错误码失败

**服务器验证**：
- 在开发服务器上跑一次脚本任务
- 确认结果回传与错误码符合预期

### Day 3：统一状态流转与错误码

**目标**：避免注册、任务、结果、重连的状态字段彼此不一致。

**文件**：
- 修改：`shared/protocol/error_codes.py`
- 修改：`shared/protocol/messages.py`
- 修改：`cloud/api/main.py`
- 修改：`edge/runtime/core.py`
- 新建：`tests/test_edge_status_transitions.py`

**本机验证**：
- `python -m pytest tests/test_edge_status_transitions.py -q`
- 确认成功、失败、超时、重试、离线状态都能稳定流转

**服务器验证**：
- 造一次失败任务
- 确认云边两侧状态展示一致

### Day 4：补幂等与断线恢复边界

**目标**：确保断线、重复回传、重复注册不会污染状态。

**文件**：
- 修改：`cloud/api/main.py`
- 修改：`edge/cloud/client.py`
- 新建：`tests/test_edge_idempotency.py`

**本机验证**：
- `python -m pytest tests/test_edge_idempotency.py -q`
- 确认重复回传不会产生重复状态写入

**服务器验证**：
- 模拟网络抖动
- 确认恢复后任务状态仍然正确

### Day 5：整理当前实现与文档一致性

**目标**：把“已经实现的东西”写进文档，把“还没做的东西”写成缺口。

**文件**：
- 修改：`docs/plans/2026-04-12-edge-management-next-steps.md`
- 修改：`docs/plans/2026-04-12-edge-management-weekday-execution-plan.md`
- 新建：`docs/specs/edge-control-protocol.md`

**本机验证**：
- 文档中的“已完成 / 部分完成 / 待确认”与代码一致

**服务器验证**：
- 在开发服务器上复核一遍核心链路的日志与文档字段

## Week 2：联调、测试、部署固化

### Day 6：补齐核心集成测试

**目标**：把现有链路变成可回归的测试。

**文件**：
- 新建：`tests/integration/test_edge_e2e.py`
- 新建：`tests/integration/test_edge_restart_recovery.py`
- 新建：`tests/test_edge_registration.py`
- 新建：`tests/test_edge_heartbeat.py`

**本机验证**：
- `python -m pytest tests/test_edge_registration.py tests/test_edge_heartbeat.py -q`
- `python -m pytest tests/integration/test_edge_e2e.py -q`

**服务器验证**：
- 在开发服务器上完整跑一遍注册、心跳、任务、回传、重连

### Day 7：固化开发服务器部署方式

**目标**：把联调环境固定下来，减少手工操作。

**文件**：
- 新建：`scripts/dev_start_cloud.sh`
- 新建：`scripts/dev_start_edge.sh`
- 新建：`scripts/dev_reset_edge_state.sh`
- 新建：`docs/runbooks/edge-management-ops.md`

**本机验证**：
- `bash scripts/dev_start_cloud.sh --dry-run`
- `bash scripts/dev_start_edge.sh --dry-run`

**服务器验证**：
- 一键启动云端与模拟节点
- 重启后状态可恢复

### Day 8：做一次完整验收演练

**目标**：确认当前实现已经达到“可演示、可恢复、可复现”。

**文件**：
- 复用现有测试与脚本

**本机验证**：
- 先跑单测，再跑集成测试
- 确认失败点能定位到具体模块

**服务器验证**：
- 完整演练一次：注册 → 心跳 → 任务下发 → 执行 → 回传 → 断线 → 重连

### Day 9：整理验收结论和剩余缺口

**目标**：把当前阶段结论写清楚，避免下阶段误判为“还在起步”。

**文件**：
- 修改：`docs/plans/2026-04-12-edge-management-next-steps.md`
- 新建：`docs/plans/2026-04-12-edge-management-phase-review.md`（如需要）

**本机验证**：
- 缺口清单与测试结果一致

**服务器验证**：
- 开发服务器结果与本机结果一致

### Day 10：收尾与下一阶段入口

**目标**：给下一阶段留一个明确入口，不把本阶段遗留问题带过去。

**文件**：
- 修改：`docs/plans/2026-04-12-edge-management-next-steps.md`
- 修改：`docs/plans/2026-04-12-edge-management-weekday-execution-plan.md`

**本机验证**：
- 核心闭环、部署、测试、文档都能对应到明确状态

**服务器验证**：
- 核心链路可稳定演示，剩余缺口有明确负责人/优先级

## 验收标准

满足以下条件时，可认为这一轮没有跑偏：
- 已实现能力和文档描述一致
- 剩余缺口明确且可追踪
- 核心链路可重复验证
- 本机与开发服务器结论一致
- 脚本任务缺口处理清楚

## 推荐推进顺序

严格按顺序执行：
1. 复核当前实现
2. 补脚本任务与状态缺口
3. 固化集成测试
4. 固化部署脚本
5. 做完整验收演练
6. 更新文档与下一阶段入口

## 风险提示

- 如果继续按“从零开发”推进，会重复已有工作
- 如果不先补脚本任务缺口，当前闭环仍然不是完全闭合
- 如果文档不跟代码同步，后续计划会继续偏差
- 如果没有开发服务器验证，本机通过不代表真实可用

## 下一步建议

先执行 Day 1 和 Day 2：先确认当前实现状态，再把最明确的缺口补掉。
