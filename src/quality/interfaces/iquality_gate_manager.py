"""
Интерфейс Quality Gate Manager
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..models.quality_result import QualityGateResult, QualityCheckType


class IQualityGateManager(ABC):
    """
    Интерфейс для управления quality gates.
    Отвечает за координацию выполнения всех gates и агрегацию результатов.
    """

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка менеджера quality gates

        Args:
            config: Общая конфигурация quality gates
        """
        pass

    @abstractmethod
    async def run_all_gates(self, context: Optional[Dict[str, Any]] = None) -> QualityGateResult:
        """
        Выполнение всех активных quality gates

        Args:
            context: Контекст выполнения

        Returns:
            Агрегированный результат всех gates
        """
        pass

    @abstractmethod
    async def run_specific_gates(self, gate_types: List[QualityCheckType],
                                context: Optional[Dict[str, Any]] = None) -> QualityGateResult:
        """
        Выполнение только указанных типов gates

        Args:
            gate_types: Типы gates для выполнения
            context: Контекст выполнения

        Returns:
            Агрегированный результат указанных gates
        """
        pass

    @abstractmethod
    def enable_gate(self, gate_type: QualityCheckType) -> None:
        """
        Включение quality gate

        Args:
            gate_type: Тип gate для включения
        """
        pass

    @abstractmethod
    def disable_gate(self, gate_type: QualityCheckType) -> None:
        """
        Отключение quality gate

        Args:
            gate_type: Тип gate для отключения
        """
        pass

    @abstractmethod
    def is_gate_enabled(self, gate_type: QualityCheckType) -> bool:
        """
        Проверка включен ли gate

        Args:
            gate_type: Тип gate

        Returns:
            True если gate включен
        """
        pass

    @abstractmethod
    def get_enabled_gates(self) -> List[QualityCheckType]:
        """
        Получение списка включенных gates

        Returns:
            Список включенных типов gates
        """
        pass

    @abstractmethod
    def get_gate_configuration(self, gate_type: QualityCheckType) -> Optional[Dict[str, Any]]:
        """
        Получение конфигурации конкретного gate

        Args:
            gate_type: Тип gate

        Returns:
            Конфигурация gate или None если gate не найден
        """
        pass

    @abstractmethod
    def update_gate_configuration(self, gate_type: QualityCheckType,
                                 config: Dict[str, Any]) -> None:
        """
        Обновление конфигурации gate

        Args:
            gate_type: Тип gate
            config: Новая конфигурация
        """
        pass

    @abstractmethod
    def should_block_execution(self, gate_result: QualityGateResult) -> bool:
        """
        Определение нужно ли блокировать выполнение на основе результатов

        Args:
            gate_result: Результат выполнения gates

        Returns:
            True если выполнение должно быть заблокировано
        """
        pass

    @abstractmethod
    def get_overall_quality_score(self, gate_result: QualityGateResult) -> float:
        """
        Вычисление общего скора качества (0.0 - 1.0)

        Args:
            gate_result: Результат выполнения gates

        Returns:
            Общий скор качества
        """
        pass