# Aruba 真机验证快速参考卡

**设备**: ArubaAP (172.16.200.21)  
**连接**: SSH admin@172.16.200.21  
**密码**: aruba123

---

## 🚀 快速启动

### 1. SSH连接
```bash
ssh admin@172.16.200.21
# 输入密码: aruba123
```

### 2. 验证提示符
期望看到类似: `ArubaAP#` 或 `admin@ArubaAP#`

---

## 📋 核心验证命令 (按顺序执行)

### 阶段1: 基础验证 (5分钟)
```bash
# 1. 设备版本信息
show version

# 2. AP数据库
show ap database

# 3. 客户端摘要
show client summary

# 4. 接口状态
show interface brief
```

### 阶段2: 配置验证 (3分钟)
```bash
# 5. 查看运行配置 (可按q退出)
show running-config

# 6. 保存配置
write memory
```

### 阶段3: 高级验证 (5分钟)
```bash
# 7. 命令组合测试
show version && show ap database && show client summary

# 8. 网络测试
ping 8.8.8.8

# 9. Aruba巡检模板
show version && show ap database && show client summary && show wlan ssid
```

### 阶段4: 错误处理 (2分钟)
```bash
# 10. 无效命令测试
show invalid_command

# 11. 权限测试
configure terminal
```

---

## ✅ 验证检查点

### 每个命令执行后检查:
- [ ] 命令执行无语法错误
- [ ] 返回结果格式正确
- [ ] 响应时间合理 (< 5秒)
- [ ] 无异常错误信息

### 关键验证点:
- [ ] `show interface brief` - 验证命令适配映射
- [ ] `write memory` - 验证配置保存映射  
- [ ] `show ap database` - 验证Aruba特有命令
- [ ] 复杂命令组合 - 验证命令不被错误修改

---

## 📊 结果记录表

| # | 命令 | 状态 | 耗时 | 备注 |
|---|------|------|------|------|
| 1 | show version | ☐ | ___s | |
| 2 | show ap database | ☐ | ___s | Aruba特有 |
| 3 | show client summary | ☐ | ___s | Aruba特有 |
| 4 | show interface brief | ☐ | ___s | 适配映射 |
| 5 | show running-config | ☐ | ___s | |
| 6 | write memory | ☐ | ___s | 适配映射 |
| 7 | 组合命令 | ☐ | ___s | 复杂命令 |
| 8 | ping测试 | ☐ | ___s | |
| 9 | 巡检模板 | ☐ | ___s | 模板验证 |
| 10 | 无效命令 | ☐ | ___s | 错误处理 |
| 11 | 权限测试 | ☐ | ___s | 错误处理 |

**符号说明**: ☐ = 待测试 | ✅ = 成功 | ❌ = 失败 | ⚠️ = 部分成功

---

## 🛑 故障排除

### SSH连接问题
```bash
# 检查网络连通性
ping 172.16.200.21

# 检查SSH端口
telnet 172.16.200.21 22

# 尝试详细连接
ssh -v admin@172.16.200.21
```

### 命令执行问题
```bash
# 检查当前模式 (enable/disable)
show mode

# 进入特权模式 (如需要)
enable

# 退出特权模式
disable

# 退出SSH
exit 或 logout
```

### 输出过长处理
```bash
# 分页查看
show running-config | include interface

# 保存到文件 (本地)
ssh admin@172.16.200.21 "show running-config" > output.txt
```

---

## 📝 快速记录模板

```
=== 验证开始 ===
时间: __:___
连接: ☐ 成功  ☐ 失败

=== 基础验证 ===
show version:          ☐ 成功  ☐ 失败  | 耗时: ___s
show ap database:      ☐ 成功  ☐ 失败  | 耗时: ___s  
show client summary:   ☐ 成功  ☐ 失败  | 耗时: ___s
show interface brief:  ☐ 成功  ☐ 失败  | 耗时: ___s

=== 配置验证 ===
show running-config:   ☐ 成功  ☐ 失败  | 耗时: ___s
write memory:          ☐ 成功  ☐ 失败  | 耗时: ___s

=== 高级验证 ===
组合命令:              ☐ 成功  ☐ 失败  | 耗时: ___s
ping测试:              ☐ 成功  ☐ 失败  | 耗时: ___s
巡检模板:              ☐ 成功  ☐ 失败  | 耗时: ___s

=== 错误处理 ===
无效命令:              ☐ 正常  ☐ 异常
权限测试:              ☐ 正常  ☐ 异常

=== 验证完成 ===
总耗时: ___ 分钟
成功率: ___ / 11 (___%)
总体评估: ☐ 生产就绪  ☐ 需要修复  ☐ 不推荐

=== 备注 ===
[记录重要发现和问题]
```

---

## 🎯 验证完成标准

### ✅ 生产就绪 (推荐部署)
- 所有11项测试 ✅ 通过
- 无关键错误
- 响应时间正常
- 输出格式正确

### ⚠️ 需要修复 (谨慎部署)
- 8-10项测试通过
- 有非关键问题
- 需要小修复
- 功能基本完整

### ❌ 不推荐 (停止部署)
- < 8项测试通过
- 有关键功能失败
- 有严重错误
- 需要重大修复

---

## 📞 验证支持

**遇到问题时记录**:
1. 具体错误消息
2. 执行的命令
3. 设备响应
4. 网络状态

**快速诊断信息**:
```bash
# 收集诊断信息
show system
show version
show ip interface
show arp
```

---

**预计验证时间**: 15-20分钟  
**难度级别**: ⭐⭐☆☆☆ (简单)  
**前置条件**: 网络连接正常，SSH客户端可用

---

**创建时间**: 2026-04-21  
**适用版本**: Phase 4B Aruba设备支持  
**验证状态**: 准备执行