# 🚨 HermesNexus 生产环境紧急修复 - 立即执行

## 📊 当前状态: ❌ Partially ready

根据复测，生产环境的关键问题已确认：
- **API v1兼容端点全部404** - Cloud API代码未更新
- **Edge节点连接错误** - 仍连接localhost:8080
- **E2E任务链路中断** - 任务无法执行

---

## 🚀 立即修复方案

### 📦 完整修复包已准备

所有必要的修复脚本已准备好在 `fix/` 目录：

```
fix/
├── api_v1_patch.py      # Cloud API修复脚本 (添加API v1端点)
├── edge_fix.py          # Edge节点修复脚本 (修复连接配置)
├── EXECUTE_FIX.sh       # 一键自动修复脚本 (推荐)
└── README.md            # 详细修复指南
```

### ⚡ 快速执行 (推荐)

**在本地机器上执行以下命令**:

```bash
# 1. 上传修复包到生产服务器
scp -r fix/ scsun@172.16.100.101:/home/scsun/hermesnexus-fix/

# 2. 执行自动修复 (会自动完成所有修复步骤)
ssh scsun@172.16.100.101 "cd /home/scsun/hermesnexus-fix && chmod +x EXECUTE_FIX.sh && ./EXECUTE_FIX.sh"
```

### 📋 修复脚本会自动执行：

1. **修复Cloud API** - 添加API v1兼容端点
   - `GET /api/v1/tasks` - 任务列表查询
   - `POST /api/v1/nodes/<id>/heartbeat` - 节点心跳
   - `GET /api/v1/nodes/<id>/tasks/<id>/result` - 任务结果

2. **修复Edge节点** - 停止旧进程，启动新配置
   - 停止 `final-edge-node.py`
   - 修复配置：`localhost:8080` → `172.16.100.101:8082`
   - 启动修复后的Edge节点

3. **重启服务** - 使代码更改生效

4. **自动验证** - 测试所有端点和连接

---

## ✅ 修复后验证

修复脚本会自动验证，但建议手动确认：

```bash
# 1. 验证API v1端点 (应返回200 OK，不再是404)
curl http://localhost:8082/api/v1/tasks

# 2. 验证Edge节点 (应显示连接到8082)
curl http://localhost:8081/health

# 3. 创建E2E测试任务
curl -X POST http://localhost:8082/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_id": "fix-test-'$(date +%s)'", "name": "修复验证", "job_type": "command", "target_node_id": "edge-test-001", "command": "echo \"Fix validation passed\"", "created_by": "fix-test"}'

# 4. 等待20秒后检查任务状态
sleep 20
curl http://localhost:8082/api/jobs | grep fix-test
```

---

## 🎯 预期结果

### 修复前 ❌
```
GET /api/v1/tasks → 404 Not Found
Edge日志: Connection refused (localhost:8080)
任务状态: pending (永久不执行)
整体状态: Partially ready
```

### 修复后 ✅
```
GET /api/v1/tasks → 200 OK (返回任务列表)
Edge日志: 正常连接到 172.16.100.101:8082
任务状态: pending → running → completed (20秒内完成)
整体状态: 完整E2E通过
```

---

## 📈 时间预估

- **修复执行**: 5-8分钟
- **服务启动**: 3-5分钟
- **E2E验证**: 15-20分钟
- **总计**: 30分钟内完成

---

## 🔄 故障排查

如果自动修复脚本失败，请查看 `fix/README.md` 中的手动修复步骤。

### 常见问题

**Q: 脚本执行失败怎么办？**
A: 查看 `fix/README.md` 中的手动修复步骤，分步执行。

**Q: 修复后仍有404错误？**
A: 检查Cloud API是否重启：`ps aux | grep v12_standard_cloud`

**Q: Edge节点仍连接localhost？**
A: 检查Edge节点进程和配置：`curl http://localhost:8081/health`

---

## 📞 支持

详细修复指南：`fix/README.md`
故障排查：`fix/README.md` 中的故障排查章节

---

## 🎉 成功标志

修复成功的标志：

- ✅ `curl http://localhost:8082/api/v1/tasks` 返回200 OK
- ✅ Edge节点日志不再显示localhost:8080错误
- ✅ E2E测试任务在20秒内完成并返回completed状态
- ✅ 系统状态从"Partially ready"升级到"完整E2E通过"

---

**🎯 立即执行修复，30分钟内解决生产环境API不匹配问题！**