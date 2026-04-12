# Graph Report - .  (2026-04-12)

## Corpus Check
- Large corpus: 334 files · ~189,187 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 1364 nodes · 4473 edges · 47 communities detected
- Extraction: 44% EXTRACTED · 56% INFERRED · 0% AMBIGUOUS · INFERRED: 2517 edges (avg confidence: 0.5)
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

## God Nodes (most connected - your core abstractions)
1. `AuditAction` - 65 edges
2. `EventLevel` - 65 edges
3. `AuditCategory` - 65 edges
4. `AuditLogCreateRequest` - 64 edges
5. `任务执行器模块  包含各种任务类型的执行器实现` - 63 edges
6. `Asset` - 58 edges
7. `ErrorCode` - 55 edges
8. `Task` - 54 edges
9. `BaseDAO` - 53 edges
10. `AuditService` - 52 edges

## Surprising Connections (you probably didn't know these)
- `SSH 任务执行器 (完善版)  实现通过 SSH 协议在远程 Linux 主机上执行命令 包含连接管理、错误处理、审计日志等完整功能` --uses--> `ErrorCode`  [INFERRED]
  edge/executors/ssh_executor.py → shared/protocol/error_codes.py
- `任务执行器模块  包含各种任务类型的执行器实现` --uses--> `DatabaseBackend`  [INFERRED]
  edge/executors/__init__.py → shared/database/base.py
- `任务执行器模块  包含各种任务类型的执行器实现` --uses--> `SQLiteBackend`  [INFERRED]
  edge/executors/__init__.py → shared/database/sqlite_backend.py
- `任务执行器模块  包含各种任务类型的执行器实现` --uses--> `AuthManager`  [INFERRED]
  edge/executors/__init__.py → shared/security/auth_manager.py
- `任务执行器模块  包含各种任务类型的执行器实现` --uses--> `AuthMiddleware`  [INFERRED]
  edge/executors/__init__.py → shared/security/middleware.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (84): TaskModel, cancel_task(), create_job_legacy(), create_task(), dispatch_tasks(), get_current_user(), get_job_legacy(), get_pending_tasks_for_node() (+76 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (79): create_recovery_service(), get_recovery_service(), HermesNexus Phase 3 - 故障恢复服务 实现故障检测和自动恢复逻辑, 处理故障          Args:             task_id: 关联任务ID             failure_type: 故障类型, 初始化恢复服务          Args:             config: 恢复服务配置, 注册故障检测器          Args:             detector: 故障检测器函数，签名为 async def detector() ->, 创建自定义恢复服务      Args:         config: 恢复服务配置      Returns:         恢复服务实例, RecoveryService (+71 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (89): asset_heartbeat(), associate_node(), create_asset(), delete_asset(), disassociate_node(), get_asset(), get_asset_stats(), list_assets() (+81 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (79): create_audit_log(), export_audit_logs(), get_asset_audit_logs(), get_audit_stats(), get_node_audit_logs(), get_task_audit_logs(), query_audit_logs(), HermesNexus Phase 2 - Audit API Endpoints 审计日志 API 端点 (+71 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (81): add_approval_comment(), AddApprovalComment, cancel_approval_request(), check_approval_permission(), check_approval_timeout(), create_approval_request(), CreateApprovalRequest, get_approval_comments() (+73 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (50): Alert, AlertCategory, AlertManager, AlertRule, AlertSeverity, get_alert_manager(), HermesNexus 告警规则定义 定义告警阈值、严重级别和通知策略, ActionResult (+42 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (52): ActionType, BuiltInRoles, create_permission_checker(), get_permission_checker(), PermissionChecker, HermesNexus Phase 3 - 权限检查器 实现权限检查的核心逻辑，结合身份、权限矩阵和风险评估, 批量检查权限          Args:             operations: 操作列表             context: 权限上下文, 获取用户的所有权限          Args:             context: 权限上下文          Returns: (+44 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (22): AuditLogger, 审计日志记录器  记录SSH执行器的操作日志, CloudClient, 边缘节点云边通信  实现与云端API的通信功能, EdgeRuntime, main(), 边缘节点运行时核心  实现边缘节点的主要功能：注册、心跳、任务执行, # TODO: 实现脚本执行 (+14 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (39): BaseDAO, 初始化DAO          Args:             database: 数据库后端实例, 获取数据库会话          Returns:             数据库会话对象          Raises:             Runti, BaseDAO, FastAPI 应用主入口  提供云端 REST API 服务, 注册新节点 - Phase 3: 增强版，支持Token颁发, NodeModel, 节点表ORM模型 - Phase 3: 节点身份管理 (+31 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (36): create_error_response(), ErrorCode, 创建标准错误响应      Args:         error_code: 错误码         details: 错误详情         reques, get_current_user(), HermesNexus Phase 2 - Authentication Middleware 认证中间件 - FastAPI依赖注入, 检查用户权限（基于请求路径和方法）          Args:             request: FastAPI请求对象             cu, 权限装饰器工厂          Args:             permission: 所需权限          Returns:, 角色装饰器工厂          Args:             role: 所需角色          Returns:             Fast (+28 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (5): _create_database_instance(), Database, 数据库操作工具类  提供线程安全的数据库访问, SQLite数据库持久化实现  提供基于SQLite的数据库持久化功能，支持数据重启恢复, SQLiteDatabase

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (16): ABC, HermesNexus Phase 2 - Base DAO 数据访问对象基类, DatabaseBackend, HermesNexus Phase 2 - Database Backend Interface 数据库后端抽象接口, 初始化数据库后端          Args:             connection_string: 数据库连接字符串             echo, DatabaseBackend, HermesNexus Phase 2 - SQLite Backend SQLite数据库后端实现, 获取数据库会话          Returns:             数据库会话对象 (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (7): HermesAPIHandler, init_database(), main(), HermesNexus API请求处理器 - 完整版, 处理任务结果回写 - 应用stable版本验证过的逻辑, 获取作业列表（jobs是tasks的别名）, 初始化数据库 - 添加events和audit_logs表

### Community 13 - "Community 13"
Cohesion: 0.22
Nodes (4): init_database(), main(), 获取作业列表（jobs是tasks的别名）, StableAPIHandler

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (11): AuthManager, HermesNexus Phase 2 - Authentication Manager 认证管理器 - 支持简单Token和API Key认证, 验证Token          Args:             token: Token字符串          Returns:, 创建API Key          Args:             user_id: 用户ID             name: API Key名称, 验证API Key          Args:             api_key: API Key字符串          Returns:, 撤销Token          Args:             token: Token字符串          Returns:, 撤销API Key          Args:             api_key: API Key字符串          Returns:, 获取用户权限列表          Args:             token: Token字符串          Returns: (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (12): cancel_job(), create_device(), create_job(), get_job(), get_node(), get_node_tasks(), list_devices(), list_jobs() (+4 more)

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (14): escapeHtml(), filterEvents(), filterTasks(), initializeFilters(), loadAllData(), loadEvents(), loadNodes(), loadTasks() (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (3): EdgeNode, main(), 🔥 关键功能：回写任务结果到Cloud API

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (3): EdgeNode, main(), 🔥 关键功能：回写任务结果到Cloud API

### Community 19 - "Community 19"
Cohesion: 0.27
Nodes (2): EdgeNode, main()

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (3): HermesAPIHandler, init_database(), main()

### Community 21 - "Community 21"
Cohesion: 0.23
Nodes (3): get_monitoring_dashboard(), MonitoringDashboard, HermesNexus 监控面板 提供系统状态可视化和告警展示

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): 初始化数据库连接          创建引擎、连接池和会话工厂

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): 创建所有数据表          根据ORM模型定义创建表结构

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): 删除所有数据表          注意：此操作会删除所有数据，谨慎使用

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): 关闭数据库连接          释放资源，清理连接池

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): 获取数据库会话          Returns:             数据库会话对象

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): 健康检查          Returns:             数据库是否可用

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): 获取角色的默认权限          Args:             role: 角色名称          Returns:             权限

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): 检查用户是否有指定权限          Args:             user_permissions: 用户权限列表             requ

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): 检查用户是否有任意一个指定权限          Args:             user_permissions: 用户权限列表

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): 检查用户是否有所有指定权限          Args:             user_permissions: 用户权限列表             re

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): 插入实体          Args:             entity: 要插入的实体对象          Returns:             插

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): 按ID查询          Args:             id: 实体ID          Returns:             实体对象，如果不

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): 更新实体          Args:             entity: 要更新的实体对象          Returns:             更

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): 删除实体          Args:             id: 实体ID          Returns:             是否删除成功

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): 查询实体列表          Args:             filters: 过滤条件字典             limit: 返回数量限制

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): 统计实体数量          Args:             filters: 过滤条件字典          Returns:

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): 兼容旧字段名 meta_data，并把常见的扁平字典转换为 AssetMetadata

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): 检查是否可以进行状态转换          Args:             from_status: 当前状态             to_status:

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): 获取当前状态的所有有效转换          Args:             from_status: 当前状态          Returns:

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): 检查是否为终态          Args:             status: 审批状态          Returns:             是否

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **79 isolated node(s):** `节点表ORM模型 - Phase 3: 节点身份管理`, `HermesNexus Phase 2 - Database Backend Interface 数据库后端抽象接口`, `初始化数据库后端          Args:             connection_string: 数据库连接字符串             echo`, `初始化数据库连接          创建引擎、连接池和会话工厂`, `创建所有数据表          根据ORM模型定义创建表结构` (+74 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 22`** (1 nodes): `初始化数据库连接          创建引擎、连接池和会话工厂`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `创建所有数据表          根据ORM模型定义创建表结构`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `删除所有数据表          注意：此操作会删除所有数据，谨慎使用`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `关闭数据库连接          释放资源，清理连接池`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `获取数据库会话          Returns:             数据库会话对象`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `健康检查          Returns:             数据库是否可用`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `获取角色的默认权限          Args:             role: 角色名称          Returns:             权限`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `检查用户是否有指定权限          Args:             user_permissions: 用户权限列表             requ`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `检查用户是否有任意一个指定权限          Args:             user_permissions: 用户权限列表`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `检查用户是否有所有指定权限          Args:             user_permissions: 用户权限列表             re`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `插入实体          Args:             entity: 要插入的实体对象          Returns:             插`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `按ID查询          Args:             id: 实体ID          Returns:             实体对象，如果不`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `更新实体          Args:             entity: 要更新的实体对象          Returns:             更`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `删除实体          Args:             id: 实体ID          Returns:             是否删除成功`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `查询实体列表          Args:             filters: 过滤条件字典             limit: 返回数量限制`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `统计实体数量          Args:             filters: 过滤条件字典          Returns:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `兼容旧字段名 meta_data，并把常见的扁平字典转换为 AssetMetadata`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `检查是否可以进行状态转换          Args:             from_status: 当前状态             to_status:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `获取当前状态的所有有效转换          Args:             from_status: 当前状态          Returns:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `检查是否为终态          Args:             status: 审批状态          Returns:             是否`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `任务执行器模块  包含各种任务类型的执行器实现` connect `Community 5` to `Community 0`, `Community 2`, `Community 3`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 14`, `Community 21`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `ErrorCode` connect `Community 9` to `Community 0`, `Community 2`, `Community 3`, `Community 5`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `BaseDAO` connect `Community 8` to `Community 0`, `Community 2`, `Community 3`, `Community 5`, `Community 11`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `AuditAction` (e.g. with `TaskScheduler` and `TaskService`) actually correct?**
  _`AuditAction` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `EventLevel` (e.g. with `TaskScheduler` and `TaskService`) actually correct?**
  _`EventLevel` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `AuditCategory` (e.g. with `TaskScheduler` and `TaskService`) actually correct?**
  _`AuditCategory` has 62 INFERRED edges - model-reasoned connections that need verification._
- **What connects `节点表ORM模型 - Phase 3: 节点身份管理`, `HermesNexus Phase 2 - Database Backend Interface 数据库后端抽象接口`, `初始化数据库后端          Args:             connection_string: 数据库连接字符串             echo` to the rest of the system?**
  _79 weakly-connected nodes found - possible documentation gaps or missing edges._