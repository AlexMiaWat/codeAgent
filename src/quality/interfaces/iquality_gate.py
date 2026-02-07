"""Interface for a quality gate."""
from abc import ABC, abstractmethod

class IQualityGate(ABC):
    @abstractmethod
    def run(self) -> bool:
        pass
