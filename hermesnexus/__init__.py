"""
HermesNexus - Distributed Edge Device Management System
"""

__version__ = "2.0.0-dev"
__author__ = "HermesNexus Team"
__description__ = "Distributed Edge Device Management System with Task Orchestration"

# Import main modules
from .task import Task, TaskTemplate, TaskManager, TaskExecutor

__all__ = [
    'Task',
    'TaskTemplate',
    'TaskManager',
    'TaskExecutor',
    '__version__',
    '__author__',
    '__description__',
]