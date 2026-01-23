"""
Консольный репортёр результатов качества
"""

import logging
from typing import Dict, Any, List
from ..interfaces import IQualityReporter
from ..models.quality_result import QualityResult, QualityGateResult, QualityStatus

logger = logging.getLogger(__name__)


class ConsoleReporter(IQualityReporter):
    """
    Репортёр для вывода результатов качества в консоль
    """

    def __init__(self):
        self._config = {}
        self._verbose = False

    @property
    def name(self) -> str:
        return "Console Reporter"

    @property
    def output_format(self) -> str:
        return "console"

    def configure(self, config: Dict[str, Any]) -> None:
        """Настройка репортёра"""
        self._config = config
        self._verbose = config.get('verbose', False)

    async def report_result(self, result: QualityResult) -> None:
        """
        Отчет о результате отдельной проверки

        Args:
            result: Результат проверки
        """
        status_icon = self._get_status_icon(result.status)
        status_color = self._get_status_color(result.status)

        print(f"{status_icon} {result.check_type.value.upper()}: {result.message}")

        if self._verbose and result.details:
            print(f"   Details: {result.details}")

        if result.score is not None:
            score_percent = result.score * 100
            threshold_percent = result.threshold * 100 if result.threshold else 0
            print(f"   Score: {score_percent:.1f}% (threshold: {threshold_percent:.1f}%)")

        print(f"   Execution time: {result.execution_time:.2f}s")
        print()

    async def report_gate_result(self, gate_result: QualityGateResult) -> None:
        """
        Отчет о результате выполнения quality gate

        Args:
            gate_result: Результат выполнения gate
        """
        print(f"{'='*50}")
        print(f"QUALITY GATE REPORT: {gate_result.gate_name.upper()}")
        print(f"{'='*50}")

        print(f"Overall Status: {self._get_status_icon(gate_result.overall_status)} {gate_result.overall_status.value.upper()}")
        print(f"Total Execution Time: {gate_result.execution_time:.2f}s")
        print()

        # Статистика
        passed = len(gate_result.passed_checks)
        failed = len(gate_result.failed_checks)
        warning = len(gate_result.warning_checks)
        total = len(gate_result.results)

        print("Results Summary:")
        print(f"  ✓ Passed: {passed}")
        print(f"  ⚠ Warnings: {warning}")
        print(f"  ✗ Failed: {failed}")
        print(f"  Total checks: {total}")
        print()

        # Детальные результаты
        if gate_result.results:
            print("Detailed Results:")
            for result in gate_result.results:
                await self.report_result(result)

        print(f"{'='*50}")

    async def report_batch_results(self, results: List[QualityResult]) -> None:
        """
        Отчет о результатах нескольких проверок

        Args:
            results: Список результатов проверок
        """
        print(f"{'-'*40}")
        print("BATCH QUALITY CHECK RESULTS")
        print(f"{'-'*40}")

        for result in results:
            await self.report_result(result)

        print(f"{'-'*40}")

    def get_output_destination(self) -> str:
        """Получение места назначения вывода"""
        return "stdout"

    def supports_realtime_reporting(self) -> bool:
        """Поддерживает ли репортёр отчеты в реальном времени"""
        return True

    def _get_status_icon(self, status: QualityStatus) -> str:
        """Получение иконки для статуса"""
        icons = {
            QualityStatus.PASSED: "✅",
            QualityStatus.WARNING: "⚠️",
            QualityStatus.FAILED: "❌",
            QualityStatus.ERROR: "💥",
            QualityStatus.SKIPPED: "⏭️"
        }
        return icons.get(status, "?")

    def _get_status_color(self, status: QualityStatus) -> str:
        """Получение цвета для статуса (для будущей реализации с цветами)"""
        colors = {
            QualityStatus.PASSED: "green",
            QualityStatus.WARNING: "yellow",
            QualityStatus.FAILED: "red",
            QualityStatus.ERROR: "red",
            QualityStatus.SKIPPED: "gray"
        }
        return colors.get(status, "white")