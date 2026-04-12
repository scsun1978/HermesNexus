"""
HermesNexus Phase 2 - Database Backend Interface
数据库后端抽象接口
"""

from abc import ABC, abstractmethod
from typing import Optional


class DatabaseBackend(ABC):
    """数据库后端抽象接口"""

    def __init__(self, connection_string: str, echo: bool = False):
        """
        初始化数据库后端

        Args:
            connection_string: 数据库连接字符串
            echo: 是否打印SQL语句（用于调试）
        """
        self.connection_string = connection_string
        self.echo = echo
        self.engine = None
        self.Session = None

    @abstractmethod
    def initialize(self):
        """
        初始化数据库连接

        创建引擎、连接池和会话工厂
        """
        pass

    @abstractmethod
    def create_tables(self):
        """
        创建所有数据表

        根据ORM模型定义创建表结构
        """
        pass

    @abstractmethod
    def drop_tables(self):
        """
        删除所有数据表

        注意：此操作会删除所有数据，谨慎使用
        """
        pass

    @abstractmethod
    def close(self):
        """
        关闭数据库连接

        释放资源，清理连接池
        """
        pass

    @abstractmethod
    def get_session(self):
        """
        获取数据库会话

        Returns:
            数据库会话对象
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            数据库是否可用
        """
        pass
