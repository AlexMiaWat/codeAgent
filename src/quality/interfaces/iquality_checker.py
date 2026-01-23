"""
Интерфейс Quality Checker
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..models.quality_result import QualityResult, QualityCheckType


class IQualityChecker(ABC):
    """
    Интерфейс для отдельной проверки качества.
    Каждая проверка фокусируется на конкретном аспекте качества кода.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Имя проверки"""
        pass

    @property
    @abstractmethod
    def check_type(self) -> QualityCheckType:
        """Тип проверки"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Описание того, что проверяет эта проверка"""
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка проверки

        Args:
            config: Конфигурация проверки
        """
        pass

    @abstractmethod
    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки качества

        Args:
            context: Контекст выполнения (путь к файлу, проекту и т.д.)

        Returns:
            Результат проверки
        """
        pass

    @abstractmethod
    def get_default_threshold(self) -> float:
        """
        Значение порога по умолчанию (0.0 - 1.0)

        Returns:
            Порог по умолчанию
        """
        pass

    @abstractmethod
    def is_configurable(self) -> bool:
        """
        Можно ли настроить параметры этой проверки

        Returns:
            True если проверка поддерживает настройку
        """
        pass

    @abstractmethod
    def get_supported_file_types(self) -> list[str]:
        """
        Список поддерживаемых типов файлов

        Returns:
            Список расширений файлов (например, ['.py', '.js'])
        """
        pass

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации проверки

        Args:
            config: Конфигурация для проверки

        Returns:
            True если конфигурация валидна
        """
        pass