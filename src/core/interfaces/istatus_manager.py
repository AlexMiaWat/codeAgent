"""
Interface for Status Manager component.

This interface defines the contract for managing project status files in the Code Agent system.
It ensures consistent status tracking and reporting across different implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path


class IStatusManager(ABC):
    """
    Interface for status file management.

    This interface defines methods for:
    - Reading and writing status information
    - Managing task status updates
    - Maintaining status file structure
    """

    @abstractmethod
    def __init__(self, status_file: Path, config: Optional[dict] = None) -> None:
        """
        Initialize the status manager.

        Args:
            status_file: Path to the status file
            config: Optional configuration for the manager
        """
        pass

    @abstractmethod
    def read_status(self) -> str:
        """
        Read the current status from the file.

        Returns:
            Current status content as string
        """
        pass

    @abstractmethod
    def write_status(self, content: str) -> None:
        """
        Write new status content to the file.

        Args:
            content: Status content to write
        """
        pass

    @abstractmethod
    def append_status(self, message: str, level: int = 1) -> None:
        """
        Append a message to the status file with proper formatting.

        Args:
            message: Message to append
            level: Header level for markdown formatting (1-6)
        """
        pass

    @abstractmethod
    def update_task_status(self, task_name: str, status: str, details: Optional[str] = None) -> None:
        """
        Update the status of a specific task.

        Args:
            task_name: Name of the task
            status: New status of the task
            details: Optional additional details
        """
        pass

    @abstractmethod
    def add_separator(self) -> None:
        """
        Add a visual separator to the status file.
        """
        pass