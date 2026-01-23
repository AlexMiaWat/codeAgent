"""
Интерфейс Quality Reporter
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..models.quality_result import QualityResult, QualityGateResult


class IQualityReporter(ABC):
    """
    Интерфейс для отчетов о результатах проверок качества.
    Репортеры отвечают за форматирование и вывод результатов.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Имя репортёра"""
        pass

    @property
    @abstractmethod
    def output_format(self) -> str:
        """Формат вывода (console, json, html, etc.)"""
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка репортёра

        Args:
            config: Конфигурация репортёра
        """
        pass

    @abstractmethod
    async def report_result(self, result: QualityResult) -> None:
        """
        Отчет о результате отдельной проверки

        Args:
            result: Результат проверки
        """
        pass

    @abstractmethod
    async def report_gate_result(self, gate_result: QualityGateResult) -> None:
        """
        Отчет о результате выполнения quality gate

        Args:
            gate_result: Результат выполнения gate
        """
        pass

    @abstractmethod
    async def report_batch_results(self, results: List[QualityResult]) -> None:
        """
        Отчет о результатах нескольких проверок

        Args:
            results: Список результатов проверок
        """
        pass

    @abstractmethod
    def get_output_destination(self) -> str:
        """
        Получение места назначения вывода (файл, stdout, etc.)

        Returns:
            Описание места назначения
        """
        pass

    @abstractmethod
    def supports_realtime_reporting(self) -> bool:
        """
        Поддерживает ли репортёр отчеты в реальном времени

        Returns:
            True если поддерживает realtime
        """
        pass