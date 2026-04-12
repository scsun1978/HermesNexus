# HermesNexus v1.0 发布说明

## 1. 版本信息

- 版本号：v1.0.0-mvp
- 发布日期：2026-04-11
- 当前状态：MVP 验证通过
- 参考运行时：stable-cloud-api.py + final-edge-node.py

## 2. 本版完成了什么

### 已完成能力

- Cloud API 健康检查
- 设备注册
- 节点心跳
- 任务创建
- 任务轮询
- 任务执行
- 结果回写
- 事件流记录
- 审计日志记录

### 已验证闭环

- POST /api/v1/devices
- POST /api/v1/jobs 或 POST /api/v1/tasks
- GET /api/v1/tasks/{task_id}
- POST /api/v1/nodes/{node_id}/tasks/{task_id}/result
- GET /api/v1/events
- GET /api/v1/audit_logs

## 3. 这版的关键约定

- node_id 是任务目标必须字段
- Edge Node 轮询的是 /api/v1/tasks
- jobs 与 tasks 是当前实现中的别名
- 当前默认运行路径是 /home/scsun/hermesnexus

## 4. 当前已知限制

- 还不是高可用集群
- 还不是多机房方案
- 还不是复杂权限体系
- 还不是最终调度器版本

## 5. 下一阶段建议

下一阶段建议优先做三件事：

1. 把任务契约再统一一轮，减少 jobs/tasks/devices/nodes 的边界歧义
2. 给部署脚本做参数化，减少对固定路径的依赖
3. 把更多验证脚本整理成正式的 smoke / e2e 流程
