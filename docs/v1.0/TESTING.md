# HermesNexus v1.0 测试文档

## 1. 测试目标

测试重点不是“有没有跑起来”，而是确认这条闭环是否真的成立：

1. 创建设备
2. 创建任务
3. Edge Node 轮询到任务
4. Edge Node 执行
5. 任务结果回写
6. events 有记录
7. audit_logs 有记录

## 2. 测试层级

### 单元测试

用于验证共享模块、数据库、执行器和基础逻辑。

```bash
python -m pytest tests/unit/ -q
```

### 集成测试

用于验证 cloud / edge / shared 模块之间的联动。

```bash
python -m pytest tests/integration/ -q
```

### 端到端测试

用于验证真实运行时闭环。

```bash
python -m pytest tests/e2e/ -q
```

### 一键运行

```bash
python tests/run_all_tests.py
```

这个脚本会依次跑：

- 单元测试
- 集成测试
- 模拟器测试
- 控制台测试
- SSH 执行器测试
- Cloud/Edge 集成测试
- 可选的 E2E 测试

## 3. 运行前的系统检查

```bash
python tests/scripts/system_health_check.py
```

这个脚本适合做“项目级健康扫描”：

- Python 环境
- 项目目录结构
- 共享模块
- 数据库模块
- 控制台
- Cloud API 健康状态

## 4. 任务闭环的推荐烟囱测试

```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/api/v1/devices   -H 'Content-Type: application/json'   -d '{"device_id":"dev-edge-node-001","name":"开发服务器边缘节点","device_type":"edge_node"}'

curl -X POST http://localhost:8080/api/v1/jobs   -H 'Content-Type: application/json'   -d '{
    "task_id":"smoke-001",
    "node_id":"dev-edge-node-001",
    "task_type":"system_test",
    "target":{"test":"deployment_verification"},
    "created_by":"smoke"
  }'

curl http://localhost:8080/api/v1/tasks/smoke-001
curl http://localhost:8080/api/v1/events
curl http://localhost:8080/api/v1/audit_logs
```

## 5. 任务分发模拟脚本

```bash
python tests/scripts/task_dispatcher.py --cloud-url http://localhost:8080 --scenario --device-id dev-edge-node-001
```

也可以直接发命令任务：

```bash
python tests/scripts/task_dispatcher.py --cloud-url http://localhost:8080 --device-id dev-edge-node-001 --command 'uname -a'
```

## 6. 验收标准

一次完整测试至少满足：

- /health 返回 healthy
- 创建设备成功
- 创建任务成功
- 任务状态从 pending 变为 completed 或 failed
- result 里有 node_id、completed_at、success
- events 中有 task_created 和 task_completed/task_failed
- audit_logs 中有 task_created 和 task_result_completed/task_result_failed

## 7. 当前实现中的注意点

- 任务创建必须带 node_id
- Edge Node 轮询的是 /api/v1/tasks，不是 node-specific task list
- /api/v1/jobs 与 /api/v1/tasks 是别名
- /api/v1/audit_logs 才是当前真实审计接口，不再使用旧版 /api/v1/audit
