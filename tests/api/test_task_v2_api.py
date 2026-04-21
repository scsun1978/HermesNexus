"""
Task API v2 测试 - Week 4 Day 4-5
测试v2 API的模板驱动和设备感知功能
"""
import pytest
from fastapi.testclient import TestClient
from cloud.api.main import app
from cloud.api.task_v2_api import (
    TaskCreateV2Request,
    TaskResponseV2,
    TemplateRenderRequest
)


class TestTaskAPIV2:
    """Task API v2 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_create_task_with_template(self, client):
        """测试使用模板创建任务 - MVP验收"""
        request_data = {
            "name": "系统巡检任务",
            "template_id": "inspection",
            "device_id": "server-001",
            "priority": "high"
        }

        response = client.post(
            "/api/v2/tasks",
            json=request_data,
            headers={"Authorization": "Bearer test_user"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "系统巡检任务"
        assert data["template_id"] == "inspection"
        assert data["device_id"] == "server-001"
        assert data["priority"] == "high"
        assert "task_id" in data
        assert "command" in data

    def test_create_task_with_direct_command(self, client):
        """测试直接命令创建任务"""
        request_data = {
            "name": "自定义命令",
            "command": "echo 'test command'",
            "device_config": {
                "device_type": "router",
                "vendor": "cisco"
            },
            "priority": "medium"
        }

        response = client.post(
            "/api/v2/tasks",
            json=request_data,
            headers={"Authorization": "Bearer test_user"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "自定义命令"
        assert data["command"] in ["echo 'test command'", "display version"]  # 可能被适配
        assert data["priority"] == "medium"

    def test_create_task_with_device_command_adaptation(self, client):
        """测试设备命令适配"""
        # 测试Cisco路由器命令
        request_data = {
            "name": "Cisco路由器巡检",
            "command": "show version",
            "device_config": {
                "device_type": "router",
                "vendor": "cisco"
            }
        }

        response = client.post(
            "/api/v2/tasks",
            json=request_data,
            headers={"Authorization": "Bearer test_user"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "show version" in data["command"]

        # 测试Huawei路由器命令适配
        request_data = {
            "name": "Huawei路由器巡检",
            "command": "show version",
            "device_config": {
                "device_type": "router",
                "vendor": "huawei"
            }
        }

        response = client.post(
            "/api/v2/tasks",
            json=request_data,
            headers={"Authorization": "Bearer test_user"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "display version" in data["command"]  # 应该被适配为display

    def test_list_templates(self, client):
        """测试获取模板列表"""
        response = client.get("/api/v2/tasks/templates")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total" in data
        assert data["total"] >= 4  # 至少有4个核心模板

        # 验证核心模板存在
        template_ids = [t["template_id"] for t in data["templates"]]
        assert "inspection" in template_ids
        assert "restart-service" in template_ids
        assert "upgrade-package" in template_ids
        assert "rollback-service" in template_ids

    def test_render_template(self, client):
        """测试模板渲染"""
        request_data = {
            "template_id": "inspection",
            "parameters": {}
        }

        response = client.post(
            "/api/v2/tasks/templates/render",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["template_id"] == "inspection"
        assert "rendered_command" in data
        assert "uptime" in data["rendered_command"]  # inspection模板包含uptime

    def test_render_restart_template(self, client):
        """测试重启模板渲染"""
        request_data = {
            "template_id": "restart-service",
            "parameters": {
                "service": "nginx"
            }
        }

        response = client.post(
            "/api/v2/tasks/templates/render",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "nginx" in data["rendered_command"]
        assert "systemctl" in data["rendered_command"]

    def test_get_task_v2(self, client):
        """测试获取任务详情"""
        # 先创建任务
        create_data = {
            "name": "测试任务",
            "template_id": "inspection",
            "priority": "low"
        }

        create_response = client.post(
            "/api/v2/tasks",
            json=create_data,
            headers={"Authorization": "Bearer test_user"}
        )

        assert create_response.status_code == 201
        created_task = create_response.json()
        task_id = created_task["task_id"]

        # 获取任务详情
        response = client.get(f"/api/v2/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["name"] == "测试任务"

    def test_list_tasks_v2(self, client):
        """测试列出任务"""
        # 创建几个任务
        for i in range(3):
            create_data = {
                "name": f"任务{i}",
                "command": f"echo 'task{i}'",
                "priority": "medium"
            }
            client.post(
                "/api/v2/tasks",
                json=create_data,
                headers={"Authorization": "Bearer test_user"}
            )

        # 列出任务
        response = client.get("/api/v2/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_authorization_required(self, client):
        """测试授权必需"""
        request_data = {
            "name": "未授权任务",
            "command": "echo 'test'"
        }

        # 不提供Authorization header
        response = client.post("/api/v2/tasks", json=request_data)

        assert response.status_code == 401
        # 自定义异常处理器使用 'error' 字段而非 'detail'
        error_response = response.json()
        assert "error" in error_response
        assert "Authorization header required" in error_response["error"]

    def test_invalid_template_id(self, client):
        """测试无效模板ID"""
        request_data = {
            "name": "无效模板任务",
            "template_id": "nonexistent_template"
        }

        response = client.post(
            "/api/v2/tasks",
            json=request_data,
            headers={"Authorization": "Bearer test_user"}
        )

        assert response.status_code == 404
        # 自定义异常处理器使用 'error' 字段而非 'detail'
        error_response = response.json()
        assert "error" in error_response
        assert "Template not found" in error_response["error"]


class TestMVPTaskAPIV2Acceptance:
    """MVP Task API v2 验收测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_mvp_template_driven_task_creation(self, client):
        """MVP 模板驱动任务创建验收"""
        # 使用4类核心模板创建任务
        templates = ["inspection", "restart-service", "upgrade-package", "rollback-service"]

        for template_id in templates:
            request_data = {
                "name": f"{template_id}任务",
                "template_id": template_id,
                "priority": "medium"
            }

            response = client.post(
                "/api/v2/tasks",
                json=request_data,
                headers={"Authorization": "Bearer test_user"}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["template_id"] == template_id
            assert data["command"] is not None

        print("✅ MVP 模板驱动任务创建验收通过")

    def test_mvp_device_aware_task_creation(self, client):
        """MVP 设备感知任务创建验收"""
        # 测试3类设备的任务创建
        devices = [
            {"device_type": "router", "vendor": "cisco"},
            {"device_type": "switch", "vendor": "huawei"},
            {"device_type": "server", "os_type": "linux"}
        ]

        for device_config in devices:
            request_data = {
                "name": f"{device_config['device_type']}任务",
                "command": "show version" if device_config['device_type'] != "server" else "uptime",
                "device_config": device_config
            }

            response = client.post(
                "/api/v2/tasks",
                json=request_data,
                headers={"Authorization": "Bearer test_user"}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["command"] is not None

        print("✅ MVP 设备感知任务创建验收通过")

    def test_mvp_vendor_command_adaptation(self, client):
        """MVP 厂商命令适配验收"""
        # 测试不同厂商的命令适配
        vendors = ["cisco", "huawei"]

        for vendor in vendors:
            request_data = {
                "name": f"{vendor}路由器巡检",
                "command": "show version",
                "device_config": {
                    "device_type": "router",
                    "vendor": vendor
                }
            }

            response = client.post(
                "/api/v2/tasks",
                json=request_data,
                headers={"Authorization": "Bearer test_user"}
            )

            assert response.status_code == 201
            data = response.json()

            # 验证命令适配
            if vendor == "cisco":
                assert "show version" in data["command"]
            elif vendor == "huawei":
                assert "display version" in data["command"]

        print("✅ MVP 厂商命令适配验收通过")

    def test_mvp_template_parameter_substitution(self, client):
        """MVP 模板参数替换验收"""
        request_data = {
            "template_id": "restart-service",
            "parameters": {
                "service": "mysql"
            }
        }

        response = client.post(
            "/api/v2/tasks/templates/render",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "mysql" in data["rendered_command"]
        assert data["parameters"]["service"] == "mysql"

        print("✅ MVP 模板参数替换验收通过")

    def test_mvp_end_to_end_workflow(self, client):
        """MVP 端到端工作流验收"""
        # 1. 查看可用模板
        templates_response = client.get("/api/v2/tasks/templates")
        assert templates_response.status_code == 200
        templates = templates_response.json()
        assert templates["total"] >= 4

        # 2. 选择模板并预览
        template_id = "inspection"
        preview_response = client.post(
            "/api/v2/tasks/templates/render",
            json={"template_id": template_id, "parameters": {}}
        )
        assert preview_response.status_code == 200
        preview = preview_response.json()
        assert preview["preview"] is True

        # 3. 使用模板创建任务
        create_response = client.post(
            "/api/v2/tasks",
            json={
                "name": "端到端测试任务",
                "template_id": template_id,
                "priority": "high"
            },
            headers={"Authorization": "Bearer test_user"}
        )
        assert create_response.status_code == 201
        created_task = create_response.json()

        # 4. 查询任务状态
        task_id = created_task["task_id"]
        get_response = client.get(f"/api/v2/tasks/{task_id}")
        assert get_response.status_code == 200
        task_status = get_response.json()
        assert task_status["task_id"] == task_id

        print("✅ MVP 端到端工作流验收通过")
        print(f"   完成工作流：模板选择 → 预览 → 创建 → 查询")
        print(f"   任务ID：{task_id}")