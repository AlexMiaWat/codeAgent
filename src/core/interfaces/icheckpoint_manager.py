"""
Interface for Checkpoint Manager component.

This interface defines the contract for managing checkpoints and recovery
in the Code Agent system. It ensures reliable state management and crash recovery.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class ICheckpointManager(ABC):
    """
    Interface for checkpoint and recovery management.

    This interface defines methods for:
    - Managing server session state
    - Tracking task execution progress
    - Recovery after failures
    - Statistics and monitoring
    """

    @abstractmethod
    def __init__(self, project_dir: Path, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the checkpoint manager.

        Args:
            project_dir: Directory containing the project files
            config: Optional configuration for the manager
        """
        pass

    @abstractmethod
    def mark_server_start(self, session_id: str) -> None:
        """
        Mark the server as started with a session ID.

        Args:
            session_id: Unique identifier for the server session
        """
        pass

    @abstractmethod
    def mark_server_stop(self, clean: bool = True) -> None:
        """
        Mark the server as stopped.

        Args:
            clean: Whether the shutdown was clean (no errors)
        """
        pass

    @abstractmethod
    def increment_iteration(self) -> None:
        """
        Increment the iteration counter.
        """
        pass

    @abstractmethod
    def get_iteration_count(self) -> int:
        """
        Get the current iteration count.

        Returns:
            Current iteration number
        """
        pass

    @abstractmethod
    def was_clean_shutdown(self) -> bool:
        """
        Check if the last shutdown was clean.

        Returns:
            True if last shutdown was clean, False otherwise
        """
        pass

    @abstractmethod
    def add_task(self, task_id: str, task_text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new task to the checkpoint.

        Args:
            task_id: Unique identifier for the task
            task_text: Text description of the task
            metadata: Optional metadata for the task
        """
        pass

    @abstractmethod
    def mark_task_start(self, task_id: str) -> None:
        """
        Mark a task as started.

        Args:
            task_id: Unique identifier for the task
        """
        pass

    @abstractmethod
    def mark_task_completed(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark a task as completed.

        Args:
            task_id: Unique identifier for the task
            result: Optional result data from task execution
        """
        pass

    @abstractmethod
    def mark_task_failed(self, task_id: str, error_message: str) -> None:
        """
        Mark a task as failed.

        Args:
            task_id: Unique identifier for the task
            error_message: Error message describing the failure
        """
        pass

    @abstractmethod
    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently executing task.

        Returns:
            Task information or None if no task is running
        """
        pass

    @abstractmethod
    def get_incomplete_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks that are not completed.

        Returns:
            List of incomplete task information
        """
        pass

    @abstractmethod
    def get_completed_tasks(self) -> List[Dict[str, Any]]:
        """
        Get all tasks that are completed.

        Returns:
            List of completed task information
        """
        pass

    @abstractmethod
    def is_task_completed(self, task_text: str) -> bool:
        """
        Check if a task with given text is completed.

        Args:
            task_text: Text of the task to check

        Returns:
            True if task is completed, False otherwise
        """
        pass

    @abstractmethod
    def get_recovery_info(self) -> Dict[str, Any]:
        """
        Get information needed for recovery after a crash.

        Returns:
            Dictionary with recovery information
        """
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about task execution and server state.

        Returns:
            Dictionary with statistical information
        """
        pass