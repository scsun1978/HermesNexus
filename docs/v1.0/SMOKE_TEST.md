# HermesNexus Phase 2 E2E 测试文档

**Version**: Phase 2 v2.0.0
**Date**: 2026-04-12
**Purpose**: 端到端测试流程验证

## 测试概述

E2E（End-to-End）测试验证完整的业务流程，从用户操作到系统响应的全链路测试。

## 前置条件

### 1. 环境准备
```bash
# 1. 确保Python环境已准备
python3 --version  # 应该是 3.12+

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
export HERMES_ENV=development
source .env.development
```

### 2. 服务启动
```bash
# 启动Cloud API
python3 stable-cloud-api.py &
CLOUD_PID=$!

# 等待服务启动
sleep 5

# 验证服务健康
curl http://localhost:8080/health
```

## E2E 测试场景

### 场景 1: 完整任务生命周期

#### 1.1 注册资产
```bash
# 创建Linux主机资产
ASSET_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/assets \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "E2E测试Linux主机",
    "asset_type": "linux_host",
    "description": "端到端测试资产",
    "metadata": {
      "ip_address": "192.168.1.100",
      "hostname": "e2e-test.local",
      "ssh_port": 22,
      "ssh_username": "testuser",
      "tags": ["e2e", "test"]
    }
  }')

ASSET_ID=$(echo $ASSET_RESPONSE | jq -r '.asset_id')
echo "创建资产: $ASSET_ID"
```

#### 1.2 创建任务
```bash
# 创建基础执行任务
TASK_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d "{
    \"name\": \"E2E测试任务\",
    \"task_type\": \"basic_exec\",
    \"priority\": \"normal\",
    \"target_asset_id\": \"$ASSET_ID\",
    \"command\": \"uname -a\",
    \"timeout\": 30,
    \"description\": \"端到端测试任务\"
  }")

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
echo "创建任务: $TASK_ID"
```

#### 1.3 分发任务
```bash
# 模拟分发任务到节点
DISPATCH_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/tasks/dispatch \
  -H 'Content-Type: application/json' \
  -d "{
    \"task_ids\": [\"$TASK_ID\"],
    \"target_node_id\": \"e2e-test-node\",
    \"dispatch_strategy\": \"batch\"
  }")

echo "任务分发完成"
```

#### 1.4 提交任务结果
```bash
# 模拟节点执行并提交结果
RESULT_RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/tasks/$TASK_ID/result \
  -H 'Content-Type: application/json' \
  -d "{
    \"task_id\": \"$TASK_ID\",
    \"node_id\": \"e2e-test-node\",
    \"status\": \"succeeded\",
    \"result\": {
      \"exit_code\": 0,
      \"stdout\": \"Linux localhost 5.15.0-72-generic x86_64\",
      \"stderr\": \"\",
      \"execution_time\": 0.5,
      \"started_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"completed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }
  }")

echo "任务结果提交完成"
```

#### 1.5 验证任务状态
```bash
# 查询任务最终状态
TASK_STATUS=$(curl -s http://localhost:8080/api/v1/tasks/$TASK_ID)
echo $TASK_STATUS | jq '.status'

# 验证审计日志
AUDIT_LOGS=$(curl -s "http://localhost:8080/api/v1/audit_logs/tasks/$TASK_ID?limit=10")
echo "审计日志记录数: $(echo $AUDIT_LOGS | jq '.audit_logs | length')"
```

### 场景 2: 资产管理完整流程

#### 2.1 批量创建资产
```bash
for i in {1..3}; do
  curl -s -X POST http://localhost:8080/api/v1/assets \
    -H 'Content-Type: application/json' \
    -d "{
      \"name\": \"批量测试资产 $i\",
      \"asset_type\": \"linux_host\",
      \"metadata\": {
        \"ip_address\": \"192.168.1.$((100+i))\",
        \"hostname\": \"batch-test-$i.local\"
      }
    }" > /dev/null
done
echo "批量创建资产完成"
```

#### 2.2 查询和过滤
```bash
# 查询所有资产
ALL_ASSETS=$(curl -s http://localhost:8080/api/v1/assets)
echo "总资产数: $(echo $ALL_ASSETS | jq '.total')"

# 按类型过滤
LINUX_HOSTS=$(curl -s "http://localhost:8080/api/v1/assets?asset_type=linux_host")
echo "Linux主机数: $(echo $LINUX_HOSTS | jq '.total')"

# 搜索资产
SEARCH_RESULT=$(curl -s "http://localhost:8080/api/v1/assets?search=批量")
echo "搜索结果数: $(echo $SEARCH_RESULT | jq '.total')"
```

#### 2.3 资产统计验证
```bash
# 获取资产统计
ASSETS_STATS=$(curl -s http://localhost:8080/api/v1/assets/stats)
echo $ASSETS_STATS | jq '.'
```

### 场景 3: 审计追踪验证

#### 3.1 验证完整审计链
```bash
# 1. 创建任务应该产生审计日志
# 2. 任务状态变更应该产生审计日志
# 3. 资产操作应该产生审计日志

# 查询所有审计日志
ALL_AUDITS=$(curl -s "http://localhost:8080/api/v1/audit_logs?page=1&page_size=100")
echo "总审计事件数: $(echo $ALL_AUDITS | jq '.total')"

# 查询错误级别日志
ERROR_LOGS=$(curl -s "http://localhost:8080/api/v1/audit_logs?level=error")
echo "错误事件数: $(echo $ERROR_LOGS | jq '.total')"
```

#### 3.2 按时间范围查询
```bash
# 查询最近1小时的审计日志
ONE_HOUR_AGO=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)
RECENT_LOGS=$(curl -s "http://localhost:8080/api/v1/audit_logs?start_time=$ONE_HOUR_AGO")
echo "最近1小时事件数: $(echo $RECENT_LOGS | jq '.total')"
```

## 测试验证点

### 功能验证
- [ ] 资产创建成功并可以查询
- [ ] 任务创建成功并可以查询
- [ ] 任务分发功能正常
- [ ] 任务结果提交功能正常
- [ ] 审计日志正确记录所有操作

### 性能验证
- [ ] API响应时间 < 1秒
- [ ] 批量操作支持
- [ ] 分页查询正确
- [ ] 过滤和搜索功能正常

### 数据验证
- [ ] 创建的数据可以正确查询
- [ ] 数据一致性保持
- [ ] 关联关系正确
- [ ] 统计数据准确

## 清理测试数据

```bash
# 清理测试资产
echo "清理测试数据..."

# 获取所有测试资产
TEST_ASSETS=$(curl -s "http://localhost:8080/api/v1/assets?search=测试")

# 删除每个测试资产
echo $TEST_ASSETS | jq -r '.assets[].asset_id' | while read asset_id; do
  curl -s -X DELETE "http://localhost:8080/api/v1/assets/$asset_id" > /dev/null
  echo "删除资产: $asset_id"
done

echo "清理完成"
```

## 测试报告模板

```markdown
# E2E 测试报告

**测试时间**: $(date)
**测试人员**: [姓名]
**测试环境**: Development

## 测试结果
- 总测试用例: X
- 通过: X
- 失败: X
- 成功率: XX%

## 详细结果

### 场景1: 完整任务生命周期
- 状态: ✅ 通过 / ❌ 失败
- 详情: ...

### 场景2: 资产管理完整流程
- 状态: ✅ 通过 / ❌ 失败
- 详情: ...

### 场景3: 审计追踪验证
- 状态: ✅ 通过 / ❌ 失败
- 详情: ...

## 问题记录

| 问题ID | 描述 | 严重程度 | 状态 |
|--------|------|----------|------|
| E2E-001 | ... | High | Open |

## 建议
- [建议列表]
```

## 自动化执行

```bash
# 保存测试脚本
chmod +x tests/scripts/e2e_test.sh

# 执行E2E测试
./tests/scripts/e2e_test.sh

# 查看测试报告
cat e2e_test_report.md
```

---

**注意事项**:
1. E2E测试应在隔离环境中进行
2. 每次测试后清理测试数据
3. 测试失败时保留现场以便调试
4. 定期执行E2E测试以验证系统稳定性
