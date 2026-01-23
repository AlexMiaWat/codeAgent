"""
Проверка прогресса выполнения задачи
"""

import logging
import time
from typing import Dict, Any, Optional

from ..interfaces import IQualityChecker
from ..models.quality_result import QualityResult, QualityCheckType, QualityStatus

logger = logging.getLogger(__name__)


class ProgressChecker(IQualityChecker):
    """
    Проверка прогресса выполнения задачи (используется во время выполнения)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация чекера прогресса

        Args:
            config: Конфигурация чекера
        """
        self.config = config or {}
        self.max_execution_time = self.config.get('max_execution_time', 300)  # Максимальное время выполнения в секундах
        self.progress_timeout = self.config.get('progress_timeout', 60)  # Таймаут без прогресса
        self.check_deadlines = self.config.get('check_deadlines', True)

    @property
    def name(self) -> str:
        """Имя проверки"""
        return "progress_checker"

    @property
    def check_type(self) -> QualityCheckType:
        """Тип проверки"""
        return QualityCheckType.PROGRESS

    @property
    def description(self) -> str:
        """Описание проверки"""
        return "Checks task execution progress and detects stalls"

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
        for key in ['max_execution_time', 'progress_timeout']:
            if key in config and not isinstance(config[key], (int, float)):
                return False
        if 'check_deadlines' in config and not isinstance(config['check_deadlines'], bool):
            return False
        return True
        self.check_stuck_processes = self.config.get('check_stuck_processes', True)

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки прогресса

        Args:
            context: Контекст выполнения (должен содержать информацию о задаче)

        Returns:
            Результат проверки
        """
        start_time = time.time()

        try:
            if not context:
                return QualityResult(
                    check_type=QualityCheckType.PROGRESS,
                    status=QualityStatus.SKIPPED,
                    message="No context provided for progress check",
                    score=0.5,
                    execution_time=time.time() - start_time
                )

            issues = []
            score = 1.0

            # Проверка времени выполнения
            task_start_time = context.get('task_start_time')
            if task_start_time and self.check_deadlines:
                execution_time = time.time() - task_start_time
                if execution_time > self.max_execution_time:
                    issues.append(f"Task execution time exceeded: {execution_time:.1f}s > {self.max_execution_time}s")
                    score -= 0.5

            # Проверка наличия прогресса
            last_progress_time = context.get('last_progress_time')
            if last_progress_time and self.check_stuck_processes:
                time_since_progress = time.time() - last_progress_time
                if time_since_progress > self.progress_timeout:
                    issues.append(f"No progress for {time_since_progress:.1f}s (timeout: {self.progress_timeout}s)")
                    score -= 0.4

            # Проверка статуса задачи
            task_status = context.get('task_status', 'unknown')
            if task_status == 'stuck':
                issues.append("Task appears to be stuck")
                score -= 0.6
            elif task_status == 'error':
                issues.append("Task encountered an error")
                score -= 0.8

            # Определение статуса
            if score >= 0.8:
                status = QualityStatus.PASSED
            elif score >= 0.5:
                status = QualityStatus.WARNING
            else:
                status = QualityStatus.FAILED

            message = "Progress check completed"
            if issues:
                message += f" with {len(issues)} issues: " + "; ".join(issues[:2])
                if len(issues) > 2:
                    message += f" and {len(issues) - 2} more"

            return QualityResult(
                check_type=QualityCheckType.PROGRESS,
                status=status,
                message=message,
                score=max(0.0, score),
                execution_time=time.time() - start_time,
                details={
                    'issues': issues,
                    'execution_time': execution_time if task_start_time else None,
                    'time_since_progress': time_since_progress if last_progress_time else None,
                    'task_status': task_status
                }
            )

        except Exception as e:
            logger.error(f"Error during progress check: {e}")
            return QualityResult(
                check_type=QualityCheckType.PROGRESS,
                status=QualityStatus.ERROR,
                message=f"Progress check failed: {str(e)}",
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
        self.max_execution_time = self.config.get('max_execution_time', 300)
        self.progress_timeout = self.config.get('progress_timeout', 60)
        self.check_deadlines = self.config.get('check_deadlines', True)
        self.check_stuck_processes = self.config.get('check_stuck_processes', True)