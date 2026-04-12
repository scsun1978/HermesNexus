# Edge Management MVP Environment Plan

Date: 2026-04-11

## Goal

在 MVP 阶段先打通“本机开发 + 开发服务器部署测试 + 边缘节点验证”的完整闭环，确保服务端与边缘节点都可以在服务器环境中部署、联调和回归测试。

## Core Decisions

### 1. 开发方式

- 本机继续做日常开发、调试和单元测试。
- 由于本机已经安装了 Hermes，项目开发不直接依赖本机全局 Hermes 环境。
- 项目应使用独立的虚拟环境、锁定版本和项目内配置，避免污染系统环境。
- 本机只承担“开发入口”，不承担最终验证职责。

### 2. MVP 阶段必须补齐部署测试环境

- MVP 不只是完成代码，还要完成可重复部署的测试环境。
- 开发服务器承担集成验证角色：服务端、边缘节点、配置、日志、健康检查、重启恢复都要在这里跑通。
- 先用容器或虚拟机模拟边缘节点，后续再替换为真实边缘设备。
- 目标是让每次改动都能通过同一套部署流程验证，而不是手工拷贝和临时启动。

### 3. 环境分层

建议分成三层：

- 本机开发层
  - 代码编写
  - 单元测试
  - 快速调试
  - 依赖和配置开发

- 开发服务器集成层
  - 服务端部署
  - 边缘节点部署
  - 节点注册/心跳/任务下发
  - 集成测试和接口验证

- 验证层
  - 接近生产的部署配置
  - 升级、重启、异常恢复测试
  - 发布前回归

## Recommended Implementation

### Local development environment

- Use the local machine for day-to-day coding, debugging, and unit tests.
- Do not rely on the globally installed Hermes runtime as the project execution environment.
- Create a project-specific virtual environment and pin dependencies inside the repository.
- Keep project config isolated from the user's existing Hermes config by using a separate profile or dedicated HERMES_HOME.
- Local development should focus on fast feedback: edit → test → inspect → iterate.

### Development server environment

- Use a dedicated development server as the integration and verification environment.
- Deploy both the control plane and edge-node processes on the server.
- Treat the server as the source of truth for deployment testing, because it mirrors the real runtime topology better than the laptop.
- Validate registration, heartbeat, task dispatch, task execution, and result reporting on this server.
- Keep logs, data directories, and runtime state on the server so failures are reproducible.

### MVP deployment model

- Local machine: development + unit tests + lightweight API checks.
- Development server: integration tests + end-to-end validation.
- Edge nodes: run as server-hosted processes first, then replace with real edge hardware later.
- Prefer a simple repeatable startup script over manual process launches.
- Keep the first version boring: one server, one or two nodes, one database, one log path.

### Suggested repo layout

- `docs/plans/` — planning and decision documents.
- `scripts/` or `deploy/` — deployment/startup scripts for the dev server.
- `configs/local/` — local-only configuration templates.
- `configs/dev-server/` — development server configuration templates.
- `tests/e2e/` or `tests/integration/` — deployment and workflow verification tests.

## MVP Scope

### 本机侧必须完成

- 代码仓库初始化和依赖隔离
- hermes 相关依赖的固定版本管理
- 本机开发配置与服务器配置分离
- 本机可执行的单元测试和静态检查

### 开发服务器侧必须完成

- 服务端可部署
- 边缘节点可部署
- 节点自动注册/注销
- 心跳和状态上报
- 任务下发与结果回传
- 日志收集与故障排查
- 重启后可恢复连接或重新注册

### MVP 阶段不强制完成

- 大规模多节点调度
- 高可用集群
- 复杂权限体系
- 完整生产监控平台
- 多云/多机房部署

## Task Breakdown

### Task 1: 明确环境边界和依赖策略

**Objective:** 明确本机、开发服务器、边缘节点三类环境各自承担的职责。

**Deliverables:**
- 一页环境边界说明
- 本机与服务器的配置分离原则
- Hermes 使用方式说明

**Checklist:**
- [ ] 本机只做开发和测试
- [ ] 服务器负责集成验证
- [ ] Hermes 依赖版本固定
- [ ] 不使用系统全局环境直接跑项目

### Task 2: 定义项目本地开发环境

**Objective:** 让开发者可以在本机稳定开发而不污染全局环境。

**Deliverables:**
- 独立虚拟环境方案
- 依赖锁定方案
- 本机配置文件模板

**Checklist:**
- [ ] 创建项目专用虚拟环境
- [ ] 固定关键依赖版本
- [ ] 本机配置与服务器配置拆分
- [ ] 文档说明如何切换环境

### Task 3: 设计开发服务器部署方式

**Objective:** 确定服务端和边缘节点在开发服务器上的部署模式。

**Deliverables:**
- 部署拓扑图
- 启动顺序说明
- 端口和服务列表

**Checklist:**
- [ ] 服务端先启动
- [ ] 边缘节点后启动并注册
- [ ] 明确对外暴露端口
- [ ] 明确数据/日志目录

### Task 4: 建立 MVP 一键部署脚本

**Objective:** 用脚本把环境搭建流程固化下来，减少手工操作。

**Deliverables:**
- 一键启动脚本
- 一键停止脚本
- 清理脚本

**Checklist:**
- [ ] 可重复部署
- [ ] 可重复销毁
- [ ] 脚本可在开发服务器执行
- [ ] 脚本输出清晰

### Task 5: 打通服务端与边缘节点最小链路

**Objective:** 跑通“注册 → 心跳 → 下发任务 → 回传结果”的最小闭环。

**Deliverables:**
- 最小可运行服务端
- 最小边缘节点进程
- 最小协议和消息格式

**Checklist:**
- [ ] 节点可注册
- [ ] 节点可上报心跳
- [ ] 服务端可下发任务
- [ ] 节点可回传执行结果

### Task 6: 建立集成测试用例

**Objective:** 用自动化测试验证部署环境和通信链路。

**Deliverables:**
- 集成测试清单
- API/CLI 测试脚本
- 环境健康检查脚本

**Checklist:**
- [ ] 启动测试通过
- [ ] 节点注册测试通过
- [ ] 心跳测试通过
- [ ] 任务执行测试通过
- [ ] 异常重连测试通过

### Task 7: 补齐日志与排障能力

**Objective:** 让开发服务器上的问题可以快速定位。

**Deliverables:**
- 服务端日志规范
- 边缘节点日志规范
- 常见故障排查文档

**Checklist:**
- [ ] 日志包含时间、节点 ID、任务 ID
- [ ] 错误信息可追踪
- [ ] 启动失败原因可见
- [ ] 重连失败原因可见

### Task 8: 编写 MVP 部署与验证文档

**Objective:** 把开发和部署流程写成可执行文档。

**Deliverables:**
- 本机开发指南
- 开发服务器部署指南
- MVP 验收清单

**Checklist:**
- [ ] 新人可照文档跑通
- [ ] 部署步骤可复制
- [ ] 验收标准明确
- [ ] 回滚步骤明确

## Recommended Execution Order

1. 先定环境边界
2. 再做本机隔离
3. 再做服务器部署脚本
4. 再打通服务端与边缘节点链路
5. 再补集成测试
6. 最后补文档和排障

## MVP Acceptance Criteria

MVP 阶段至少满足以下条件：

- 本机能完成代码开发和单元测试
- 开发服务器能一键部署服务端和边缘节点
- 节点能稳定注册并维持心跳
- 服务端能下发任务，节点能回传结果
- 重启后可以恢复运行
- 有最基本的日志和测试文档

## Notes

- 如果 Hermes 只是项目依赖之一，建议把它当作“受控依赖”而不是“系统级前置条件”。
- MVP 阶段不要追求复杂高可用，优先验证闭环。
- 只要部署链路没有跑通，功能开发的风险都会被放大。
