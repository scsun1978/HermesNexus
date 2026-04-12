# 61 开发脚本与 Makefile 约定

## 目标

让开发者通过统一命令完成启动、测试、迁移、模拟和发布准备。

## 推荐命令集合

### 基础命令
- make init
- make dev
- make test
- make lint
- make fmt
- make clean

### 运维命令
- make migrate
- make seed
- make backup
- make restore
- make doctor

### 模拟命令
- make simulate-node
- make simulate-device
- make simulate-alert
- make simulate-network-fail

## Makefile 设计原则

- 命令短且稳定
- 每个命令只做一件事
- 命令输出要清晰
- 命令失败要有明确错误

## 脚本分层

### scripts/init
初始化开发环境。

### scripts/dev
本地启动服务。

### scripts/migrate
数据库迁移。

### scripts/seed
写入测试数据。

### scripts/simulate
模拟边缘节点、设备和事件。

## 建议输出

- 执行了什么
- 成功/失败
- 下一步建议

## 开发体验建议

- 一条命令拉起完整本地环境
- 一条命令跑全量测试
- 一条命令生成 mock 数据
- 一条命令查看系统状态
