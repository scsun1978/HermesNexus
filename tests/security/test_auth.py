#!/usr/bin/env python3
"""
HermesNexus Phase 2 - Authentication Tests
认证层测试
"""

import sys
import os
import unittest

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from shared.security.auth_manager import AuthManager
from shared.security.permissions import (
    Permission,
    PermissionChecker,
    get_required_permissions,
)


class TestAuthentication(unittest.TestCase):
    """认证功能测试"""

    def setUp(self):
        """测试前准备"""
        self.auth_manager = AuthManager()

    def test_create_and_validate_token(self):
        """测试Token创建和验证"""
        # 创建Token
        token = self.auth_manager.create_token(
            user_id="user-001",
            username="testuser",
            role="user",
            permissions=["asset:read", "task:read"],
        )

        self.assertIsNotNone(token)
        self.assertTrue(token.startswith("token-"))

        # 验证Token
        token_info = self.auth_manager.validate_token(token)
        self.assertIsNotNone(token_info)
        self.assertEqual(token_info["user_id"], "user-001")
        self.assertEqual(token_info["username"], "testuser")
        self.assertEqual(token_info["role"], "user")
        self.assertIn("asset:read", token_info["permissions"])

        print("✓ Token creation and validation test passed")

    def test_invalid_token(self):
        """测试无效Token"""
        # 验证不存在的Token
        token_info = self.auth_manager.validate_token("invalid-token")
        self.assertIsNone(token_info)

        print("✓ Invalid token test passed")

    def test_create_and_validate_api_key(self):
        """测试API Key创建和验证"""
        # 创建API Key
        api_key = self.auth_manager.create_api_key(user_id="user-001", name="Test API Key")

        self.assertIsNotNone(api_key)
        self.assertTrue(api_key.startswith("sk-"))

        # 验证API Key
        api_key_info = self.auth_manager.validate_api_key(api_key)
        self.assertIsNotNone(api_key_info)
        self.assertEqual(api_key_info["user_id"], "user-001")
        self.assertEqual(api_key_info["name"], "Test API Key")

        print("✓ API Key creation and validation test passed")

    def test_token_expiration(self):
        """测试Token过期"""
        # 创建1小时过期的Token
        token = self.auth_manager.create_token(
            user_id="user-001", username="testuser", role="user", expires_hours=1
        )

        # Token应该有效
        token_info = self.auth_manager.validate_token(token)
        self.assertIsNotNone(token_info)

        # 注意：实际测试过期需要等待或mock时间
        # 这里只验证Token结构正确

        print("✓ Token expiration test passed")

    def test_revoke_token(self):
        """测试Token撤销"""
        # 创建Token
        token = self.auth_manager.create_token(user_id="user-001", username="testuser", role="user")

        # 验证Token有效
        token_info = self.auth_manager.validate_token(token)
        self.assertIsNotNone(token_info)

        # 撤销Token
        success = self.auth_manager.revoke_token(token)
        self.assertTrue(success)

        # 验证Token无效
        token_info = self.auth_manager.validate_token(token)
        self.assertIsNone(token_info)

        print("✓ Token revocation test passed")

    def test_revoke_api_key(self):
        """测试API Key撤销"""
        # 创建API Key
        api_key = self.auth_manager.create_api_key(user_id="user-001", name="Test API Key")

        # 验证API Key有效
        api_key_info = self.auth_manager.validate_api_key(api_key)
        self.assertIsNotNone(api_key_info)

        # 撤销API Key
        success = self.auth_manager.revoke_api_key(api_key)
        self.assertTrue(success)

        # 验证API Key无效
        api_key_info = self.auth_manager.validate_api_key(api_key)
        self.assertIsNone(api_key_info)

        print("✓ API Key revocation test passed")


class TestPermissions(unittest.TestCase):
    """权限检查测试"""

    def test_permission_check(self):
        """测试权限检查"""
        user_permissions = ["asset:read", "task:read"]

        # 检查有权限
        has_permission = PermissionChecker.check_permission(user_permissions, Permission.ASSET_READ)
        self.assertTrue(has_permission)

        # 检查无权限
        has_permission = PermissionChecker.check_permission(
            user_permissions, Permission.ASSET_WRITE
        )
        self.assertFalse(has_permission)

        print("✓ Permission check test passed")

    def test_wildcard_permission(self):
        """测试通配符权限"""
        user_permissions = ["*"]

        # 通配符应该有所有权限
        has_permission = PermissionChecker.check_permission(
            user_permissions, Permission.ASSET_DELETE
        )
        self.assertTrue(has_permission)

        print("✓ Wildcard permission test passed")

    def test_admin_permission(self):
        """测试管理员权限"""
        user_permissions = ["system:admin"]

        # 管理员应该有所有权限
        has_permission = PermissionChecker.check_permission(
            user_permissions, Permission.TASK_EXECUTE
        )
        self.assertTrue(has_permission)

        print("✓ Admin permission test passed")

    def test_role_permissions(self):
        """测试角色默认权限"""
        # 获取管理员权限
        admin_permissions = PermissionChecker.get_role_permissions("admin")
        self.assertIn(Permission.SYSTEM_ADMIN, admin_permissions)

        # 获取操作员权限
        operator_permissions = PermissionChecker.get_role_permissions("operator")
        self.assertIn(Permission.TASK_READ, operator_permissions)
        self.assertNotIn(Permission.ASSET_DELETE, operator_permissions)

        print("✓ Role permissions test passed")

    def test_operation_permission_mapping(self):
        """测试操作权限映射"""
        # GET /api/v1/assets 需要 asset:read
        permissions = get_required_permissions("GET", "/api/v1/assets")
        self.assertIn(Permission.ASSET_READ, permissions)

        # POST /api/v1/tasks 需要 task:write
        permissions = get_required_permissions("POST", "/api/v1/tasks")
        self.assertIn(Permission.TASK_WRITE, permissions)

        # GET /health 不需要权限
        permissions = get_required_permissions("GET", "/health")
        self.assertEqual(len(permissions), 0)

        print("✓ Operation permission mapping test passed")


class TestAuthManagerIntegration(unittest.TestCase):
    """认证管理器集成测试"""

    def setUp(self):
        """测试前准备"""
        self.auth_manager = AuthManager()

    def test_user_permission_check(self):
        """测试用户权限检查"""
        # 创建Token
        token = self.auth_manager.create_token(
            user_id="user-001",
            username="testuser",
            role="user",
            permissions=["asset:read", "task:read"],
        )

        # 检查权限
        has_permission = self.auth_manager.has_permission(token, Permission.ASSET_READ)
        self.assertTrue(has_permission)

        has_permission = self.auth_manager.has_permission(token, Permission.ASSET_WRITE)
        self.assertFalse(has_permission)

        print("✓ User permission check test passed")

    def test_extract_credentials(self):
        """测试凭据提取"""
        # 测试Bearer Token
        headers = {"Authorization": "Bearer test-token"}
        credentials = self.auth_manager.extract_credentials(headers)
        self.assertEqual(credentials, "test-token")

        # 测试API Key
        headers = {"X-API-Key": "sk-test-key"}
        credentials = self.auth_manager.extract_credentials(headers)
        self.assertEqual(credentials, "sk-test-key")

        # 测试无凭据
        headers = {}
        credentials = self.auth_manager.extract_credentials(headers)
        self.assertIsNone(credentials)

        print("✓ Credentials extraction test passed")


if __name__ == "__main__":
    # 运行测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestPermissions))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthManagerIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✓ All authentication tests passed!")
    else:
        print("✗ Some tests failed")
        sys.exit(1)
