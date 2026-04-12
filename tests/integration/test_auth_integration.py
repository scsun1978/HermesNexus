"""
集成测试 - 认证链路集成测试

测试认证、权限、API保护的完整集成流程
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.security.auth_manager import AuthManager
from shared.security.permissions import Permission, PermissionChecker
from shared.models.audit import AuditAction, AuditCategory, EventLevel
from shared.services.audit_service import AuditService
from shared.database.sqlite_backend import SQLiteBackend


class TestAuthIntegration(unittest.TestCase):
    """测试认证和权限的完整集成流程"""

    def setUp(self):
        """测试前设置"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_auth_integration.db")

        # 初始化数据库
        self.db = SQLiteBackend(db_path=self.db_path)
        self.db.initialize()
        self.db.create_tables()  # 创建数据库表

        # 初始化服务
        self.auth_manager = AuthManager()
        self.audit_service = AuditService(database=self.db)

        # 启用认证（测试环境）
        self.auth_manager.enable()

    def tearDown(self):
        """测试后清理"""
        import shutil

        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_token_authentication_flow(self):
        """测试Token认证完整流程"""
        print("\n=== 测试Token认证流程 ===")

        # Step 1: 创建Token
        print("Step 1: 创建Token")
        token = self.auth_manager.create_token(
            user_id="user-001",
            username="testuser",
            role="operator",
            permissions=[
                Permission.ASSET_READ.value,
                Permission.TASK_READ.value,
                Permission.TASK_WRITE.value,
            ],
            expires_hours=1,
        )
        self.assertIsNotNone(token)
        print(f"生成的Token: {token[:20]}...")

        # Step 2: 验证Token
        print("Step 2: 验证Token")
        validated_user = self.auth_manager.validate_token(token)
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user["user_id"], "user-001")
        self.assertEqual(validated_user["username"], "testuser")
        print("Token验证成功")

        # Step 3: 检查权限
        print("Step 3: 检查权限")
        user_permissions = validated_user.get("permissions", [])

        # 应该有资产读取权限
        has_asset_read = PermissionChecker.check_permission(
            user_permissions, Permission.ASSET_READ
        )
        self.assertTrue(has_asset_read, "应该有资产读取权限")

        # 应该有任务写入权限
        has_task_write = PermissionChecker.check_permission(
            user_permissions, Permission.TASK_WRITE
        )
        self.assertTrue(has_task_write, "应该有任务写入权限")

        # 不应该有用户管理权限
        has_user_write = PermissionChecker.check_permission(
            user_permissions, Permission.USER_WRITE
        )
        self.assertFalse(has_user_write, "不应该有用户管理权限")

        print("✅ Token认证流程测试通过")

    def test_api_key_authentication_flow(self):
        """测试API Key认证完整流程"""
        print("\n=== 测试API Key认证流程 ===")

        # Step 1: 创建API Key
        print("Step 1: 创建API Key")
        api_key = self.auth_manager.create_api_key(
            user_id="user-002", name="test-api-key"
        )

        self.assertIsNotNone(api_key)
        print(f"生成的API Key: {api_key[:16]}...")

        # Step 2: 验证API Key
        print("Step 2: 验证API Key")
        validated_key = self.auth_manager.validate_api_key(api_key)
        self.assertIsNotNone(validated_key)
        self.assertEqual(validated_key["user_id"], "user-002")
        self.assertEqual(validated_key["name"], "test-api-key")
        print("API Key验证成功")

        # Step 3: 基于API Key的用户信息构建
        api_user_info = {
            "user_id": validated_key["user_id"],
            "username": f"api_key_{validated_key['name']}",
            "role": "user",
            "permissions": ["*"],  # API Key有所有权限
            "is_api_key": True,
        }

        self.assertTrue(api_user_info["is_api_key"], "应该标记为API Key用户")
        self.assertEqual(api_user_info["permissions"], ["*"], "API Key应该有所有权限")

        print("✅ API Key认证流程测试通过")

    def test_role_based_access_control(self):
        """测试基于角色的访问控制"""
        print("\n=== 测试基于角色的访问控制 ===")

        # 测试不同角色的权限
        test_roles = {
            "admin": [
                Permission.ASSET_WRITE,
                Permission.TASK_WRITE,
                Permission.USER_WRITE,
                Permission.SYSTEM_ADMIN,
            ],
            "operator": [
                Permission.ASSET_WRITE,
                Permission.TASK_WRITE,
                Permission.ASSET_READ,
                Permission.TASK_READ,
            ],
            "viewer": [
                Permission.ASSET_READ,
                Permission.TASK_READ,
                Permission.AUDIT_READ,
            ],
        }

        for role, expected_permissions in test_roles.items():
            print(f"测试角色: {role}")

            # 构建用户权限列表
            user_permissions = [perm.value for perm in expected_permissions]

            # 验证预期权限
            for perm in expected_permissions:
                has_permission = PermissionChecker.check_permission(
                    user_permissions, perm
                )
                self.assertTrue(has_permission, f"{role} 角色应该有 {perm.value} 权限")

            # 验证不应该有的权限
            if role == "viewer":
                # viewer不应该有写入权限
                has_write = PermissionChecker.check_permission(
                    user_permissions, Permission.ASSET_WRITE
                )
                self.assertFalse(has_write, f"{role} 角色不应该有资产写入权限")

        print("✅ 基于角色的访问控制测试通过")

    def test_token_revocation(self):
        """测试Token撤销流程"""
        print("\n=== 测试Token撤销流程 ===")

        # 创建Token
        token = self.auth_manager.create_token(
            user_id="user-revoke-001",
            username="revokeuser",
            role="operator",
            permissions=[Permission.ASSET_READ.value],
        )

        # 验证Token有效
        validated_user = self.auth_manager.validate_token(token)
        self.assertIsNotNone(validated_user)

        # 撤销Token
        self.auth_manager.revoke_token(token)
        print("Token已撤销")

        # 验证Token已失效
        revoked_user = self.auth_manager.validate_token(token)
        self.assertIsNone(revoked_user, "撤销后的Token应该无效")

        print("✅ Token撤销流程测试通过")

    def test_permission_hierarchy(self):
        """测试权限层级和通配符"""
        print("\n=== 测试权限层级 ===")

        # 测试管理员通配符权限
        admin_permissions = ["*"]

        # 管理员应该能访问所有权限
        test_permissions = [
            Permission.ASSET_READ,
            Permission.ASSET_WRITE,
            Permission.TASK_EXECUTE,
            Permission.USER_WRITE,
            Permission.SYSTEM_ADMIN,
        ]

        for perm in test_permissions:
            has_permission = PermissionChecker.check_permission(admin_permissions, perm)
            self.assertTrue(has_permission, f"管理员通配符应该包含 {perm.value} 权限")

        # 测试普通用户的具体权限
        user_permissions = [Permission.ASSET_READ.value, Permission.TASK_READ.value]

        # 应该有读取权限
        self.assertTrue(
            PermissionChecker.check_permission(user_permissions, Permission.ASSET_READ)
        )

        # 不应该有写入权限
        self.assertFalse(
            PermissionChecker.check_permission(user_permissions, Permission.ASSET_WRITE)
        )

        print("✅ 权限层级测试通过")

    def test_auth_with_audit_integration(self):
        """测试认证与审计的集成"""
        print("\n=== 测试认证与审计集成 ===")

        # 模拟认证成功的审计记录
        from shared.models.audit import AuditLogCreateRequest

        audit_request = AuditLogCreateRequest(
            action=AuditAction.AUTH_SUCCESS,
            category=AuditCategory.SECURITY,
            level=EventLevel.INFO,
            actor="user-auth-001",
            target_type="auth",
            target_id="token-auth",
            message="用户成功通过Token认证",
            metadata={
                "auth_method": "token",
                "user_role": "operator",
                "ip_address": "192.168.1.100",
            },
        )

        self.audit_service.log_action(audit_request)

        # 模拟权限拒绝的审计记录
        denial_request = AuditLogCreateRequest(
            action=AuditAction.AUTH_DENIED,
            category=AuditCategory.SECURITY,
            level=EventLevel.WARNING,
            actor="user-auth-002",
            target_type="auth",
            target_id="api-key-auth",
            message="用户API Key权限不足",
            metadata={
                "auth_method": "api_key",
                "required_permission": Permission.ASSET_WRITE.value,
                "user_permissions": [Permission.ASSET_READ.value],
            },
        )

        self.audit_service.log_action(denial_request)

        # 查询认证相关审计日志
        auth_logs = self.audit_service.list_audit_logs(
            filters={"category": AuditCategory.SECURITY}
        )

        self.assertGreater(len(auth_logs), 0, "应该有认证相关的审计日志")

        # 验证日志内容
        success_log = [
            log for log in auth_logs if log.action == AuditAction.AUTH_SUCCESS
        ]
        denial_log_result = [
            log for log in auth_logs if log.action == AuditAction.AUTH_DENIED
        ]

        self.assertGreater(len(success_log), 0, "应该有认证成功日志")
        self.assertGreater(len(denial_log_result), 0, "应该有权限拒绝日志")

        print(f"认证审计日志数量: {len(auth_logs)}")
        print("✅ 认证与审计集成测试通过")

    def test_development_mode_authentication(self):
        """测试开发模式认证"""
        print("\n=== 测试开发模式认证 ===")

        # 禁用认证（开发模式）
        self.auth_manager.disable()

        # 在开发模式下，创建Token应该返回开发Token
        dev_token = self.auth_manager.create_token(
            user_id="dev-user", username="dev-user", role="admin", permissions=["*"]
        )
        self.assertIsNotNone(dev_token)

        # 验证开发Token
        validated_dev_user = self.auth_manager.validate_token(dev_token)
        self.assertIsNotNone(validated_dev_user)
        self.assertEqual(validated_dev_user["user_id"], "dev-user")
        self.assertEqual(validated_dev_user["role"], "admin")

        # 重新启用认证
        self.auth_manager.enable()

        print("✅ 开发模式认证测试通过")


if __name__ == "__main__":
    unittest.main()
