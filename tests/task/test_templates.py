"""
任务模板系统测试 - Week 3 Day 1-2
重点：MVP 4类任务模板验收
"""
import pytest
from hermesnexus.task.model import TaskTemplate
from hermesnexus.task.templates import (
    CoreTemplates, TemplateManager, MVPTaskTemplates, ExtendedTemplates
)


class TestCoreTemplates:
    """MVP 4类核心任务模板测试"""

    def test_inspection_template(self):
        """巡检任务模板 - MVP验收"""
        template = CoreTemplates.get_inspection_template()

        # 验证模板基本信息
        assert template.template_id == "inspection"
        assert template.name == "系统巡检"
        assert "运行时间、磁盘使用、内存使用" in template.description

        # 验证命令渲染
        command = template.render()
        assert "uptime" in command
        assert "df -h" in command
        assert "free -h" in command
        assert "netstat" in command

        # 验证无参数模板
        assert template.default_params == {}

        print("✅ 巡检任务模板验证通过")
        print(f"   命令: {command}")

    def test_restart_service_template(self):
        """重启服务任务模板 - MVP验收"""
        template = CoreTemplates.get_restart_service_template()

        # 验证模板基本信息
        assert template.template_id == "restart-service"
        assert template.name == "服务重启"
        assert "systemctl restart" in template.command_template

        # 验证默认参数
        assert template.default_params == {"service": "nginx"}

        # 验证使用默认参数渲染
        command = template.render()
        assert "systemctl restart nginx" in command
        assert "systemctl status nginx" in command

        # 验证自定义参数渲染
        custom_command = template.render(service="apache2")
        assert "systemctl restart apache2" in custom_command
        assert "systemctl status apache2" in custom_command

        print("✅ 重启服务任务模板验证通过")
        print(f"   默认命令: {command}")
        print(f"   自定义命令: {custom_command}")

    def test_upgrade_package_template(self):
        """升级任务模板 - MVP验收"""
        template = CoreTemplates.get_upgrade_package_template()

        # 验证模板基本信息
        assert template.template_id == "upgrade-package"
        assert template.name == "软件包升级"
        assert "apt-get" in template.command_template

        # 验证默认参数
        assert template.default_params == {"package": "nginx"}

        # 验证命令渲染
        command = template.render()
        assert "apt-get update" in command
        assert "apt-get install -y nginx" in command

        # 验证自定义包名
        custom_command = template.render(package="mysql-server")
        assert "apt-get install -y mysql-server" in custom_command

        print("✅ 软件包升级任务模板验证通过")
        print(f"   升级nginx: {command}")
        print(f"   升级mysql: {custom_command}")

    def test_rollback_service_template(self):
        """回滚任务模板 - MVP验收"""
        template = CoreTemplates.get_rollback_service_template()

        # 验证模板基本信息
        assert template.template_id == "rollback-service"
        assert template.name == "服务回滚"
        assert "systemctl" in template.command_template

        # 验证默认参数
        assert template.default_params == {"service": "nginx", "version": "previous"}

        # 验证命令渲染
        command = template.render()
        assert "systemctl stop nginx" in command
        assert "systemctl revert nginx" in command
        assert "systemctl start nginx" in command

        # 验证自定义参数
        custom_command = template.render(service="apache2", version="1.2.3")
        assert "systemctl stop apache2" in custom_command
        assert "systemctl revert apache2" in custom_command
        assert "systemctl start apache2" in custom_command

        print("✅ 服务回滚任务模板验证通过")
        print(f"   默认回滚: {command}")
        print(f"   自定义回滚: {custom_command}")

    def test_get_all_templates(self):
        """获取所有核心模板"""
        templates = CoreTemplates.get_all_templates()

        # 验证模板数量和类型
        assert len(templates) == 4
        assert "inspection" in templates
        assert "restart-service" in templates
        assert "upgrade-package" in templates
        assert "rollback-service" in templates

        # 验证所有模板都是TaskTemplate类型
        for template_id, template in templates.items():
            assert isinstance(template, TaskTemplate)
            assert template.template_id == template_id

        print("✅ 所有核心模板获取验证通过")
        print(f"   模板数量: {len(templates)}")


class TestTemplateManager:
    """模板管理器测试"""

    @pytest.fixture
    def template_manager(self):
        """创建模板管理器"""
        return TemplateManager()

    def test_template_manager_initialization(self, template_manager):
        """模板管理器初始化"""
        # 验证内置模板已自动注册 (4个MVP核心模板 + 4个Aruba模板)
        assert len(template_manager.templates) == 8
        assert "inspection" in template_manager.templates
        assert "restart-service" in template_manager.templates
        # 验证Aruba模板也注册了
        assert "aruba-inspection" in template_manager.templates
        assert "aruba-ap-restart" in template_manager.templates

    def test_register_template(self, template_manager):
        """注册自定义模板"""
        custom_template = TaskTemplate.create(
            template_id="custom-test",
            name="自定义测试",
            description="用于测试的自定义模板",
            command_template="echo '{message}'",
            default_params={"message": "hello"}
        )

        # 注册模板
        result = template_manager.register_template(custom_template)
        assert result is True

        # 验证模板已注册
        assert "custom-test" in template_manager.templates
        assert len(template_manager.templates) == 9  # 8个内置模板(4 MVP + 4 Aruba) + 1个自定义

    def test_get_template(self, template_manager):
        """获取模板"""
        # 获取存在的模板
        template = template_manager.get_template("inspection")
        assert template.template_id == "inspection"
        assert isinstance(template, TaskTemplate)

        # 获取不存在的模板应该抛出异常
        with pytest.raises(ValueError, match="not found"):
            template_manager.get_template("nonexistent")

    def test_list_templates(self, template_manager):
        """列出所有模板"""
        templates = template_manager.list_templates()

        # 验证列表结构 (4个MVP核心模板 + 4个Aruba模板)
        assert len(templates) == 8
        assert all(isinstance(t, dict) for t in templates)

        # 验证每个模板包含必要字段
        for template_info in templates:
            assert "template_id" in template_info
            assert "name" in template_info
            assert "description" in template_info
            assert "params" in template_info

        # 验证模板信息正确
        inspection_info = next(t for t in templates if t["template_id"] == "inspection")
        assert inspection_info["name"] == "系统巡检"

    def test_create_task_from_template(self, template_manager):
        """从模板创建任务命令"""
        # 使用默认参数
        command = template_manager.create_task_from_template("restart-service")
        assert "systemctl restart nginx" in command
        assert "systemctl status nginx" in command

        # 使用自定义参数
        custom_command = template_manager.create_task_from_template(
            "restart-service", service="mysql"
        )
        assert "systemctl restart mysql" in custom_command
        assert "systemctl status mysql" in custom_command

    def test_validate_template_params(self, template_manager):
        """验证模板参数"""
        # 验证正确参数
        assert template_manager.validate_template_params("restart-service", {"service": "nginx"})
        assert template_manager.validate_template_params("inspection", {})

        # 验证有默认参数的模板可以不传参数
        assert template_manager.validate_template_params("restart-service", {})  # 有默认值"nginx"

        # 验证不存在的模板
        assert not template_manager.validate_template_params("nonexistent", {})

        # 验证自定义模板注册和验证
        custom_template = TaskTemplate.create(
            template_id="custom-validation",
            name="自定义验证测试",
            description="测试自定义模板验证",
            command_template="echo '{required_param}'",
            default_params={}
        )
        template_manager.register_template(custom_template)

        # 缺少必需参数应该验证失败
        assert not template_manager.validate_template_params("custom-validation", {})
        assert template_manager.validate_template_params("custom-validation", {"required_param": "test"})

    def test_get_template_info(self, template_manager):
        """获取模板详细信息"""
        info = template_manager.get_template_info("restart-service")

        # 验证信息结构
        assert info["template_id"] == "restart-service"
        assert info["name"] == "服务重启"
        assert "systemctl" in info["command_template"]
        assert info["default_params"] == {"service": "nginx"}
        assert "service" in info["required_params"]

        # 验证必需参数提取
        assert len(info["required_params"]) > 0
        assert all(isinstance(param, str) for param in info["required_params"])


class TestMVPTaskTemplates:
    """MVP任务模板工厂测试"""

    def test_create_inspection_task(self):
        """创建巡检任务"""
        command = MVPTaskTemplates.create_inspection_task("device-001")
        assert "uptime" in command
        assert "df -h" in command
        assert "free -h" in command
        assert "netstat" in command

        print("✅ MVP工厂：巡检任务创建验证")

    def test_create_restart_task(self):
        """创建重启任务"""
        # 默认参数
        command = MVPTaskTemplates.create_restart_task("device-001")
        assert "systemctl restart nginx" in command

        # 自定义参数
        custom_command = MVPTaskTemplates.create_restart_task("device-002", "apache2")
        assert "systemctl restart apache2" in custom_command

        print("✅ MVP工厂：重启任务创建验证")

    def test_create_upgrade_task(self):
        """创建升级任务"""
        # 默认参数
        command = MVPTaskTemplates.create_upgrade_task("device-001")
        assert "apt-get install -y nginx" in command

        # 自定义参数
        custom_command = MVPTaskTemplates.create_upgrade_task("device-002", "mysql-server")
        assert "apt-get install -y mysql-server" in custom_command

        print("✅ MVP工厂：升级任务创建验证")

    def test_create_rollback_task(self):
        """创建回滚任务"""
        # 默认参数
        command = MVPTaskTemplates.create_rollback_task("device-001")
        assert "systemctl revert nginx" in command

        # 自定义参数
        custom_command = MVPTaskTemplates.create_rollback_task(
            "device-002", "apache2", "1.2.3"
        )
        assert "systemctl revert apache2" in custom_command

        print("✅ MVP工厂：回滚任务创建验证")


class TestExtendedTemplates:
    """扩展模板测试（为后续Phase准备）"""

    def test_database_backup_template(self):
        """数据库备份模板"""
        template = ExtendedTemplates.get_database_backup_template()
        assert template.template_id == "database-backup"
        assert "mysqldump" in template.command_template

        command = template.render()
        assert "mysqldump mydb" in command
        assert "/tmp/backups" in command

    def test_log_cleanup_template(self):
        """日志清理模板"""
        template = ExtendedTemplates.get_log_cleanup_template()
        assert template.template_id == "log-cleanup"
        assert "find" in template.command_template
        assert "-delete" in template.command_template

        command = template.render()
        assert "/var/log" in command
        assert "-mtime +7" in command

    def test_network_check_template(self):
        """网络检查模板"""
        template = ExtendedTemplates.get_network_check_template()
        assert template.template_id == "network-check"
        assert "ping" in template.command_template
        assert "traceroute" in template.command_template

        command = template.render()
        assert "ping -c 4" in command
        assert "8.8.8.8" in command


class TestTemplateParameterHandling:
    """模板参数处理测试"""

    def test_parameter_substitution(self):
        """参数替换测试"""
        template = TaskTemplate.create(
            template_id="param-test",
            name="参数测试",
            description="测试参数替换",
            command_template="echo '{name}' && echo '{value}' && echo '{message}'",
            default_params={"name": "default", "value": "100", "message": "hello"}
        )

        # 全部使用默认参数
        command1 = template.render()
        assert "echo 'default'" in command1
        assert "echo '100'" in command1
        assert "echo 'hello'" in command1

        # 部分覆盖默认参数
        command2 = template.render(name="custom")
        assert "echo 'custom'" in command2
        assert "echo '100'" in command2  # 默认值仍被使用
        assert "echo 'hello'" in command2

        # 完全覆盖默认参数
        command3 = template.render(name="test", value="200", message="world")
        assert "echo 'test'" in command3
        assert "echo '200'" in command3
        assert "echo 'world'" in command3

    def test_missing_required_parameter(self):
        """缺少必需参数测试"""
        template = TaskTemplate.create(
            template_id="required-test",
            name="必需参数测试",
            description="测试必需参数",
            command_template="echo '{required_param}'",
            default_params={}
        )

        # 缺少必需参数应该抛出异常
        with pytest.raises(ValueError, match="Missing required parameter"):
            template.render()

    def test_complex_parameter_substitution(self):
        """复杂参数替换测试"""
        template = TaskTemplate.create(
            template_id="complex-test",
            name="复杂参数测试",
            description="测试复杂命令参数",
            command_template="cat {file} | grep '{pattern}' > {output}",
            default_params={"file": "/var/log/syslog", "pattern": "error", "output": "/tmp/errors.txt"}
        )

        command = template.render()
        assert "cat /var/log/syslog" in command
        assert "grep 'error'" in command
        assert "> /tmp/errors.txt" in command

        # 自定义参数
        custom_command = template.render(
            file="/var/log/auth.log",
            pattern="failed",
            output="/tmp/auth_failed.txt"
        )
        assert "cat /var/log/auth.log" in custom_command
        assert "grep 'failed'" in custom_command
        assert "> /tmp/auth_failed.txt" in custom_command


class TestTemplateIntegration:
    """模板集成测试"""

    def test_template_serialization(self):
        """模板序列化测试"""
        template = CoreTemplates.get_inspection_template()
        template_dict = template.to_dict()

        # 验证序列化结果
        assert template_dict["template_id"] == "inspection"
        assert template_dict["name"] == "系统巡检"
        assert "uptime" in template_dict["command_template"]
        assert isinstance(template_dict["default_params"], dict)

        # 验证反序列化
        restored_template = TaskTemplate.from_dict(template_dict)
        assert restored_template.template_id == template.template_id
        assert restored_template.command_template == template.command_template

    def test_template_consistency_across_calls(self):
        """模板调用一致性测试"""
        template1 = CoreTemplates.get_inspection_template()
        template2 = CoreTemplates.get_inspection_template()

        # 验证多次调用返回相同模板
        assert template1.template_id == template2.template_id
        assert template1.command_template == template2.command_template
        assert template1.default_params == template2.default_params