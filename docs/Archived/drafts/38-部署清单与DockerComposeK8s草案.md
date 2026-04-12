# 38 部署清单与 Docker Compose / K8s 草案

## 目标

给 Hermes 云边系统设计可落地的部署方式，兼顾本地试验、边缘部署和云端生产。

## 部署形态

### 1. 本地开发
- Hermes Core
- 云端 API
- PostgreSQL
- Redis / NATS
- Grafana / Loki（可选）

### 2. 边缘节点
- Hermes Edge Node
- 本地队列
- 本地缓存
- 设备适配器

### 3. 云端生产
- API 服务
- 任务编排服务
- 资产服务
- 事件服务
- 控制台

## Docker Compose 草案

适合本地开发和小规模验证：
- cloud-api
- task-orchestrator
- postgres
- redis
- edge-node
- console

## K8s 草案

适合生产或准生产：
- cloud-api Deployment
- task-orchestrator Deployment
- asset-service Deployment
- event-service Deployment
- console Deployment
- postgres StatefulSet
- redis / nats StatefulSet
- edge-node DaemonSet 或独立 Deployment

## 部署原则

- 云端和边缘分离部署
- 边缘节点要能离线运行
- 任务与状态要持久化
- 密钥和证书不要写死进镜像

## 运维要求

- 支持滚动升级
- 支持蓝绿发布
- 支持配置热更新
- 支持单节点回滚

## 建议

- 开发阶段用 Docker Compose
- 生产阶段用 K8s
- 现场边缘节点可容器化，也可直接 systemd 部署
