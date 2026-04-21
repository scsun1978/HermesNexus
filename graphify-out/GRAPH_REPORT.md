# Graph Report - .  (2026-04-21)

## Corpus Check
- 162 files · ~0 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2820 nodes · 8082 edges · 88 communities detected
- Extraction: 48% EXTRACTED · 52% INFERRED · 0% AMBIGUOUS · INFERRED: 4228 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]

## God Nodes (most connected - your core abstractions)
1. `AuditAction` - 117 edges
2. `AuditCategory` - 109 edges
3. `EventLevel` - 106 edges
4. `AuditService` - 91 edges
5. `AuditLogCreateRequest` - 88 edges
6. `Asset` - 88 edges
7. `Task` - 80 edges
8. `TaskPriority` - 79 edges
9. `AssetType` - 79 edges
10. `AuditLog` - 77 edges

## Surprising Connections (you probably didn't know these)
- `数据库模块单元测试  测试数据库的CRUD操作和线程安全性` --uses--> `Database`  [INFERRED]
  tests/unit/test_database.py → cloud/database/db.py
- `TestDataCleaner` --uses--> `SQLiteBackend`  [INFERRED]
  tests/integration/test_data_isolation.py → shared/database/sqlite_backend.py
- `TestConcurrencyManager` --uses--> `SQLiteBackend`  [INFERRED]
  tests/integration/test_data_isolation.py → shared/database/sqlite_backend.py
- `集成测试辅助工具 - 测试数据隔离和清理  提供测试数据隔离、临时数据库管理、测试环境清理等功能` --uses--> `SQLiteBackend`  [INFERRED]
  tests/integration/test_data_isolation.py → shared/database/sqlite_backend.py
- `测试数据隔离装饰器      Usage:         @with_test_data_isolation         def test_somethi` --uses--> `SQLiteBackend`  [INFERRED]
  tests/integration/test_data_isolation.py → shared/database/sqlite_backend.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (129): AuditExportRequest, AuditItemResult, AuditOperationType, AuditQueryRequest, AuditQueryResponse, AuditStatistics, BatchOperationAudit, Config (+121 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (118): PerformanceAnalyzer, 性能基线分析工具 - Week 4 Day 1 用于识别系统性能瓶颈，确定优化优先级, 测量操作性能          Args:             name: 操作名称             operation: 要测量的操作函数, DatabaseBackend, TaskModel, SQLiteBackend, cancel_task(), create_task() (+110 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (106): create_recovery_service(), get_recovery_service(), HermesNexus Phase 3 - 故障恢复服务 实现故障检测和自动恢复逻辑, 处理故障          Args:             task_id: 关联任务ID             failure_type: 故障类型, 初始化恢复服务          Args:             config: 恢复服务配置, 注册故障检测器          Args:             detector: 故障检测器函数，签名为 async def detector() ->, 创建自定义恢复服务      Args:         config: 恢复服务配置      Returns:         恢复服务实例, RecoveryService (+98 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (122): asset_heartbeat(), associate_node(), create_asset(), delete_asset(), disassociate_node(), get_asset(), get_asset_stats(), list_assets() (+114 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (101): create_audit_log(), export_audit_logs(), get_asset_audit_logs(), get_audit_stats(), get_node_audit_logs(), get_task_audit_logs(), query_audit_logs(), HermesNexus Phase 2 - Audit API Endpoints 审计日志 API 端点 (+93 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (72): Alert, AlertCategory, AlertManager, AlertRule, AlertSeverity, get_alert_manager(), HermesNexus 告警规则定义 定义告警阈值、严重级别和通知策略, RiskLevel (+64 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (64): ActionResult, ActorType, AuditFields, SecurityEventType, ActionType, BuiltInRoles, create_permission_checker(), get_permission_checker() (+56 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (52): BaseDAO, 初始化DAO          Args:             database: 数据库后端实例, 获取数据库会话          Returns:             数据库会话对象          Raises:             Runti, BaseDAO, NodeModel, 节点表ORM模型 - Phase 3: 节点身份管理, Config, NodeDAO (+44 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (66): add_approval_comment(), AddApprovalComment, cancel_approval_request(), check_approval_permission(), check_approval_timeout(), create_approval_request(), CreateApprovalRequest, get_approval_comments() (+58 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (17): FailureScenarios, main(), 失败场景模拟脚本  测试各种失败场景下系统的错误处理和恢复能力, main(), 简单SSH测试服务器  用于测试的轻量级SSH服务器，支持基本的SSH连接和命令执行, SimpleSSHServer, SSHTestServer, main() (+9 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (12): AuditLogger, 审计日志记录器  记录SSH执行器的操作日志, main(), SSH 任务执行器 (完善版)  实现通过 SSH 协议在远程 Linux 主机上执行命令 包含连接管理、错误处理、审计日志等完整功能, SSHExecutor, SSHExecutorPool, SSH执行器单元测试  测试SSH执行器的功能，不需要真实SSH连接, TestAuditLogger (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (9): EdgeNodeIntegrator, main(), 边缘节点集成脚本  自动化边缘节点的部署、注册和测试, EdgeStorage, 集成测试 - 云端与边缘节点集成  测试云端API和边缘节点之间的完整集成, TestCloudEdgeIntegration, TestDataConsistency, TestMultiNodeScenarios (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (14): AuthManager, HermesNexus Phase 2 - Authentication Manager 认证管理器 - 支持简单Token和API Key认证, 验证Token          Args:             token: Token字符串          Returns:, 创建API Key          Args:             user_id: 用户ID             name: API Key名称, 验证API Key          Args:             api_key: API Key字符串          Returns:, 撤销Token          Args:             token: Token字符串          Returns:, 撤销API Key          Args:             api_key: API Key字符串          Returns:, 获取用户权限列表          Args:             token: Token字符串          Returns: (+6 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (14): ABC, HermesNexus Phase 2 - Base DAO 数据访问对象基类, DatabaseBackend, HermesNexus Phase 2 - Database Backend Interface 数据库后端抽象接口, 初始化数据库后端          Args:             connection_string: 数据库连接字符串             echo, HermesNexus Phase 2 - SQLite Backend SQLite数据库后端实现, 获取数据库会话          Returns:             数据库会话对象, 健康检查          Returns:             数据库是否可用 (+6 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (16): batch_assets_operation(), batch_tasks_operation(), cancel_job(), create_device(), create_job(), get_job(), get_node(), get_node_tasks() (+8 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (27): closeBatchModal(), closeBatchResultModal(), closeModal(), deleteAsset(), displayAssets(), editAsset(), executeBatchOperation(), exportBatchResult() (+19 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (7): HermesAPIHandler, init_database(), main(), HermesNexus API请求处理器 - 完整版, 处理任务结果回写 - 应用stable版本验证过的逻辑, 获取作业列表（jobs是tasks的别名）, 初始化数据库 - 添加events和audit_logs表

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (3): EdgeNode, main(), SimpleEdgeNode

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (5): 批量获取设备          Args:             device_ids: 设备ID列表          Returns:, 批量更新设备          Args:             updates: 设备ID到更新数据的字典          Returns:, 批量添加设备          Args:             devices_data: 设备ID到设备数据的字典          Returns:, SQLite数据库持久化实现  提供基于SQLite的数据库持久化功能，支持数据重启恢复, SQLiteDatabase

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (23): changeViewMode(), escapeHtml(), filterNodes(), formatDateTime(), formatDuration(), getAssetTypeLabel(), getHealthStatusBadge(), getHealthStatusText() (+15 more)

### Community 20 - "Community 20"
Cohesion: 0.22
Nodes (4): init_database(), main(), 获取作业列表（jobs是tasks的别名）, StableAPIHandler

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (4): 数据库模块单元测试  测试数据库的CRUD操作和线程安全性, TestDatabaseCRUD, TestDatabaseEdgeCases, TestDatabaseThreadSafety

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (5): 端到端测试 - 完整工作流  测试从任务创建到结果返回的完整流程, TestAPIEndpoints, TestCompleteWorkflow, TestDataIntegrity, TestErrorHandling

### Community 23 - "Community 23"
Cohesion: 0.16
Nodes (19): cancelTask(), closeModal(), displayTasks(), filterTasks(), formatDate(), getPriorityBadge(), getStatusBadge(), getTaskTypeLabel() (+11 more)

### Community 24 - "Community 24"
Cohesion: 0.1
Nodes (13): assert_no_test_data_leak(), assert_test_data_isolated(), IsolatedTestCase, 集成测试辅助工具 - 测试数据隔离和清理  提供测试数据隔离、临时数据库管理、测试环境清理等功能, 测试数据隔离装饰器      Usage:         @with_test_data_isolation         def test_somethi, 断言测试数据相互隔离      Args:         test_ids: 测试数据ID列表, 断言没有测试数据泄漏      Args:         db: 数据库连接         test_prefixes: 测试数据前缀列表, setUpClass() (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (19): applyTimeRange(), displayLogs(), escapeHtml(), exportLogs(), filterLogs(), formatDateTime(), getActionLabel(), getCategoryLabel() (+11 more)

### Community 26 - "Community 26"
Cohesion: 0.1
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (7): hideLoading(), NotificationSystem, showError(), showInfo(), showLoading(), showSuccess(), showWarning()

### Community 28 - "Community 28"
Cohesion: 0.22
Nodes (14): escapeHtml(), filterEvents(), filterTasks(), initializeFilters(), loadAllData(), loadEvents(), loadNodes(), loadTasks() (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.25
Nodes (3): EdgeNode, main(), 🔥 关键功能：回写任务结果到Cloud API

### Community 30 - "Community 30"
Cohesion: 0.25
Nodes (3): EdgeNode, main(), 🔥 关键功能：回写任务结果到Cloud API

### Community 31 - "Community 31"
Cohesion: 0.19
Nodes (3): main(), 任务分发模拟脚本  模拟完整的任务分发流程：创建任务 -> 分配节点 -> 执行 -> 返回结果, TaskDispatcher

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (4): HermesAPIRequestHandler, HermesNexusCloudAPI, HermesNexus Cloud API v1.2.0, start_hermes_api()

### Community 33 - "Community 33"
Cohesion: 0.27
Nodes (4): _generate_performance_report(), PerformanceMetric, tearDownClass(), TestDatabasePerformanceBaseline

### Community 34 - "Community 34"
Cohesion: 0.12
Nodes (17): ApiKeyCreateRequest, ApiKeyCreateResponse, create_api_key(), create_token(), get_auth_config(), get_current_user_info(), HermesNexus Phase 2 - Authentication API 认证管理API, 撤销Token（需要管理员权限）      Args:         token: Token字符串         current_user: 当前用户信息 (+9 more)

### Community 35 - "Community 35"
Cohesion: 0.29
Nodes (3): HermesAPIHandler, init_database(), main()

### Community 36 - "Community 36"
Cohesion: 0.21
Nodes (2): EnhancedEdgeNode, main()

### Community 37 - "Community 37"
Cohesion: 0.21
Nodes (12): loadDashboard(), loadRecentActivity(), refreshAll(), refreshDashboard(), showError(), showSuccess(), updateAssetStats(), updateHeaderStats() (+4 more)

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (3): FinalE2ETest, main(), 最终端到端测试 - 完整系统验证  验证HermesNexus MVP的完整功能：云端创建任务 → 边缘节点接收 → SSH 执行 → 结果回传 → 云端可见

### Community 39 - "Community 39"
Cohesion: 0.23
Nodes (3): get_monitoring_dashboard(), MonitoringDashboard, HermesNexus 监控面板 提供系统状态可视化和告警展示

### Community 40 - "Community 40"
Cohesion: 0.27
Nodes (2): main(), SystemMonitor

### Community 41 - "Community 41"
Cohesion: 0.28
Nodes (2): main(), PerformanceAnalyzer

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (6): 测试jobs API修复 - 验证422错误是否解决  专门测试 /api/v1/jobs 端点的契约正确性, 测试POST /api/v1/jobs端点 - 创建任务, 测试GET /api/v1/jobs/{job_id}端点, 测试GET /api/v1/jobs端点 - 最基础的连通性测试, 测试GET /api/v1/jobs带查询参数, TestJobsAPIFix

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (4): check_cloud_api(), generate_mvp_summary(), main(), 系统健康检查脚本  快速验证HermesNexus MVP各组件状态

### Community 44 - "Community 44"
Cohesion: 0.25
Nodes (3): main(), PerformanceTester, 性能和压力测试  测试HermesNexus MVP的性能表现和负载能力

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (2): PerformanceBottleneckAnalyzer, 性能瓶颈识别工具 - Week 4 Day 1 通过代码静态分析和架构审查识别潜在性能瓶颈

### Community 46 - "Community 46"
Cohesion: 0.2
Nodes (9): health_check(), metrics(), performance_stats(), HermesNexus Monitoring API 监控和指标API端点, 性能统计端点      Returns:         系统性能统计数据, 详细健康检查端点      Returns:         系统健康状态详情, 系统状态概览      Returns:         系统整体状态信息, Prometheus格式的指标导出端点      Returns:         Prometheus格式的指标文本 (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.36
Nodes (2): ConfigValidator, main()

### Community 48 - "Community 48"
Cohesion: 0.46
Nodes (7): main(), test_api_registration(), test_code_structure(), test_documentation(), test_file_structure(), test_json_configs(), test_test_files()

### Community 49 - "Community 49"
Cohesion: 0.46
Nodes (7): main(), test_batch_operation_models(), test_batch_operation_service(), test_error_classification(), test_idempotency(), test_parallel_execution(), test_partial_failure_handling()

### Community 50 - "Community 50"
Cohesion: 0.32
Nodes (6): check_all_permissions(), check_any_permission(), check_permission(), get_required_permissions(), HermesNexus Phase 2 - Permission Checker 权限检查器 - 定义和检查操作权限, 获取操作所需的权限      Args:         method: HTTP方法         path: 请求路径      Returns:

### Community 51 - "Community 51"
Cohesion: 0.71
Nodes (6): _cleanup_isolated_db(), main(), _make_isolated_db(), test_asset_crud(), test_audit_crud(), test_task_crud()

### Community 52 - "Community 52"
Cohesion: 0.52
Nodes (6): main(), test_api_integration(), test_node_identity_models(), test_node_list_models(), test_node_list_service(), test_ui_compatibility()

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 0.6
Nodes (5): find_edge_node_files(), fix_edge_node_config(), main(), start_edge_node(), stop_old_edge_processes()

### Community 55 - "Community 55"
Cohesion: 0.6
Nodes (4): main(), 控制台功能测试  验证控制台页面和API集成, test_api_endpoints(), test_console_integration()

### Community 56 - "Community 56"
Cohesion: 0.6
Nodes (3): demonstrate_monitoring(), simulate_api_traffic(), simulate_system_metrics()

### Community 57 - "Community 57"
Cohesion: 0.4
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (3): main(), 测试运行器 - 运行所有测试套件  执行单元测试、集成测试和端到端测试, run_command()

### Community 59 - "Community 59"
Cohesion: 0.67
Nodes (3): main(), 简单性能测试  测试基础性能指标，不依赖复杂模块, test_api_performance()

### Community 60 - "Community 60"
Cohesion: 0.5
Nodes (2): add_api_v1_endpoints(), 在Cloud API中添加API v1兼容端点

### Community 61 - "Community 61"
Cohesion: 0.67
Nodes (2): add_api_v1_post_heartbeat(), 在Cloud API的do_POST方法中添加API v1 heartbeat端点

### Community 62 - "Community 62"
Cohesion: 0.67
Nodes (2): add_api_v1_compatibility(), 在现有的Cloud API代码中添加API v1兼容端点

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): 初始化数据库连接          创建引擎、连接池和会话工厂

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): 创建所有数据表          根据ORM模型定义创建表结构

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): 删除所有数据表          注意：此操作会删除所有数据，谨慎使用

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): 关闭数据库连接          释放资源，清理连接池

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): 获取数据库会话          Returns:             数据库会话对象

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): 健康检查          Returns:             数据库是否可用

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): 获取角色的默认权限          Args:             role: 角色名称          Returns:             权限

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): 检查用户是否有指定权限          Args:             user_permissions: 用户权限列表             requ

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): 检查用户是否有任意一个指定权限          Args:             user_permissions: 用户权限列表

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): 检查用户是否有所有指定权限          Args:             user_permissions: 用户权限列表             re

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): 插入实体          Args:             entity: 要插入的实体对象          Returns:             插

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): 按ID查询          Args:             id: 实体ID          Returns:             实体对象，如果不

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): 更新实体          Args:             entity: 要更新的实体对象          Returns:             更

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): 删除实体          Args:             id: 实体ID          Returns:             是否删除成功

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): 查询实体列表          Args:             filters: 过滤条件字典             limit: 返回数量限制

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): 统计实体数量          Args:             filters: 过滤条件字典          Returns:

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): 兼容旧字段名 meta_data，并把常见的扁平字典转换为 AssetMetadata

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): 检查是否可以进行状态转换          Args:             from_status: 当前状态             to_status:

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): 获取当前状态的所有有效转换          Args:             from_status: 当前状态          Returns:

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): 检查是否为终态          Args:             status: 审批状态          Returns:             是否

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (0): 

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (0): 

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (0): 

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (0): 

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **110 isolated node(s):** `🔥 关键功能：回写任务结果到Cloud API`, `🔥 关键功能：回写任务结果到Cloud API`, `HermesNexus API请求处理器 - 完整版`, `处理任务结果回写 - 应用stable版本验证过的逻辑`, `获取作业列表（jobs是tasks的别名）` (+105 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 63`** (1 nodes): `初始化数据库连接          创建引擎、连接池和会话工厂`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `创建所有数据表          根据ORM模型定义创建表结构`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `删除所有数据表          注意：此操作会删除所有数据，谨慎使用`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `关闭数据库连接          释放资源，清理连接池`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `获取数据库会话          Returns:             数据库会话对象`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `健康检查          Returns:             数据库是否可用`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `获取角色的默认权限          Args:             role: 角色名称          Returns:             权限`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `检查用户是否有指定权限          Args:             user_permissions: 用户权限列表             requ`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `检查用户是否有任意一个指定权限          Args:             user_permissions: 用户权限列表`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `检查用户是否有所有指定权限          Args:             user_permissions: 用户权限列表             re`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `插入实体          Args:             entity: 要插入的实体对象          Returns:             插`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `按ID查询          Args:             id: 实体ID          Returns:             实体对象，如果不`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `更新实体          Args:             entity: 要更新的实体对象          Returns:             更`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `删除实体          Args:             id: 实体ID          Returns:             是否删除成功`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `查询实体列表          Args:             filters: 过滤条件字典             limit: 返回数量限制`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `统计实体数量          Args:             filters: 过滤条件字典          Returns:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `兼容旧字段名 meta_data，并把常见的扁平字典转换为 AssetMetadata`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `检查是否可以进行状态转换          Args:             from_status: 当前状态             to_status:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `获取当前状态的所有有效转换          Args:             from_status: 当前状态          Returns:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `检查是否为终态          Args:             status: 审批状态          Returns:             是否`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `云端 API 服务  使用 FastAPI 提供 REST API 接口` connect `Community 5` to `Community 1`, `Community 3`, `Community 4`, `Community 7`, `Community 39`, `Community 10`, `Community 12`, `Community 13`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `Database` connect `Community 0` to `Community 43`, `Community 11`, `Community 44`, `Community 18`, `Community 21`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `ErrorCode` connect `Community 5` to `Community 10`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 114 inferred relationships involving `AuditAction` (e.g. with `TestAuditReplayService` and `TestAuditReplayIntegration`) actually correct?**
  _`AuditAction` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Are the 106 inferred relationships involving `AuditCategory` (e.g. with `TestAuditReplayService` and `TestAuditReplayIntegration`) actually correct?**
  _`AuditCategory` has 106 INFERRED edges - model-reasoned connections that need verification._
- **Are the 103 inferred relationships involving `EventLevel` (e.g. with `TestAuditReplayService` and `TestAuditReplayIntegration`) actually correct?**
  _`EventLevel` has 103 INFERRED edges - model-reasoned connections that need verification._
- **Are the 76 inferred relationships involving `AuditService` (e.g. with `TestAuditReplayService` and `TestAuditReplayIntegration`) actually correct?**
  _`AuditService` has 76 INFERRED edges - model-reasoned connections that need verification._