"""Interface for a quality reporter."""
from abc import ABC, abstractmethod

class IQualityReporter(ABC):
    @abstractmethod
    def report(self, results: dict):
        pass
