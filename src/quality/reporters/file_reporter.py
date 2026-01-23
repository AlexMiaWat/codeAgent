"""
Файловый репортёр результатов качества
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from ..interfaces import IQualityReporter
from ..models.quality_result import QualityResult, QualityGateResult, QualityStatus

logger = logging.getLogger(__name__)


class FileReporter(IQualityReporter):
    """
    Репортёр для сохранения результатов качества в файл
    """

    def __init__(self):
        self._config = {}
        self._output_file = "quality_report.json"
        self._output_dir = "logs"

    @property
    def name(self) -> str:
        return "File Reporter"

    @property
    def output_format(self) -> str:
        return "json"

    def configure(self, config: Dict[str, Any]) -> None:
        """Настройка репортёра"""
        self._config = config
        self._output_file = config.get('output_file', 'quality_report.json')
        self._output_dir = config.get('output_dir', 'logs')

        # Создаем директорию если не существует
        Path(self._output_dir).mkdir(exist_ok=True)

    async def report_result(self, result: QualityResult) -> None:
        """
        Отчет о результате отдельной проверки

        Args:
            result: Результат проверки
        """
        # Для файлового репортёра результат сохраняется в пакетном режиме
        pass

    async def report_gate_result(self, gate_result: QualityGateResult) -> None:
        """
        Отчет о результате выполнения quality gate

        Args:
            gate_result: Результат выполнения gate
        """
        output_path = Path(self._output_dir) / self._output_file

        try:
            data = gate_result.to_dict()

            # Добавляем метаданные
            data['metadata'] = {
                'reporter': self.name,
                'output_format': self.output_format,
                'generated_at': gate_result.timestamp.isoformat()
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Quality gate report saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to save quality report to {output_path}: {e}")

    async def report_batch_results(self, results: List[QualityResult]) -> None:
        """
        Отчет о результатах нескольких проверок

        Args:
            results: Список результатов проверок
        """
        output_path = Path(self._output_dir) / f"batch_{self._output_file}"

        try:
            data = {
                'batch_results': [r.to_dict() for r in results],
                'summary': {
                    'total_checks': len(results),
                    'passed': len([r for r in results if r.is_passed]),
                    'failed': len([r for r in results if r.is_failed]),
                    'warnings': len([r for r in results if r.is_warning])
                },
                'metadata': {
                    'reporter': self.name,
                    'output_format': self.output_format
                }
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Batch quality report saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to save batch report to {output_path}: {e}")

    def get_output_destination(self) -> str:
        """Получение места назначения вывода"""
        return str(Path(self._output_dir) / self._output_file)

    def supports_realtime_reporting(self) -> bool:
        """Поддерживает ли репортёр отчеты в реальном времени"""
        return False