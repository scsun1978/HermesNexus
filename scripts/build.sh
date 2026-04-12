#!/bin/bash
# 构建脚本 - 创建发布产物

set -e

VERSION=${1:-"dev"}
BUILD_DIR="dist"
ARTIFACT_DIR="build-artifacts"

echo "🔨 HermesNexus 构建脚本"
echo "=================================="
echo "版本: $VERSION"
echo "构建目录: $BUILD_DIR"
echo "产物目录: $ARTIFACT_DIR"
echo ""

# 创建构建目录
mkdir -p "$BUILD_DIR"
mkdir -p "$ARTIFACT_DIR"

# 1. 清理旧构建产物
echo "🧹 清理旧构建产物..."
rm -rf "$BUILD_DIR"/*
rm -rf "$ARTIFACT_DIR"/*
echo "✅ 清理完成"

# 2. 检查代码质量
echo ""
echo "🔍 代码质量检查..."
if [ -f "scripts/ci-check.sh" ]; then
    bash scripts/ci-check.sh
else
    echo "⚠️  未找到CI检查脚本，跳过"
fi

# 3. 创建Python包
echo ""
echo "📦 创建Python包..."
if command -v python3 &> /dev/null; then
    python3 -m pip install --quiet build
    python3 -m build
    echo "✅ Python包创建完成"

    # 复制构建产物
    cp -r dist/* "$ARTIFACT_DIR/"
else
    echo "❌ Python3未安装"
    exit 1
fi

# 4. 生成版本信息
echo ""
echo "📝 生成版本信息..."
cat > "$ARTIFACT_DIR/version.json" << EOF
{
  "version": "$VERSION",
  "build_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo "unknown")",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
}
EOF
echo "✅ 版本信息生成完成"

# 5. 创建部署包
echo ""
echo "📦 创建部署包..."
DEPLOY_PACKAGE="hermesnexus-$VERSION.tar.gz"

tar -czf "$ARTIFACT_DIR/$DEPLOY_PACKAGE" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='*.db' \
    --exclude='dist' \
    --exclude='build-artifacts' \
    --exclude='.venv' \
    --exclude='venv' \
    . 2>/dev/null || true

echo "✅ 部署包创建完成: $DEPLOY_PACKAGE"

# 6. 生成构建清单
echo ""
echo "📋 生成构建清单..."
cat > "$ARTIFACT_DIR/build-manifest.txt" << EOF
HermesNexus 构建清单
==================
版本: $VERSION
构建时间: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
构建主机: $(hostname)

构建产物:
$(ls -la "$ARTIFACT_DIR")

文件清单:
$(find "$ARTIFACT_DIR" -type f | sort)

检查清单:
- [ ] 代码质量检查通过
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] Smoke测试通过
- [ ] 性能基线验证通过
- [ ] 安全扫描无高危问题
- [ ] 构建产物完整
- [ ] 版本信息正确
EOF

echo "✅ 构建清单生成完成"

# 7. 生成部署说明
echo ""
echo "📖 生成部署说明..."
cat > "$ARTIFACT_DIR/deploy-guide.md" << EOF
# HermesNexus 部署指南

## 版本信息
- **版本**: $VERSION
- **构建时间**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **Git提交**: $(git rev-parse HEAD 2>/dev/null || echo "unknown")

## 部署包内容
\`\`\`
$DEPLOY_PACKAGE - 完整源码包
version.json - 版本信息
build-manifest.txt - 构建清单
\`\`\`

## 部署步骤

### 1. 环境准备
\`\`\`bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init-database.sh
\`\`\`

### 2. 配置检查
\`\`\`bash
# 检查环境变量
cp .env.example .env
# 编辑.env文件，设置必要的配置

# 验证配置
python scripts/validate-config.py
\`\`\`

### 3. 服务启动
\`\`\`bash
# 启动云控制平面
python cloud/main.py

# 启动边缘节点 (在目标服务器上)
python edge/main.py
\`\`\`

### 4. 健康检查
\`\`\`bash
# 检查服务状态
curl http://localhost:8000/health

# 运行Smoke测试
python tests/e2e/test_smoke.py
\`\`\`

## 回滚说明
如果部署后出现问题，按以下步骤回滚：

1. 停止服务
2. 恢复上一个版本的代码
3. 恢复数据库备份
4. 重启服务
5. 运行Smoke测试验证

## 注意事项
- 确保Python版本 >= 3.11
- 数据库迁移需要备份
- 配置文件需要根据环境调整
- 监控日志确保服务正常启动
EOF

echo "✅ 部署说明生成完成"

# 最终总结
echo ""
echo "=================================="
echo "🎉 构建完成！"
echo "=================================="
echo ""
echo "📦 构建产物:"
ls -la "$ARTIFACT_DIR"
echo ""
echo "📋 构建清单: $ARTIFACT_DIR/build-manifest.txt"
echo "📖 部署说明: $ARTIFACT_DIR/deploy-guide.md"
echo "🏷️  版本信息: $ARTIFACT_DIR/version.json"
echo ""
echo "✅ 构建产物已准备就绪，可以进行部署"

exit 0