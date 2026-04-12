# HermesNexus 服务器部署指南

**目标服务器**: scsun@172.16.100.101:22  
**部署时间**: 2026年4月11日  
**网络状态**: ✅ 连接正常

---

## 🚀 快速部署步骤

由于SSH认证限制，请按以下步骤在服务器上执行部署：

### 方法一：手动上传部署脚本 (推荐)

**步骤 1**: 创建部署包
```bash
# 在本地机器上，创建包含所有必要文件的部署包
tar -czf hermesnexus-deploy.tar.gz \
    cloud/ \
    edge/ \
    shared/ \
    deploy-package.sh \
    requirements.txt \
    configs/
```

**步骤 2**: 上传到服务器
```bash
# 使用scp上传部署包 (需要解决SSH认证问题)
scp hermesnexus-deploy.tar.gz scsun@172.16.100.101:~/

# 或者使用其他文件传输方法
# - 通过USB拷贝
# - 通过网络共享
# - 通过Git服务器
```

**步骤 3**: 在服务器上执行部署
```bash
# SSH登录到服务器
ssh scsun@172.16.100.101

# 解压部署包
tar -xzf hermesnexus-deploy.tar.gz
cd hermesnexus  # 或者解压后的目录

# 执行部署脚本
chmod +x deploy-package.sh
./deploy-package.sh
```

### 方法二：直接在服务器上Git克隆

**步骤 1**: 在服务器上克隆代码仓库
```bash
# SSH登录到服务器
ssh scsun@172.16.100.101

# 克隆代码仓库 (替换为实际的Git仓库地址)
git clone <your-git-repo-url> /home/scsun/hermesnexus
cd /home/scsun/hermesnexus

# 执行部署脚本
chmod +x deploy-package.sh
./deploy-package.sh
```

---

## 📋 部署脚本功能

`deploy-package.sh` 会自动执行以下操作：

### ✅ 自动化功能

1. **环境检查** - Python版本、磁盘空间、用户权限
2. **目录结构创建** - 项目根目录、数据目录、日志目录
3. **虚拟环境设置** - Python虚拟环境创建和依赖安装
4. **配置文件生成** - Cloud和Edge服务配置
5. **服务启动** - Cloud控制平面启动和健康检查

---

## 🧪 云边通信链路测试

部署完成后，执行以下测试验证完整功能：

### 1. 基础连接测试
```bash
# 健康检查
curl http://172.16.100.101:8080/health

# API统计
curl http://172.16.100.101:8080/api/v1/stats
```

### 2. 任务执行测试
```bash
# 创建测试任务
curl -X POST http://172.16.100.101:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-task-001",
    "node_id": "dev-edge-node-001",
    "task_type": "ssh_command",
    "target": {
      "host": "localhost",
      "command": "echo Hello from HermesNexus",
      "username": "scsun"
    }
  }'
```

---

**预计部署时间**: 15-30分钟
