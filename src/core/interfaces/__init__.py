"""
Core interfaces for Code Agent components

This module contains all interfaces that define contracts for components
following SOLID principles and dependency injection patterns.
"""

from .imanager import IManager
from .itodo_manager import ITodoManager
from .istatus_manager import IStatusManager
from .icheckpoint_manager import ICheckpointManager
from .ilogger import ILogger, ITaskLogger
from .iserver import IServer
from .iagent import IAgent
from .itaskmanager import ITaskManager, TaskExecutionState

__all__ = [
    "IManager",
    "ITodoManager",
    "IStatusManager",
    "ICheckpointManager",
    "ILogger",
    "ITaskLogger",
    "IServer",
    "IAgent",
    "ITaskManager",
    "TaskExecutionState",
]