# HermesNexus Next Development Roadmap

Date: 2026-04-11

> Based on: `docs/Hermes分布式边缘设备管理系统.md`, `docs/09-MVP开发路线图.md`, `docs/DEVELOPMENT-SERVER-DEPLOYMENT.md`, `docs/54-测试与联调规范.md`

## Goal

把 HermesNexus 从“理念文档 + MVP 方向”推进到“可开发、可部署、可联调、可验证”的最小闭环。

## Current Direction

当前主线已经明确：

- 本机负责开发和单测
- 开发服务器负责部署和集成验证
- 服务端和边缘节点都要在开发服务器上跑起来
- MVP 先只做最小闭环，不做复杂高可用和大规模调度

## What to Build Next

### 1. Freeze MVP scope

先把范围锁死，避免开发过程中不断膨胀。

建议只保留：

- 1 个云端控制平面
- 1 个边缘节点
- 1 套 Linux 主机执行链路
- 核心闭环：注册、心跳、任务下发、结果回传
- 基础审计与日志

明确不做：

- 多机房
- 多云
- 高可用集群
- 复杂权限矩阵
- 全量协议矩阵

### 2. Complete local development isolation

先让本机开发环境稳定、可重复。

重点是：

- 项目专用虚拟环境
- 项目专用 `HERMES_HOME`
- 项目专用 `.env`
- 项目专用配置模板
- 本机 Hermes 主环境不被污染

### 3. Establish repository and module skeleton

把代码仓库骨架先固定下来，避免后续大改。

建议形成这些主目录：

- `cloud/`：云端控制平面
- `edge/`：边缘节点运行时
- `shared/`：共享协议、模型、事件格式
- `tests/`：单测、集成测试、联调测试
- `deploy/`：开发服务器部署脚本
- `docs/`：主文档和操作文档

### 4. Define shared contracts first

先统一云端和边缘共享的数据结构，再写业务逻辑。

优先冻结：

- Node heartbeat schema
- Task schema
- Device schema
- Event schema
- Error code schema

### 5. Implement cloud control plane minimum

先做最小云端能力，不要上来就铺全功能。

优先能力：

- 健康检查
- 设备/节点注册
- 任务创建与查询
- 任务状态流转
- 事件记录
- 审计记录

### 6. Implement edge runtime minimum

边缘节点先能活起来，再谈高级能力。

优先能力：

- 启动入口
- 节点注册
- 心跳上报
- 任务轮询或接收
- 任务执行
- 结果回写

### 7. Build deployment test environment on dev server

开发服务器要成为真实集成验证环境。

必须具备：

- Cloud 服务启动方式
- Edge 节点启动方式
- 配置隔离
- 日志目录
- 数据目录
- 重启恢复验证

### 8. Build integration and smoke tests

本机单测不够，要补最小闭环验证。

至少要有：

- 云端 API smoke test
- 节点注册测试
- 心跳测试
- 任务下发测试
- 结果回传测试
- 重启后恢复测试

### 9. Add logging and troubleshooting basics

开发服务器一旦出问题，要能快速定位。

最低要求：

- 日志含时间、节点 ID、任务 ID
- 启动失败可见
- 心跳失败可见
- 结果回传失败可见
- 常见故障排查步骤文档化

### 10. Write developer-facing deployment docs

把“怎么开发、怎么部署、怎么验证”写清楚。

需要补齐：

- 本机开发指南
- 开发服务器部署指南
- 测试与联调规范
- MVP 验收清单

## Suggested Execution Order

1. 先冻结 MVP 范围
2. 再完成本机隔离
3. 再确定仓库骨架
4. 再冻结共享契约
5. 再实现云端最小能力
6. 再实现边缘运行时
7. 再搭开发服务器部署
8. 再补测试、日志和文档

## Suggested Acceptance Criteria

进入下一阶段前，至少满足：

- 本机开发环境可稳定复现
- 云端和边缘节点能在开发服务器启动
- 节点可注册、可心跳
- 任务可下发、结果可回传
- 重启后能恢复或重新注册
- 文档能支持别人按步骤跑通

## Non-goals for Now

这阶段不建议优先投入：

- K8s 生产化部署
- 多节点大规模调度
- 高可用和自动伸缩
- 复杂告警平台
- 完整企业级权限体系

## Next Action

如果要继续推进，下一步应该把这份 roadmap 拆成可执行任务块，按“本机环境 → 共享契约 → 云端最小版 → 边缘最小版 → 开发服务器联调 → 测试与文档”逐项落地。
