"""Interface for the quality gate manager."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IQualityGateManager(ABC):
    @abstractmethod
    def add_gate(self, gate):
        pass

    @abstractmethod

    @abstractmethod
    async def run_specific_gates(self, check_types: List["QualityCheckType"], context: Dict[str, Any]) -> "QualityGateResult":
        pass
    def run_gates(self) -> bool:
        pass
