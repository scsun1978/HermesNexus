"""
任务执行器模块

包含各种任务类型的执行器实现
"""

from .ssh_executor import SSHExecutor

__all__ = ["SSHExecutor"]
