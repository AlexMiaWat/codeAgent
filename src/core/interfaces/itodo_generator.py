from abc import ABC, abstractmethod
from typing import Any

class ITodoGenerator(ABC):
    @abstractmethod
    async def generate_new_todo_list(self) -> bool:
        """
        Generates a new TODO list.
        
        Returns:
            True if a new TODO list was successfully generated, False otherwise.
        """
        pass
