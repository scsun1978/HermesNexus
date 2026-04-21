# HermesNexus 审计功能使用指南

## 📋 概述

HermesNexus v1.2 提供完整的审计功能，自动记录所有批量操作的详细信息，支持操作追踪、问题分析、合规审计等需求。

## 🎯 主要功能

### 1. 自动审计记录
- **自动化**: 批量操作完成后自动记录审计日志
- **详细信息**: 记录操作参数、结果、错误信息等
- **性能无影响**: 异步记录，不影响操作性能
- **完整追踪**: 记录操作时间、用户、IP地址等

### 2. 强大的查询功能
- **按操作ID查询**: 快速查找特定操作的审计记录
- **按资产/节点查询**: 查看特定资源的历史操作
- **按用户查询**: 追踪特定用户的操作历史
- **按错误类型查询**: 分析特定类型的失败操作
- **按时间范围查询**: 查看指定时间段的操作记录

### 3. 统计分析功能
- **操作统计**: 总操作数、成功/失败统计
- **成功率分析**: 整体成功率和分类成功率
- **错误分析**: 错误类型分布和趋势
- **用户活动**: 用户操作活跃度排名
- **时间分布**: 操作时间分布分析

## 🔍 审计记录内容

### 基本信息
```json
{
  "audit_id": "audit-abc123",
  "operation_id": "batch-op-def456",
  "operation_type": "batch_asset_update",
  "user_id": "user-001",
  "username": "admin",
  "timestamp": "2026-04-15T10:30:00Z"
}
```

### 操作结果
```json
{
  "total_items": 10,
  "successful_items": 8,
  "failed_items": 2,
  "success_rate": 80.0,
  "error_summary": {
    "validation_error": 1,
    "not_found_error": 1
  }
}
```

### 详细结果
```json
{
  "results": [
    {
      "item_id": "asset-001",
      "success": true,
      "error_code": null,
      "error_message": null
    },
    {
      "item_id": "asset-002",
      "success": false,
      "error_code": "validation_error",
      "error_message": "缺少必需字段"
    }
  ]
}
```

## 🚀 使用场景

### 场景1: 追踪特定操作
**需求**: 查看批量操作的详细执行情况

**操作步骤**:
1. 获取批量操作的 `operation_id`
2. 使用操作ID查询审计记录
3. 查看详细结果和错误信息

**API调用**:
```python
# 查询特定操作的审计记录
audit = await audit_service.get_audit_by_operation_id("batch-op-def456")

# 查看操作结果
print(f"操作时间: {audit.timestamp}")
print(f"总项目数: {audit.total_items}")
print(f"成功: {audit.successful_items}")
print(f"失败: {audit.failed_items}")
print(f"成功率: {audit.success_rate}%")

# 查看详细结果
for result in audit.results:
    if result.success:
        print(f"✅ {result.item_id} - 成功")
    else:
        print(f"❌ {result.item_id} - 失败: {result.error_message}")
```

### 场景2: 资产历史查询
**需求**: 查看特定资产的所有操作历史

**操作步骤**:
1. 提供资产ID
2. 查询该资产的审计历史
3. 分析操作趋势和问题

**API调用**:
```python
# 查询资产历史
asset_history = await audit_service.get_asset_history("asset-001", limit=50)

# 按时间排序查看历史
for audit in reversed(asset_history):
    print(f"{audit.timestamp}: {audit.operation_type}")
    print(f"  状态: {'成功' if audit.failed_items == 0 else '部分失败'}")
    print(f"  成功率: {audit.success_rate}%")
```

### 场景3: 失败操作分析
**需求**: 分析特定类型的失败操作

**操作步骤**:
1. 指定错误类型或时间范围
2. 查询失败操作记录
3. 分析失败原因和模式

**API调用**:
```python
from datetime import datetime, timedelta

# 查询最近一天的失败操作
end_time = datetime.now()
start_time = end_time - timedelta(days=1)

failed_ops = await audit_service.get_failed_operations(
    error_type="validation_error",
    start_time=start_time,
    end_time=end_time,
    limit=100
)

# 分析失败模式
for audit in failed_ops:
    print(f"操作ID: {audit.operation_id}")
    print(f"失败数量: {audit.failed_items}")
    print(f"错误摘要: {audit.error_summary}")
    print(f"时间: {audit.timestamp}")
```

### 场景4: 操作统计分析
**需求**: 生成操作统计报告

**操作步骤**:
1. 指定统计时间范围
2. 获取统计数据
3. 生成分析报告

**API调用**:
```python
# 获取统计数据
from datetime import datetime, timedelta

end_time = datetime.now()
start_time = end_time - timedelta(days=7)

statistics = await audit_service.get_statistics(start_time, end_time)

# 生成报告
print(f"📊 操作统计报告 (最近7天)")
print(f"总操作数: {statistics.total_operations}")
print(f"成功操作: {statistics.successful_operations}")
print(f"失败操作: {statistics.failed_operations}")
print(f"成功率: {statistics.success_rate}%")

print(f"\n操作类型分布:")
for op_type, count in statistics.operation_type_counts.items():
    print(f"  {op_type}: {count}")

print(f"\n错误类型分布:")
for error_type, count in statistics.error_type_counts.items():
    print(f"  {error_type}: {count}")

print(f"\n用户活跃度:")
for user_id, count in statistics.user_activity.items():
    print(f"  {user_id}: {count} 次操作")
```

## 🔧 高级查询

### 复杂条件查询
```python
# 创建复杂查询条件
from shared.models.audit_models import AuditQueryRequest
from datetime import datetime, timedelta

query = AuditQueryRequest(
    # 基础过滤
    operation_type=AuditOperationType.BATCH_ASSET_UPDATE,
    user_id="admin",
    
    # 时间范围
    start_time=datetime.now() - timedelta(days=1),
    end_time=datetime.now(),
    
    # 结果过滤
    failed_only=True,
    error_type="validation_error",
    
    # 分页和排序
    page=1,
    page_size=20,
    sort_by="timestamp",
    sort_order="desc"
)

# 执行查询
response = await audit_service.query_audits(query)

print(f"找到 {response.total_count} 条记录")
for audit in response.records:
    print(f"操作: {audit.operation_id}")
    print(f"时间: {audit.timestamp}")
    print(f"失败: {audit.failed_items}/{audit.total_items}")
```

### 分页查询
```python
# 分页获取大量数据
page = 1
page_size = 50

while True:
    query = AuditQueryRequest(
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
        sort_by="timestamp",
        sort_order="desc"
    )
    
    response = await audit_service.query_audits(query)
    
    # 处理当前页数据
    for audit in response.records:
        # 处理审计记录
        pass
    
    # 检查是否还有更多数据
    if page >= response.total_pages:
        break
    page += 1
```

## 📊 数据导出

### 导出审计数据
```python
# 导出为JSON格式
query = AuditQueryRequest(
    start_time=start_time,
    end_time=end_time,
    page=1,
    page_size=1000
)

json_data = await audit_service.export_audits(
    query=query,
    format_type="json",
    include_details=True,
    max_records=1000
)

# 保存到文件
with open("audit_export.json", "w") as f:
    f.write(json_data)
```

### 导出格式
```json
{
  "export_time": "2026-04-15T10:30:00Z",
  "total_records": 150,
  "records": [
    {
      "audit_id": "audit-001",
      "operation_id": "batch-op-001",
      "operation_type": "batch_asset_create",
      "user_id": "admin",
      "timestamp": "2026-04-15T09:00:00Z",
      "total_items": 10,
      "successful_items": 8,
      "failed_items": 2,
      "success_rate": 80.0,
      "results": [...]
    }
  ]
}
```

## 🛡️ 安全与合规

### 数据安全
- **不可篡改**: 审计记录一旦创建不可修改
- **完整性保证**: 所有操作都有完整记录
- **访问控制**: 审计数据访问需要相应权限
- **备份机制**: 支持审计数据导出备份

### 合规支持
- **操作追踪**: 完整的用户操作轨迹
- **时间戳**: 精确的操作时间记录
- **用户身份**: 记录操作用户信息
- **源信息**: 记录请求来源IP和用户代理

## 📱 控制台审计查看

### 审计页面功能
1. **审计列表**: 显示所有审计记录
2. **详细查看**: 点击查看审计详情
3. **过滤搜索**: 按条件筛选审计记录
4. **统计图表**: 可视化操作统计
5. **数据导出**: 导出审计数据

### 审计详情页面
- **操作基本信息**: 操作ID、类型、时间、用户
- **操作结果摘要**: 总数、成功、失败、成功率
- **详细结果列表**: 每个项目的操作结果
- **错误信息展示**: 失败项目的详细错误
- **关联信息**: 相关的资产、节点、任务

## ⚠️ 注意事项

### 性能考虑
- **大量记录**: 长期运行会产生大量审计记录
- **查询优化**: 合理使用时间范围和过滤条件
- **分页处理**: 大量数据使用分页查询
- **定期清理**: 根据需求定期清理过期审计数据

### 存储管理
- **存储空间**: 监控审计数据存储空间使用
- **数据归档**: 定期归档历史审计数据
- **清理策略**: 制定合理的审计数据保留策略
- **备份恢复**: 确保审计数据有可靠备份

## 🔍 故障排查

### 审计记录缺失
**可能原因**:
- 审计服务未启用
- 审计存储空间不足
- 网络或系统故障

**解决方法**:
1. 检查审计服务状态
2. 检查存储空间和日志
3. 重启相关服务

### 查询缓慢
**可能原因**:
- 审计记录数量过大
- 缺少合适的索引
- 查询条件不够精确

**解决方法**:
1. 添加时间范围限制
2. 使用更精确的过滤条件
3. 考虑数据分页或归档

---

**版本**: v1.2.0  
**更新日期**: 2026-04-15  
**适用系统**: HermesNexus 批量操作和审计系统