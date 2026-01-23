"""
Interface for Todo Manager component.

This interface defines the contract for managing todo lists in the Code Agent system.
It follows the Interface Segregation Principle by focusing only on todo management operations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...todo_manager import TodoItem
    from ..types import TaskType


class ITodoManager(ABC):
    """
    Interface for todo list management.

    This interface defines methods for:
    - Loading and parsing todo files
    - Managing task states
    - Providing task hierarchies
    - Supporting different file formats
    """

    @abstractmethod
    def load_todos(self) -> bool:
        """
        Load todo items from the project directory.

        Returns:
            True if loading was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_pending_tasks(self) -> List['TodoItem']:
        """
        Get all pending (not completed) tasks.

        Returns:
            List of pending TodoItem objects
        """
        pass

    @abstractmethod
    def get_all_tasks(self) -> List['TodoItem']:
        """
        Get all tasks including completed ones.

        Returns:
            List of all TodoItem objects
        """
        pass

    @abstractmethod
    def mark_task_done(self, task_text: str, comment: Optional[str] = None) -> bool:
        """
        Mark a specific task as completed.

        Args:
            task_text: Text of the task to mark as done
            comment: Optional comment about the completion

        Returns:
            True if task was found and marked, False otherwise
        """
        pass

    @abstractmethod
    def get_task_hierarchy(self) -> Dict[str, Any]:
        """
        Get the hierarchical structure of all tasks.

        Returns:
            Dictionary representing the task hierarchy
        """
        pass

    @abstractmethod
    def save_todos(self) -> bool:
        """
        Save the current todo state to file.

        Returns:
            True if saving was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_tasks_by_type(self, task_type: 'TaskType') -> List['TodoItem']:
        """
        Get all tasks of a specific type.

        Args:
            task_type: TaskType to filter by

        Returns:
            List of TodoItem instances of the specified type
        """
        pass

    @abstractmethod
    def get_task_type_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about task types distribution.

        Returns:
            Dictionary containing statistics about task types (counts, percentages, etc.)
        """
        pass

    @abstractmethod
    def update_task_type(self, task_id: str, task_type: Optional['TaskType']) -> bool:
        """
        Update the task type for a specific task.

        Args:
            task_id: Unique task identifier
            task_type: New TaskType to assign, or None for auto-detection

        Returns:
            True if update was successful, False otherwise
        """
        pass

    @abstractmethod
    def validate_task_types(self) -> Dict[str, Any]:
        """
        Validate that all tasks have appropriate types assigned.

        Returns:
            Dictionary containing validation results, including any tasks
            that may need type assignment or correction
        """
        pass