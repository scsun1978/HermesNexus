# 12 任务 DSL 与 Job 模型

## 目标

让 Hermes 能把自然语言目标转换成结构化任务，并且支持验证、回滚和审计。

## Job 分层

### Job
顶层目标，例如：
- 检查本区域设备健康
- 升级 20 台交换机固件
- 发现新 IoT 设备

### JobStep
每个可执行步骤，例如：
- ping 检查
- SSH 读取配置
- 比对版本
- 执行升级
- 验证结果
- 回滚

### Action
最底层动作，例如：
- exec_command
- snmp_get
- mqtt_publish
- netconf_edit
- fetch_log

## DSL 设计目标

- 可读
- 可验证
- 可回放
- 可回滚
- 可审计

## 一个示例

```yaml
job:
  name: restart-nginx-site-a
  target: device-group/site-a/linux
  mode: supervised
  timeout: 900
  rollback: enabled
  steps:
    - name: precheck
      action: read_status
      verify: true
    - name: restart
      action: restart_service
      params:
        service: nginx
    - name: validate
      action: read_status
      verify:
        expect: service_running
    - name: rollback
      action: restart_service
      params:
        service: nginx
      when: step_failed
```

## 关键字段

- target：目标设备或设备组
- mode：自动 / 半自动 / 审批后执行
- precheck：执行前检查
- verify：执行后验证
- rollback：回滚策略
- retry：重试策略
- audit_tag：审计标签

## Hermes 的作用

Hermes 负责：
- 解释自然语言
- 生成 Job
- 选择适配器
- 决定是否需要拆分子任务
- 在执行中动态调整

## 约束建议

- 一个 Job 只做一类意图
- 一个 JobStep 只做一个动作
- 高风险 Job 必须附带 rollback
- 默认先验证再变更
