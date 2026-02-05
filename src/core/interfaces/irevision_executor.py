from abc import ABC, abstractmethod
from typing import Any

class IRevisionExecutor(ABC):
    @abstractmethod
    async def execute_revision(self) -> bool:
        """
        Executes a project revision process.
        
        Returns:
            True if the revision was completed successfully, False otherwise.
        """
        pass
