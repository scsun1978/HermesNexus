"""
Aruba任务模板单元测试 - Phase 4B
测试Aruba专用任务模板功能
"""
import pytest
from hermesnexus.task.templates import (
    ArubaTemplates,
    TemplateManager,
    MVPTaskTemplates,
    CoreTemplates
)
from hermesnexus.task.model import TaskTemplate


class TestArubaTemplates:
    """Aruba模板系统测试套件"""

    def test_aruba_inspection_template_exists(self):
        """测试Aruba巡检模板存在性 - 基础功能测试"""
        template = ArubaTemplates.get_aruba_inspection_template()

        assert template is not None, "Aruba巡检模板应该存在"
        assert template.template_id == "aruba-inspection"
        assert "Aruba设备巡检" in template.name
        print(f"✅ Aruba巡检模板存在: {template.name}")

    def test_aruba_ap_restart_template_exists(self):
        """测试Aruba AP重启模板存在性 - 基础功能测试"""
        template = ArubaTemplates.get_aruba_ap_restart_template()

        assert template is not None, "Aruba AP重启模板应该存在"
        assert template.template_id == "aruba-ap-restart"
        assert "Aruba AP重启" in template.name
        print(f"✅ Aruba AP重启模板存在: {template.name}")

    def test_aruba_config_backup_template_exists(self):
        """测试Aruba配置备份模板存在性 - 基础功能测试"""
        template = ArubaTemplates.get_aruba_config_backup_template()

        assert template is not None, "Aruba配置备份模板应该存在"
        assert template.template_id == "aruba-config-backup"
        assert "Aruba配置备份" in template.name
        print(f"✅ Aruba配置备份模板存在: {template.name}")

    def test_aruba_client_check_template_exists(self):
        """测试Aruba客户端检查模板存在性 - 基础功能测试"""
        template = ArubaTemplates.get_aruba_client_check_template()

        assert template is not None, "Aruba客户端检查模板应该存在"
        assert template.template_id == "aruba-client-check"
        assert "Aruba客户端检查" in template.name
        print(f"✅ Aruba客户端检查模板存在: {template.name}")

    def test_aruba_template_command_content(self):
        """测试Aruba模板命令内容 - 功能测试"""
        inspection_template = ArubaTemplates.get_aruba_inspection_template()

        # 验证命令包含关键的Aruba特定命令
        assert "show version" in inspection_template.command_template
        assert "show ap database" in inspection_template.command_template
        assert "show client summary" in inspection_template.command_template
        assert "show wlan ssid" in inspection_template.command_template

        print(f"✅ Aruba巡检模板命令内容正确: {inspection_template.command_template}")

    def test_aruba_template_parameter_replacement(self):
        """测试Aruba模板参数替换 - 功能测试"""
        ap_restart_template = ArubaTemplates.get_aruba_ap_restart_template()

        # 测试默认参数
        command_with_default = ap_restart_template.render()
        assert "ap-01" in command_with_default
        assert "ap restart" in command_with_default

        # 测试自定义参数
        command_with_custom = ap_restart_template.render(ap_name="ap-prod-02")
        assert "ap-prod-02" in command_with_custom
        assert "ap-01" not in command_with_custom

        print(f"✅ Aruba模板参数替换正常")
        print(f"   默认: {command_with_default}")
        print(f"   自定义: {command_with_custom}")

    def test_aruba_get_all_templates(self):
        """测试获取所有Aruba模板 - 集成测试"""
        all_templates = ArubaTemplates.get_all_templates()

        assert isinstance(all_templates, dict)
        assert len(all_templates) == 4  # 应该有4个Aruba模板

        expected_template_ids = [
            "aruba-inspection",
            "aruba-ap-restart",
            "aruba-config-backup",
            "aruba-client-check"
        ]

        for template_id in expected_template_ids:
            assert template_id in all_templates, f"应该包含模板: {template_id}"
            assert isinstance(all_templates[template_id], TaskTemplate)

        print(f"✅ 获取所有Aruba模板: {len(all_templates)}个")

    def test_aruba_template_vs_mvp_templates(self):
        """测试Aruba模板与MVP模板的关系 - 兼容性测试"""
        # 获取MVP核心模板
        mvp_templates = CoreTemplates.get_all_templates()

        # 获取Aruba模板
        aruba_templates = ArubaTemplates.get_all_templates()

        # 验证没有模板ID冲突
        mvp_ids = set(mvp_templates.keys())
        aruba_ids = set(aruba_templates.keys())

        conflicts = mvp_ids & aruba_ids
        assert len(conflicts) == 0, f"不应该有模板ID冲突: {conflicts}"

        print(f"✅ Aruba模板与MVP模板无冲突")
        print(f"   MVP模板: {len(mvp_ids)}个")
        print(f"   Aruba模板: {len(aruba_ids)}个")


class TestArubaTemplateManager:
    """Aruba模板管理器集成测试"""

    def test_template_manager_registers_aruba_templates(self):
        """测试模板管理器注册Aruba模板 - 集成测试"""
        manager = TemplateManager()

        # 验证Aruba模板已注册
        aruba_template_ids = [
            "aruba-inspection",
            "aruba-ap-restart",
            "aruba-config-backup",
            "aruba-client-check"
        ]

        for template_id in aruba_template_ids:
            # 应该能获取到Aruba模板，不抛出异常
            template = manager.get_template(template_id)
            assert template is not None, f"应该能获取模板: {template_id}"
            assert template.template_id == template_id

        print(f"✅ 模板管理器已注册所有Aruba模板")

    def test_template_manager_lists_aruba_templates(self):
        """测试模板管理器列出Aruba模板 - 集成测试"""
        manager = TemplateManager()

        all_templates = manager.list_templates()

        # 验证Aruba模板在列表中
        aruba_template_ids = [
            "aruba-inspection",
            "aruba-ap-restart",
            "aruba-config-backup",
            "aruba-client-check"
        ]

        listed_template_ids = [t['template_id'] for t in all_templates]

        for template_id in aruba_template_ids:
            assert template_id in listed_template_ids, f"模板列表应包含: {template_id}"

        print(f"✅ 模板管理器正确列出Aruba模板: 总计{len(all_templates)}个模板")

    def test_template_manager_creates_aruba_task(self):
        """测试模板管理器创建Aruba任务 - 端到端测试"""
        manager = TemplateManager()

        # 从模板创建任务命令
        inspection_command = manager.create_task_from_template("aruba-inspection")

        # 验证命令内容
        assert "show version" in inspection_command
        assert "show ap database" in inspection_command
        assert "show client summary" in inspection_command
        assert "show wlan ssid" in inspection_command

        print(f"✅ 从模板创建Aruba任务成功")
        print(f"   命令: {inspection_command}")

    def test_template_manager_aruba_ap_restart_with_params(self):
        """测试Aruba AP重启任务参数化 - 端到端测试"""
        manager = TemplateManager()

        # 使用自定义参数创建任务
        custom_command = manager.create_task_from_template(
            "aruba-ap-restart",
            ap_name="ap-branch-office-03"
        )

        assert "ap-branch-office-03" in custom_command
        assert "ap restart" in custom_command

        print(f"✅ 参数化Aruba AP重启任务成功")
        print(f"   命令: {custom_command}")

    def test_template_manager_validates_aruba_template_params(self):
        """测试Aruba模板参数验证 - 功能测试"""
        manager = TemplateManager()

        # 测试参数验证
        is_valid_default = manager.validate_template_params("aruba-ap-restart", {})
        assert is_valid_default, "默认参数应该有效"

        is_valid_custom = manager.validate_template_params(
            "aruba-ap-restart",
            {"ap_name": "ap-test-01"}
        )
        assert is_valid_custom, "自定义参数应该有效"

        print(f"✅ Aruba模板参数验证正常")

    def test_template_manager_get_aruba_template_info(self):
        """测试获取Aruba模板详细信息 - 功能测试"""
        manager = TemplateManager()

        # 获取Aruba巡检模板信息
        template_info = manager.get_template_info("aruba-inspection")

        assert template_info['template_id'] == "aruba-inspection"
        assert "Aruba设备巡检" in template_info['name']
        assert "version" in template_info['command_template']
        assert "ap database" in template_info['command_template']

        print(f"✅ Aruba模板信息获取成功")
        print(f"   模板ID: {template_info['template_id']}")
        print(f"   名称: {template_info['name']}")
        print(f"   命令模板: {template_info['command_template']}")


class TestArubaTemplateIntegration:
    """Aruba模板集成测试"""

    def test_full_aruba_workflow(self):
        """测试Aruba模板完整工作流 - 端到端测试"""
        # 1. 创建模板管理器
        manager = TemplateManager()

        # 2. 验证Aruba模板可用
        aruba_templates = manager.list_templates()
        aruba_template_ids = [t['template_id'] for t in aruba_templates if t['template_id'].startswith('aruba-')]

        assert len(aruba_template_ids) == 4, "应该有4个Aruba模板"

        # 3. 创建各种Aruba任务
        tasks_created = []

        # 巡检任务
        inspection_cmd = manager.create_task_from_template("aruba-inspection")
        tasks_created.append(("巡检", inspection_cmd))

        # AP重启任务
        restart_cmd = manager.create_task_from_template("aruba-ap-restart", ap_name="ap-floor2-05")
        tasks_created.append(("AP重启", restart_cmd))

        # 配置备份任务
        backup_cmd = manager.create_task_from_template("aruba-config-backup")
        tasks_created.append(("配置备份", backup_cmd))

        # 客户端检查任务
        client_cmd = manager.create_task_from_template("aruba-client-check")
        tasks_created.append(("客户端检查", client_cmd))

        # 4. 验证所有任务创建成功
        for task_name, command in tasks_created:
            assert command, f"{task_name}任务命令不能为空"
            assert len(command) > 0, f"{task_name}任务命令不能为空字符串"

        print(f"✅ Aruba模板完整工作流测试通过")
        for task_name, command in tasks_created:
            print(f"   {task_name}: {command[:80]}...")

    def test_aruba_templates_dont_break_mvp(self):
        """测试Aruba模板不影响MVP模板 - 兼容性测试"""
        manager = TemplateManager()

        # 验证MVP模板仍然可用
        mvp_template_ids = [
            "inspection",
            "restart-service",
            "upgrade-package",
            "rollback-service"
        ]

        for template_id in mvp_template_ids:
            template = manager.get_template(template_id)
            assert template is not None, f"MVP模板仍应可用: {template_id}"

        # 验证Aruba模板也可用
        aruba_template_ids = [
            "aruba-inspection",
            "aruba-ap-restart",
            "aruba-config-backup",
            "aruba-client-check"
        ]

        for template_id in aruba_template_ids:
            template = manager.get_template(template_id)
            assert template is not None, f"Aruba模板应可用: {template_id}"

        total_templates = len(manager.list_templates())
        assert total_templates == 8, f"应该有8个模板（4个MVP + 4个Aruba）"

        print(f"✅ Aruba模板不影响MVP模板，总模板数: {total_templates}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
