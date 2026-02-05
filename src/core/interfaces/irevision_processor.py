from abc import ABC, abstractmethod
from typing import Any, Dict


class IRevisionProcessor(ABC):
    @abstractmethod
    async def execute_revision(self) -> bool:
        """
        Выполнение ревизии проекта.

        Returns:
            True, если ревизия успешна, False в противном случае.
        """
        pass