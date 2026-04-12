"""
HermesNexus Phase 2 - SQLite Backend
SQLite数据库后端实现
"""

import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from shared.database.base import DatabaseBackend


class SQLiteBackend(DatabaseBackend):
    """SQLite数据库后端实现"""

    def __init__(self, db_path: str = "data/hermesnexus.db", echo: bool = False):
        """
        初始化SQLite后端

        Args:
            db_path: 数据库文件路径
            echo: 是否打印SQL语句（用于调试）
        """
        # 确保db_path是绝对路径
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 构建SQLite连接字符串
        connection_string = f"sqlite:///{db_path}"

        super().__init__(connection_string, echo)
        self.db_path = db_path

    def initialize(self):
        """
        初始化数据库连接

        创建引擎、连接池和会话工厂
        """
        # 创建SQLite引擎
        # SQLite特定配置：
        # - check_same_thread=False: 允许多线程访问（FastAPI需要）
        # - StaticPool: 使用静态连接池（SQLite单文件场景）
        self.engine = create_engine(
            self.connection_string,
            connect_args={"check_same_thread": False},
            echo=self.echo,
            future=True  # 使用SQLAlchemy 2.0风格
        )

        # 创建会话工厂
        self.Session = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False  # 避免对象在commit后过期
        )

    def create_tables(self):
        """
        创建所有数据表

        根据ORM模型定义创建表结构
        """
        # 延迟导入避免循环依赖
        from shared.database.models import Base, AssetModel, TaskModel, AuditLogModel, NodeModel

        # 创建所有表
        Base.metadata.create_all(self.engine)

        # 确保数据库文件存在，便于依赖文件存在性的旧测试通过
        try:
            open(self.db_path, "a").close()
        except Exception:
            pass

    def drop_tables(self):
        """
        删除所有数据表

        注意：此操作会删除所有数据，谨慎使用
        """
        # 延迟导入避免循环依赖
        from shared.database.models import Base

        # 删除所有表
        Base.metadata.drop_all(self.engine)

    def close(self):
        """
        关闭数据库连接

        释放资源，清理连接池
        """
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.Session = None

    def get_session(self) -> Session:
        """
        获取数据库会话

        Returns:
            数据库会话对象
        """
        if not self.Session:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.Session()

    def _get_session(self) -> Session:
        """兼容旧测试/旧调用的会话别名"""
        return self.get_session()

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            数据库是否可用
        """
        try:
            session = self.get_session()
            # 执行简单查询测试连接
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False

    def get_connection_info(self) -> dict:
        """
        获取连接信息

        Returns:
            连接信息字典
        """
        return {
            "type": "sqlite",
            "path": self.db_path,
            "connection_string": self.connection_string,
            "file_exists": os.path.exists(self.db_path),
            "file_size": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        }
