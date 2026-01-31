"""
IntelligentRouter - интеллектуальный роутер для выбора моделей

Ответственность:
- Анализ контекста запросов
- Интеллектуальный выбор моделей на основе характеристик запроса
- Адаптация к паттернам использования
- Обучение на исторических данных
"""

import asyncio
import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter

from .types import (
    ModelConfig, ModelResponse, ModelRole,
    GenerationRequest, IIntelligentRouter, IModelRegistry,
    RequestAnalysis, RoutingDecision, TaskType, ComplexityLevel, ModelPerformance
)

logger = logging.getLogger(__name__)


# TaskType imported from types.py


class ComplexityLevel(Enum):
    """Уровень сложности запроса"""
    SIMPLE = "simple"          # Простой запрос
    MODERATE = "moderate"      # Средней сложности
    COMPLEX = "complex"        # Сложный запрос
    VERY_COMPLEX = "very_complex"  # Очень сложный


@dataclass
class RequestAnalysis:
    """Анализ запроса"""
    task_type: TaskType
    complexity: ComplexityLevel
    estimated_tokens: int
    requires_accuracy: bool = False
    requires_creativity: bool = False
    requires_speed: bool = False
    is_structured: bool = False  # JSON, structured output
    keywords: Set[str] = field(default_factory=set)
    confidence: float = 0.0


@dataclass
class ModelPerformance:
    """Производительность модели для конкретного типа задач"""
    model_name: str
    task_type: TaskType
    avg_score: float = 0.0
    avg_response_time: float = 0.0
    success_rate: float = 0.0
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingDecision:
    """Решение о маршрутизации"""
    model_name: str
    strategy: str  # "single", "parallel", "fallback"
    reasoning: str
    confidence: float
    alternatives: List[str] = field(default_factory=list)


class IntelligentRouter(IIntelligentRouter):
    """
    Интеллектуальный роутер - анализирует запросы и выбирает оптимальные модели

    Предоставляет:
    - Анализ контекста запросов
    - Интеллектуальный выбор моделей
    - Адаптацию к паттернам использования
    - Обучение на исторических данных
    """

    def __init__(self, registry: IModelRegistry):
        """
        Инициализация интеллектуального роутера

        Args:
            registry: Реестр моделей
        """
        self.registry = registry
        self.performance_history: Dict[str, List[ModelPerformance]] = defaultdict(list)
        self.task_patterns: Dict[TaskType, Dict[str, Any]] = self._init_task_patterns()
        self.learning_enabled = True

        # Кэш для анализа запросов
        self.analysis_cache: Dict[str, RequestAnalysis] = {}
        self.cache_max_size = 1000

        logger.info("IntelligentRouter initialized")

    def _init_task_patterns(self) -> Dict[TaskType, Dict[str, Any]]:
        """Инициализация паттернов для распознавания типов задач"""
        return {
            TaskType.CODE_GENERATION: {
                "keywords": ["function", "class", "def ", "import ", "code", "programming", "script", "algorithm"],
                "patterns": [r"def\s+\w+", r"class\s+\w+", r"import\s+\w+", r"function\s+\w+"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.8,
                "creativity_weight": 0.4,
                "speed_weight": 0.3
            },
            TaskType.CODE_REVIEW: {
                "keywords": ["review", "bug", "error", "fix", "optimize", "refactor", "improve"],
                "patterns": [r"review.*code", r"fix.*bug", r"optimize.*code"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.9,
                "creativity_weight": 0.2,
                "speed_weight": 0.4
            },
            TaskType.ANALYSIS: {
                "keywords": ["analyze", "analysis", "data", "statistics", "insights", "patterns"],
                "patterns": [r"analy[sz]e", r"data.*analysis", r"find.*patterns"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.8,
                "creativity_weight": 0.6,
                "speed_weight": 0.5
            },
            TaskType.QUESTION_ANSWERING: {
                "keywords": ["what", "how", "why", "explain", "tell me", "question"],
                "patterns": [r"what.*is", r"how.*to", r"explain.*why"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.7,
                "creativity_weight": 0.3,
                "speed_weight": 0.7
            },
            TaskType.SUMMARIZATION: {
                "keywords": ["summarize", "summary", "tl;dr", "brief", "overview"],
                "patterns": [r"summari[sz]e", r"tl;?dr", r"brief.*overview"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.6,
                "creativity_weight": 0.2,
                "speed_weight": 0.8
            },
            TaskType.JSON_GENERATION: {
                "keywords": ["json", "structured", "format", "schema", "object"],
                "patterns": [r"json.*format", r"structured.*output", r"\{.*\}"],  # Простой паттерн для JSON
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.9,
                "creativity_weight": 0.1,
                "speed_weight": 0.6,
                "structured_output": True
            },
            TaskType.MATH_PROBLEM: {
                "keywords": ["calculate", "solve", "equation", "math", "formula"],
                "patterns": [r"calculate", r"solve.*equation", r"\d+.*[+\-*/]"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.9,
                "creativity_weight": 0.1,
                "speed_weight": 0.6
            },
            TaskType.CREATIVE_WRITING: {
                "keywords": ["write", "story", "creative", "imagine", "fiction"],
                "patterns": [r"write.*story", r"creative.*writing", r"imagine.*scenario"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.5,
                "creativity_weight": 0.9,
                "speed_weight": 0.4
            },
            TaskType.TECHNICAL_WRITING: {
                "keywords": ["documentation", "docs", "manual", "guide", "tutorial"],
                "patterns": [r"write.*documentation", r"create.*guide", r"technical.*writing"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.8,
                "creativity_weight": 0.5,
                "speed_weight": 0.5
            },
            TaskType.CHAT_CONVERSATION: {
                "keywords": ["hello", "hi", "thanks", "thank you", "help"],
                "patterns": [r"^(hi|hello|hey)", r"thank.*you", r"can.*help"],
                "preferred_roles": [ModelRole.PRIMARY],
                "accuracy_weight": 0.6,
                "creativity_weight": 0.7,
                "speed_weight": 0.8
            }
        }

    def analyze_request(self, request: GenerationRequest) -> RequestAnalysis:
        """
        Анализировать запрос и определить его характеристики

        Args:
            request: Запрос на генерацию

        Returns:
            Анализ запроса
        """
        # Проверяем кэш
        cache_key = hash(request.prompt + str(request.response_format))
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]

        prompt = request.prompt.lower()
        task_type = self._classify_task_type(prompt)
        complexity = self._assess_complexity(prompt)

        # Оцениваем примерное количество токенов
        estimated_tokens = self._estimate_token_count(prompt)

        # Определяем требования
        requires_accuracy = self._requires_high_accuracy(task_type, prompt)
        requires_creativity = self._requires_creativity(task_type, prompt)
        requires_speed = request.use_fastest or estimated_tokens < 100

        # Проверяем на структурированный вывод
        is_structured = (
            request.response_format and
            request.response_format.get("type") == "json_object"
        ) or task_type == TaskType.JSON_GENERATION

        # Извлекаем ключевые слова
        keywords = self._extract_keywords(prompt, task_type)

        # Рассчитываем уверенность анализа
        confidence = self._calculate_analysis_confidence(prompt, task_type)

        analysis = RequestAnalysis(
            task_type=task_type,
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            requires_accuracy=requires_accuracy,
            requires_creativity=requires_creativity,
            requires_speed=requires_speed,
            is_structured=is_structured,
            keywords=keywords,
            confidence=confidence
        )

        # Сохраняем в кэше
        if len(self.analysis_cache) < self.cache_max_size:
            self.analysis_cache[cache_key] = analysis

        return analysis

    def _classify_task_type(self, prompt: str) -> TaskType:
        """Классифицировать тип задачи на основе текста запроса"""
        best_match = TaskType.UNKNOWN
        best_score = 0.0

        for task_type, patterns in self.task_patterns.items():
            score = 0.0

            # Проверяем ключевые слова
            keywords = patterns.get("keywords", [])
            keyword_matches = sum(1 for keyword in keywords if keyword in prompt)
            if keyword_matches > 0:
                score += keyword_matches * 0.3

            # Проверяем регулярные выражения
            regex_patterns = patterns.get("patterns", [])
            for pattern in regex_patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    score += 0.4
                    break

            # Бонус за специфические маркеры
            if task_type == TaskType.JSON_GENERATION and ("json" in prompt or "{" in prompt):
                score += 0.5
            elif task_type == TaskType.CODE_GENERATION and any(lang in prompt for lang in ["python", "javascript", "java", "c++"]):
                score += 0.3

            if score > best_score:
                best_score = score
                best_match = task_type

        return best_match if best_score > 0.2 else TaskType.CHAT_CONVERSATION

    def _assess_complexity(self, prompt: str) -> ComplexityLevel:
        """Оценить сложность запроса"""
        length = len(prompt)
        sentences = len(re.findall(r'[.!?]+', prompt))
        complex_words = len(re.findall(r'\b\w{8,}\b', prompt))

        complexity_score = 0

        # Факторы сложности
        if length > 1000:
            complexity_score += 2
        elif length > 500:
            complexity_score += 1

        if sentences > 5:
            complexity_score += 1

        if complex_words > 10:
            complexity_score += 1

        # Проверяем на наличие технических терминов
        technical_terms = ["algorithm", "optimization", "architecture", "framework", "paradigm"]
        if any(term in prompt for term in technical_terms):
            complexity_score += 1

        if complexity_score >= 3:
            return ComplexityLevel.VERY_COMPLEX
        elif complexity_score >= 2:
            return ComplexityLevel.COMPLEX
        elif complexity_score >= 1:
            return ComplexityLevel.MODERATE
        else:
            return ComplexityLevel.SIMPLE

    def _estimate_token_count(self, prompt: str) -> int:
        """Оценить количество токенов в запросе"""
        # Примерная оценка: 1 токен ≈ 4 символа для английского текста
        # Для кода и технического текста коэффициент может быть выше
        char_count = len(prompt)

        # Корректировка для кода (больше специальных символов)
        if any(keyword in prompt for keyword in ["def ", "class ", "import ", "function"]):
            tokens = char_count // 3  # Для кода меньше токенов на символ
        else:
            tokens = char_count // 4  # Для обычного текста

        return max(10, min(tokens, 8000))  # Ограничиваем разумными пределами

    def _requires_high_accuracy(self, task_type: TaskType, prompt: str) -> bool:
        """Определить, требуется ли высокая точность"""
        high_accuracy_tasks = [
            TaskType.CODE_GENERATION,
            TaskType.CODE_REVIEW,
            TaskType.MATH_PROBLEM,
            TaskType.JSON_GENERATION,
            TaskType.ANALYSIS
        ]

        if task_type in high_accuracy_tasks:
            return True

        # Проверяем ключевые слова
        accuracy_keywords = ["accurate", "precise", "correct", "exact", "error-free"]
        return any(keyword in prompt for keyword in accuracy_keywords)

    def _requires_creativity(self, task_type: TaskType, prompt: str) -> bool:
        """Определить, требуется ли креативность"""
        creative_tasks = [
            TaskType.CREATIVE_WRITING,
            TaskType.CHAT_CONVERSATION
        ]

        if task_type in creative_tasks:
            return True

        # Проверяем ключевые слова
        creative_keywords = ["creative", "imagine", "story", "fiction", "innovative"]
        return any(keyword in prompt for keyword in creative_keywords)

    def _extract_keywords(self, prompt: str, task_type: TaskType) -> Set[str]:
        """Извлечь ключевые слова из запроса"""
        keywords = set()

        # Добавляем ключевые слова для типа задачи
        task_keywords = self.task_patterns.get(task_type, {}).get("keywords", [])
        keywords.update(task_keywords)

        # Извлекаем дополнительные ключевые слова
        words = re.findall(r'\b\w{4,}\b', prompt.lower())
        significant_words = [word for word in words if len(word) > 3]

        # Берем наиболее частые слова (исключая стоп-слова)
        stop_words = {"that", "this", "with", "from", "they", "have", "what", "where", "when", "which"}
        filtered_words = [word for word in significant_words if word not in stop_words]

        # Добавляем топ-5 наиболее частых слов
        word_counts = Counter(filtered_words)
        top_words = [word for word, count in word_counts.most_common(5)]
        keywords.update(top_words)

        return keywords

    def _calculate_analysis_confidence(self, prompt: str, task_type: TaskType) -> float:
        """Рассчитать уверенность анализа"""
        if task_type == TaskType.UNKNOWN:
            return 0.1

        # Базовая уверенность
        confidence = 0.5

        # Увеличиваем за специфические маркеры
        specific_markers = {
            TaskType.CODE_GENERATION: ["def ", "class ", "import "],
            TaskType.JSON_GENERATION: ["json", "format", "schema"],
            TaskType.MATH_PROBLEM: ["calculate", "solve", "="]
        }

        markers = specific_markers.get(task_type, [])
        if any(marker in prompt for marker in markers):
            confidence += 0.3

        # Уменьшаем за неоднозначность
        if len(prompt.strip()) < 10:
            confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def route_request(self, request: GenerationRequest) -> RoutingDecision:
        """
        Определить оптимальный маршрут для запроса

        Args:
            request: Запрос на генерацию

        Returns:
            Решение о маршрутизации
        """
        analysis = self.analyze_request(request)

        # Получаем доступные модели
        available_models = self.registry.get_models_by_role(ModelRole.PRIMARY)
        if not available_models:
            return RoutingDecision(
                model_name="",
                strategy="fallback",
                reasoning="No primary models available",
                confidence=0.0
            )

        # Выбираем оптимальную модель
        best_model, alternatives = self._select_optimal_model(analysis, available_models)

        # Определяем стратегию
        strategy = self._determine_strategy(analysis, best_model)

        # Формируем объяснение
        reasoning = self._build_routing_reasoning(analysis, best_model, strategy)

        return RoutingDecision(
            model_name=best_model.name,
            strategy=strategy,
            reasoning=reasoning,
            confidence=analysis.confidence,
            alternatives=[m.name for m in alternatives]
        )

    def _select_optimal_model(
        self,
        analysis: RequestAnalysis,
        available_models: List[ModelConfig]
    ) -> Tuple[ModelConfig, List[ModelConfig]]:
        """Выбрать оптимальную модель для анализа"""

        # Если запрошена конкретная модель и она доступна
        if hasattr(analysis, 'model_name') and analysis.model_name:
            requested_model = self.registry.get_model(analysis.model_name)
            if requested_model and requested_model.enabled:
                return requested_model, available_models

        # Оцениваем каждую модель
        model_scores = []
        for model in available_models:
            if not model.enabled:
                continue

            score = self._score_model_for_task(model, analysis)
            model_scores.append((model, score))

        # Сортируем по score
        model_scores.sort(key=lambda x: x[1], reverse=True)

        if not model_scores:
            # Fallback к первой доступной модели
            return available_models[0], []

        best_model, best_score = model_scores[0]
        alternatives = [model for model, score in model_scores[1:3]]  # Топ-3 альтернативы

        logger.debug(f"Selected model {best_model.name} with score {best_score:.2f} for task {analysis.task_type.value}")

        return best_model, alternatives

    def _score_model_for_task(self, model: ModelConfig, analysis: RequestAnalysis) -> float:
        """Оценить модель для конкретной задачи"""
        base_score = 1.0

        # Проверяем историческую производительность
        performance = self._get_model_performance(model.name, analysis.task_type)
        if performance and performance.sample_count > 0:
            # Учитываем средний score, success rate и скорость
            performance_score = (
                performance.avg_score * 0.4 +
                performance.success_rate * 0.4 +
                (1.0 / (1.0 + performance.avg_response_time)) * 0.2
            )
            base_score = performance_score

        # Корректируем на основе требований задачи
        task_weights = self.task_patterns.get(analysis.task_type, {})

        if analysis.requires_accuracy and task_weights.get("accuracy_weight", 0) > 0:
            # Предпочитаем модели с хорошей точностью
            accuracy_bonus = task_weights["accuracy_weight"] * 0.3
            base_score += accuracy_bonus

        if analysis.requires_creativity and task_weights.get("creativity_weight", 0) > 0:
            # Предпочитаем модели с креативностью
            creativity_bonus = task_weights["creativity_weight"] * 0.2
            base_score += creativity_bonus

        if analysis.requires_speed:
            # Предпочитаем быстрые модели
            speed_bonus = (1.0 / (1.0 + model.last_response_time)) * 0.2
            base_score += speed_bonus

        # Корректируем на основе сложности
        if analysis.complexity == ComplexityLevel.VERY_COMPLEX:
            # Для очень сложных задач предпочитаем более мощные модели
            complexity_bonus = 0.1
            base_score += complexity_bonus
        elif analysis.complexity == ComplexityLevel.SIMPLE:
            # Для простых задач можем использовать более быстрые модели
            simplicity_bonus = 0.05
            base_score += simplicity_bonus

        return min(2.0, base_score)  # Ограничиваем максимальный score

    def _get_model_performance(self, model_name: str, task_type: TaskType) -> Optional[ModelPerformance]:
        """Получить историческую производительность модели для типа задачи"""
        performances = self.performance_history[model_name]
        for perf in performances:
            if perf.task_type == task_type and perf.sample_count > 0:
                return perf
        return None

    def _determine_strategy(self, analysis: RequestAnalysis, model: ModelConfig) -> str:
        """Определить стратегию генерации"""

        # Для структурированного вывода (JSON) используем best_of_two для надежности
        if analysis.is_structured:
            return "parallel"

        # Для очень сложных задач используем parallel для лучшего качества
        if analysis.complexity == ComplexityLevel.VERY_COMPLEX:
            return "parallel"

        # Для задач требующих высокой точности используем parallel
        if analysis.requires_accuracy and analysis.confidence > 0.7:
            return "parallel"

        # Для простых задач используем single для скорости
        if analysis.complexity == ComplexityLevel.SIMPLE and analysis.requires_speed:
            return "single"

        # По умолчанию single
        return "single"

    def _build_routing_reasoning(
        self,
        analysis: RequestAnalysis,
        model: ModelConfig,
        strategy: str
    ) -> str:
        """Сформировать объяснение выбора маршрута"""
        reasons = []

        reasons.append(f"Task classified as {analysis.task_type.value}")
        reasons.append(f"Complexity: {analysis.complexity.value}")
        reasons.append(f"Selected model: {model.name}")

        if strategy == "parallel":
            reasons.append("Using parallel strategy for better quality/reliability")
        else:
            reasons.append("Using single model strategy for speed")

        if analysis.is_structured:
            reasons.append("Structured output required (JSON/schema)")

        if analysis.requires_accuracy:
            reasons.append("High accuracy required")

        return "; ".join(reasons)

    def learn_from_result(
        self,
        request: GenerationRequest,
        response: ModelResponse,
        evaluation_score: Optional[float] = None
    ):
        """
        Обучаться на результате выполнения запроса

        Args:
            request: Исходный запрос
            response: Полученный ответ
            evaluation_score: Оценка качества ответа (если доступна)
        """
        if not self.learning_enabled:
            return

        analysis = self.analyze_request(request)
        model_name = response.model_name

        # Находим или создаем запись производительности
        performances = self.performance_history[model_name]
        existing_perf = None

        for perf in performances:
            if perf.task_type == analysis.task_type:
                existing_perf = perf
                break

        if not existing_perf:
            existing_perf = ModelPerformance(
                model_name=model_name,
                task_type=analysis.task_type
            )
            performances.append(existing_perf)

        # Обновляем статистику
        existing_perf.sample_count += 1
        existing_perf.last_updated = datetime.now()

        # Обновляем средний score
        if evaluation_score is not None:
            existing_perf.avg_score = (
                (existing_perf.avg_score * (existing_perf.sample_count - 1)) + evaluation_score
            ) / existing_perf.sample_count

        # Обновляем success rate
        success = 1.0 if response.success else 0.0
        existing_perf.success_rate = (
            (existing_perf.success_rate * (existing_perf.sample_count - 1)) + success
        ) / existing_perf.sample_count

        # Обновляем среднее время ответа
        existing_perf.avg_response_time = (
            (existing_perf.avg_response_time * (existing_perf.sample_count - 1)) + response.response_time
        ) / existing_perf.sample_count

        logger.debug(f"Updated performance for {model_name} on {analysis.task_type.value}: "
                    f"score={existing_perf.avg_score:.2f}, "
                    f"success_rate={existing_perf.success_rate:.2f}, "
                    f"avg_time={existing_perf.avg_response_time:.2f}s")

    def get_routing_stats(self) -> Dict[str, Any]:
        """Получить статистику маршрутизации"""
        total_requests = sum(len(perfs) for perfs in self.performance_history.values())
        total_samples = sum(sum(perf.sample_count for perf in perfs)
                          for perfs in self.performance_history.values())

        return {
            "models_tracked": len(self.performance_history),
            "task_types_analyzed": len(set(perf.task_type
                                         for perfs in self.performance_history.values()
                                         for perf in perfs)),
            "total_performance_records": total_requests,
            "total_samples": total_samples,
            "cache_size": len(self.analysis_cache),
            "learning_enabled": self.learning_enabled
        }

    def reset_learning_data(self):
        """Сбросить данные обучения"""
        self.performance_history.clear()
        self.analysis_cache.clear()
        logger.info("Learning data reset")

    def enable_learning(self, enabled: bool = True):
        """Включить/выключить обучение"""
        self.learning_enabled = enabled
        logger.info(f"Learning {'enabled' if enabled else 'disabled'}")