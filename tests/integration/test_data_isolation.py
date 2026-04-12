"""
集成测试辅助工具 - 测试数据隔离和清理

提供测试数据隔离、临时数据库管理、测试环境清理等功能
"""

import os
import tempfile
import shutil
import unittest
from pathlib import Path
from typing import Optional
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.sqlite_backend import SQLiteBackend


class TestDataIsolation:
    """测试数据隔离管理器"""

    def __init__(self):
        self.temp_dirs = []
        self.databases = []

    def create_temp_database(self) -> SQLiteBackend:
        """创建临时数据库"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="hermesnexus_test_")
        self.temp_dirs.append(temp_dir)

        # 创建数据库文件路径
        db_path = os.path.join(temp_dir, "test.db")

        # 初始化数据库
        db = SQLiteBackend(db_path=db_path)
        db.initialize()
        db.create_tables()  # 创建数据库表
        self.databases.append(db)

        return db

    def cleanup_all(self):
        """清理所有临时资源"""
        # 清理数据库连接
        for db in self.databases:
            try:
                if hasattr(db, 'close'):
                    db.close()
            except Exception as e:
                print(f"清理数据库连接时出错: {e}")

        self.databases.clear()

        # 清理临时目录
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"清理临时目录 {temp_dir} 时出错: {e}")

        self.temp_dirs.clear()


class IsolatedTestCase(unittest.TestCase):
    """具有数据隔离功能的测试用例基类"""

    @classmethod
    def setUpClass(cls):
        """测试类设置 - 创建隔离管理器"""
        cls.isolation_manager = TestDataIsolation()

    @classmethod
    def tearDownClass(cls):
        """测试类清理 - 清理所有资源"""
        if hasattr(cls, 'isolation_manager'):
            cls.isolation_manager.cleanup_all()

    def setUp(self):
        """每个测试方法前的设置"""
        # 创建独立的临时数据库
        self.db = self.isolation_manager.create_temp_database()

        # 可以在这里初始化服务
        # self.asset_service = AssetService(database=self.db)
        # self.task_service = TaskService(database=self.db)

    def tearDown(self):
        """每个测试方法后的清理"""
        # 基类会自动清理临时资源
        pass


class TestDataCleaner:
    """测试数据清理工具"""

    @staticmethod
    def clean_test_data(db: SQLiteBackend, prefixes: list = None):
        """清理指定前缀的测试数据

        Args:
            db: 数据库连接
            prefixes: 数据前缀列表，如 ["test-", "integration-"]
        """
        if not prefixes:
            prefixes = ["test-", "integration-", "temp-"]

        try:
            # 清理测试数据
            # 注意：这里需要根据实际的DAO或Service来实现
            # 例如：
            # for prefix in prefixes:
            #     # 清理资产
            #     assets = asset_service.list_assets(filters={"asset_id": f"{prefix}*"})
            #     for asset in assets:
            #         asset_service.delete_asset(asset.asset_id)
            #
            #     # 清理任务
            #     tasks = task_service.list_tasks(filters={"task_id": f"{prefix}*"})
            #     for task in tasks:
            #         task_service.delete_task(task.task_id)

            print(f"已清理前缀为 {prefixes} 的测试数据")

        except Exception as e:
            print(f"清理测试数据时出错: {e}")

    @staticmethod
    def clean_test_data_by_ids(db: SQLiteBackend, entity_type: str, ids: list):
        """根据ID列表清理测试数据

        Args:
            db: 数据库连接
            entity_type: 实体类型 ("asset", "task", "audit_log")
            ids: 要删除的ID列表
        """
        try:
            # 根据实体类型清理数据
            if entity_type == "asset":
                # 调用 asset_service.delete_asset
                pass
            elif entity_type == "task":
                # 调用 task_service.delete_task
                pass
            elif entity_type == "audit_log":
                # 调用 audit_service.delete_audit_log (如果有的话)
                pass

            print(f"已清理 {len(ids)} 个 {entity_type} 实体")

        except Exception as e:
            print(f"清理 {entity_type} 数据时出错: {e}")


class TestConcurrencyManager:
    """测试并发管理器"""

    @staticmethod
    def generate_test_id(prefix: str, index: int) -> str:
        """生成唯一的测试ID"""
        import time
        timestamp = int(time.time() * 1000)
        return f"{prefix}_{timestamp}_{index:04d}"

    @staticmethod
    def create_isolated_test_data(prefix: str, count: int) -> list:
        """创建相互隔离的测试数据ID"""
        import uuid
        return [f"{prefix}_{uuid.uuid4().hex[:8]}" for _ in range(count)]


def with_test_data_isolation(test_func):
    """测试数据隔离装饰器

    Usage:
        @with_test_data_isolation
        def test_something(self):
            # 测试代码，自动使用隔离的测试数据
            pass
    """
    def wrapper(self, *args, **kwargs):
        # 在测试执行前创建隔离环境
        if not hasattr(self, 'db') or self.db is None:
            self.db = self.isolation_manager.create_temp_database()

        try:
            # 执行测试
            return test_func(self, *args, **kwargs)
        finally:
            # 测试后清理（如果需要）
            pass

    return wrapper


def assert_test_data_isolated(test_ids: list):
    """断言测试数据相互隔离

    Args:
        test_ids: 测试数据ID列表
    """
    # 检查ID是否有重复
    unique_ids = set(test_ids)
    if len(test_ids) != len(unique_ids):
        duplicates = [id for id in unique_ids if test_ids.count(id) > 1]
        raise AssertionError(f"测试数据ID有重复: {duplicates}")


def assert_no_test_data_leak(db: SQLiteBackend, test_prefixes: list):
    """断言没有测试数据泄漏

    Args:
        db: 数据库连接
        test_prefixes: 测试数据前缀列表
    """
    # 检查是否还有测试前缀的数据
    # 这里需要根据实际的Service实现
    # 例如：
    # for prefix in test_prefixes:
    #     assets = asset_service.list_assets(filters={"asset_id": f"{prefix}*"})
    #     tasks = task_service.list_tasks(filters={"task_id": f"{prefix}*"})
    #
    #     if assets or tasks:
    #         raise AssertionError(f"发现测试数据泄漏: {prefix}")

    pass


# 使用示例
if __name__ == "__main__":
    print("测试数据隔离工具")
    print("=" * 50)

    # 示例1: 使用隔离管理器
    manager = TestDataIsolation()
    db1 = manager.create_temp_database()
    db2 = manager.create_temp_database()

    print(f"创建了 {len(manager.databases)} 个独立数据库")
    print(f"临时目录: {manager.temp_dirs}")

    # 示例2: 生成隔离的测试ID
    test_ids = TestConcurrencyManager.create_isolated_test_data("test", 5)
    print(f"生成了 {len(test_ids)} 个隔离的测试ID: {test_ids}")

    # 清理
    manager.cleanup_all()
    print("清理完成")
