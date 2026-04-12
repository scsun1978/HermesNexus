# HermesNexus v1.0 用户使用指南

## 1. 这个系统能做什么

HermesNexus v1.0 现在能稳定完成以下动作：

- 注册设备/节点
- 创建任务
- 边缘节点轮询任务
- 执行任务
- 回写结果
- 记录事件和审计日志

## 2. 角色视角

### 开发者

开发者通常只需要：

- 启动 Cloud API
- 启动 Edge Node
- 创建任务
- 看任务状态、事件和审计日志

### 节点运维

节点运维主要关注：

- node_id 是否一致
- 心跳是否正常
- 任务是否卡在 pending
- 日志是否写入 /home/scsun/hermesnexus/logs/

## 3. 常用访问地址

- 健康检查：http://localhost:8080/health
- 任务列表：http://localhost:8080/api/v1/tasks
- 事件流：http://localhost:8080/api/v1/events
- 审计日志：http://localhost:8080/api/v1/audit_logs

## 4. 一个完整的使用流程

### 第一步：创建设备

```bash
curl -X POST http://localhost:8080/api/v1/devices   -H 'Content-Type: application/json'   -d '{
    "device_id": "dev-edge-node-001",
    "name": "开发服务器边缘节点",
    "device_type": "edge_node"
  }'
```

### 第二步：创建任务

```bash
curl -X POST http://localhost:8080/api/v1/jobs   -H 'Content-Type: application/json'   -d '{
    "task_id": "user-guide-001",
    "node_id": "dev-edge-node-001",
    "task_type": "system_test",
    "target": {"test": "deployment_verification"},
    "created_by": "user-guide"
  }'
```

### 第三步：查看任务状态

```bash
curl http://localhost:8080/api/v1/tasks/user-guide-001
```

### 第四步：查看事件和审计

```bash
curl http://localhost:8080/api/v1/events
curl http://localhost:8080/api/v1/audit_logs
```

## 5. 你需要知道的约定

- 任务必须带 node_id
- jobs 和 tasks 都可以创建任务
- Edge Node 会从任务列表里筛选自己的任务
- 结果回写是自动完成的，不需要手工补写

## 6. 当前限制

- 运行路径默认是 /home/scsun/hermesnexus
- 当前是 MVP 运行方式，不是多节点大规模调度
- 设备和节点在当前实现里有一定程度的映射关系
