# 19 Hermes Skills 设计规范

## 目标

把设备操作和站点经验沉淀成可复用、可组合、可审计的技能。

## Skill 的定位

Skill 是 Hermes 的流程能力单元，应该负责：
- 一个清晰场景
- 一组相关动作
- 一种设备/协议能力
- 一套可复用经验

## Skill 分类

### 1. 设备类
- ssh-host-maintenance
- mqtt-device-control
- snmp-network-check

### 2. 运维类
- backup-and-restore
- incident-triage
- firmware-upgrade

### 3. 观察类
- health-audit
- config-drift-detect
- topology-discovery

### 4. 站点类
- site-a-onboarding
- site-a-nightly-check
- site-a-remediation

## 一个好 Skill 应该包含

- 适用范围
- 前置条件
- 输入参数
- 执行步骤
- 验证方法
- 回滚方案
- 风险说明

## 设计原则

1. 颗粒度适中，不能太大也不能太碎。
2. Skill 要可组合。
3. Skill 要写明风险边界。
4. Skill 要尽量幂等。
5. Skill 要避免硬编码站点私有信息。

## 推荐结构

- README / 说明
- 触发条件
- 执行步骤
- 失败处理
- 验证标准
- 示例

## Hermes 如何使用 Skill

Hermes 可根据任务自动选择技能，也可在云端控制平面中显示为可选操作模板。
