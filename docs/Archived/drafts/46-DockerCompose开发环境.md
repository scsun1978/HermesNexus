# 46 Docker Compose 开发环境

## 目标

提供一个本地可快速启动的 Hermes 云边开发环境。

## 必备服务

- cloud-api
- task-orchestrator
- asset-service
- event-service
- edge-node
- postgres
- redis / nats
- console

## 开发环境原则

- 一键启动
- 一键清理
- 可热重载
- 便于调试日志
- 保留最小依赖

## 推荐目录

```text
deploy/
├── compose/
├── k8s/
├── scripts/
└── env/
```

## 开发场景

### 场景 1：只跑云端
- 启动 API、DB、Console

### 场景 2：云边联调
- 再启动 edge-node
- 模拟任务下发与回传

### 场景 3：设备驱动开发
- 挂载驱动代码
- 模拟协议端点

## 调试建议

- 日志统一输出到 stdout
- 每个服务单独一个容器
- 配置通过 env 注入
- 本地卷挂载代码和数据
