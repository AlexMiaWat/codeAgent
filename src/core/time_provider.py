from abc import ABC, abstractmethod
from datetime import datetime

class IDateTimeProvider(ABC):
    """Interface for providing current datetime, allowing for testability."""

    @abstractmethod
    def now(self) -> datetime:
        pass

class SystemDateTimeProvider(IDateTimeProvider):
    """Concrete implementation of IDateTimeProvider that returns the system's current datetime."""

    def now(self) -> datetime:
        return datetime.now()