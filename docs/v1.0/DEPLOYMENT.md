# HermesNexus v1.0 部署指南

## 1. 部署目标

当前 v1.0 的部署目标很明确：

- 本机用于开发和快速验证
- 开发服务器用于真实联调和回归
- 云端服务与边缘节点都在服务器上运行
- 以当前验证通过的稳定运行时为准

## 2. 当前默认运行约定

当前实现默认假设运行目录为：

- /home/scsun/hermesnexus

默认数据和日志路径：

- 数据库：/home/scsun/hermesnexus/data/hermesnexus.db
- 日志：/home/scsun/hermesnexus/logs/

如果你把项目放在别的目录，需要同步修改代码中的常量，或者用软链接保持该路径可用。

## 3. 依赖

### Cloud API

Cloud API 当前使用标准库即可运行：

- Python 3.12+
- 无强制第三方依赖

### Edge Node

Edge Node 需要：

- Python 3.12+
- requests
- psutil（可选；没有也能运行，会退化为 0 资源值）

建议在项目虚拟环境里安装：

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests psutil
```

## 4. 本机开发部署

### 启动 Cloud API

```bash
source venv/bin/activate
python3 stable-cloud-api.py
```

默认监听：

- http://localhost:8080

### 启动 Edge Node

```bash
source venv/bin/activate
export CLOUD_API_URL=http://localhost:8080
export NODE_ID=dev-edge-node-001
export NODE_NAME="开发服务器边缘节点"
python3 final-edge-node.py
```

## 5. 开发服务器部署

推荐顺序：

1. 先启动 Cloud API
2. 确认 /health 返回 healthy
3. 再启动 Edge Node
4. 创建设备
5. 创建任务
6. 验证任务完成、事件、审计日志

### Cloud API

```bash
cd /home/scsun/hermesnexus
source venv/bin/activate
nohup python3 stable-cloud-api.py > logs/cloud-api.log 2>&1 &
```

### Edge Node

```bash
cd /home/scsun/hermesnexus
source venv/bin/activate
export CLOUD_API_URL=http://127.0.0.1:8080
export NODE_ID=dev-edge-node-001
export NODE_NAME="开发服务器边缘节点"
nohup python3 final-edge-node.py > logs/edge-node.log 2>&1 &
```

## 6. systemd 示例

如果你希望开机自启，可以使用 systemd。示例路径仍然按当前实现的默认目录写死。

### Cloud API

```ini
[Unit]
Description=HermesNexus Cloud API
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/scsun/hermesnexus
ExecStart=/usr/bin/python3 /home/scsun/hermesnexus/stable-cloud-api.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Edge Node

```ini
[Unit]
Description=HermesNexus Edge Node
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/scsun/hermesnexus
Environment=CLOUD_API_URL=http://127.0.0.1:8080
Environment=NODE_ID=dev-edge-node-001
Environment=NODE_NAME=开发服务器边缘节点
ExecStart=/usr/bin/python3 /home/scsun/hermesnexus/final-edge-node.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## 7. 部署后验证

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/stats
curl http://localhost:8080/api/v1/devices
curl http://localhost:8080/api/v1/tasks
curl http://localhost:8080/api/v1/events
curl http://localhost:8080/api/v1/audit_logs
```

## 8. 最小可用验收顺序

1. /health 正常
2. 创建设备成功
3. 创建任务成功
4. Edge Node 拉到该任务
5. Edge Node 回写结果成功
6. events 有 task_created / task_completed
7. audit_logs 有 task_created / task_result_completed

## 9. 常见问题

- 任务一直 pending：检查任务是否带了 node_id，且 node_id 与 Edge Node 一致
- 节点不执行：确认 Edge Node 在轮询 /api/v1/tasks
- 回写失败：确认 /api/v1/nodes/{node_id}/tasks/{task_id}/result 可访问
- 数据不见了：确认数据库文件是否还是 /home/scsun/hermesnexus/data/hermesnexus.db
