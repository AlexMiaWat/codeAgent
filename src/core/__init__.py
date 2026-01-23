"""
Core module for Code Agent Server

This module contains the core components extracted from the monolithic server.py.
It provides modular architecture with clear separation of responsibilities.

Components:
- ServerCore: Main execution loop and session management with proper task coordination

Author: Code Agent
Version: 1.0.0
"""

# Core component imports
from .server_core import ServerCore, TaskExecutor, RevisionExecutor, TodoGenerator
from .di_container import DIContainer, create_default_container, ServiceLifetime

# Interface imports
from .interfaces import (
    IManager,
    ITodoManager,
    IStatusManager,
    ICheckpointManager,
    ILogger,
)

# Version info
__version__ = "1.0.0"
__all__ = [
    # Components
    "ServerCore",
    "TaskExecutor",
    "RevisionExecutor",
    "TodoGenerator",
    "DIContainer",
    "create_default_container",
    "ServiceLifetime",

    # Interfaces
    "IManager",
    "ITodoManager",
    "IStatusManager",
    "ICheckpointManager",
    "ILogger",
]