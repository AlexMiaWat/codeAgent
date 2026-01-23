"""
Интерфейс Quality Gate
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..models.quality_result import QualityResult, QualityCheckType


class IQualityGate(ABC):
    """
    Интерфейс для отдельного quality gate.
    Quality gate представляет собой набор проверок качества определенного типа.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Имя quality gate"""
        pass

    @property
    @abstractmethod
    def check_type(self) -> QualityCheckType:
        """Тип проверок, выполняемых этим gate"""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Включен ли gate"""
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка quality gate

        Args:
            config: Конфигурация gate
        """
        pass

    @abstractmethod
    async def run_checks(self, context: Optional[Dict[str, Any]] = None) -> List[QualityResult]:
        """
        Выполнение всех проверок quality gate

        Args:
            context: Контекст выполнения (путь к проекту, параметры и т.д.)

        Returns:
            Список результатов проверок
        """
        pass

    @abstractmethod
    def get_required_score(self) -> float:
        """
        Минимальный требуемый скор для прохождения gate (0.0 - 1.0)

        Returns:
            Минимальный скор
        """
        pass

    @abstractmethod
    def is_strict_mode(self) -> bool:
        """
        Должен ли gate блокировать выполнение при невыполнении критериев

        Returns:
            True если strict mode включен
        """
        pass

    @abstractmethod
    def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Схема конфигурации для этого gate

        Returns:
            JSON схема конфигурации
        """
        pass