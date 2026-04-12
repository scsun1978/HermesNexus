# 68 技术栈决策与 MVP 边界

## 目标

为 HermesNexus 选定一套适合 MVP 的技术栈，并明确哪些能力需要在 MVP 阶段实现，哪些能力可以延后。

## 总体原则

- 先保证最小闭环可跑通，再考虑扩展性。
- 先统一协议与数据模型，再扩展多设备、多协议、多区域。
- 先让本机开发和开发服务器部署测试跑通，再谈生产化。
- 能用成熟通用技术解决的，不在 MVP 里自研复杂基础设施。

## 推荐技术栈

### 1. 云端控制平面

- 语言：Python 3.12
- Web 框架：FastAPI
- 数据建模：Pydantic
- ORM：SQLAlchemy 2.x
- 迁移：Alembic
- 主数据库：PostgreSQL
- 缓存 / 队列：Redis

适用范围：身份、资产、任务、事件、审计、简单策略。

### 2. 边缘节点运行时

- 语言：Python 3.12
- 异步：asyncio
- HTTP 客户端：httpx
- SSH：AsyncSSH 或 Paramiko
- 本地存储：SQLite

适用范围：节点注册、心跳、任务消费、本地审计、离线缓存、SSH 执行。

### 3. 共享协议层

- Pydantic
- JSON Schema
- OpenAPI

适用范围：Job、Event、Node、Device、Error Code 等稳定模型。

### 4. 控制台前端

- 框架：Next.js
- 语言：TypeScript
- 样式：Tailwind CSS
- 组件：shadcn/ui

适用范围：总览页、资产页、任务页、审计页、记忆页。

### 5. 部署与开发环境

- 容器：Docker
- 本地/开发服务器编排：Docker Compose
- 生产化预留：Kubernetes

开发部署测试服务器：`scsun@172.16.100.101:22`

### 6. 可观测性

- 结构化日志
- OpenTelemetry
- Prometheus
- Grafana
- Loki

MVP 可以先只做结构化日志 + 基础指标，后续再补完整链路追踪。

## OpenViking 是否进入 MVP

结论：不需要作为 MVP 的必做项。

原因：

- MVP 的关键路径是“任务闭环”，不是“知识引擎复杂度”。
- OpenViking 会引入额外的知识分层、检索、同步、权限和数据治理成本。
- 这些能力更适合在核心任务执行链路跑通后再接入。

MVP 的正确做法是：

- 先定义 memory provider 接口
- 先用本地 SQLite / PostgreSQL / 简单文件存储实现最小记忆
- 保留 OpenViking 作为二阶段的云端共同记忆体方案

## MVP 必做项

- 云端任务 API
- 边缘节点 runtime
- SSH 执行链路
- 结果回传
- 基础审计
- 最小可视化控制台
- 本地开发与服务器部署测试

## MVP 可延后项

- OpenViking 深度集成
- 多协议设备全覆盖
- 多区域调度
- 高可用集群
- 复杂审批流
- 全量知识图谱

## 选型结论

如果目标是尽快把 HermesNexus 做成一个能跑通、能验证、能迭代的系统，那么推荐栈是：

- 后端 / 边缘：Python + FastAPI + Pydantic
- 数据：PostgreSQL + Redis + SQLite
- 前端：Next.js + TypeScript + Tailwind CSS
- 部署：Docker Compose 起步，Kubernetes 预留
- 记忆：MVP 先做 provider 抽象和最小实现，OpenViking 放到二阶段
