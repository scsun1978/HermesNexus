"""
Phase 3 审批流系统测试
验证审批流程的核心功能
"""

import unittest
import time
from pathlib import Path

import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.approval import (
    ApprovalRequest,
    ApprovalDecision,
    ApprovalComment,
    ApprovalStatus,
    ApprovalPriority,
    ApprovalConfig,
    ApprovalStateTransition,
)
from shared.services.approval_service import ApprovalService


class TestApprovalModels(unittest.TestCase):
    """审批模型测试"""

    def test_01_approval_status_transitions(self):
        """测试1: 审批状态转换"""
        print("\n[1/5] 测试审批状态转换...")

        # 测试有效转换
        self.assertTrue(
            ApprovalStateTransition.can_transition(
                ApprovalStatus.DRAFT, ApprovalStatus.PENDING
            )
        )
        self.assertTrue(
            ApprovalStateTransition.can_transition(
                ApprovalStatus.PENDING, ApprovalStatus.APPROVED
            )
        )
        self.assertTrue(
            ApprovalStateTransition.can_transition(
                ApprovalStatus.PENDING, ApprovalStatus.REJECTED
            )
        )

        # 测试无效转换
        self.assertFalse(
            ApprovalStateTransition.can_transition(
                ApprovalStatus.APPROVED, ApprovalStatus.PENDING
            )
        )
        self.assertFalse(
            ApprovalStateTransition.can_transition(
                ApprovalStatus.DRAFT, ApprovalStatus.APPROVED
            )
        )

        # 测试终态
        self.assertTrue(
            ApprovalStateTransition.is_terminal_state(ApprovalStatus.APPROVED)
        )
        self.assertTrue(
            ApprovalStateTransition.is_terminal_state(ApprovalStatus.REJECTED)
        )
        self.assertFalse(
            ApprovalStateTransition.is_terminal_state(ApprovalStatus.PENDING)
        )

        print("  ✅ 审批状态转换测试通过")

    def test_02_approval_request_creation(self):
        """测试2: 审批请求创建"""
        print("\n[2/5] 测试审批请求创建...")

        request = ApprovalRequest(
            request_id="test-approval-001",
            title="测试审批请求",
            description="这是一个测试审批请求",
            requester_id="user-001",
            requester_name="张三",
            approver_role="tenant_admin",
            operation_type="delete",
            resource_type="asset",
            resource_id="server-001",
            target_operation={"action": "delete", "name": "server-001"},
            risk_level="high",
            priority=ApprovalPriority.HIGH,
        )

        self.assertEqual(request.request_id, "test-approval-001")
        self.assertEqual(request.status, ApprovalStatus.DRAFT)
        self.assertEqual(request.priority, ApprovalPriority.HIGH)
        # 注意：手动创建的请求不会自动计算expires_at，服务创建的会
        self.assertIsNone(request.expires_at)

        print("  ✅ 审批请求创建测试通过")

    def test_03_approval_decision_model(self):
        """测试3: 审批决策模型"""
        print("\n[3/5] 测试审批决策模型...")

        decision = ApprovalDecision(
            decision_id="decision-001",
            request_id="approval-001",
            decision="approve",
            reason="同意执行",
            approver_id="admin-001",
            approver_name="李四",
        )

        self.assertEqual(decision.decision, "approve")
        self.assertEqual(decision.request_id, "approval-001")
        self.assertIsNotNone(decision.decided_at)

        print("  ✅ 审批决策模型测试通过")

    def test_04_approval_comment_model(self):
        """测试4: 审批评论模型"""
        print("\n[4/5] 测试审批评论模型...")

        comment = ApprovalComment(
            comment_id="comment-001",
            request_id="approval-001",
            content="请确认是否已备份数据",
            author_id="user-002",
            author_name="王五",
            is_internal=False,
        )

        self.assertEqual(comment.request_id, "approval-001")
        self.assertFalse(comment.is_internal)
        self.assertIsNotNone(comment.created_at)

        print("  ✅ 审批评论模型测试通过")

    def test_05_approval_config_model(self):
        """测试5: 审批配置模型"""
        print("\n[5/5] 测试审批配置模型...")

        config = ApprovalConfig(
            default_timeout_seconds=3600,
            default_approver_role="admin",
            notification_enabled=True,
        )

        self.assertEqual(config.default_timeout_seconds, 3600)
        self.assertTrue(config.notification_enabled)
        self.assertTrue(config.auto_expire_enabled)

        print("  ✅ 审批配置模型测试通过")


class TestApprovalService(unittest.TestCase):
    """审批服务测试"""

    def setUp(self):
        """测试前准备"""
        self.service = ApprovalService()

    def test_01_create_approval_request(self):
        """测试1: 创建审批请求"""
        print("\n[1/8] 测试创建审批请求...")

        request = self.service.create_request(
            title="删除生产服务器",
            description="需要删除一台生产环境的服务器",
            requester_id="user-001",
            requester_name="张三",
            operation_type="delete",
            resource_type="asset",
            target_operation={"action": "delete", "server_id": "prod-001"},
            risk_level="high",
            approver_role="tenant_admin",
            resource_id="server-001",
            priority=ApprovalPriority.HIGH,
        )

        self.assertIsNotNone(request)
        self.assertEqual(request.status, ApprovalStatus.DRAFT)
        self.assertEqual(request.requester_name, "张三")
        self.assertEqual(request.risk_level, "high")

        # 验证可以获取到请求
        retrieved = self.service.get_request(request.request_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "删除生产服务器")

        print("  ✅ 创建审批请求测试通过")

    def test_02_submit_approval_request(self):
        """测试2: 提交审批请求"""
        print("\n[2/8] 测试提交审批请求...")

        # 先创建请求
        request = self.service.create_request(
            title="重启服务",
            description="需要重启核心服务",
            requester_id="user-001",
            requester_name="李四",
            operation_type="restart",
            resource_type="service",
            target_operation={"service": "core-api"},
            risk_level="medium",
            approver_role="operator",
        )

        # 提交请求
        submitted = self.service.submit_request(request.request_id)

        self.assertEqual(submitted.status, ApprovalStatus.PENDING)
        self.assertIsNotNone(submitted.submitted_at)
        self.assertIsNone(submitted.decided_at)

        print("  ✅ 提交审批请求测试通过")

    def test_03_approve_request(self):
        """测试3: 批准审批请求"""
        print("\n[3/8] 测试批准审批请求...")

        # 创建并提交请求
        request = self.service.create_request(
            title="更新配置",
            description="更新系统配置",
            requester_id="user-001",
            requester_name="王五",
            operation_type="update",
            resource_type="config",
            target_operation={"config": "database"},
            risk_level="medium",
            approver_role="admin",
        )
        self.service.submit_request(request.request_id)

        # 批准请求
        approved = self.service.make_decision(
            request_id=request.request_id,
            decision="approve",
            reason="配置更新安全，批准执行",
            approver_id="admin-001",
            approver_name="管理员",
        )

        self.assertEqual(approved.status, ApprovalStatus.APPROVED)
        self.assertEqual(approved.decision, "approve")
        self.assertEqual(approved.approver_name, "管理员")
        self.assertIsNotNone(approved.decided_at)

        # 验证决策记录
        decisions = self.service.get_decisions(request.request_id)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].decision, "approve")

        print("  ✅ 批准审批请求测试通过")

    def test_04_reject_request(self):
        """测试4: 拒绝审批请求"""
        print("\n[4/8] 测试拒绝审批请求...")

        # 创建并提交请求
        request = self.service.create_request(
            title="删除数据库",
            description="删除生产数据库",
            requester_id="user-001",
            requester_name="赵六",
            operation_type="delete",
            resource_type="database",
            target_operation={"database": "prod-db"},
            risk_level="high",
            approver_role="admin",
        )
        self.service.submit_request(request.request_id)

        # 拒绝请求
        rejected = self.service.make_decision(
            request_id=request.request_id,
            decision="reject",
            reason="生产数据库不能删除，风险太高",
            approver_id="admin-001",
            approver_name="管理员",
        )

        self.assertEqual(rejected.status, ApprovalStatus.REJECTED)
        self.assertEqual(rejected.decision, "reject")
        self.assertIn("风险太高", rejected.decision_reason)

        print("  ✅ 拒绝审批请求测试通过")

    def test_05_withdraw_request(self):
        """测试5: 撤回审批请求"""
        print("\n[5/8] 测试撤回审批请求...")

        # 创建并提交请求
        request = self.service.create_request(
            title="部署新版本",
            description="部署新版本到生产环境",
            requester_id="user-001",
            requester_name="孙七",
            operation_type="deploy",
            resource_type="application",
            target_operation={"version": "v2.0"},
            risk_level="high",
            approver_role="admin",
        )
        self.service.submit_request(request.request_id)

        # 撤回请求
        withdrawn = self.service.withdraw_request(
            request_id=request.request_id,
            withdrawer_id="user-001",
            withdrawer_name="孙七",
            reason="发现新版本有bug，先撤回",
        )

        self.assertEqual(withdrawn.status, ApprovalStatus.WITHDRAWN)
        self.assertIn("撤回", withdrawn.decision_reason)

        print("  ✅ 撤回审批请求测试通过")

    def test_06_cancel_draft_request(self):
        """测试6: 取消草案请求"""
        print("\n[6/8] 测试取消草案请求...")

        # 创建请求（不提交）
        request = self.service.create_request(
            title="测试取消",
            description="测试取消功能",
            requester_id="user-001",
            requester_name="周八",
            operation_type="test",
            resource_type="test",
            target_operation={},
            risk_level="low",
            approver_role="operator",
        )

        # 取消请求
        cancelled = self.service.cancel_request(request.request_id)

        self.assertEqual(cancelled.status, ApprovalStatus.CANCELLED)

        # 测试已提交的请求不能取消
        submitted = self.service.create_request(
            title="测试无法取消",
            description="已提交的请求不能取消",
            requester_id="user-002",
            requester_name="吴九",
            operation_type="test",
            resource_type="test",
            target_operation={},
            risk_level="low",
            approver_role="operator",
        )
        self.service.submit_request(submitted.request_id)

        # 尝试取消已提交的请求应该失败
        with self.assertRaises(ValueError):
            self.service.cancel_request(submitted.request_id)

        print("  ✅ 取消草案请求测试通过")

    def test_07_add_comments(self):
        """测试7: 添加审批评论"""
        print("\n[7/8] 测试添加审批评论...")

        # 创建请求
        request = self.service.create_request(
            title="需要评论的审批",
            description="测试评论功能",
            requester_id="user-001",
            requester_name="郑十",
            operation_type="test",
            resource_type="test",
            target_operation={},
            risk_level="medium",
            approver_role="admin",
        )

        # 添加评论
        self.service.add_comment(
            request_id=request.request_id,
            content="请确认操作安全性",
            author_id="user-002",
            author_name="审批人A",
        )

        self.service.add_comment(
            request_id=request.request_id,
            content="已经做好安全检查",
            author_id="user-001",
            author_name="郑十",
        )

        # 获取评论
        comments = self.service.get_comments(request.request_id)

        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].content, "请确认操作安全性")
        self.assertEqual(comments[1].author_name, "郑十")

        print("  ✅ 添加审批评论测试通过")

    def test_08_list_and_filter_requests(self):
        """测试8: 列出和过滤审批请求"""
        print("\n[8/8] 测试列出和过滤审批请求...")

        # 创建多个不同状态的请求
        request1 = self.service.create_request(
            title="待审批请求1",
            description="测试过滤",
            requester_id="user-001",
            requester_name="用户A",
            operation_type="test",
            resource_type="test",
            target_operation={},
            risk_level="medium",
            approver_role="admin",
            priority=ApprovalPriority.HIGH,
        )

        self.service.create_request(
            title="待审批请求2",
            description="测试过滤",
            requester_id="user-001",
            requester_name="用户A",
            operation_type="test",
            resource_type="test",
            target_operation={},
            risk_level="low",
            approver_role="admin",
            priority=ApprovalPriority.LOW,
        )

        # 提交第一个请求
        self.service.submit_request(request1.request_id)

        # 按状态过滤
        pending_requests = self.service.list_requests(status=ApprovalStatus.PENDING)
        self.assertEqual(len(pending_requests), 1)
        self.assertEqual(pending_requests[0].request_id, request1.request_id)

        # 按优先级过滤
        high_priority_requests = self.service.list_requests(
            priority=ApprovalPriority.HIGH
        )
        self.assertGreaterEqual(len(high_priority_requests), 1)

        # 按申请人过滤
        user_requests = self.service.list_requests(requester_id="user-001")
        self.assertGreaterEqual(len(user_requests), 2)

        print("  ✅ 列出和过滤审批请求测试通过")


class TestApprovalStatistics(unittest.TestCase):
    """审批统计测试"""

    def setUp(self):
        """测试前准备"""
        self.service = ApprovalService()

        # 创建一些测试数据
        for i in range(5):
            request = self.service.create_request(
                title=f"测试请求{i}",
                description=f"测试数据{i}",
                requester_id=f"user-{i % 3}",  # 分散申请人
                requester_name=f"用户{i}",
                operation_type="test",
                resource_type="test",
                target_operation={},
                risk_level=["low", "medium", "high"][i % 3],  # 分散风险等级
                approver_role="admin",
            )
            self.service.submit_request(request.request_id)

        # 批准一些，拒绝一些
        requests = self.service.list_requests(status=ApprovalStatus.PENDING)
        for i, request in enumerate(requests[:2]):
            if i % 2 == 0:
                self.service.make_decision(
                    request_id=request.request_id,
                    decision="approve",
                    reason=f"批准{i}",
                    approver_id="admin-001",
                    approver_name="管理员",
                )
            else:
                self.service.make_decision(
                    request_id=request.request_id,
                    decision="reject",
                    reason=f"拒绝{i}",
                    approver_id="admin-001",
                    approver_name="管理员",
                )

    def test_01_get_statistics(self):
        """测试1: 获取统计信息"""
        print("\n[1/3] 测试获取统计信息...")

        stats = self.service.get_statistics()

        self.assertEqual(stats.total_requests, 5)
        self.assertGreater(stats.pending_requests, 0)
        self.assertGreater(stats.approved_requests, 0)
        self.assertGreater(stats.rejected_requests, 0)

        # 检查分类统计
        self.assertIsInstance(stats.by_priority, dict)
        self.assertIsInstance(stats.by_risk_level, dict)
        self.assertIsInstance(stats.by_operation_type, dict)
        self.assertGreater(len(stats.by_priority), 0)

        print("  ✅ 获取统计信息测试通过")

    def test_02_approval_time_statistics(self):
        """测试2: 审批时间统计"""
        print("\n[2/3] 测试审批时间统计...")

        stats = self.service.get_statistics()

        # 应该有审批时间数据
        self.assertGreater(stats.avg_approval_time_seconds, 0)

        # 最大时间应该大于等于最小时间
        self.assertGreaterEqual(
            stats.max_approval_time_seconds, stats.min_approval_time_seconds
        )

        print("  ✅ 审批时间统计测试通过")

    def test_03_timeout_checking(self):
        """测试3: 超时检查"""
        print("\n[3/3] 测试超时检查...")

        # 创建一个会超时的配置
        config = ApprovalConfig(default_timeout_seconds=1)  # 1秒超时
        service = ApprovalService(config)

        # 创建请求并提交
        request = service.create_request(
            title="超时测试",
            description="测试超时处理",
            requester_id="user-001",
            requester_name="测试用户",
            operation_type="test",
            resource_type="test",
            target_operation={},
            risk_level="low",
            approver_role="admin",
        )
        service.submit_request(request.request_id)

        # 等待超时
        time.sleep(2)

        # 检查超时
        timeout_requests = service.check_timeout()

        self.assertIn(request.request_id, timeout_requests)

        # 验证状态已更新
        expired_request = service.get_request(request.request_id)
        self.assertEqual(expired_request.status, ApprovalStatus.EXPIRED)

        print("  ✅ 超时检查测试通过")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 HermesNexus Phase 3 审批流系统测试")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestApprovalModels))
    suite.addTests(loader.loadTestsFromTestCase(TestApprovalService))
    suite.addTests(loader.loadTestsFromTestCase(TestApprovalStatistics))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 审批流系统测试全部通过")
        print("=" * 60)
        print("🎯 Phase 3 Day 3 核心功能验证完成:")
        print("  - 审批状态机 ✅")
        print("  - 审批请求创建 ✅")
        print("  - 审批决策流程 ✅")
        print("  - 审批撤回功能 ✅")
        print("  - 审批评论系统 ✅")
        print("  - 超时处理机制 ✅")
        print("  - 审批统计功能 ✅")
        print("=" * 60)
        return 0
    else:
        print("❌ 部分测试失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
