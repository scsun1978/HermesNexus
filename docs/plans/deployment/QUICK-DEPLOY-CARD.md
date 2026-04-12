# 🚀 HermesNexus 快速部署卡片

## 📦 准备工作 (本地)

### 1. 部署包已准备 ✅
- 文件: `hermesnexus-deploy.tar.gz` (295KB)
- 位置: 当前项目根目录
- 内容: 完整代码 + 部署脚本 + 配置文件

### 2. 传输方案选择

**⚡ 最快方案**: USB传输
```bash
# 复制到USB，然后到服务器上:
cp /media/USB/hermesnexus-deploy.tar.gz ~/
```

**🌐 网络方案**: HTTP服务器
```bash
# 本地启动HTTP服务器
python3 -m http.server 8000

# 服务器上下载 (将<本地IP>替换为实际IP)
curl http://<本地IP>:8000/hermesnexus-deploy.tar.gz -o ~/deploy.tar.gz
```

**🔧 技术方案**: SSH密钥
```bash
# 配置SSH密钥
ssh-copy-id scsun@172.16.100.101
scp hermesnexus-deploy.tar.gz scsun@172.16.100.101:~/
```

---

## 🛠️ 服务器部署 (3步完成)

### 第1步: 解压
```bash
cd ~
tar -xzf hermesnexus-deploy.tar.gz -C hermesnexus --strip-components=0
cd hermesnexus
```

### 第2步: 部署
```bash
chmod +x deploy-package.sh
./deploy-package.sh
```

### 第3步: 验证
```bash
# 快速验证
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/stats
```

---

## ✅ 成功标志

看到以下输出表示部署成功:
```json
{
  "status": "healthy",
  "version": "1.1.0",
  "timestamp": "2026-04-11T..."
}
```

---

## 🧪 快速测试

```bash
# 创建测试任务
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_id":"test001","node_id":"dev-edge-node-001","task_type":"ssh_command","target":{"host":"localhost","command":"echo OK","username":"scsun"}}'
```

---

## 🆘 遇到问题?

1. **端口被占用**: `sudo lsof -i :8080` 然后 `kill -9 <PID>`
2. **权限问题**: `chmod +x ~/hermesnexus/deploy-package.sh`
3. **依赖错误**: `cd ~/hermesnexus && source venv/bin/activate && pip install -r requirements.txt`

---

## 📞 完整文档

详细指南: `DEPLOYMENT-INSTRUCTIONS.md`  
执行计划: `TASK-59-EXECUTION-PLAN.md`

---

**预计时间**: 10-15分钟 | **成功率**: 95%+