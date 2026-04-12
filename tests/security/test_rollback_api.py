"""
HermesNexus Phase 3 - 回滚API测试
测试回滚和故障恢复的API端点
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json
from datetime import datetime

from cloud.api.main import app
from shared.models.rollback import (
    RollbackPlan,
    RollbackType,
    RollbackStatus,
    FailureRecord,
    RecoveryPlan,
    RecoveryAction,
    FailureType,
    FailureSeverity,
)


class TestRollbackAPI:
    """回滚API测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_headers(self):
        """模拟认证头"""
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def mock_current_user(self):
        """模拟当前用户"""
        return {
            "user_id": "test-user-001",
            "user_name": "测试用户",
            "user_type": "human",
            "roles": ["operator"],
            "tenant_id": "tenant-001",
        }

    @pytest.fixture
    def sample_rollback_plan_data(self):
        """示例回滚计划数据"""
        return {
            "name": "配置回滚测试",
            "description": "测试配置文件回滚功能",
            "trigger_reason": "配置更新导致服务异常",
            "rollback_type": "config",
            "target_resources": ["/etc/app/config.json"],
            "original_task_id": "task-001",
            "priority": 5,
            "estimated_duration_seconds": 300,
        }

    @pytest.fixture
    def sample_failure_data(self):
        """示例故障数据"""
        return {
            "task_id": "task-001",
            "failure_type": "execution_failure",
            "severity": "high",
            "error_message": "服务启动失败",
            "node_id": "node-001",
            "asset_id": "asset-001",
        }

    @pytest.fixture
    def sample_recovery_plan_data(self):
        """示例恢复计划数据"""
        return {
            "failure_id": "failure-001",
            "recovery_action": "retry",
            "steps": ["检查故障", "重试任务", "验证结果"],
            "validation_criteria": ["任务成功"],
            "priority": 5,
        }

    def test_create_rollback_plan_success(
        self, client, mock_auth_headers, sample_rollback_plan_data
    ):
        """测试成功创建回滚计划"""
        # 模拟认证和权限检查
        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["tenant_admin"]},
        ):
            response = client.post(
                "/api/v1/rollback/plans",
                json=sample_rollback_plan_data,
                headers=mock_auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"].startswith("rollback-")
        assert data["name"] == sample_rollback_plan_data["name"]
        assert data["status"] == "planned"

    def test_create_rollback_plan_unauthorized(self, client, sample_rollback_plan_data):
        """测试未授权创建回滚计划"""
        response = client.post("/api/v1/rollback/plans", json=sample_rollback_plan_data)

        assert response.status_code == 401

    def test_create_rollback_plan_forbidden(
        self, client, mock_auth_headers, sample_rollback_plan_data
    ):
        """测试权限不足创建回滚计划"""
        # 模拟普通用户，没有管理员权限
        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={
                "user_id": "test-user-001",
                "roles": ["viewer"],  # 没有管理员权限
            },
        ):
            response = client.post(
                "/api/v1/rollback/plans",
                json=sample_rollback_plan_data,
                headers=mock_auth_headers,
            )

        assert response.status_code == 403

    def test_create_rollback_plan_invalid_type(
        self, client, mock_auth_headers, sample_rollback_plan_data
    ):
        """测试无效的回滚类型"""
        invalid_data = {**sample_rollback_plan_data, "rollback_type": "invalid_type"}

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["tenant_admin"]},
        ):
            response = client.post(
                "/api/v1/rollback/plans", json=invalid_data, headers=mock_auth_headers
            )

        assert response.status_code == 400

    def test_execute_rollback_plan_success(self, client, mock_auth_headers):
        """测试成功执行回滚计划"""
        execute_data = {"plan_id": "rollback-test001", "auto_confirm": True}

        # 模拟回滚服务
        mock_plan = MagicMock(spec=RollbackPlan)
        mock_plan.plan_id = "rollback-test001"
        mock_plan.status = RollbackStatus.COMPLETED
        mock_plan.started_at = datetime.utcnow()
        mock_plan.completed_at = datetime.utcnow()
        mock_plan.final_status = "success"
        mock_plan.rollback_summary = "回滚成功"

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.execute_rollback_plan = AsyncMock(
                    return_value=mock_plan
                )
                mock_service.return_value.get_rollback_plan.return_value = mock_plan

                response = client.post(
                    "/api/v1/rollback/plans/execute",
                    json=execute_data,
                    headers=mock_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "rollback-test001"

    def test_execute_rollback_plan_not_found(self, client, mock_auth_headers):
        """测试执行不存在的回滚计划"""
        execute_data = {"plan_id": "non-existent-plan", "auto_confirm": True}

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.execute_rollback_plan.side_effect = (
                    ValueError("回滚计划不存在")
                )

                response = client.post(
                    "/api/v1/rollback/plans/execute",
                    json=execute_data,
                    headers=mock_auth_headers,
                )

        assert response.status_code == 400

    def test_cancel_rollback_plan_success(self, client, mock_auth_headers):
        """测试成功取消回滚计划"""
        mock_plan = MagicMock(spec=RollbackPlan)
        mock_plan.plan_id = "rollback-test001"
        mock_plan.status = RollbackStatus.CANCELLED
        mock_plan.completed_at = datetime.utcnow()
        mock_plan.final_status = "cancelled"

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.cancel_rollback_plan.return_value = mock_plan

                response = client.post(
                    "/api/v1/rollback/plans/rollback-test001/cancel",
                    headers=mock_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_get_rollback_plan_success(self, client, mock_auth_headers):
        """测试成功获取回滚计划"""
        mock_plan = MagicMock(spec=RollbackPlan)
        mock_plan.plan_id = "rollback-test001"
        mock_plan.name = "测试回滚计划"
        mock_plan.status = RollbackStatus.PLANNED

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.get_rollback_plan.return_value = mock_plan

                response = client.get(
                    "/api/v1/rollback/plans/rollback-test001", headers=mock_auth_headers
                )

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "rollback-test001"

    def test_get_rollback_plan_not_found(self, client, mock_auth_headers):
        """测试获取不存在的回滚计划"""
        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.get_rollback_plan.return_value = None

                response = client.get(
                    "/api/v1/rollback/plans/non-existent-plan",
                    headers=mock_auth_headers,
                )

        assert response.status_code == 404

    def test_list_rollback_plans_success(self, client, mock_auth_headers):
        """测试成功列出回滚计划"""
        mock_plans = [
            MagicMock(plan_id="rollback-001", name="计划1", status="planned"),
            MagicMock(plan_id="rollback-002", name="计划2", status="completed"),
        ]

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.list_rollback_plans.return_value = mock_plans

                response = client.get(
                    "/api/v1/rollback/plans", headers=mock_auth_headers
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_rollback_plans_with_filters(self, client, mock_auth_headers):
        """测试带过滤条件列出回滚计划"""
        mock_plans = [MagicMock(plan_id="rollback-001", status="planned")]

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.list_rollback_plans.return_value = mock_plans

                response = client.get(
                    "/api/v1/rollback/plans?status=planned&limit=10",
                    headers=mock_auth_headers,
                )

        assert response.status_code == 200

    def test_list_rollback_plans_invalid_filter(self, client, mock_auth_headers):
        """测试无效的过滤参数"""
        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            response = client.get(
                "/api/v1/rollback/plans?status=invalid_status",
                headers=mock_auth_headers,
            )

        assert response.status_code == 400

    def test_create_failure_record_success(
        self, client, mock_auth_headers, sample_failure_data
    ):
        """测试成功创建故障记录"""
        mock_failure = MagicMock(spec=FailureRecord)
        mock_failure.failure_id = "failure-test001"
        mock_failure.task_id = "task-001"
        mock_failure.failure_type = FailureType.EXECUTION_FAILURE
        mock_failure.severity = FailureSeverity.HIGH

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_recovery_service") as mock_service:
                mock_service.return_value.handle_failure = AsyncMock(
                    return_value=mock_failure
                )

                response = client.post(
                    "/api/v1/rollback/failures",
                    json=sample_failure_data,
                    headers=mock_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["failure_id"] == "failure-test001"

    def test_create_failure_record_invalid_type(
        self, client, mock_auth_headers, sample_failure_data
    ):
        """测试无效的故障类型"""
        invalid_data = {**sample_failure_data, "failure_type": "invalid_type"}

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            response = client.post(
                "/api/v1/rollback/failures",
                json=invalid_data,
                headers=mock_auth_headers,
            )

        assert response.status_code == 400

    def test_get_failure_record_success(self, client, mock_auth_headers):
        """测试成功获取故障记录"""
        mock_failure = MagicMock(spec=FailureRecord)
        mock_failure.failure_id = "failure-test001"
        mock_failure.task_id = "task-001"
        mock_failure.error_message = "测试故障"

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.get_failure_record.return_value = mock_failure

                response = client.get(
                    "/api/v1/rollback/failures/failure-test001",
                    headers=mock_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["failure_id"] == "failure-test001"

    def test_get_failure_record_not_found(self, client, mock_auth_headers):
        """测试获取不存在的故障记录"""
        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.get_failure_record.return_value = None

                response = client.get(
                    "/api/v1/rollback/failures/non-existent-failure",
                    headers=mock_auth_headers,
                )

        assert response.status_code == 404

    def test_list_failure_records_success(self, client, mock_auth_headers):
        """测试成功列出故障记录"""
        mock_failures = [
            MagicMock(failure_id="failure-001", task_id="task-001"),
            MagicMock(failure_id="failure-002", task_id="task-002"),
        ]

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.list_failure_records.return_value = (
                    mock_failures
                )

                response = client.get(
                    "/api/v1/rollback/failures", headers=mock_auth_headers
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_create_recovery_plan_success(
        self, client, mock_auth_headers, sample_recovery_plan_data
    ):
        """测试成功创建恢复计划"""
        mock_plan = MagicMock(spec=RecoveryPlan)
        mock_plan.plan_id = "recovery-test001"
        mock_plan.failure_id = "failure-001"
        mock_plan.recovery_action = RecoveryAction.RETRY

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.create_recovery_plan.return_value = mock_plan

                response = client.post(
                    "/api/v1/rollback/recoveries",
                    json=sample_recovery_plan_data,
                    headers=mock_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "recovery-test001"

    def test_create_recovery_plan_invalid_action(
        self, client, mock_auth_headers, sample_recovery_plan_data
    ):
        """测试无效的恢复动作"""
        invalid_data = {
            **sample_recovery_plan_data,
            "recovery_action": "invalid_action",
        }

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            response = client.post(
                "/api/v1/rollback/recoveries",
                json=invalid_data,
                headers=mock_auth_headers,
            )

        assert response.status_code == 400

    def test_get_recovery_plan_success(self, client, mock_auth_headers):
        """测试成功获取恢复计划"""
        mock_plan = MagicMock(spec=RecoveryPlan)
        mock_plan.plan_id = "recovery-test001"
        mock_plan.failure_id = "failure-001"
        mock_plan.status = "pending"

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.get_recovery_plan.return_value = mock_plan

                response = client.get(
                    "/api/v1/rollback/recoveries/recovery-test001",
                    headers=mock_auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "recovery-test001"

    def test_get_recovery_plan_not_found(self, client, mock_auth_headers):
        """测试获取不存在的恢复计划"""
        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.get_recovery_plan.return_value = None

                response = client.get(
                    "/api/v1/rollback/recoveries/non-existent-plan",
                    headers=mock_auth_headers,
                )

        assert response.status_code == 404

    def test_get_rollback_statistics_success(self, client, mock_auth_headers):
        """测试成功获取回滚统计信息"""
        mock_stats = MagicMock()
        mock_stats.total_rollback_plans = 100
        mock_stats.successful_rollbacks = 85
        mock_stats.failed_rollbacks = 10
        mock_stats.cancelled_rollbacks = 5
        mock_stats.success_rate = 0.85

        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["operator"]},
        ):
            with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
                mock_service.return_value.get_statistics.return_value = mock_stats

                response = client.get(
                    "/api/v1/rollback/statistics", headers=mock_auth_headers
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total_rollback_plans"] == 100
        assert data["success_rate"] == 0.85

    def test_rollback_health_check(self, client):
        """测试回滚服务健康检查"""
        with patch("cloud.api.rollback_api.get_rollback_service") as mock_service:
            mock_stats = MagicMock()
            mock_stats.total_rollback_plans = 50
            mock_service.return_value.get_statistics.return_value = mock_stats

            with patch(
                "cloud.api.rollback_api.get_recovery_service"
            ) as mock_recovery_service:
                mock_recovery_service.return_value._active_recoveries = {}

                response = client.get("/api/v1/rollback/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


@pytest.mark.integration
class TestRollbackAPIIntegration:
    """回滚API集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_headers(self):
        """模拟认证头"""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.asyncio
    async def test_full_rollback_workflow_api(self, client, mock_auth_headers):
        """测试完整的回滚工作流API"""
        with patch(
            "cloud.api.rollback_api.get_current_user",
            return_value={"user_id": "test-user-001", "roles": ["tenant_admin"]},
        ):
            # 1. 创建故障记录
            failure_data = {
                "task_id": "task-integration-001",
                "failure_type": "execution_failure",
                "severity": "high",
                "error_message": "集成测试故障",
                "auto_process": False,
            }

            failure_response = client.post(
                "/api/v1/rollback/failures",
                json=failure_data,
                headers=mock_auth_headers,
            )

            assert failure_response.status_code == 200
            failure = failure_response.json()
            failure_id = failure["failure_id"]

            # 2. 创建回滚计划
            rollback_data = {
                "name": "集成测试回滚",
                "description": "API集成测试",
                "trigger_reason": "测试故障",
                "rollback_type": "task",
                "target_resources": ["task-integration-001"],
                "original_task_id": "task-integration-001",
            }

            rollback_response = client.post(
                "/api/v1/rollback/plans", json=rollback_data, headers=mock_auth_headers
            )

            assert rollback_response.status_code == 200
            rollback_plan = rollback_response.json()
            plan_id = rollback_plan["plan_id"]

            # 3. 获取回滚计划详情
            get_response = client.get(
                f"/api/v1/rollback/plans/{plan_id}", headers=mock_auth_headers
            )

            assert get_response.status_code == 200

            # 4. 列出故障记录
            list_response = client.get(
                "/api/v1/rollback/failures", headers=mock_auth_headers
            )

            assert list_response.status_code == 200


@pytest.mark.parametrize(
    "endpoint,method",
    [
        ("/api/v1/rollback/plans", "POST"),
        ("/api/v1/rollback/plans/execute", "POST"),
        ("/api/v1/rollback/plans/test-plan/cancel", "POST"),
        ("/api/v1/rollback/plans/test-plan", "GET"),
        ("/api/v1/rollback/plans", "GET"),
        ("/api/v1/rollback/failures", "POST"),
        ("/api/v1/rollback/failures/test-failure", "GET"),
        ("/api/v1/rollback/failures", "GET"),
        ("/api/v1/rollback/recoveries", "POST"),
        ("/api/v1/rollback/recoveries/test-plan", "GET"),
        ("/api/v1/rollback/statistics", "GET"),
    ],
)
def test_rollback_endpoints_require_auth(endpoint, method):
    """测试回滚API端点需要认证"""
    client = TestClient(app)

    if method == "POST":
        response = client.post(endpoint, json={})
    elif method == "GET":
        response = client.get(endpoint)
    else:
        response = client.request(method, endpoint)

    # 所有端点都应该需要认证
    assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
