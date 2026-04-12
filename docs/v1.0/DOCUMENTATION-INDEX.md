# HermesNexus v1.0 文档索引

## 文档结构

```text
docs/v1.0/
├── README.md            # 文档总览
├── ARCHITECTURE.md      # 架构与运行模型
├── API.md               # 接口契约
├── DEPLOYMENT.md        # 部署指南
├── DEVELOPMENT.md       # 开发指南
├── TESTING.md           # 测试与验收
├── USER-GUIDE.md        # 用户使用说明
├── RELEASE-NOTES.md     # 版本说明
└── DOCUMENTATION-INDEX.md
```

## 说明

这套文档按当前真实实现重写，默认以以下运行时为准：

- Cloud API：stable-cloud-api.py
- Edge Node：final-edge-node.py
- 数据库：/home/scsun/hermesnexus/data/hermesnexus.db
- 日志：/home/scsun/hermesnexus/logs/
- 默认服务端口：8080

## 阅读顺序

### 1. 先看 README.md
快速了解版本状态、当前实现路径和文档入口。

### 2. 再看 ARCHITECTURE.md
理解 Cloud API、Edge Node、SQLite、事件和审计日志的关系。

### 3. 再看 API.md
这是开发和联调的接口事实来源。

### 4. 再看 DEPLOYMENT.md
说明如何在本机和开发服务器上启动当前实现。

### 5. 再看 TESTING.md
说明如何验证部署、任务闭环和回归。

### 6. 再看 DEVELOPMENT.md
说明本机开发时应该如何避免环境污染。

### 7. 最后看 USER-GUIDE.md 与 RELEASE-NOTES.md
用于向使用方说明能力边界和版本状态。

## 文档维护原则

- API 先于文档：接口变更必须先更新代码契约，再更新文档。
- 以已验证实现为准：文档不保留过时接口名作为默认表述。
- 目标和现状分开写：尚未实现的能力必须明确标注为“下一阶段”。
