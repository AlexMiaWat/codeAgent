"""
Многоуровневый менеджер верификации результатов
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .interfaces import IMultiLevelVerificationManager
from .execution_monitor import ExecutionMonitor
from .llm_validator import LLMValidator
from src.quality.quality_gate_manager import QualityGateManager
from ..quality.models.quality_result import (
    VerificationResult, MultiLevelVerificationResult, VerificationLevel,
    QualityGateResult, QualityResult, QualityCheckType, QualityStatus
)

logger = logging.getLogger(__name__)


class MultiLevelVerificationManager(IMultiLevelVerificationManager):
    """
    Менеджер многоуровневой верификации результатов выполнения задач
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация менеджера верификации

        Args:
            config: Конфигурация верификации
        """
        self.config = config or {}
        self.verification_config = self.config.get('verification', {})

        # Инициализация компонентов
        self.quality_gate_manager = QualityGateManager(self.verification_config.get('quality_gates', {}))
        self.execution_monitor = ExecutionMonitor(self.verification_config.get('execution_monitor', {}))
        self.llm_validator = LLMValidator(config=self.verification_config.get('llm_validator', {}))

        # Настройки уровней верификации
        self.level_configs = self.verification_config.get('levels', {
            VerificationLevel.PRE_EXECUTION: {
                'enabled': True,
                'weight': 0.2,
                'required_score': 0.7
            },
            VerificationLevel.IN_EXECUTION: {
                'enabled': True,
                'weight': 0.3,
                'required_score': 0.8
            },
            VerificationLevel.POST_EXECUTION: {
                'enabled': True,
                'weight': 0.3,
                'required_score': 0.75
            },
            VerificationLevel.AI_VALIDATION: {
                'enabled': True,
                'weight': 0.2,
                'required_score': 0.6
            },
            VerificationLevel.CROSS_VALIDATION: {
                'enabled': True,
                'weight': 0.0,  # Не влияет на общий скор
                'required_score': 0.0
            }
        })

        self.overall_threshold = self.verification_config.get('overall_threshold', 0.7)

        # Активные верификации
        self.active_verifications: Dict[str, MultiLevelVerificationResult] = {}

    async def run_verification_pipeline(self, task_id: str,
                                       context: Optional[Dict[str, Any]] = None) -> MultiLevelVerificationResult:
        """
        Запуск полного пайплайна верификации

        Args:
            task_id: Идентификатор задачи
            context: Контекст верификации

        Returns:
            Результат многоуровневой верификации
        """
        start_time = datetime.now()
        context = context or {}

        logger.info(f"Starting multi-level verification pipeline for task {task_id}")

        # Инициализируем результат верификации
        verification_result = MultiLevelVerificationResult(task_id=task_id)
        self.active_verifications[task_id] = verification_result

        try:
            # Уровень 1: Pre-execution verification
            if self._is_level_enabled(VerificationLevel.PRE_EXECUTION):
                pre_result = await self.run_pre_execution_checks(task_id, context)
                verification_result.add_verification_result(pre_result)

            # Уровень 2: In-execution monitoring
            if self._is_level_enabled(VerificationLevel.IN_EXECUTION):
                in_result = await self.run_in_execution_monitoring(task_id, context)
                verification_result.add_verification_result(in_result)

            # Уровень 3: Post-execution validation
            if self._is_level_enabled(VerificationLevel.POST_EXECUTION):
                post_result = await self.run_post_execution_validation(task_id, context.get('execution_result', {}), context)
                verification_result.add_verification_result(post_result)

            # Уровень 4: AI validation
            if self._is_level_enabled(VerificationLevel.AI_VALIDATION):
                ai_result = await self.run_ai_validation(task_id, context.get('analysis_data', {}), context)
                verification_result.add_verification_result(ai_result)

            # Уровень 5: Cross-validation
            if self._is_level_enabled(VerificationLevel.CROSS_VALIDATION):
                cross_result = await self.run_cross_validation(verification_result.results_by_level, context)
                verification_result.add_verification_result(cross_result)

            # Финализация
            verification_result.execution_time = (datetime.now() - start_time).total_seconds()
            verification_result.cross_validation_score = self._calculate_cross_validation_score(verification_result)

            logger.info(f"Multi-level verification completed for task {task_id}: "
                       f"overall_score={verification_result.overall_score:.2f}, "
                       f"successful={verification_result.is_successful}")

        except Exception as e:
            logger.error(f"Error in verification pipeline for task {task_id}: {e}")
            verification_result.execution_time = (datetime.now() - start_time).total_seconds()

        finally:
            # Очищаем активную верификацию
            if task_id in self.active_verifications:
                del self.active_verifications[task_id]

        return verification_result

    async def run_pre_execution_checks(self, task_id: str,
                                      context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Выполнение проверок перед выполнением

        Args:
            task_id: Идентификатор задачи
            context: Контекст выполнения

        Returns:
            Результат pre-execution верификации
        """
        start_time = datetime.now()
        context = context or {}

        logger.debug(f"Running pre-execution checks for task {task_id}")

        try:
            # Определяем, какие чекеры запускать для pre-execution
            pre_execution_checks = [
                QualityCheckType.COVERAGE,
                QualityCheckType.COMPLEXITY,
                QualityCheckType.SECURITY,
                QualityCheckType.STYLE,
                QualityCheckType.TASK_TYPE,
                QualityCheckType.DEPENDENCY,
                QualityCheckType.RESOURCE,
                QualityCheckType.CONFIGURATION
            ]

            # Запускаем проверки
            gate_result = await self.quality_gate_manager.run_specific_gates(pre_execution_checks, context)

            return VerificationResult(
                task_id=task_id,
                verification_level=VerificationLevel.PRE_EXECUTION,
                quality_result=gate_result,
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={'checks_run': len(gate_result.results)}
            )

        except Exception as e:
            logger.error(f"Error in pre-execution checks for task {task_id}: {e}")
            return self._create_error_verification_result(
                task_id, VerificationLevel.PRE_EXECUTION, str(e), start_time
            )

    async def run_in_execution_monitoring(self, task_id: str,
                                         context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Мониторинг выполнения задачи

        Args:
            task_id: Идентификатор задачи
            context: Контекст выполнения

        Returns:
            Результат in-execution верификации
        """
        start_time = datetime.now()
        context = context or {}

        logger.debug(f"Running in-execution monitoring for task {task_id}")

        try:
            # Начинаем мониторинг
            await self.execution_monitor.start_monitoring(task_id, context)

            # Имитируем ожидание выполнения (в реальности это будет интегрировано в процесс выполнения)
            # Здесь мы просто проверяем здоровье выполнения
            health_status = await self.execution_monitor.check_execution_health(task_id)

            # Создаем результат на основе статуса здоровья
            score = 1.0 if health_status.get('healthy', False) else 0.5

            if health_status.get('healthy', False):
                status = QualityStatus.PASSED
                message = "Execution monitoring completed successfully"
            else:
                status = QualityStatus.WARNING
                issues = health_status.get('issues', [])
                message = f"Execution monitoring found issues: {', '.join(issues[:3])}"

            quality_result = QualityResult(
                check_type=QualityCheckType.PROGRESS,
                status=status,
                message=message,
                score=score,
                details=health_status
            )

            gate_result = QualityGateResult(
                gate_name="in_execution_monitoring",
                results=[quality_result]
            )

            return VerificationResult(
                task_id=task_id,
                verification_level=VerificationLevel.IN_EXECUTION,
                quality_result=gate_result,
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={'monitoring_active': True, 'health_status': health_status}
            )

        except Exception as e:
            logger.error(f"Error in in-execution monitoring for task {task_id}: {e}")
            return self._create_error_verification_result(
                task_id, VerificationLevel.IN_EXECUTION, str(e), start_time
            )

    async def run_post_execution_validation(self, task_id: str,
                                           execution_result: Dict[str, Any],
                                           context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Валидация после выполнения

        Args:
            task_id: Идентификатор задачи
            execution_result: Результат выполнения
            context: Контекст валидации

        Returns:
            Результат post-execution верификации
        """
        start_time = datetime.now()
        context = context or {}

        logger.debug(f"Running post-execution validation for task {task_id}")

        try:
            # Определяем пост-выполнение чекеры
            post_execution_checks = [
                QualityCheckType.OUTPUT_VALIDATION,
                QualityCheckType.CODE_CHANGE,
                QualityCheckType.TEST_EXECUTION,
                QualityCheckType.PERFORMANCE
            ]

            # Добавляем контекст выполнения
            validation_context = {**context, 'execution_result': execution_result}

            # Запускаем проверки
            gate_result = await self.quality_gate_manager.run_specific_gates(post_execution_checks, validation_context)

            return VerificationResult(
                task_id=task_id,
                verification_level=VerificationLevel.POST_EXECUTION,
                quality_result=gate_result,
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={'execution_result_keys': list(execution_result.keys())}
            )

        except Exception as e:
            logger.error(f"Error in post-execution validation for task {task_id}: {e}")
            return self._create_error_verification_result(
                task_id, VerificationLevel.POST_EXECUTION, str(e), start_time
            )

    async def run_ai_validation(self, task_id: str, analysis_data: Dict[str, Any],
                               context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        AI-based валидация результатов

        Args:
            task_id: Идентификатор задачи
            analysis_data: Данные для анализа
            context: Контекст валидации

        Returns:
            Результат AI валидации
        """
        start_time = datetime.now()
        context = context or {}

        logger.debug(f"Running AI validation for task {task_id}")

        try:
            # Запускаем разные типы AI валидации параллельно
            validation_tasks = []

            if 'code_changes' in analysis_data:
                # Валидация качества кода
                validation_tasks.append(
                    self.llm_validator.validate_code_quality(analysis_data, context)
                )

                # Валидация логики
                validation_tasks.append(
                    self.llm_validator.validate_logic_correctness(analysis_data, context)
                )

            if 'task_description' in analysis_data and 'execution_result' in analysis_data:
                # Валидация соответствия задаче
                validation_tasks.append(
                    self.llm_validator.validate_task_compliance(
                        analysis_data['task_description'],
                        analysis_data['execution_result'],
                        context
                    )
                )

            if not validation_tasks:
                # Если нет данных для анализа, возвращаем пропуск
                return VerificationResult(
                    task_id=task_id,
                    verification_level=VerificationLevel.AI_VALIDATION,
                    quality_result=QualityGateResult(
                        gate_name="ai_validation_skipped",
                        results=[QualityResult(
                            check_type=QualityCheckType.CODE_QUALITY_AI,
                            status=QualityStatus.SKIPPED,
                            message="No analysis data provided for AI validation",
                            score=0.5
                        )]
                    ),
                    execution_time=(datetime.now() - start_time).total_seconds()
                )

            # Выполняем все AI валидации
            ai_results = await asyncio.gather(*validation_tasks, return_exceptions=True)

            # Агрегируем результаты
            all_results = []
            total_score = 0.0
            valid_results = 0

            for result in ai_results:
                if isinstance(result, Exception):
                    logger.warning(f"AI validation task failed: {result}")
                    continue

                if isinstance(result, VerificationResult):
                    all_results.extend(result.quality_result.results)
                    if result.overall_score is not None:
                        total_score += result.overall_score
                        valid_results += 1

            # Создаем агрегированный результат
            avg_score = total_score / valid_results if valid_results > 0 else 0.0

            gate_result = QualityGateResult(
                gate_name="ai_validation_aggregated",
                results=all_results
            )

            return VerificationResult(
                task_id=task_id,
                verification_level=VerificationLevel.AI_VALIDATION,
                quality_result=gate_result,
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    'ai_validations_run': len(validation_tasks),
                    'valid_results': valid_results,
                    'average_score': avg_score
                }
            )

        except Exception as e:
            logger.error(f"Error in AI validation for task {task_id}: {e}")
            return self._create_error_verification_result(
                task_id, VerificationLevel.AI_VALIDATION, str(e), start_time
            )

    async def run_cross_validation(self, verification_results: Dict[str, VerificationResult],
                                  context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Кросс-валидация результатов между уровнями

        Args:
            verification_results: Результаты верификации по уровням
            context: Контекст валидации

        Returns:
            Результат кросс-валидации
        """
        start_time = datetime.now()

        logger.debug("Running cross-validation between verification levels")

        try:
            issues = []
            consistency_score = 1.0

            # Проверяем согласованность результатов между уровнями
            pre_result = verification_results.get(VerificationLevel.PRE_EXECUTION.value)
            in_result = verification_results.get(VerificationLevel.IN_EXECUTION.value)
            post_result = verification_results.get(VerificationLevel.POST_EXECUTION.value)
            ai_result = verification_results.get(VerificationLevel.AI_VALIDATION.value)

            # Проверка согласованности pre-execution и post-execution
            if pre_result and post_result:
                pre_score = pre_result.overall_score or 0
                post_score = post_result.overall_score or 0

                if abs(pre_score - post_score) > 0.3:
                    issues.append("Significant discrepancy between pre and post execution scores")
                    consistency_score -= 0.2

            # Проверка согласованности AI и других результатов
            if ai_result and post_result:
                ai_score = ai_result.overall_score or 0
                post_score = post_result.overall_score or 0

                if abs(ai_score - post_score) > 0.4:
                    issues.append("AI validation score differs significantly from post-execution results")
                    consistency_score -= 0.3

            # Проверка на неожиданные провалы
            if in_result and in_result.quality_result.has_errors():
                if post_result and not post_result.quality_result.has_errors():
                    issues.append("In-execution errors not reflected in post-execution results")
                    consistency_score -= 0.1

            # Определяем статус
            if consistency_score >= 0.9 and not issues:
                status = QualityStatus.PASSED
                message = "Cross-validation passed with high consistency"
            elif consistency_score >= 0.7:
                status = QualityStatus.WARNING
                message = f"Cross-validation completed with minor inconsistencies: {len(issues)} issues"
            else:
                status = QualityStatus.FAILED
                message = f"Cross-validation failed with consistency score {consistency_score:.2f}"

            quality_result = QualityResult(
                check_type=QualityCheckType.CONSISTENCY_CHECK,
                status=status,
                message=message,
                score=consistency_score,
                details={
                    'issues': issues,
                    'levels_compared': list(verification_results.keys()),
                    'consistency_analysis': {
                        'pre_post_diff': abs((pre_result.overall_score or 0) - (post_result.overall_score or 0)) if pre_result and post_result else None,
                        'ai_post_diff': abs((ai_result.overall_score or 0) - (post_result.overall_score or 0)) if ai_result and post_result else None
                    }
                }
            )

            gate_result = QualityGateResult(
                gate_name="cross_validation",
                results=[quality_result]
            )

            return VerificationResult(
                task_id=list(verification_results.values())[0].task_id if verification_results else "cross_validation",
                verification_level=VerificationLevel.CROSS_VALIDATION,
                quality_result=gate_result,
                execution_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    'levels_analyzed': len(verification_results),
                    'consistency_score': consistency_score,
                    'cross_validation_issues': issues
                }
            )

        except Exception as e:
            logger.error(f"Error in cross-validation: {e}")
            return self._create_error_verification_result(
                "cross_validation", VerificationLevel.CROSS_VALIDATION, str(e), start_time
            )

    def _is_level_enabled(self, level: VerificationLevel) -> bool:
        """Проверка включен ли уровень верификации"""
        return self.level_configs.get(level, {}).get('enabled', False)

    def _calculate_cross_validation_score(self, verification_result: MultiLevelVerificationResult) -> float:
        """Расчет скора кросс-валидации"""
        # Простая логика: проверяем согласованность результатов
        scores = []
        for result in verification_result.results_by_level.values():
            if result.overall_score is not None:
                scores.append(result.overall_score)

        if len(scores) < 2:
            return 0.5  # Недостаточно данных для кросс-валидации

        # Вычисляем стандартное отклонение как меру несогласованности
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5

        # Чем меньше разброс, тем выше скор кросс-валидации
        cross_score = max(0.0, 1.0 - std_dev)
        return cross_score

    def _create_error_verification_result(self, task_id: str, level: VerificationLevel,
                                        error: str, start_time: datetime) -> VerificationResult:
        """Создание результата ошибки верификации"""
        return VerificationResult(
            task_id=task_id,
            verification_level=level,
            quality_result=QualityGateResult(
                gate_name=f"{level.value}_error",
                results=[QualityResult(
                    check_type=QualityCheckType.COVERAGE,  # placeholder
                    status=QualityStatus.ERROR,
                    message=f"Verification failed: {error}",
                    score=0.0
                )]
            ),
            execution_time=(datetime.now() - start_time).total_seconds(),
            metadata={'error': error}
        )

    def get_active_verifications(self) -> List[str]:
        """Получение списка активных верификаций"""
        return list(self.active_verifications.keys())

    def get_verification_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получение статуса верификации задачи"""
        if task_id not in self.active_verifications:
            return None

        verification = self.active_verifications[task_id]
        return {
            'task_id': task_id,
            'levels_completed': list(verification.results_by_level.keys()),
            'current_score': verification.overall_score,
            'execution_time': verification.execution_time,
            'is_successful': verification.is_successful
        }