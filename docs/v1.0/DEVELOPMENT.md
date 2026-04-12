# HermesNexus v1.0 开发指南

## 1. 开发原则

- 本机负责开发、调试、单测
- 开发服务器负责集成验证
- 文档和接口以当前真实实现为准
- 不要把旧版节点/审计草稿当成默认契约

## 2. 本机环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install requests psutil pytest httpx
```

说明：

- Cloud API 本身只依赖标准库
- Edge Node 需要 requests
- psutil 仅用于资源采集，缺失时会自动降级

## 3. 本机开发时要注意的路径约束

当前代码默认写死了开发服务器路径：

- /home/scsun/hermesnexus/data/hermesnexus.db
- /home/scsun/hermesnexus/logs/edge-node.log

因此如果你在别的目录开发，有两种办法：

1. 在本机建立同路径软链接
2. 先改代码里的常量再跑

这不是理想状态，但它就是当前真实实现。

## 4. 推荐的日常开发流程

1. 改代码
2. 跑单测
3. 启动 Cloud API
4. 启动 Edge Node
5. 发一个测试任务
6. 看事件、审计日志和任务状态

## 5. 本机快速验证命令

### 启动 Cloud API

```bash
source venv/bin/activate
python3 stable-cloud-api.py
```

### 启动 Edge Node

```bash
source venv/bin/activate
export CLOUD_API_URL=http://localhost:8080
export NODE_ID=dev-edge-node-001
python3 final-edge-node.py
```

### 创建一个最小验证任务

```bash
curl -X POST http://localhost:8080/api/v1/jobs   -H 'Content-Type: application/json'   -d '{
    "task_id": "dev-check-001",
    "node_id": "dev-edge-node-001",
    "task_type": "system_test",
    "target": {"test": "deployment_verification"},
    "created_by": "developer"
  }'
```

## 6. 开发约定

- task 的目标节点字段是 node_id
- node_id 为空时，Edge Node 不会接单
- jobs 和 tasks 是当前实现中的别名入口
- 设备注册使用 /api/v1/devices，不要再假设有单独的 node create API

## 7. 代码修改后至少要跑的验证

- 单元测试
- cloud-edge 集成测试
- 端到端 smoke test
- 任务创建 + 回写闭环

## 8. 建议的本地检查命令

```bash
python -m pytest tests/unit/ -q
python -m pytest tests/integration/ -q
python -m pytest tests/e2e/ -q
python tests/run_all_tests.py
```
