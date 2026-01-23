"""
AdaptiveStrategyManager - адаптивный менеджер стратегий генерации

Ответственность:
- Автоматическое переключение между стратегиями на основе контекста
- Адаптация к производительности и обратной связи
- Оптимизация стратегий для различных типов задач
- Обучение на исторических данных
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter

from .types import (
    ModelConfig, ModelResponse, ModelRole,
    GenerationRequest, EvaluationResult,
    IAdaptiveStrategyManager, IModelRegistry, IClientManager,
    IResponseEvaluator, IJsonValidator, IIntelligentRouter
)
from .strategy import StrategyManager

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Типы стратегий генерации"""
    SINGLE = "single"                    # Одна модель
    PARALLEL = "parallel"                # Параллельная генерация (best_of_two)
    FALLBACK = "fallback"                # Fallback цепочка
    ADAPTIVE = "adaptive"                # Адаптивная (выбирается автоматически)
    CONSENSUS = "consensus"              # Консенсус нескольких моделей
    ITERATIVE = "iterative"              # Итеративное улучшение


class AdaptationTrigger(Enum):
    """Триггеры для адаптации стратегии"""
    LOW_SUCCESS_RATE = "low_success_rate"      # Низкая успешность
    HIGH_LATENCY = "high_latency"             # Высокая задержка
    LOW_QUALITY = "low_quality"               # Низкое качество ответов
    TASK_TYPE_CHANGE = "task_type_change"     # Изменение типа задачи
    ERROR_PATTERN = "error_pattern"           # Паттерны ошибок
    PERFORMANCE_DEGRADATION = "performance_degradation"  # Снижение производительности


@dataclass
class StrategyPerformance:
    """Производительность стратегии для конкретного типа задач"""
    strategy: StrategyType
    task_type: str  # Из IntelligentRouter.TaskType
    avg_score: float = 0.0
    avg_response_time: float = 0.0
    success_rate: float = 0.0
    sample_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    adaptation_count: int = 0


@dataclass
class StrategyDecision:
    """Решение о выборе стратегии"""
    strategy: StrategyType
    confidence: float
    reasoning: str
    expected_score: float = 0.0
    expected_latency: float = 0.0
    alternatives: List[StrategyType] = field(default_factory=list)


@dataclass
class AdaptationContext:
    """Контекст для адаптации стратегии"""
    trigger: AdaptationTrigger
    current_strategy: StrategyType
    performance_metrics: Dict[str, float]
    task_characteristics: Dict[str, Any]
    historical_performance: List[StrategyPerformance]
    timestamp: datetime = field(default_factory=datetime.now)


class AdaptiveStrategyManager(IAdaptiveStrategyManager):
    """
    Адаптивный менеджер стратегий - автоматически выбирает и адаптирует стратегии генерации

    Предоставляет:
    - Автоматический выбор стратегии на основе контекста
    - Адаптацию к производительности и обратной связи
    - Обучение на исторических данных
    - Оптимизацию для различных типов задач
    """

    def __init__(
        self,
        registry: IModelRegistry,
        client_manager: IClientManager,
        evaluator: IResponseEvaluator,
        json_validator: IJsonValidator,
        intelligent_router: IIntelligentRouter
    ):
        """
        Инициализация адаптивного менеджера стратегий

        Args:
            registry: Реестр моделей
            client_manager: Менеджер клиентов
            evaluator: Оценщик ответов
            json_validator: Валидатор JSON
            intelligent_router: Интеллектуальный роутер
        """
        self.registry = registry
        self.client_manager = client_manager
        self.evaluator = evaluator
        self.json_validator = json_validator
        self.intelligent_router = intelligent_router

        # Базовый менеджер стратегий
        self.strategy_manager = StrategyManager(
            registry, client_manager, evaluator, json_validator
        )

        # История производительности стратегий
        self.strategy_performance: Dict[str, List[StrategyPerformance]] = defaultdict(list)

        # Правила адаптации для различных типов задач
        self.adaptation_rules = self._init_adaptation_rules()

        # Пороги для триггеров адаптации
        self.adaptation_thresholds = {
            'min_success_rate': 0.7,      # Минимум 70% успешности
            'max_avg_latency': 30.0,      # Максимум 30 секунд
            'min_avg_score': 3.0,         # Минимум средний score 3.0
            'min_samples_for_adaptation': 5,  # Минимум 5 выборок для адаптации
            'adaptation_cooldown': 300    # 5 минут между адаптациями
        }

        # Кэш последних решений
        self.decision_cache: Dict[str, StrategyDecision] = {}
        self.cache_max_size = 200

        # Время последней адаптации
        self.last_adaptation_time = datetime.min

        # Активные адаптации
        self.active_adaptations: Dict[str, AdaptationContext] = {}

        logger.info("AdaptiveStrategyManager initialized")

    def _init_adaptation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Инициализация правил адаптации для различных типов задач"""
        return {
            "code_generation": {
                "preferred_strategies": [StrategyType.SINGLE, StrategyType.PARALLEL],
                "fallback_strategy": StrategyType.FALLBACK,
                "success_threshold": 0.8,
                "quality_threshold": 3.5,
                "use_parallel_for_complexity": "complex"
            },
            "code_review": {
                "preferred_strategies": [StrategyType.PARALLEL, StrategyType.CONSENSUS],
                "fallback_strategy": StrategyType.FALLBACK,
                "success_threshold": 0.85,
                "quality_threshold": 3.8,
                "use_parallel_for_accuracy": True
            },
            "analysis": {
                "preferred_strategies": [StrategyType.PARALLEL, StrategyType.CONSENSUS],
                "fallback_strategy": StrategyType.FALLBACK,
                "success_threshold": 0.75,
                "quality_threshold": 3.2,
                "use_parallel_for_complexity": "moderate"
            },
            "question_answering": {
                "preferred_strategies": [StrategyType.SINGLE, StrategyType.PARALLEL],
                "fallback_strategy": StrategyType.FALLBACK,
                "success_threshold": 0.8,
                "quality_threshold": 3.0,
                "use_parallel_for_accuracy": False
            },
            "json_generation": {
                "preferred_strategies": [StrategyType.PARALLEL, StrategyType.ITERATIVE],
                "fallback_strategy": StrategyType.FALLBACK,
                "success_threshold": 0.9,
                "quality_threshold": 3.5,
                "use_parallel_for_structured": True
            },
            "creative_writing": {
                "preferred_strategies": [StrategyType.SINGLE, StrategyType.PARALLEL],
                "fallback_strategy": StrategyType.FALLBACK,
                "success_threshold": 0.7,
                "quality_threshold": 3.2,
                "use_parallel_for_creativity": False
            },
            "math_problem": {
                "preferred_strategies": [StrategyType.PARALLEL, StrategyType.ITERATIVE],
                "fallback_strategy": StrategyType.FALLBACK,
                "success_threshold": 0.85,
                "quality_threshold": 3.8,
                "use_parallel_for_accuracy": True
            }
        }

    async def generate_adaptive(self, request: GenerationRequest) -> ModelResponse:
        """
        Адаптивная генерация - автоматически выбирает оптимальную стратегию

        Args:
            request: Запрос на генерацию

        Returns:
            Ответ модели
        """
        # Анализируем запрос через интеллектуальный роутер
        analysis = self.intelligent_router.analyze_request(request)
        task_type_key = analysis.task_type.value

        # Проверяем кэш решений
        cache_key = self._get_cache_key(request, analysis)
        if cache_key in self.decision_cache:
            cached_decision = self.decision_cache[cache_key]
            # Проверяем актуальность кэша (не старше 10 минут)
            if (datetime.now() - cached_decision.__class__().last_used) < timedelta(minutes=10):
                return await self._execute_strategy(cached_decision.strategy, request)

        # Определяем оптимальную стратегию
        strategy_decision = self._decide_strategy(request, analysis)

        # Кэшируем решение
        if len(self.decision_cache) < self.cache_max_size:
            self.decision_cache[cache_key] = strategy_decision

        # Выполняем выбранную стратегию
        response = await self._execute_strategy(strategy_decision.strategy, request)

        # Обучаемся на результате
        asyncio.create_task(self._learn_from_result_async(request, response, analysis, strategy_decision))

        return response

    def _get_cache_key(self, request: GenerationRequest, analysis) -> str:
        """Получить ключ для кэширования решения"""
        return f"{hash(request.prompt)}:{analysis.task_type.value}:{analysis.complexity.value}"

    def _decide_strategy(self, request: GenerationRequest, analysis) -> StrategyDecision:
        """
        Определить оптимальную стратегию для запроса

        Args:
            request: Запрос на генерацию
            analysis: Анализ запроса от интеллектуального роутера

        Returns:
            Решение о стратегии
        """
        task_type_key = analysis.task_type.value

        # Проверяем правила для данного типа задач
        rules = self.adaptation_rules.get(task_type_key, self.adaptation_rules.get("question_answering", {}))

        # Получаем историческую производительность
        historical_perf = self.strategy_performance.get(task_type_key, [])

        # Проверяем триггеры адаптации
        adaptation_needed, trigger = self._check_adaptation_triggers(rules, historical_perf)

        if adaptation_needed:
            # Нужна адаптация - выбираем лучшую стратегию на основе истории
            best_strategy = self._select_best_historical_strategy(historical_perf, rules)
            reasoning = f"Adaptation triggered by {trigger.value}, using historical best: {best_strategy.value}"
        else:
            # Выбираем стратегию на основе правил и характеристик запроса
            best_strategy = self._select_strategy_by_rules(request, analysis, rules)
            reasoning = f"Selected {best_strategy.value} based on task rules"

        # Рассчитываем ожидаемые метрики
        expected_metrics = self._predict_performance(best_strategy, task_type_key, historical_perf)

        # Определяем альтернативные стратегии
        alternatives = [s for s in rules.get("preferred_strategies", [])
                       if s != best_strategy][:2]

        return StrategyDecision(
            strategy=best_strategy,
            confidence=self._calculate_decision_confidence(best_strategy, historical_perf),
            reasoning=reasoning,
            expected_score=expected_metrics.get('score', 3.0),
            expected_latency=expected_metrics.get('latency', 10.0),
            alternatives=alternatives
        )

    def _check_adaptation_triggers(
        self,
        rules: Dict[str, Any],
        historical_perf: List[StrategyPerformance]
    ) -> Tuple[bool, Optional[AdaptationTrigger]]:
        """
        Проверить триггеры адаптации

        Returns:
            (нужна_адаптация, триггер)
        """
        if not historical_perf:
            return False, None

        # Группируем по стратегиям
        strategy_stats = {}
        for perf in historical_perf[-20:]:  # Последние 20 записей
            if perf.sample_count >= self.adaptation_thresholds['min_samples_for_adaptation']:
                strategy_stats[perf.strategy] = {
                    'success_rate': perf.success_rate,
                    'avg_score': perf.avg_score,
                    'avg_latency': perf.avg_response_time,
                    'samples': perf.sample_count
                }

        if not strategy_stats:
            return False, None

        # Находим текущую лучшую стратегию
        current_best = max(strategy_stats.items(),
                          key=lambda x: x[1]['success_rate'] * 0.4 +
                                       x[1]['avg_score'] * 0.4 +
                                       (1.0 / (1.0 + x[1]['avg_latency'])) * 0.2)

        current_strategy, current_stats = current_best

        # Проверяем пороги
        if current_stats['success_rate'] < self.adaptation_thresholds['min_success_rate']:
            return True, AdaptationTrigger.LOW_SUCCESS_RATE

        if current_stats['avg_score'] < self.adaptation_thresholds['min_avg_score']:
            return True, AdaptationTrigger.LOW_QUALITY

        if current_stats['avg_latency'] > self.adaptation_thresholds['max_avg_latency']:
            return True, AdaptationTrigger.HIGH_LATENCY

        # Проверяем время с последней адаптации
        time_since_last_adaptation = datetime.now() - self.last_adaptation_time
        if time_since_last_adaptation < timedelta(seconds=self.adaptation_thresholds['adaptation_cooldown']):
            return False, None

        return False, None

    def _select_best_historical_strategy(
        self,
        historical_perf: List[StrategyPerformance],
        rules: Dict[str, Any]
    ) -> StrategyType:
        """Выбрать лучшую стратегию на основе исторической производительности"""

        # Фильтруем по предпочтительным стратегиям
        preferred_strategies = set(rules.get("preferred_strategies", []))

        # Считаем взвешенный score для каждой стратегии
        strategy_scores = {}

        for perf in historical_perf[-50:]:  # Последние 50 записей
            if perf.sample_count < 3:  # Минимум 3 выборки
                continue

            if preferred_strategies and perf.strategy not in preferred_strategies:
                continue

            # Взвешенный score
            weighted_score = (
                perf.success_rate * 0.4 +           # Успешность
                (perf.avg_score / 5.0) * 0.4 +     # Качество (нормализованное)
                (1.0 / (1.0 + perf.avg_response_time / 10.0)) * 0.2  # Скорость (инвертированная)
            )

            if perf.strategy not in strategy_scores:
                strategy_scores[perf.strategy] = []
            strategy_scores[perf.strategy].append(weighted_score)

        if not strategy_scores:
            # Fallback к предпочтительной стратегии
            return rules.get("preferred_strategies", [StrategyType.SINGLE])[0]

        # Выбираем стратегию с лучшим средним score
        best_strategy = max(strategy_scores.items(),
                           key=lambda x: sum(x[1]) / len(x[1]))

        return best_strategy[0]

    def _select_strategy_by_rules(
        self,
        request: GenerationRequest,
        analysis,
        rules: Dict[str, Any]
    ) -> StrategyType:
        """Выбрать стратегию на основе правил и характеристик запроса"""

        # Базовая стратегия
        base_strategy = StrategyType.SINGLE

        # Проверяем условия для parallel
        should_use_parallel = False

        # 1. Запрос явно указывает на parallel
        if request.use_parallel:
            should_use_parallel = True

        # 2. JSON генерация
        elif analysis.is_structured or rules.get("use_parallel_for_structured", False):
            should_use_parallel = True

        # 3. Высокая точность требуется
        elif analysis.requires_accuracy and rules.get("use_parallel_for_accuracy", False):
            should_use_parallel = True

        # 4. Сложная задача
        elif (analysis.complexity.name in ['COMPLEX', 'VERY_COMPLEX'] and
              rules.get("use_parallel_for_complexity") in ['complex', 'moderate']):
            should_use_parallel = True

        # 5. Низкая скорость не критична, но нужна надежность
        elif (not analysis.requires_speed and
              rules.get("success_threshold", 0.7) > 0.8):
            should_use_parallel = True

        if should_use_parallel:
            # Выбираем между PARALLEL и CONSENSUS
            if rules.get("preferred_strategies") and StrategyType.CONSENSUS in rules["preferred_strategies"]:
                return StrategyType.CONSENSUS
            else:
                return StrategyType.PARALLEL

        # Для простых задач используем SINGLE для скорости
        if analysis.complexity == analysis.complexity.SIMPLE and analysis.requires_speed:
            return StrategyType.SINGLE

        # По умолчанию возвращаем первую предпочтительную стратегию
        preferred = rules.get("preferred_strategies", [StrategyType.SINGLE])
        return preferred[0] if preferred else StrategyType.SINGLE

    def _predict_performance(
        self,
        strategy: StrategyType,
        task_type: str,
        historical_perf: List[StrategyPerformance]
    ) -> Dict[str, float]:
        """Предсказать производительность стратегии"""

        # Ищем историческую производительность для данной стратегии и типа задач
        relevant_perf = None
        for perf in historical_perf:
            if perf.strategy == strategy:
                relevant_perf = perf
                break

        if relevant_perf and relevant_perf.sample_count > 0:
            return {
                'score': relevant_perf.avg_score,
                'latency': relevant_perf.avg_response_time,
                'success_rate': relevant_perf.success_rate
            }

        # Значения по умолчанию на основе типа стратегии
        defaults = {
            StrategyType.SINGLE: {'score': 3.2, 'latency': 8.0, 'success_rate': 0.8},
            StrategyType.PARALLEL: {'score': 3.6, 'latency': 15.0, 'success_rate': 0.85},
            StrategyType.CONSENSUS: {'score': 3.8, 'latency': 20.0, 'success_rate': 0.9},
            StrategyType.FALLBACK: {'score': 2.8, 'latency': 25.0, 'success_rate': 0.95},
            StrategyType.ITERATIVE: {'score': 3.9, 'latency': 30.0, 'success_rate': 0.88}
        }

        return defaults.get(strategy, {'score': 3.0, 'latency': 10.0, 'success_rate': 0.8})

    def _calculate_decision_confidence(
        self,
        strategy: StrategyType,
        historical_perf: List[StrategyPerformance]
    ) -> float:
        """Рассчитать уверенность в решении"""

        # Ищем производительность выбранной стратегии
        strategy_perf = None
        for perf in historical_perf:
            if perf.strategy == strategy:
                strategy_perf = perf
                break

        if not strategy_perf or strategy_perf.sample_count < 3:
            return 0.5  # Низкая уверенность при отсутствии данных

        # Уверенность основана на количестве выборок и стабильности
        sample_confidence = min(1.0, strategy_perf.sample_count / 20.0)  # Максимум при 20+ выборках

        # Уверенность в качестве
        quality_confidence = strategy_perf.avg_score / 5.0

        # Уверенность в стабильности (более высокая при consistent результатах)
        stability_confidence = min(1.0, strategy_perf.success_rate * 1.2)

        return (sample_confidence * 0.4 + quality_confidence * 0.4 + stability_confidence * 0.2)

    async def _execute_strategy(self, strategy: StrategyType, request: GenerationRequest) -> ModelResponse:
        """Выполнить выбранную стратегию"""

        # Маппинг типов стратегий на методы базового менеджера
        strategy_mapping = {
            StrategyType.SINGLE: lambda: self._execute_single_strategy(request),
            StrategyType.PARALLEL: lambda: self._execute_parallel_strategy(request),
            StrategyType.FALLBACK: lambda: self._execute_fallback_strategy(request),
            StrategyType.CONSENSUS: lambda: self._execute_consensus_strategy(request),
            StrategyType.ITERATIVE: lambda: self._execute_iterative_strategy(request)
        }

        executor = strategy_mapping.get(strategy, strategy_mapping[StrategyType.SINGLE])

        try:
            return await executor()
        except Exception as e:
            logger.error(f"Error executing strategy {strategy.value}: {e}")
            # Fallback на single стратегию
            return await self._execute_single_strategy(request)

    async def _execute_single_strategy(self, request: GenerationRequest) -> ModelResponse:
        """Выполнить single стратегию"""
        request.use_parallel = False
        return await self.strategy_manager.generate(request)

    async def _execute_parallel_strategy(self, request: GenerationRequest) -> ModelResponse:
        """Выполнить parallel стратегию"""
        request.use_parallel = True
        return await self.strategy_manager.generate(request)

    async def _execute_fallback_strategy(self, request: GenerationRequest) -> ModelResponse:
        """Выполнить fallback стратегию"""
        # Fallback стратегия реализована в базовом StrategyManager
        request.use_parallel = False
        return await self.strategy_manager.generate(request)

    async def _execute_consensus_strategy(self, request: GenerationRequest) -> ModelResponse:
        """Выполнить consensus стратегию - получить ответы от нескольких моделей и выбрать консенсус"""

        # Получаем несколько моделей
        primary_models = self.registry.get_models_by_role(ModelRole.PRIMARY)
        if len(primary_models) < 3:
            # Недостаточно моделей, fallback на parallel
            return await self._execute_parallel_strategy(request)

        # Выбираем 3 модели
        selected_models = primary_models[:3]

        # Генерируем ответы параллельно
        responses = []
        for model in selected_models:
            try:
                model_request = GenerationRequest(
                    prompt=request.prompt,
                    model_name=model.name,
                    use_fastest=False,
                    use_parallel=False,
                    response_format=request.response_format
                )
                response = await self.strategy_manager.generate(model_request)
                if response.success:
                    responses.append(response)
            except Exception as e:
                logger.debug(f"Consensus strategy error for model {model.name}: {e}")

        if not responses:
            # Все модели провалились, fallback
            return await self._execute_fallback_strategy(request)

        if len(responses) == 1:
            return responses[0]

        # Оцениваем все ответы
        evaluations = []
        for response in responses:
            try:
                evaluation = await self.evaluator.evaluate_response(
                    prompt=request.prompt,
                    response=response.content,
                    client_manager=self.client_manager
                )
                evaluations.append((response, evaluation.score))
            except Exception as e:
                logger.debug(f"Evaluation error in consensus: {e}")
                evaluations.append((response, 3.0))  # Нейтральная оценка

        # Выбираем лучший ответ
        best_response, best_score = max(evaluations, key=lambda x: x[1])

        logger.debug(f"Consensus strategy selected response with score {best_score}")
        return best_response

    async def _execute_iterative_strategy(self, request: GenerationRequest) -> ModelResponse:
        """Выполнить iterative стратегию - итеративно улучшать ответ"""

        max_iterations = 3
        current_response = None

        for iteration in range(max_iterations):
            # Генерируем ответ
            if iteration == 0:
                # Первая итерация - обычная генерация
                temp_request = GenerationRequest(
                    prompt=request.prompt,
                    use_parallel=False,
                    response_format=request.response_format
                )
                current_response = await self.strategy_manager.generate(temp_request)
            else:
                # Последующие итерации - улучшаем предыдущий ответ
                improvement_prompt = f"""Please improve the following response to make it better:

Original request: {request.prompt}

Current response: {current_response.content}

Provide an improved version that is more accurate, comprehensive, and well-structured."""

                temp_request = GenerationRequest(
                    prompt=improvement_prompt,
                    use_parallel=False,
                    response_format=request.response_format
                )
                improved_response = await self.strategy_manager.generate(temp_request)

                if improved_response.success:
                    # Оцениваем улучшение
                    try:
                        original_eval = await self.evaluator.evaluate_response(
                            prompt=request.prompt,
                            response=current_response.content,
                            client_manager=self.client_manager
                        )
                        improved_eval = await self.evaluator.evaluate_response(
                            prompt=request.prompt,
                            response=improved_response.content,
                            client_manager=self.client_manager
                        )

                        # Используем улучшенный ответ если он лучше
                        if improved_eval.score > original_eval.score:
                            current_response = improved_response
                            logger.debug(f"Iteration {iteration + 1}: Improved score from {original_eval.score} to {improved_eval.score}")
                        else:
                            logger.debug(f"Iteration {iteration + 1}: No improvement ({original_eval.score} -> {improved_eval.score})")
                            break
                    except Exception as e:
                        logger.debug(f"Evaluation error in iterative strategy: {e}")
                        current_response = improved_response
                else:
                    break

        return current_response

    async def _learn_from_result_async(
        self,
        request: GenerationRequest,
        response: ModelResponse,
        analysis,
        strategy_decision: StrategyDecision
    ):
        """Обучаться на результате выполнения стратегии"""
        try:
            task_type_key = analysis.task_type.value
            strategy = strategy_decision.strategy

            # Получаем оценку качества
            evaluation_score = None
            if response.success:
                try:
                    evaluation = await self.evaluator.evaluate_response(
                        prompt=request.prompt,
                        response=response.content,
                        client_manager=self.client_manager
                    )
                    evaluation_score = evaluation.score
                except Exception as e:
                    logger.debug(f"Could not evaluate response for strategy learning: {e}")

            # Находим или создаем запись производительности
            performances = self.strategy_performance[task_type_key]
            existing_perf = None

            for perf in performances:
                if perf.strategy == strategy:
                    existing_perf = perf
                    break

            if not existing_perf:
                existing_perf = StrategyPerformance(
                    strategy=strategy,
                    task_type=task_type_key
                )
                performances.append(existing_perf)

            # Обновляем статистику
            existing_perf.sample_count += 1
            existing_perf.last_used = datetime.now()

            # Обновляем средние значения
            success = 1.0 if response.success else 0.0
            existing_perf.success_rate = (
                (existing_perf.success_rate * (existing_perf.sample_count - 1)) + success
            ) / existing_perf.sample_count

            if evaluation_score is not None:
                existing_perf.avg_score = (
                    (existing_perf.avg_score * (existing_perf.sample_count - 1)) + evaluation_score
                ) / existing_perf.sample_count

            existing_perf.avg_response_time = (
                (existing_perf.avg_response_time * (existing_perf.sample_count - 1)) + response.response_time
            ) / existing_perf.sample_count

            logger.debug(f"Updated strategy performance for {strategy.value} on {task_type_key}: "
                        f"score={existing_perf.avg_score:.2f}, "
                        f"success_rate={existing_perf.success_rate:.2f}, "
                        f"avg_time={existing_perf.avg_response_time:.2f}s")

            # Проверяем необходимость адаптации
            await self._check_and_trigger_adaptation(task_type_key, strategy_decision)

        except Exception as e:
            logger.debug(f"Error during strategy learning: {e}")

    async def _check_and_trigger_adaptation(self, task_type: str, strategy_decision: StrategyDecision):
        """Проверить и запустить адаптацию если необходимо"""
        try:
            rules = self.adaptation_rules.get(task_type, {})
            historical_perf = self.strategy_performance.get(task_type, [])

            adaptation_needed, trigger = self._check_adaptation_triggers(rules, historical_perf)

            if adaptation_needed:
                self.last_adaptation_time = datetime.now()

                # Создаем контекст адаптации
                context = AdaptationContext(
                    trigger=trigger,
                    current_strategy=strategy_decision.strategy,
                    performance_metrics={
                        'expected_score': strategy_decision.expected_score,
                        'expected_latency': strategy_decision.expected_latency,
                        'actual_confidence': strategy_decision.confidence
                    },
                    task_characteristics={'task_type': task_type},
                    historical_performance=historical_perf
                )

                self.active_adaptations[task_type] = context

                logger.info(f"Triggered adaptation for {task_type}: {trigger.value}")

        except Exception as e:
            logger.debug(f"Error during adaptation check: {e}")

    def get_adaptive_stats(self) -> Dict[str, Any]:
        """Получить статистику адаптивного менеджера стратегий"""
        total_strategies = sum(len(perfs) for perfs in self.strategy_performance.values())
        total_samples = sum(
            sum(perf.sample_count for perf in perfs)
            for perfs in self.strategy_performance.values()
        )

        # Статистика по типам задач
        task_stats = {}
        for task_type, performances in self.strategy_performance.items():
            if performances:
                best_strategy = max(performances, key=lambda p: p.avg_score if p.sample_count > 0 else 0)
                task_stats[task_type] = {
                    'strategies_count': len(performances),
                    'total_samples': sum(p.sample_count for p in performances),
                    'best_strategy': best_strategy.strategy.value,
                    'best_score': best_strategy.avg_score,
                    'best_success_rate': best_strategy.success_rate
                }

        return {
            'total_strategies_tracked': total_strategies,
            'total_samples': total_samples,
            'tasks_tracked': len(self.strategy_performance),
            'cache_size': len(self.decision_cache),
            'active_adaptations': len(self.active_adaptations),
            'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time != datetime.min else None,
            'task_statistics': task_stats
        }

    def reset_adaptive_learning(self):
        """Сбросить данные обучения адаптивного менеджера"""
        self.strategy_performance.clear()
        self.decision_cache.clear()
        self.active_adaptations.clear()
        self.last_adaptation_time = datetime.min
        logger.info("Adaptive learning data reset")

    def get_strategy_recommendations(self, task_type: str) -> List[Dict[str, Any]]:
        """Получить рекомендации по стратегиям для типа задач"""
        performances = self.strategy_performance.get(task_type, [])

        if not performances:
            return []

        # Сортируем по комплексному score
        recommendations = []
        for perf in performances:
            if perf.sample_count >= 3:
                complex_score = (
                    perf.success_rate * 0.4 +
                    (perf.avg_score / 5.0) * 0.4 +
                    (1.0 / (1.0 + perf.avg_response_time / 10.0)) * 0.2
                )

                recommendations.append({
                    'strategy': perf.strategy.value,
                    'complex_score': complex_score,
                    'avg_score': perf.avg_score,
                    'success_rate': perf.success_rate,
                    'avg_response_time': perf.avg_response_time,
                    'sample_count': perf.sample_count,
                    'confidence': min(1.0, perf.sample_count / 10.0)
                })

        return sorted(recommendations, key=lambda x: x['complex_score'], reverse=True)