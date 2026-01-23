"""
Реализация Quality Gate Manager
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .interfaces import IQualityGateManager
from .models.quality_result import QualityGateResult, QualityResult, QualityCheckType, QualityStatus
from .checkers import CoverageChecker, ComplexityChecker, SecurityChecker, StyleChecker, TaskTypeChecker

logger = logging.getLogger(__name__)


class QualityGateManager(IQualityGateManager):
    """
    Базовая реализация менеджера quality gates.
    Координирует выполнение всех типов проверок качества.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация Quality Gate Manager

        Args:
            config: Конфигурация quality gates
        """
        self._config = config or {}
        self._enabled_gates: Dict[QualityCheckType, bool] = {}
        self._gate_configs: Dict[QualityCheckType, Dict[str, Any]] = {}

        # Инициализация чекеров
        self._checkers = {
            QualityCheckType.COVERAGE: CoverageChecker(),
            QualityCheckType.COMPLEXITY: ComplexityChecker(),
            QualityCheckType.SECURITY: SecurityChecker(),
            QualityCheckType.STYLE: StyleChecker(),
            QualityCheckType.TASK_TYPE: TaskTypeChecker()
        }

        # Настройка по умолчанию
        self._setup_default_configuration()

    def _setup_default_configuration(self):
        """Настройка конфигурации по умолчанию"""
        default_config = {
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {
                    'enabled': True,
                    'min_coverage': 80.0,
                    'required_for': ['production', 'release']
                },
                'complexity': {
                    'enabled': True,
                    'max_complexity': 10,
                    'fail_on_exceed': True
                },
                'security': {
                    'enabled': True,
                    'scan_dependencies': True,
                    'check_vulnerabilities': True
                },
                'style': {
                    'enabled': True,
                    'tools': ['ruff', 'mypy', 'bandit']
                },
                'task_type': {
                    'enabled': True,
                    'max_untyped_percentage': 0.3,
                    'min_typed_percentage': 0.7,
                    'check_distribution': True
                }
            }
        }

        # Объединяем с предоставленной конфигурацией
        self._config = {**default_config, **self._config}

        # Настраиваем gates
        for gate_name, gate_config in self._config.get('gates', {}).items():
            try:
                gate_type = QualityCheckType[gate_name.upper()]
                self._enabled_gates[gate_type] = gate_config.get('enabled', True)
                self._gate_configs[gate_type] = gate_config
            except KeyError:
                logger.warning(f"Unknown quality gate type: {gate_name}")

        # Настраиваем чекеры
        for gate_type, checker in self._checkers.items():
            gate_config = self._gate_configs.get(gate_type, {})
            try:
                checker.configure(gate_config)
            except Exception as e:
                logger.error(f"Failed to configure checker {gate_type}: {e}")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настройка менеджера quality gates

        Args:
            config: Общая конфигурация quality gates
        """
        self._config.update(config)
        self._setup_default_configuration()
        logger.info("Quality Gate Manager configured")

    async def run_all_gates(self, context: Optional[Dict[str, Any]] = None) -> QualityGateResult:
        """
        Выполнение всех активных quality gates

        Args:
            context: Контекст выполнения

        Returns:
            Агрегированный результат всех gates
        """
        enabled_gates = [gt for gt in self._enabled_gates if self._enabled_gates[gt]]
        return await self.run_specific_gates(enabled_gates, context)

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
        gate_result = QualityGateResult(gate_name="all_gates")
        start_time = datetime.now()

        # Выполняем все указанные gates параллельно
        tasks = []
        for gate_type in gate_types:
            if gate_type in self._checkers:
                checker = self._checkers[gate_type]
                task = self._run_single_checker(checker, context)
                tasks.append((gate_type, task))

        # Собираем результаты
        for gate_type, task in tasks:
            try:
                result = await task
                gate_result.add_result(result)
                logger.debug(f"Gate {gate_type.value} completed with status: {result.status.value}")
            except Exception as e:
                error_result = QualityResult(
                    check_type=gate_type,
                    status=QualityStatus.ERROR,
                    message=f"Failed to run {gate_type.value} checker: {str(e)}",
                    execution_time=0.0
                )
                gate_result.add_result(error_result)
                logger.error(f"Error running gate {gate_type.value}: {e}")

        gate_result.execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"All quality gates completed in {gate_result.execution_time:.2f}s")

        return gate_result

    async def run_specific_gates(
        self,
        gate_types: List[QualityCheckType],
        context: Optional[Dict[str, Any]] = None
    ) -> QualityGateResult:
        """
        Запуск только указанных quality gates

        Args:
            gate_types: Список типов gates для запуска
            context: Контекст для чекеров

        Returns:
            Результат выполнения quality gates
        """
        start_time = datetime.now()
        gate_result = QualityGateResult()

        logger.debug(f"Running specific quality gates: {[gt.value for gt in gate_types]}")

        # Создаем задачи только для указанных типов
        tasks = []
        for gate_type in gate_types:
            if gate_type in self._checkers and self._enabled_gates.get(gate_type, False):
                checker = self._checkers[gate_type]
                task = asyncio.create_task(self._run_single_checker(checker, context))
                tasks.append((gate_type, task))

        # Выполняем задачи параллельно
        if tasks:
            for gate_type, task in tasks:
                try:
                    result = await task
                    gate_result.add_result(result)
                    logger.debug(f"Gate {gate_type.value} completed with status: {result.status.value}")
                except Exception as e:
                    error_result = QualityResult(
                        check_type=gate_type,
                        status=QualityStatus.ERROR,
                        message=f"Failed to run {gate_type.value} checker: {str(e)}",
                        execution_time=0.0
                    )
                    gate_result.add_result(error_result)
                    logger.error(f"Error running gate {gate_type.value}: {e}")

        gate_result.execution_time = (datetime.now() - start_time).total_seconds()
        logger.debug(f"Specific quality gates completed in {gate_result.execution_time:.2f}s")

        return gate_result

    async def _run_single_checker(self, checker, context: Optional[Dict[str, Any]] = None) -> QualityResult:
        """Выполнение отдельного чекера"""
        return await checker.check(context)

    def enable_gate(self, gate_type: QualityCheckType) -> None:
        """
        Включение quality gate

        Args:
            gate_type: Тип gate для включения
        """
        self._enabled_gates[gate_type] = True
        logger.info(f"Quality gate {gate_type.value} enabled")

    def disable_gate(self, gate_type: QualityCheckType) -> None:
        """
        Отключение quality gate

        Args:
            gate_type: Тип gate для отключения
        """
        self._enabled_gates[gate_type] = False
        logger.info(f"Quality gate {gate_type.value} disabled")

    def is_gate_enabled(self, gate_type: QualityCheckType) -> bool:
        """
        Проверка включен ли gate

        Args:
            gate_type: Тип gate

        Returns:
            True если gate включен
        """
        return self._enabled_gates.get(gate_type, False)

    def get_enabled_gates(self) -> List[QualityCheckType]:
        """
        Получение списка включенных gates

        Returns:
            Список включенных типов gates
        """
        return [gt for gt in self._enabled_gates if self._enabled_gates[gt]]

    def get_gate_configuration(self, gate_type: QualityCheckType) -> Optional[Dict[str, Any]]:
        """
        Получение конфигурации конкретного gate

        Args:
            gate_type: Тип gate

        Returns:
            Конфигурация gate или None если gate не найден
        """
        return self._gate_configs.get(gate_type)

    def update_gate_configuration(self, gate_type: QualityCheckType,
                                 config: Dict[str, Any]) -> None:
        """
        Обновление конфигурации gate

        Args:
            gate_type: Тип gate
            config: Новая конфигурация
        """
        if gate_type in self._gate_configs:
            self._gate_configs[gate_type].update(config)
            # Перенастраиваем чекер
            if gate_type in self._checkers:
                self._checkers[gate_type].configure(self._gate_configs[gate_type])
            logger.info(f"Configuration updated for gate {gate_type.value}")

    def should_block_execution(self, gate_result: QualityGateResult) -> bool:
        """
        Определение нужно ли блокировать выполнение на основе результатов

        Args:
            gate_result: Результат выполнения gates

        Returns:
            True если выполнение должно быть заблокировано
        """
        if not self._config.get('strict_mode', False):
            return False

        # В strict mode блокируем если есть failed или error результаты
        return gate_result.overall_status in (QualityStatus.FAILED, QualityStatus.ERROR)

    def get_overall_quality_score(self, gate_result: QualityGateResult) -> float:
        """
        Вычисление общего скора качества (0.0 - 1.0)

        Args:
            gate_result: Результат выполнения gates

        Returns:
            Общий скор качества
        """
        if not gate_result.results:
            return 0.0

        # Средний скор по всем результатам
        scores = []
        for result in gate_result.results:
            if result.score is not None:
                scores.append(result.score)

        if not scores:
            # Если нет скоринга, конвертируем статус в скор
            status_scores = {
                QualityStatus.PASSED: 1.0,
                QualityStatus.WARNING: 0.7,
                QualityStatus.FAILED: 0.3,
                QualityStatus.ERROR: 0.0,
                QualityStatus.SKIPPED: 0.5
            }
            scores = [status_scores.get(r.status, 0.5) for r in gate_result.results]

        return sum(scores) / len(scores) if scores else 0.0