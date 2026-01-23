"""
Interface for Task Manager component.

This interface defines the contract for managing task execution in the Code Agent system.
It differs from ITodoManager by focusing on task execution rather than task list management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from enum import Enum

from .imanager import IManager

if TYPE_CHECKING:
    from ...todo_manager import TodoItem


class TaskExecutionState(Enum):
    """Enumeration of possible task execution states."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ITaskManager(IManager, ABC):
    """
    Interface for task execution management in the Code Agent system.

    This interface defines methods for:
    - Managing task execution lifecycle
    - Monitoring task progress
    - Handling task failures and recovery
    - Coordinating with agents and other components
    - Providing execution metrics and status
    """

    @abstractmethod
    def initialize_task_execution(self, task: 'TodoItem') -> str:
        """
        Initialize execution of a task and return execution ID.

        Args:
            task: TodoItem to execute

        Returns:
            Unique execution ID for tracking this task execution
        """
        pass

    @abstractmethod
    def execute_task_step(
        self,
        execution_id: str,
        step_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a specific step within a task execution.

        Args:
            execution_id: Unique execution identifier
            step_data: Data describing the step to execute

        Returns:
            Dictionary containing step execution result
        """
        pass

    @abstractmethod
    def monitor_task_progress(self, execution_id: str) -> Dict[str, Any]:
        """
        Monitor progress of a task execution.

        Args:
            execution_id: Unique execution identifier

        Returns:
            Dictionary containing current progress information
        """
        pass

    @abstractmethod
    def handle_task_failure(
        self,
        execution_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle failure during task execution.

        Args:
            execution_id: Unique execution identifier
            error: Exception that occurred
            context: Additional context about the failure

        Returns:
            Dictionary containing failure handling result and recovery actions
        """
        pass

    @abstractmethod
    def finalize_task_execution(self, execution_id: str) -> bool:
        """
        Finalize a completed task execution.

        Args:
            execution_id: Unique execution identifier

        Returns:
            True if finalization was successful, False otherwise
        """
        pass

    @abstractmethod
    def cancel_task_execution(self, execution_id: str) -> bool:
        """
        Cancel an ongoing task execution.

        Args:
            execution_id: Unique execution identifier

        Returns:
            True if cancellation was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of a specific task execution.

        Args:
            execution_id: Unique execution identifier

        Returns:
            Dictionary containing execution status, progress, and metadata
        """
        pass

    @abstractmethod
    def get_active_executions(self) -> List[str]:
        """
        Get list of currently active execution IDs.

        Returns:
            List of active execution IDs
        """
        pass

    @abstractmethod
    def get_execution_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get history of task executions.

        Args:
            limit: Optional limit on number of executions to return

        Returns:
            List of execution records with status and metadata
        """
        pass

    @abstractmethod
    def retry_execution(self, execution_id: str) -> str:
        """
        Retry a failed task execution.

        Args:
            execution_id: Unique execution identifier of failed execution

        Returns:
            New execution ID for the retry attempt
        """
        pass

    @abstractmethod
    def get_execution_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about task execution performance.

        Returns:
            Dictionary containing execution metrics (success rates, timings, etc.)
        """
        pass

    @abstractmethod
    def validate_execution_requirements(
        self,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Validate that all requirements for task execution are met.

        Args:
            execution_id: Unique execution identifier

        Returns:
            Dictionary containing validation results and any missing requirements
        """
        pass