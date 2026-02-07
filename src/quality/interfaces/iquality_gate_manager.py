"""Interface for the quality gate manager."""
from abc import ABC, abstractmethod

class IQualityGateManager(ABC):
    @abstractmethod
    def add_gate(self, gate):
        pass

    @abstractmethod
    def run_gates(self) -> bool:
        pass
