"""
HermesNexus Phase 2 - Base DAO
数据访问对象基类
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session


class BaseDAO(ABC):
    """数据访问对象基类"""

    def __init__(self, database):
        """
        初始化DAO

        Args:
            database: 数据库后端实例
        """
        self.database = database

    def _get_session(self) -> Session:
        """
        获取数据库会话

        Returns:
            数据库会话对象

        Raises:
            RuntimeError: 如果数据库未初始化
        """
        return self.database.get_session()

    @abstractmethod
    def insert(self, entity: Any) -> Any:
        """
        插入实体

        Args:
            entity: 要插入的实体对象

        Returns:
            插入后的实体对象
        """
        pass

    @abstractmethod
    def select_by_id(self, id: str) -> Optional[Any]:
        """
        按ID查询

        Args:
            id: 实体ID

        Returns:
            实体对象，如果不存在则返回None
        """
        pass

    @abstractmethod
    def update(self, entity: Any) -> Any:
        """
        更新实体

        Args:
            entity: 要更新的实体对象

        Returns:
            更新后的实体对象
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        删除实体

        Args:
            id: 实体ID

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    def list(self, filters: Dict[str, Any] = None, limit: int = None,
             offset: int = None, order_by: str = None) -> List[Any]:
        """
        查询实体列表

        Args:
            filters: 过滤条件字典
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序字段

        Returns:
            实体列表
        """
        pass

    @abstractmethod
    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        统计实体数量

        Args:
            filters: 过滤条件字典

        Returns:
            实体数量
        """
        pass
