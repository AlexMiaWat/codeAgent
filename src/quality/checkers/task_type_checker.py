"""
Task Type Checker - проверка корректности типов задач
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..interfaces.iquality_checker import IQualityChecker
from ..models.quality_result import QualityResult, QualityCheckType, QualityStatus

logger = logging.getLogger(__name__)


class TaskTypeChecker(IQualityChecker):
    """
    Проверка корректности типов задач в проекте.

    Проверяет:
    - Все ли задачи имеют корректные типы
    - Не слишком ли много задач без типов
    - Сбалансировано ли распределение типов задач
    """

    def __init__(self):
        self._config = {
            'max_untyped_percentage': 0.3,  # Максимум 30% задач без типа
            'min_typed_percentage': 0.7,    # Минимум 70% задач с типами
            'check_distribution': True,     # Проверять распределение типов
        }

    @property
    def name(self) -> str:
        """Имя проверки"""
        return "Task Type Checker"

    @property
    def check_type(self) -> QualityCheckType:
        """Тип проверки"""
        return QualityCheckType.TASK_TYPE

    @property
    def description(self) -> str:
        """Описание проверки"""
        return "Проверяет корректность и распределение типов задач в проекте"

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка проверки типов задач

        Args:
            config: Конфигурация с параметрами:
                - max_untyped_percentage: Максимальный процент задач без типа (0.0-1.0)
                - min_typed_percentage: Минимальный процент задач с типами (0.0-1.0)
                - check_distribution: Проверять ли распределение типов
        """
        if 'max_untyped_percentage' in config:
            value = config['max_untyped_percentage']
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"max_untyped_percentage must be between 0.0 and 1.0, got {value}")
            self._config['max_untyped_percentage'] = value

        if 'min_typed_percentage' in config:
            value = config['min_typed_percentage']
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"min_typed_percentage must be between 0.0 and 1.0, got {value}")
            self._config['min_typed_percentage'] = value

        if 'check_distribution' in config:
            self._config['check_distribution'] = bool(config['check_distribution'])

    async def check(self, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """
        Выполнение проверки типов задач

        Args:
            context: Контекст с информацией о задачах проекта

        Returns:
            Результат проверки типов задач
        """
        start_time = datetime.now()

        try:
            # Получаем информацию о задачах из контекста
            if not context or 'todo_manager' not in context:
                return QualityResult(
                    check_type=self.check_type,
                    status=QualityStatus.ERROR,
                    message="TodoManager не предоставлен в контексте",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )

            todo_manager = context['todo_manager']

            # Получаем статистику по типам задач
            stats = todo_manager.get_task_type_statistics()

            total_tasks = stats['total_tasks']

            if total_tasks == 0:
                return QualityResult(
                    check_type=self.check_type,
                    status=QualityStatus.SKIPPED,
                    message="Нет задач для проверки типов",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )

            # Вычисляем метрики
            untyped_percentage = stats['untyped_percentage'] / 100.0  # Конвертируем в 0.0-1.0
            typed_percentage = 1.0 - untyped_percentage

            issues = []
            score = 1.0

            # Проверяем процент нетипизированных задач
            max_untyped = self._config['max_untyped_percentage']
            if untyped_percentage > max_untyped:
                issues.append(
                    ".1f"
                    ".1f"
                )
                # Уменьшаем score пропорционально превышению
                excess = (untyped_percentage - max_untyped) / max_untyped
                score -= min(0.5, excess * 0.5)

            # Проверяем минимальный процент типизированных задач
            min_typed = self._config['min_typed_percentage']
            if typed_percentage < min_typed:
                issues.append(
                    ".1f"
                    ".1f"
                )
                # Уменьшаем score пропорционально недостатку
                deficit = (min_typed - typed_percentage) / min_typed
                score -= min(0.3, deficit * 0.3)

            # Проверяем распределение типов (опционально)
            if self._config['check_distribution']:
                distribution_issues = self._check_type_distribution(stats)
                issues.extend(distribution_issues)
                if distribution_issues:
                    score -= min(0.2, len(distribution_issues) * 0.1)

            # Определяем статус на основе score
            if score >= 0.8:
                status = QualityStatus.PASSED
            elif score >= 0.6:
                status = QualityStatus.WARNING
            else:
                status = QualityStatus.FAILED

            # Формируем сообщение
            if issues:
                message = f"Найдены проблемы с типами задач: {'; '.join(issues)}"
            else:
                message = ".1f"

            return QualityResult(
                check_type=self.check_type,
                status=status,
                message=message,
                score=max(0.0, score),  # Убеждаемся, что score не отрицательный
                threshold=0.8,  # Порог для PASSED
                execution_time=(datetime.now() - start_time).total_seconds(),
                details={
                    'total_tasks': total_tasks,
                    'typed_tasks': stats.get('untyped_tasks', 0),
                    'untyped_tasks': stats['untyped_tasks'],
                    'untyped_percentage': stats['untyped_percentage'],
                    'type_distribution': stats.get('types', {}),
                    'issues': issues
                }
            )

        except Exception as e:
            logger.error(f"Ошибка при проверке типов задач: {e}")
            return QualityResult(
                check_type=self.check_type,
                status=QualityStatus.ERROR,
                message=f"Ошибка при проверке типов задач: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def _check_type_distribution(self, stats: Dict[str, Any]) -> List[str]:
        """
        Проверяет распределение типов задач на сбалансированность

        Args:
            stats: Статистика по типам задач

        Returns:
            Список проблем с распределением
        """
        issues = []
        type_distribution = stats.get('types', {})

        if not type_distribution:
            return issues

        total_typed = sum(type_info['count'] for type_info in type_distribution.values())

        # Проверяем, нет ли типов с экстремально низким или высоким процентом
        for type_name, type_info in type_distribution.items():
            percentage = type_info['percentage'] / 100.0  # Конвертируем в 0.0-1.0

            # Если тип составляет более 70% всех задач - это может быть проблемой
            if percentage > 0.7:
                issues.append(
                    ".1f"
                )
            # Если тип составляет менее 1% всех задач - это может быть проблемой
            elif percentage < 0.01 and total_typed > 10:
                issues.append(
                    ".1f"
                )

        return issues

    def get_default_threshold(self) -> float:
        """Порог по умолчанию"""
        return 0.8

    def is_configurable(self) -> bool:
        """Проверка поддерживает настройку"""
        return True

    def get_supported_file_types(self) -> List[str]:
        """Не зависит от типов файлов"""
        return []

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации

        Args:
            config: Конфигурация для проверки

        Returns:
            True если конфигурация валидна
        """
        try:
            # Проверяем числовые параметры
            if 'max_untyped_percentage' in config:
                value = config['max_untyped_percentage']
                if not (0.0 <= value <= 1.0):
                    return False

            if 'min_typed_percentage' in config:
                value = config['min_typed_percentage']
                if not (0.0 <= value <= 1.0):
                    return False

            # Проверяем логические параметры
            if 'check_distribution' in config:
                if not isinstance(config['check_distribution'], bool):
                    return False

            return True

        except (TypeError, ValueError):
            return False