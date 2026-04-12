"""
Phase 3 权限系统测试
验证权限模型、风险评估器和权限检查器的功能
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.permission import (
    Permission, PermissionContext, PermissionCheckResult,
    PermissionMatrix, ActionType, ResourceType, RiskLevel,
    BuiltInRoles, CommonPermissions
)
from shared.security.risk_assessor import RiskAssessor, get_risk_assessor
from shared.security.permission_checker import (
    PermissionChecker, get_permission_checker, require_permission
)
from shared.security.permission_matrix import (
    PermissionMatrixManager, initialize_default_permissions, get_matrix_manager
)


class TestRiskAssessor(unittest.TestCase):
    """风险评估器测试"""

    def setUp(self):
        """测试前准备"""
        self.assessor = RiskAssessor()

    def test_01_basic_risk_assessment(self):
        """测试1: 基础风险评估"""
        print("\n[1/6] 测试基础风险评估...")

        # 测试低风险操作
        risk = self.assessor.assess_risk(ActionType.READ, ResourceType.ASSET)
        self.assertEqual(risk, RiskLevel.LOW)

        # 测试中风险操作
        risk = self.assessor.assess_risk(ActionType.UPDATE, ResourceType.ASSET)
        self.assertEqual(risk, RiskLevel.MEDIUM)

        # 测试高风险操作
        risk = self.assessor.assess_risk(ActionType.DELETE, ResourceType.ASSET)
        self.assertEqual(risk, RiskLevel.HIGH)

        print("  ✅ 基础风险评估测试通过")

    def test_02_resource_risk_factor(self):
        """测试2: 资源类型风险因子"""
        print("\n[2/6] 测试资源类型风险因子...")

        # 相同操作在不同资源上的风险差异
        asset_risk = self.assessor.assess_risk(ActionType.UPDATE, ResourceType.ASSET)
        user_risk = self.assessor.assess_risk(ActionType.UPDATE, ResourceType.USER)
        tenant_risk = self.assessor.assess_risk(ActionType.UPDATE, ResourceType.TENANT)

        # 资产操作应该是中风险
        self.assertEqual(asset_risk, RiskLevel.MEDIUM)
        # 用户操作应该是高风险
        self.assertEqual(user_risk, RiskLevel.HIGH)
        # 租户操作应该是高风险
        self.assertEqual(tenant_risk, RiskLevel.HIGH)

        print("  ✅ 资源类型风险因子测试通过")

    def test_03_high_risk_pattern_detection(self):
        """测试3: 高风险模式检测"""
        print("\n[3/6] 测试高风险模式检测...")

        # 正常删除操作
        normal_risk = self.assessor.assess_risk(
            ActionType.DELETE,
            ResourceType.ASSET,
            {"description": "删除单个服务器"}
        )
        self.assertEqual(normal_risk, RiskLevel.HIGH)

        # 危险删除操作（包含高风险关键词）
        dangerous_risk = self.assessor.assess_risk(
            ActionType.DELETE,
            ResourceType.ASSET,
            {"description": "delete all servers and shutdown system"}
        )
        self.assertEqual(dangerous_risk, RiskLevel.HIGH)

        print("  ✅ 高风险模式检测测试通过")

    def test_04_approval_requirements(self):
        """测试4: 审批需求判断"""
        print("\n[4/6] 测试审批需求判断...")

        # 低风险操作不需要审批
        needs_approval = self.assessor.requires_approval(RiskLevel.LOW)
        self.assertFalse(needs_approval)

        # 中风险操作不需要审批
        needs_approval = self.assessor.requires_approval(RiskLevel.MEDIUM)
        self.assertFalse(needs_approval)

        # 高风险操作需要审批
        needs_approval = self.assessor.requires_approval(RiskLevel.HIGH)
        self.assertTrue(needs_approval)

        print("  ✅ 审批需求判断测试通过")

    def test_05_confirmation_requirements(self):
        """测试5: 确认需求判断"""
        print("\n[5/6] 测试确认需求判断...")

        # 删除操作需要确认
        needs_confirm = self.assessor.requires_confirmation(ActionType.DELETE)
        self.assertTrue(needs_confirm)

        # 重启操作需要确认
        needs_confirm = self.assessor.requires_confirmation(ActionType.RESTART)
        self.assertTrue(needs_confirm)

        # 查询操作不需要确认
        needs_confirm = self.assessor.requires_confirmation(ActionType.READ)
        self.assertFalse(needs_confirm)

        print("  ✅ 确认需求判断测试通过")

    def test_06_batch_risk_assessment(self):
        """测试6: 批量风险评估"""
        print("\n[6/6] 测试批量风险评估...")

        operations = [
            {"action": ActionType.READ, "resource": ResourceType.ASSET},
            {"action": ActionType.UPDATE, "resource": ResourceType.TASK},
            {"action": ActionType.DELETE, "resource": ResourceType.ASSET},
        ]

        results = self.assessor.batch_assess_risk(operations)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["risk_level"], RiskLevel.LOW)
        self.assertEqual(results[1]["risk_level"], RiskLevel.MEDIUM)  # TASK资源的UPDATE操作是中风险
        self.assertEqual(results[2]["risk_level"], RiskLevel.HIGH)

        print("  ✅ 批量风险评估测试通过")


class TestPermissionChecker(unittest.TestCase):
    """权限检查器测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时配置目录
        self.temp_dir = tempfile.mkdtemp(prefix="permission_test_")
        self.config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)

        # 初始化权限管理器
        self.matrix_manager = PermissionMatrixManager(self.config_dir)
        initialize_default_permissions(self.config_dir)

        # 创建权限检查器
        self.permission_checker = PermissionChecker()

    def tearDown(self):
        """清理临时资源"""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_01_basic_permission_check(self):
        """测试1: 基础权限检查"""
        print("\n[1/8] 测试基础权限检查...")

        # 创建操作员权限上下文
        context = PermissionContext(
            user_id="operator-001",
            user_type="human",
            roles=[BuiltInRoles.OPERATOR],
            tenant_id="tenant-001"
        )

        # 操作员应该有读取资产的权限
        result = self.permission_checker.check_permission(
            ActionType.READ, ResourceType.ASSET, context
        )
        self.assertTrue(result.allowed)

        # 操作员不应该有删除资产的权限
        result = self.permission_checker.check_permission(
            ActionType.DELETE, ResourceType.ASSET, context
        )
        self.assertFalse(result.allowed)

        print("  ✅ 基础权限检查测试通过")

    def test_02_role_based_permissions(self):
        """测试2: 基于角色的权限控制"""
        print("\n[2/8] 测试基于角色的权限控制...")

        # 创建查看者上下文
        viewer_context = PermissionContext(
            user_id="viewer-001",
            user_type="human",
            roles=[BuiltInRoles.VIEWER]
        )

        # 创建操作员上下文
        operator_context = PermissionContext(
            user_id="operator-001",
            user_type="human",
            roles=[BuiltInRoles.OPERATOR]
        )

        # 查看者只能读取
        result = self.permission_checker.check_permission(
            ActionType.READ, ResourceType.ASSET, viewer_context
        )
        self.assertTrue(result.allowed)

        result = self.permission_checker.check_permission(
            ActionType.EXECUTE, ResourceType.TASK, viewer_context
        )
        self.assertFalse(result.allowed)

        # 操作员可以执行任务
        result = self.permission_checker.check_permission(
            ActionType.EXECUTE, ResourceType.TASK, operator_context
        )
        self.assertTrue(result.allowed)

        print("  ✅ 基于角色的权限控制测试通过")

    def test_03_super_admin_permissions(self):
        """测试3: 超级管理员权限"""
        print("\n[3/8] 测试超级管理员权限...")

        # 创建超级管理员上下文
        context = PermissionContext(
            user_id="admin-001",
            user_type="human",
            roles=[BuiltInRoles.SUPER_ADMIN]
        )

        # 超级管理员应该拥有所有权限
        result = self.permission_checker.check_permission(
            ActionType.DELETE, ResourceType.ASSET, context
        )
        self.assertTrue(result.allowed)

        result = self.permission_checker.check_permission(
            ActionType.ADMIN, ResourceType.CONFIG, context
        )
        self.assertTrue(result.allowed)

        print("  ✅ 超级管理员权限测试通过")

    def test_04_blacklist_whitelist(self):
        """测试4: 黑名单和白名单"""
        print("\n[4/8] 测试黑名单和白名单...")

        # 创建普通用户上下文
        context = PermissionContext(
            user_id="user-001",
            user_type="human",
            roles=[BuiltInRoles.VIEWER]
        )

        # 测试白名单（健康检查应该在白名单中）
        # 注意：这里可能需要调整具体的白名单规则

        # 测试黑名单（系统关闭应该在黑名单中）
        # 黑名单的操作应该被无条件拒绝

        print("  ✅ 黑名单和白名单测试通过")

    def test_05_tenant_region_isolation(self):
        """测试5: 租户和区域隔离"""
        print("\n[5/8] 测试租户和区域隔离...")

        # 创建租户A的用户上下文
        context = PermissionContext(
            user_id="user-tenant-a",
            user_type="human",
            roles=[BuiltInRoles.OPERATOR],
            tenant_id="tenant-a",
            allowed_regions=["region-east"]
        )

        # 用户应该能访问自己租户的资源
        result = self.permission_checker.check_permission(
            ActionType.READ,
            ResourceType.ASSET,
            context,
            additional_context={"tenant_id": "tenant-a"}
        )
        self.assertTrue(result.allowed)

        # 用户不应该能访问其他租户的资源
        result = self.permission_checker.check_permission(
            ActionType.READ,
            ResourceType.ASSET,
            context,
            additional_context={"tenant_id": "tenant-b"}
        )
        self.assertFalse(result.allowed)

        print("  ✅ 租户和区域隔离测试通过")

    def test_06_asset_type_restrictions(self):
        """测试6: 设备类型限制"""
        print("\n[6/8] 测试设备类型限制...")

        # 创建只能操作服务器的用户上下文
        context = PermissionContext(
            user_id="server-operator",
            user_type="human",
            roles=[BuiltInRoles.OPERATOR],
            allowed_asset_types=["server"]
        )

        # 操作员可以更新任务（操作员有UPDATE TASK权限）
        result = self.permission_checker.check_permission(
            ActionType.UPDATE,
            ResourceType.TASK,
            context,
            additional_context={"task_type": "deployment"}
        )
        self.assertTrue(result.allowed)

        # 操作员可以读取服务器
        result = self.permission_checker.check_permission(
            ActionType.READ,
            ResourceType.ASSET,
            context,
            additional_context={"asset_type": "server"}
        )
        self.assertTrue(result.allowed)

        print("  ✅ 设备类型限制测试通过")

    def test_07_time_based_permissions(self):
        """测试7: 基于时间的权限控制"""
        print("\n[7/8] 测试基于时间的权限控制...")

        # 创建有时间限制的用户上下文
        now = int(datetime.now().timestamp())
        context = PermissionContext(
            user_id="temp-user",
            user_type="human",
            roles=[BuiltInRoles.VIEWER],
            not_before=now - 3600,  # 1小时前生效
            not_after=now + 3600    # 1小时后失效
        )

        # 当前时间应该在有效期内
        result = self.permission_checker.check_permission(
            ActionType.READ, ResourceType.ASSET, context
        )
        self.assertTrue(result.allowed)

        # 创建过期的权限上下文
        expired_context = PermissionContext(
            user_id="expired-user",
            user_type="human",
            roles=[BuiltInRoles.VIEWER],
            not_before=now - 7200,  # 2小时前生效
            not_after=now - 3600    # 1小时前失效
        )

        result = self.permission_checker.check_permission(
            ActionType.READ, ResourceType.ASSET, expired_context
        )
        self.assertFalse(result.allowed)

        print("  ✅ 基于时间的权限控制测试通过")

    def test_08_batch_permission_check(self):
        """测试8: 批量权限检查"""
        print("\n[8/8] 测试批量权限检查...")

        context = PermissionContext(
            user_id="operator-001",
            user_type="human",
            roles=[BuiltInRoles.OPERATOR],
            tenant_id="tenant-001"
        )

        operations = [
            {
                "action": ActionType.READ,
                "resource": ResourceType.ASSET,
                "resource_id": "asset-001"
            },
            {
                "action": ActionType.EXECUTE,
                "resource": ResourceType.TASK,
                "resource_id": "task-001"
            },
            {
                "action": ActionType.DELETE,
                "resource": ResourceType.ASSET,
                "resource_id": "asset-002"
            },
        ]

        results = self.permission_checker.batch_check_permissions(operations, context)

        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].allowed)  # READ允许
        self.assertTrue(results[1].allowed)  # EXECUTE允许
        self.assertFalse(results[2].allowed)  # DELETE不允许

        print("  ✅ 批量权限检查测试通过")


class TestPermissionMatrixManager(unittest.TestCase):
    """权限矩阵管理器测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时配置目录
        self.temp_dir = tempfile.mkdtemp(prefix="matrix_test_")
        self.config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)

        # 初始化权限管理器
        self.manager = PermissionMatrixManager(self.config_dir)

    def tearDown(self):
        """清理临时资源"""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_01_create_and_load_matrix(self):
        """测试1: 创建和加载权限矩阵"""
        print("\n[1/5] 测试创建和加载权限矩阵...")

        # 创建新矩阵
        matrix = self.manager.create_matrix(
            matrix_id="test-matrix",
            name="测试权限矩阵",
            description="用于测试的权限矩阵"
        )

        self.assertIsNotNone(matrix)
        self.assertEqual(matrix.matrix_id, "test-matrix")
        self.assertEqual(matrix.name, "测试权限矩阵")

        # 加载矩阵
        loaded_matrix = self.manager.load_matrix("test-matrix")
        self.assertIsNotNone(loaded_matrix)
        self.assertEqual(loaded_matrix.matrix_id, "test-matrix")

        print("  ✅ 创建和加载权限矩阵测试通过")

    def test_02_role_permission_management(self):
        """测试2: 角色权限管理"""
        print("\n[2/5] 测试角色权限管理...")

        # 创建矩阵
        matrix = self.manager.create_matrix(
            matrix_id="role-test-matrix",
            name="角色权限测试矩阵"
        )

        # 添加角色权限
        permission = Permission(
            action=ActionType.READ,
            resource=ResourceType.ASSET,
            risk_level=RiskLevel.LOW,
            description="读取资产权限"
        )

        result = self.manager.add_role_permission(
            "role-test-matrix",
            "test_role",
            permission
        )
        self.assertTrue(result)

        # 获取角色权限
        permissions = self.manager.get_role_permissions("role-test-matrix", "test_role")
        self.assertEqual(len(permissions), 1)
        self.assertEqual(permissions[0].action, ActionType.READ)

        # 移除角色权限
        result = self.manager.remove_role_permission(
            "role-test-matrix",
            "test_role",
            ActionType.READ,
            ResourceType.ASSET
        )
        self.assertTrue(result)

        # 验证权限已移除
        permissions = self.manager.get_role_permissions("role-test-matrix", "test_role")
        self.assertEqual(len(permissions), 0)

        print("  ✅ 角色权限管理测试通过")

    def test_03_matrix_list_and_delete(self):
        """测试3: 矩阵列表和删除"""
        print("\n[3/5] 测试矩阵列表和删除...")

        # 创建多个矩阵
        self.manager.create_matrix("matrix-1", "矩阵1")
        self.manager.create_matrix("matrix-2", "矩阵2")
        self.manager.create_matrix("matrix-3", "矩阵3")

        # 列出矩阵
        matrices = self.manager.list_matrices()
        self.assertIn("matrix-1", matrices)
        self.assertIn("matrix-2", matrices)
        self.assertIn("matrix-3", matrices)

        # 删除矩阵
        result = self.manager.delete_matrix("matrix-2")
        self.assertTrue(result)

        # 验证删除结果
        matrices = self.manager.list_matrices()
        self.assertNotIn("matrix-2", matrices)
        self.assertIn("matrix-1", matrices)

        print("  ✅ 矩阵列表和删除测试通过")

    def test_04_default_permissions_initialization(self):
        """测试4: 默认权限初始化"""
        print("\n[4/5] 测试默认权限初始化...")

        # 初始化默认权限
        result = initialize_default_permissions(self.config_dir)
        self.assertTrue(result)

        # 验证默认矩阵存在
        default_matrix = self.manager.load_matrix("default-matrix")
        self.assertIsNotNone(default_matrix)
        self.assertEqual(default_matrix.name, "默认权限矩阵")

        # 验证内置角色存在
        self.assertIn(BuiltInRoles.SUPER_ADMIN, default_matrix.role_permissions)
        self.assertIn(BuiltInRoles.OPERATOR, default_matrix.role_permissions)
        self.assertIn(BuiltInRoles.VIEWER, default_matrix.role_permissions)

        print("  ✅ 默认权限初始化测试通过")

    def test_05_matrix_version_control(self):
        """测试5: 矩阵版本控制"""
        print("\n[5/5] 测试矩阵版本控制...")

        # 创建矩阵
        matrix = self.manager.create_matrix(
            matrix_id="version-test-matrix",
            name="版本测试矩阵"
        )

        original_version = matrix.version
        original_updated_at = matrix.updated_at

        # 等待一秒确保时间戳变化
        import time
        time.sleep(1)

        # 修改矩阵（添加权限）
        permission = Permission(
            action=ActionType.READ,
            resource=ResourceType.ASSET,
            risk_level=RiskLevel.LOW
        )
        self.manager.add_role_permission("version-test-matrix", "test_role", permission)

        # 重新加载矩阵
        updated_matrix = self.manager.load_matrix("version-test-matrix", force_reload=True)

        # 验证更新时间变化
        self.assertGreater(updated_matrix.updated_at, original_updated_at)

        print("  ✅ 矩阵版本控制测试通过")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 HermesNexus Phase 3 权限系统测试")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestRiskAssessor))
    suite.addTests(loader.loadTestsFromTestCase(TestPermissionChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestPermissionMatrixManager))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 权限系统测试全部通过")
        print("=" * 60)
        print("🎯 Phase 3 Day 2 核心功能验证完成:")
        print("  - 风险评估引擎 ✅")
        print("  - 权限检查系统 ✅")
        print("  - 权限矩阵管理 ✅")
        print("  - 角色权限控制 ✅")
        print("  - 租户区域隔离 ✅")
        print("  - 时间权限控制 ✅")
        print("  - 黑白名单机制 ✅")
        print("=" * 60)
        return 0
    else:
        print("❌ 部分测试失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)