"""
Проверка доступности ресурсов
"""

import logging
import psutil
from typing import Dict, Any, Optional

from ..interfaces import IQualityChecker
from ..models.quality_result import QualityResult, QualityCheckType, QualityStatus

logger = logging.getLogger(__name__)


class ResourceChecker(IQualityChecker):
    """
    Проверка доступности системных ресурсов
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация чекера ресурсов

        Args:
            config: Конфигурация чекера
        """
        self.config = config or {}
        self.min_cpu_percent = self.config.get('min_cpu_percent', 10.0)  # Минимум свободного CPU
        self.min_memory_percent = self.config.get('min_memory_percent', 20.0)  # Минимум свободной памяти
        self.min_disk_percent = self.config.get('min_disk_percent', 10.0)  # Минимум свободного места на диске
        self.check_cpu = self.config.get('check_cpu', True)
        self.check_memory = self.config.get('check_memory', True)
        self.check_disk = self.config.get('check_disk', True)

    @property
    def name(self) -> str:
        """Имя проверки"""
        return "resource_checker"

    @property
    def check_type(self) -> QualityCheckType:
        """Тип проверки"""
        return QualityCheckType.RESOURCE

    @property
    def description(self) -> str:
        """Описание проверки"""
        return "Checks system resource availability (CPU, memory, disk)"

    def get_default_threshold(self) -> float:
        """Порог по умолчанию"""
        return 0.8

    def is_configurable(self) -> bool:
        """Поддерживает настройку"""
        return True

    def get_supported_file_types(self) -> list[str]:
        """Поддерживаемые типы файлов"""
        return []  # Не зависит от файлов

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации"""
        for key in ['min_cpu_percent', 'min_memory_percent', 'min_disk_percent']:
            if key in config and not isinstance(config[key], (int, float)):
                return False
        for key in ['check_cpu', 'check_memory', 'check_disk']:
            if key in config and not isinstance(config[key], bool):
                return False
        return True

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки ресурсов

        Args:
            context: Контекст выполнения

        Returns:
            Результат проверки
        """
        import time
        start_time = time.time()

        try:
            issues = []
            score = 1.0

            # Проверка CPU
            if self.check_cpu:
                cpu_available = 100.0 - psutil.cpu_percent(interval=1)
                if cpu_available < self.min_cpu_percent:
                    issues.append(f"Low CPU availability: {cpu_available:.1f}% (required: {self.min_cpu_percent}%)")
                    score -= 0.3

            # Проверка памяти
            if self.check_memory:
                memory = psutil.virtual_memory()
                memory_available_percent = 100.0 - memory.percent
                if memory_available_percent < self.min_memory_percent:
                    issues.append(f"Low memory availability: {memory_available_percent:.1f}% (required: {self.min_memory_percent}%)")
                    score -= 0.4

            # Проверка диска
            if self.check_disk:
                project_path = context.get('project_path', '.') if context else '.'
                disk_usage = psutil.disk_usage(project_path)
                disk_available_percent = 100.0 - disk_usage.percent
                if disk_available_percent < self.min_disk_percent:
                    issues.append(f"Low disk space: {disk_available_percent:.1f}% (required: {self.min_disk_percent}%)")
                    score -= 0.3

            # Определение статуса
            if score >= 0.9:
                status = QualityStatus.PASSED
            elif score >= 0.7:
                status = QualityStatus.WARNING
            else:
                status = QualityStatus.FAILED

            message = "Resource check completed"
            if issues:
                message += f" with {len(issues)} issues: " + "; ".join(issues[:2])
                if len(issues) > 2:
                    message += f" and {len(issues) - 2} more"

            return QualityResult(
                check_type=QualityCheckType.RESOURCE,
                status=status,
                message=message,
                score=max(0.0, score),
                execution_time=time.time() - start_time,
                details={
                    'issues': issues,
                    'cpu_available': cpu_available if self.check_cpu else None,
                    'memory_available_percent': memory_available_percent if self.check_memory else None,
                    'disk_available_percent': disk_available_percent if self.check_disk else None
                }
            )

        except Exception as e:
            logger.error(f"Error during resource check: {e}")
            return QualityResult(
                check_type=QualityCheckType.RESOURCE,
                status=QualityStatus.ERROR,
                message=f"Resource check failed: {str(e)}",
                score=0.0,
                execution_time=time.time() - start_time
            )

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка чекера

        Args:
            config: Конфигурация
        """
        self.config.update(config)
        self.min_cpu_percent = self.config.get('min_cpu_percent', 10.0)
        self.min_memory_percent = self.config.get('min_memory_percent', 20.0)
        self.min_disk_percent = self.config.get('min_disk_percent', 10.0)
        self.check_cpu = self.config.get('check_cpu', True)
        self.check_memory = self.config.get('check_memory', True)
        self.check_disk = self.config.get('check_disk', True)