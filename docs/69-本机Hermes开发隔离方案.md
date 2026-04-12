# 69 本机 Hermes 开发隔离方案

## 目标

让 HermesNexus 的本机开发环境可以使用 Hermes 能力，同时与当前正在使用的 Hermes 完全隔离，避免配置、记忆、会话和依赖互相污染。

## 结论

- 本机开发环境会用到 Hermes。
- 但 HermesNexus 必须使用独立的项目环境，不复用你当前正在使用的 Hermes 主环境。
- 最稳妥的做法是：独立仓库 + 独立虚拟环境 + 独立 HERMES_HOME + 独立配置文件。

## 隔离目标

需要隔离的内容包括：

- Python 依赖
- Hermes 配置
- Hermes session / memory / skills
- Claude Code 配套命令
- 项目 .env
- 临时调试数据

## 推荐隔离方式

### 1. Python 依赖隔离

- HermesNexus 使用独立虚拟环境。
- 不要依赖系统全局 Python 包。
- 开发时先激活项目环境，再启动任何 Hermes 相关命令。

建议：

```bash
cd /Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus
source .venv/bin/activate
```

### 2. Hermes 数据隔离

为 HermesNexus 单独设置 `HERMES_HOME`。

建议结构：

```text
/Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus/.hermes/
├── config.yaml
├── .env
├── memory/
├── skills/
├── sessions/
├── cache/
└── logs/
```

这样可以避免和你当前主 Hermes 的配置、记忆、技能和会话混在一起。

### 3. 配置隔离

- 项目使用自己的 `.env`
- 项目使用自己的 `config.yaml`
- 项目使用自己的 Claude Code 配套文件
- 不直接复用当前主 Hermes 的用户配置

### 4. 运行入口隔离

- 所有 HermesNexus 相关启动命令放在项目目录内
- 不直接依赖系统 PATH 里已有的全局 Hermes 入口
- 尽量使用仓库内脚本或明确路径

## 建议的开发启动流程

### 第一步：进入项目目录

```bash
cd /Users/shengchun.sun/Library/CloudStorage/OneDrive-个人/MyCloud/Code/HermesNexus
```

### 第二步：激活项目虚拟环境

```bash
source .venv/bin/activate
```

### 第三步：设置项目专用 Hermes 主目录

```bash
export HERMES_HOME="$PWD/.hermes"
```

### 第四步：启动项目相关工具

- Claude Code 配套命令
- HermesNexus 开发脚本
- 单元测试 / 集成测试
- 本地模拟器

## 与当前正在使用的 Hermes 如何共存

建议把它们当成两个独立角色：

### 当前主 Hermes

- 用于你日常现有工作流
- 保持原样
- 不改动现有配置和记忆

### HermesNexus 开发 Hermes

- 只服务于 HermesNexus 项目
- 只在项目目录和项目环境内使用
- 所有状态只写入项目自己的 `.hermes/`

## 最小可行隔离清单

如果你只想先做最小隔离，至少做到这四件事：

- [ ] 项目独立虚拟环境
- [ ] 项目独立 `HERMES_HOME`
- [ ] 项目独立 `.env`
- [ ] 项目独立启动脚本

## 推荐目录约定

```text
HermesNexus/
├── .claude/
├── .hermes/
├── .venv/
├── cloud/
├── edge/
├── shared/
├── console/
├── deploy/
├── tests/
└── docs/
```

## 注意事项

- 不要把主 Hermes 的 memory、skills、session 直接指向 HermesNexus。
- 不要在项目中硬编码 `~/.hermes`。
- 不要把系统级配置当成项目级配置。
- 如果项目后续拆分出单独的开发 profile，再把这些隔离策略固化到启动脚本里。

## MVP 建议

- MVP 阶段不需要做复杂的多 profile 自动切换。
- 先手工隔离，确保可控。
- 等项目稳定后，再考虑做自动化 profile 管理。
