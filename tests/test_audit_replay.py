"""
审计回放功能测试
Test Audit Replay Functionality
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timezone

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.services.audit_replay_service import (
    AuditReplayService,
    ReplayMode,
    ReplayResult,
)
from shared.services.audit_service import AuditService
from shared.models.audit import AuditLog, AuditAction, AuditCategory, EventLevel


class TestAuditReplayService(unittest.TestCase):
    """测试审计回放服务"""

    def setUp(self):
        """测试前设置"""
        self.audit_service = AuditService(database=None)
        self.replay_service = AuditReplayService(self.audit_service)

        # 创建测试审计日志并添加到审计服务
        self.test_audit_logs = self._create_and_add_test_audit_logs()

    def _create_and_add_test_audit_logs(self):
        """创建并添加测试用审计日志到审计服务"""
        from shared.models.audit import AuditLogCreateRequest

        test_logs = []

        # 1. 任务创建审计日志
        task_request = AuditLogCreateRequest(
            action=AuditAction.TASK_CREATED,
            category=AuditCategory.TASK,
            level="info",
            actor="user-001",
            actor_type="user",
            target_type="task",
            target_id="task-001",
            related_node_id="node-001",
            related_asset_id="asset-001",
            details={
                "command": "echo 'Hello World'",
                "target_device_id": "device-001",
                "timeout": 30,
            },
            message="创建任务: task-001",
        )
        task_audit = self.audit_service.log_action(task_request)
        test_logs.append(task_audit)

        # 2. 资产创建审计日志
        asset_request = AuditLogCreateRequest(
            action=AuditAction.ASSET_REGISTERED,
            category=AuditCategory.ASSET,
            level="info",
            actor="user-001",
            actor_type="user",
            target_type="asset",
            target_id="asset-001",
            details={
                "device_id": "device-001",
                "name": "测试设备",
                "type": "linux_host",
                "host": "192.168.1.100",
            },
            message="注册资产: asset-001",
        )
        asset_audit = self.audit_service.log_action(asset_request)
        test_logs.append(asset_audit)

        # 3. 节点注册审计日志
        node_request = AuditLogCreateRequest(
            action=AuditAction.NODE_REGISTERED,
            category=AuditCategory.NODE,
            level="info",
            actor="system",
            actor_type="system",
            target_type="node",
            target_id="node-001",
            details={
                "node_name": "测试节点",
                "capabilities": {"ssh": True, "max_tasks": 3},
            },
            message="注册节点: node-001",
        )
        node_audit = self.audit_service.log_action(node_request)
        test_logs.append(node_audit)

        return test_logs

    def test_replay_capability_check(self):
        """测试回放能力检查"""
        # 测试任务创建 - 应该支持回放
        task_audit = self.test_audit_logs[0]
        capability = self.replay_service._check_replay_capability(task_audit)
        self.assertTrue(capability["can_replay"])
        self.assertIsNone(capability["reason"])

    def test_simulation_replay(self):
        """测试模拟回放"""
        task_audit = self.test_audit_logs[0]

        result = self.replay_service.replay_audit_log(
            audit_id=task_audit.audit_id,
            mode=ReplayMode.SIMULATION,
            actor="test-user",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "simulation")
        self.assertIn("replay_id", result)
        self.assertIn("result", result)
        self.assertIn("steps", result["result"])

        # 检查生成的步骤
        steps = result["result"]["steps"]
        self.assertGreater(len(steps), 0)
        self.assertIn("step_number", steps[0])
        self.assertIn("action", steps[0])
        self.assertIn("description", steps[0])

    def test_validation_replay(self):
        """测试验证回放"""
        task_audit = self.test_audit_logs[0]

        result = self.replay_service.replay_audit_log(
            audit_id=task_audit.audit_id,
            mode=ReplayMode.VALIDATION,
            actor="test-user",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "validation")
        self.assertIn("result", result)
        self.assertIn("can_execute", result["result"])

        # 验证结果应该包含验证信息
        validation_result = result["result"]
        self.assertIn("validation_issues", validation_result)
        self.assertIn("warnings", validation_result)

    def test_execution_replay(self):
        """测试实际回放"""
        task_audit = self.test_audit_logs[0]

        result = self.replay_service.replay_audit_log(
            audit_id=task_audit.audit_id,
            mode=ReplayMode.EXECUTION,
            actor="test-user",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "execution")
        self.assertIn("result", result)
        self.assertIn("executed_steps", result["result"])

    def test_replay_with_overrides(self):
        """测试参数覆盖的回放"""
        task_audit = self.test_audit_logs[0]

        overrides = {
            "command": "echo 'Updated Command'",
            "timeout": 60,
        }

        result = self.replay_service.replay_audit_log(
            audit_id=task_audit.audit_id,
            mode=ReplayMode.SIMULATION,
            actor="test-user",
            overrides=overrides,
        )

        self.assertTrue(result["success"])

        # 检查参数是否被覆盖
        steps = result["result"]["steps"]
        for step in steps:
            if "parameters" in step:
                # 检查覆盖的参数是否生效
                if "command" in step["parameters"]:
                    self.assertEqual(step["parameters"]["command"], "echo 'Updated Command'")
                if "timeout" in step["parameters"]:
                    self.assertEqual(step["parameters"]["timeout"], 60)

    def test_non_replayable_action(self):
        """测试不支持回放的操作"""
        # 创建一个不支持回放的审计日志
        auth_audit = AuditLog(
            audit_id="audit-auth-001",
            action=AuditAction.AUTH_DENIED,
            category=AuditCategory.SECURITY,
            level=EventLevel.WARNING,
            actor="user-001",
            actor_type="user",
            target_type="system",
            target_id="auth-system",
            details={"reason": "Invalid credentials"},
            message="认证失败: user-001",
            created_at=datetime.now(timezone.utc),
        )

        result = self.replay_service.replay_audit_log(
            audit_id=auth_audit.audit_id,
            mode=ReplayMode.SIMULATION,
            actor="test-user",
        )

        # 应该失败，因为认证操作不支持回放
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_generate_replay_steps(self):
        """测试回放步骤生成"""
        task_audit = self.test_audit_logs[0]

        steps = self.replay_service._generate_replay_steps(task_audit, {})

        self.assertIsInstance(steps, list)
        self.assertGreater(len(steps), 0)

        # 验证步骤结构
        for step in steps:
            self.assertIn("step_number", step)
            self.assertIn("action", step)
            self.assertIn("description", step)
            self.assertIn("parameters", step)

    def test_asset_creation_replay(self):
        """测试资产创建的回放"""
        asset_audit = self.test_audit_logs[1]

        result = self.replay_service.replay_audit_log(
            audit_id=asset_audit.audit_id,
            mode=ReplayMode.SIMULATION,
            actor="test-user",
        )

        self.assertTrue(result["success"])
        steps = result["result"]["steps"]

        # 资产创建应该有验证和创建两个步骤
        self.assertGreaterEqual(len(steps), 1)

    def test_node_registration_replay(self):
        """测试节点注册的回放"""
        node_audit = self.test_audit_logs[2]

        result = self.replay_service.replay_audit_log(
            audit_id=node_audit.audit_id,
            mode=ReplayMode.SIMULATION,
            actor="test-user",
        )

        self.assertTrue(result["success"])
        steps = result["result"]["steps"]

        # 节点注册应该有验证和注册两个步骤
        self.assertGreaterEqual(len(steps), 1)


class TestAuditReplayIntegration(unittest.TestCase):
    """集成测试：审计回放API"""

    def setUp(self):
        """测试前设置"""
        self.audit_service = AuditService(database=None)

        # 添加一些测试审计日志到服务中
        self._setup_test_audit_logs()

    def _setup_test_audit_logs(self):
        """设置测试审计日志"""
        from shared.models.audit import AuditLogCreateRequest

        # 创建任务审计日志
        task_request = AuditLogCreateRequest(
            action=AuditAction.TASK_CREATED,
            category=AuditCategory.TASK,
            level="info",
            actor="test-user",
            actor_type="user",
            target_type="task",
            target_id="integration-test-task",
            details={
                "command": "echo 'Integration Test'",
                "target_device_id": "test-device",
            },
            message="集成测试任务创建",
        )

        self.audit_service.log_action(task_request)

    def test_full_replay_workflow(self):
        """测试完整的回放工作流"""
        from shared.services.audit_replay_service import get_replay_service

        replay_service = get_replay_service(self.audit_service)

        # 获取审计日志列表
        audit_logs = self.audit_service.list_audit_logs(limit=1)
        self.assertGreater(len(audit_logs), 0)

        # 选择第一个审计日志进行回放
        test_audit = audit_logs[0]

        # 执行模拟回放
        replay_result = replay_service.replay_audit_log(
            audit_id=test_audit.audit_id,
            mode=ReplayMode.SIMULATION,
            actor="integration-test",
        )

        self.assertTrue(replay_result["success"])
        self.assertIn("replay_id", replay_result)

        # 验证回放操作本身也被记录为审计日志
        all_logs = self.audit_service.list_audit_logs()
        replay_logs = [
            log
            for log in all_logs
            if hasattr(log, "action") and log.action == AuditAction.AUDIT_REPLAYED
        ]

        # 应该至少有一个审计回放的日志
        self.assertGreaterEqual(len(replay_logs), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
