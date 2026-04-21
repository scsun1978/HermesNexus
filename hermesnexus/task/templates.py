"""
任务模板系统 - Week 3 Day 1-2
MVP 4类任务模板实现
"""
from typing import Dict, Any, List
from .model import TaskTemplate


class CoreTemplates:
    """MVP 4类核心任务模板库"""

    @staticmethod
    def get_inspection_template() -> TaskTemplate:
        """巡检任务模板 - INSPECTION"""
        return TaskTemplate.create(
            template_id="inspection",
            name="系统巡检",
            description="检查系统基本健康状态：运行时间、磁盘使用、内存使用、网络连接状态",
            command_template="uptime && df -h && free -h && netstat -an | head -20",
            default_params={}
        )

    @staticmethod
    def get_restart_service_template() -> TaskTemplate:
        """重启服务任务模板 - RESTART"""
        return TaskTemplate.create(
            template_id="restart-service",
            name="服务重启",
            description="重启指定的系统服务",
            command_template="systemctl restart {service} && systemctl status {service}",
            default_params={"service": "nginx"}
        )

    @staticmethod
    def get_upgrade_package_template() -> TaskTemplate:
        """升级任务模板 - UPGRADE"""
        return TaskTemplate.create(
            template_id="upgrade-package",
            name="软件包升级",
            description="升级指定的软件包到最新版本",
            command_template="apt-get update && apt-get install -y {package}",
            default_params={"package": "nginx"}
        )

    @staticmethod
    def get_rollback_service_template() -> TaskTemplate:
        """回滚任务模板 - ROLLBACK"""
        return TaskTemplate.create(
            template_id="rollback-service",
            name="服务回滚",
            description="回滚服务到指定版本（通过systemd的rollback机制）",
            command_template="systemctl stop {service} && systemctl revert {service} {version} && systemctl start {service}",
            default_params={"service": "nginx", "version": "previous"}
        )

    @staticmethod
    def get_all_templates() -> Dict[str, TaskTemplate]:
        """获取所有核心模板"""
        return {
            "inspection": CoreTemplates.get_inspection_template(),
            "restart-service": CoreTemplates.get_restart_service_template(),
            "upgrade-package": CoreTemplates.get_upgrade_package_template(),
            "rollback-service": CoreTemplates.get_rollback_service_template()
        }


class TemplateManager:
    """任务模板管理器"""

    def __init__(self):
        self.templates: Dict[str, TaskTemplate] = {}
        self._register_builtin_templates()

    def _register_builtin_templates(self):
        """注册内置模板"""
        # 注册核心MVP模板
        builtin_templates = CoreTemplates.get_all_templates()
        for template_id, template in builtin_templates.items():
            self.register_template(template)

        # 注册Aruba专用模板 - Phase 4B
        aruba_templates = ArubaTemplates.get_all_templates()
        for template_id, template in aruba_templates.items():
            self.register_template(template)

    def register_template(self, template: TaskTemplate) -> bool:
        """注册模板"""
        try:
            self.templates[template.template_id] = template
            return True
        except Exception as e:
            print(f"Error registering template: {e}")
            return False

    def get_template(self, template_id: str) -> TaskTemplate:
        """获取模板"""
        if template_id not in self.templates:
            raise ValueError(f"Template '{template_id}' not found")
        return self.templates[template_id]

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有模板"""
        return [
            {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "params": template.default_params
            }
            for template in self.templates.values()
        ]

    def create_task_from_template(self, template_id: str, **params) -> str:
        """从模板创建任务命令"""
        template = self.get_template(template_id)
        return template.render(**params)

    def validate_template_params(self, template_id: str, params: Dict[str, Any]) -> bool:
        """验证模板参数"""
        try:
            template = self.get_template(template_id)
            # 提取模板中所有需要的参数
            import re
            required_params = set(re.findall(r'\{(\w+)\}', template.command_template))

            # 检查是否有未提供的必需参数（不在默认参数中，也不在用户参数中）
            missing_params = required_params - set(template.default_params.keys()) - set(params.keys())

            if missing_params:
                return False

            # 合并默认参数和用户参数
            merged_params = {**template.default_params, **params}
            # 尝试渲染来验证参数
            template.render(**merged_params)
            return True
        except (KeyError, ValueError) as e:
            print(f"Parameter validation failed: {e}")
            return False

    def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """获取模板详细信息"""
        template = self.get_template(template_id)
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "command_template": template.command_template,
            "default_params": template.default_params,
            "required_params": self._extract_required_params(template.command_template)
        }

    def _extract_required_params(self, command_template: str) -> List[str]:
        """从命令模板中提取必需参数"""
        import re
        params = re.findall(r'\{(\w+)\}', command_template)
        return list(set(params))


class MVPTaskTemplates:
    """MVP专用任务模板工厂"""

    @staticmethod
    def create_inspection_task(device_id: str, **params) -> str:
        """创建巡检任务命令"""
        template = CoreTemplates.get_inspection_template()
        return template.render(**params)

    @staticmethod
    def create_restart_task(device_id: str, service: str = "nginx") -> str:
        """创建重启任务命令"""
        template = CoreTemplates.get_restart_service_template()
        return template.render(service=service)

    @staticmethod
    def create_upgrade_task(device_id: str, package: str = "nginx") -> str:
        """创建升级任务命令"""
        template = CoreTemplates.get_upgrade_package_template()
        return template.render(package=package)

    @staticmethod
    def create_rollback_task(device_id: str, service: str = "nginx", version: str = "previous") -> str:
        """创建回滚任务命令"""
        template = CoreTemplates.get_rollback_service_template()
        return template.render(service=service, version=version)


class ArubaTemplates:
    """Aruba专用任务模板库 - Phase 4B"""

    @staticmethod
    def get_aruba_inspection_template() -> TaskTemplate:
        """Aruba设备巡检模板"""
        return TaskTemplate.create(
            template_id="aruba-inspection",
            name="Aruba设备巡检",
            description="检查Aruba设备状态：版本信息、AP数据库、客户端摘要、无线网络",
            command_template="show version && show ap database && show client summary && show wlan ssid",
            default_params={}
        )

    @staticmethod
    def get_aruba_ap_restart_template() -> TaskTemplate:
        """Aruba AP重启模板"""
        return TaskTemplate.create(
            template_id="aruba-ap-restart",
            name="Aruba AP重启",
            description="重启指定的Aruba接入点",
            command_template="ap restart {ap_name}",
            default_params={"ap_name": "ap-01"}
        )

    @staticmethod
    def get_aruba_config_backup_template() -> TaskTemplate:
        """Aruba配置备份模板"""
        return TaskTemplate.create(
            template_id="aruba-config-backup",
            name="Aruba配置备份",
            description="备份Aruba设备配置",
            command_template="show running-config",
            default_params={}
        )

    @staticmethod
    def get_aruba_client_check_template() -> TaskTemplate:
        """Aruba客户端检查模板"""
        return TaskTemplate.create(
            template_id="aruba-client-check",
            name="Aruba客户端检查",
            description="检查连接到Aruba设备的客户端信息",
            command_template="show client summary && show user-table",
            default_params={}
        )

    @staticmethod
    def get_all_templates() -> Dict[str, TaskTemplate]:
        """获取所有Aruba模板"""
        return {
            "aruba-inspection": ArubaTemplates.get_aruba_inspection_template(),
            "aruba-ap-restart": ArubaTemplates.get_aruba_ap_restart_template(),
            "aruba-config-backup": ArubaTemplates.get_aruba_config_backup_template(),
            "aruba-client-check": ArubaTemplates.get_aruba_client_check_template()
        }


# 扩展模板库 - 为未来Phase准备
class ExtendedTemplates:
    """扩展任务模板库（供后续Phase使用）"""

    @staticmethod
    def get_database_backup_template() -> TaskTemplate:
        """数据库备份模板"""
        return TaskTemplate.create(
            template_id="database-backup",
            name="数据库备份",
            description="备份指定的数据库到指定路径",
            command_template="mysqldump {database} > {backup_path}/{database}_$(date +%Y%m%d_%H%M%S).sql",
            default_params={"database": "mydb", "backup_path": "/tmp/backups"}
        )

    @staticmethod
    def get_log_cleanup_template() -> TaskTemplate:
        """日志清理模板"""
        return TaskTemplate.create(
            template_id="log-cleanup",
            name="日志清理",
            description="清理指定天数前的日志文件",
            command_template="find {log_path} -name '*.log' -mtime +{days} -delete",
            default_params={"log_path": "/var/log", "days": "7"}
        )

    @staticmethod
    def get_network_check_template() -> TaskTemplate:
        """网络检查模板"""
        return TaskTemplate.create(
            template_id="network-check",
            name="网络连接检查",
            description="检查到指定主机的网络连接",
            command_template="ping -c {count} {host} && traceroute {host}",
            default_params={"host": "8.8.8.8", "count": "4"}
        )