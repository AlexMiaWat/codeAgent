"""Interface for a quality checker."""
from abc import ABC, abstractmethod

class IQualityChecker(ABC):
    @abstractmethod
    def check(self) -> dict:
        pass
