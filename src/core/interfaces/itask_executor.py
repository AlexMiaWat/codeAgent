from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from todo_manager import TodoItem

class ITaskExecutor(ABC):
    @abstractmethod
    async def execute_task(self, todo_item: TodoItem, current_task_num: int, total_tasks: int) -> bool:
        """
        Executes a single task based on the provided TodoItem.
        
        Args:
            todo_item: The TodoItem to execute.
            current_task_num: The current task number in the iteration.
            total_tasks: The total number of tasks in the current iteration.
            
        Returns:
            True if the task was completed successfully, False otherwise.
        """
        pass
