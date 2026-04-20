"""
任务数据模型
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json


@dataclass
class Task:
    """任务核心模型"""
    task_id: str
    name: str
    description: str
    command: str
    target_device_id: str
    status: str = "pending"
    created_by: str = "system"
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换datetime对象为ISO格式字符串
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif value is None:
                data[key] = None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        # 转换ISO格式字符串回datetime对象
        processed_data = {}
        for key, value in data.items():
            if key in ['created_at', 'started_at', 'completed_at'] and value:
                if isinstance(value, str):
                    processed_data[key] = datetime.fromisoformat(value)
                else:
                    processed_data[key] = value
            else:
                processed_data[key] = value

        # 确保必要字段存在
        if 'task_id' not in processed_data:
            processed_data['task_id'] = str(uuid.uuid4())
        if 'status' not in processed_data:
            processed_data['status'] = 'pending'
        if 'created_by' not in processed_data:
            processed_data['created_by'] = 'system'

        return cls(**processed_data)

    @classmethod
    def create(cls, name: str, description: str, command: str,
               target_device_id: str, created_by: str = "system") -> 'Task':
        """创建新任务的工厂方法"""
        return cls(
            task_id=str(uuid.uuid4()),
            name=name,
            description=description,
            command=command,
            target_device_id=target_device_id,
            created_by=created_by
        )


@dataclass
class TaskTemplate:
    """任务模板模型"""
    template_id: str
    name: str
    description: str
    command_template: str
    default_params: Dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs) -> str:
        """渲染命令模板"""
        # 合并默认参数和用户提供参数
        params = {**self.default_params, **kwargs}

        try:
            # 使用format方法进行简单的字符串替换
            return self.command_template.format(**params)
        except KeyError as e:
            raise ValueError(f"Missing required parameter: {e}")

    def render_with_params(self, params: Dict[str, Any]) -> str:
        """使用参数字典渲染命令模板"""
        return self.render(**params)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskTemplate':
        """从字典创建"""
        if 'default_params' not in data:
            data['default_params'] = {}
        return cls(**data)

    @classmethod
    def create(cls, template_id: str, name: str, description: str,
               command_template: str, default_params: Dict[str, Any] = None) -> 'TaskTemplate':
        """创建新模板的工厂方法"""
        if default_params is None:
            default_params = {}
        return cls(
            template_id=template_id,
            name=name,
            description=description,
            command_template=command_template,
            default_params=default_params
        )


class TaskStatus:
    """任务状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """检查状态是否有效"""
        return status in [cls.PENDING, cls.RUNNING, cls.COMPLETED,
                        cls.FAILED, cls.CANCELLED]

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """检查是否为终止状态"""
        return status in [cls.COMPLETED, cls.FAILED, cls.CANCELLED]


class TaskPriority:
    """任务优先级常量"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def get_weight(cls, priority: str) -> int:
        """获取优先级权重"""
        weights = {
            cls.LOW: 1,
            cls.MEDIUM: 2,
            cls.HIGH: 3,
            cls.CRITICAL: 4
        }
        return weights.get(priority, 2)  # 默认为MEDIUM