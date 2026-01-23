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

# Import component interfaces (these are defined in abstract_base.py for now)
try:
    from ..abstract_base import IServerComponent, IConfigurable, IMetricsCollector
except ImportError:
    # Fallback definitions if abstract_base is not available
    from abc import ABC, abstractmethod
    from typing import Dict, Any

    class IServerComponent(ABC):
        @abstractmethod
        def initialize(self) -> bool: pass
        @abstractmethod
        def start(self) -> bool: pass
        @abstractmethod
        def stop(self) -> bool: pass
        @abstractmethod
        def get_status(self): pass
        @abstractmethod
        def get_health(self): pass

    class IConfigurable(ABC):
        @abstractmethod
        def configure(self, config: Dict[str, Any]) -> bool: pass
        @abstractmethod
        def get_configuration(self) -> Dict[str, Any]: pass
        @abstractmethod
        def validate_configuration(self, config: Dict[str, Any]) -> bool: pass

    class IMetricsCollector(ABC):
        @abstractmethod
        def collect_metrics(self) -> Dict[str, Any]: pass
        @abstractmethod
        def get_metric(self, name: str) -> Any: pass
        @abstractmethod
        def reset_metrics(self) -> bool: pass

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
    "IServerComponent",
    "IConfigurable",
    "IMetricsCollector",
]