# HermesNexus v1.0 文档总览

## 版本信息

- 版本号：v1.0.0-mvp
- 发布日期：2026-04-11
- 当前状态：MVP 闭环已验证通过
- 当前参考运行时：stable-cloud-api.py + final-edge-node.py
- 默认服务端口：8080

## 这版文档描述什么

这套 v1.0 文档只描述当前已经验证过的真实运行路径，不再沿用旧版草稿里的接口命名。

当前最小闭环是：

1. Cloud API 接收设备、任务、事件、审计日志
2. Edge Node 注册、心跳、轮询任务、执行任务、回写结果
3. SQLite 负责持久化
4. 本机负责开发和单元测试
5. 开发服务器负责集成验证

## 当前验证过的核心路径

- POST /api/v1/devices：创建设备并落到 nodes 表
- POST /api/v1/jobs 或 POST /api/v1/tasks：创建任务
- GET /api/v1/tasks/{task_id}：查询任务状态
- POST /api/v1/nodes/{node_id}/heartbeat：接收节点心跳
- POST /api/v1/nodes/{node_id}/tasks/{task_id}/result：回写任务结果
- GET /api/v1/events：查看事件流
- GET /api/v1/audit_logs：查看审计日志

注意：任务能否被 edge 处理，取决于创建任务时是否提供 node_id。
Edge Node 当前轮询 /api/v1/tasks，并在本地按 node_id 过滤。

## 快速开始

### 1. 启动 Cloud API

```bash
source venv/bin/activate
python3 stable-cloud-api.py
```

### 2. 启动 Edge Node

```bash
source venv/bin/activate
export CLOUD_API_URL=http://localhost:8080
export NODE_ID=dev-edge-node-001
export NODE_NAME="开发服务器边缘节点"
python3 final-edge-node.py
```

### 3. 验证闭环

```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/api/v1/devices \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"dev-edge-node-001","name":"开发服务器边缘节点","device_type":"edge_node"}'
```

随后创建一个带 node_id 的任务，再查看任务状态、事件流和审计日志。

## 文档导航

- ARCHITECTURE.md：架构与数据流
- API.md：当前真实接口契约
- DEPLOYMENT.md：本机与开发服务器部署方式
- DEVELOPMENT.md：本机开发约定
- TESTING.md：测试与验收方法
- USER-GUIDE.md：使用方式
- RELEASE-NOTES.md：版本说明
- DOCUMENTATION-INDEX.md：全文档索引

## 适用范围

这套文档以当前 v1.0 稳定实现为准。如果后续切换到新的实现（例如更完整的 complete-* 版本），请先更新 API.md 与 ARCHITECTURE.md，再同步其它文档。
