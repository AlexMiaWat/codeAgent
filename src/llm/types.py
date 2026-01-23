"""
Общие типы и интерфейсы для LLM модулей

Этот модуль содержит:
- Перечисления и типы данных
- Абстрактные интерфейсы для компонентов
- Общие структуры данных
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Protocol, Set
from pathlib import Path
from datetime import datetime


class ModelRole(Enum):
    """Роли моделей"""
    PRIMARY = "primary"      # Рабочие модели
    DUPLICATE = "duplicate"  # Дублирующие модели
    RESERVE = "reserve"      # Резервные модели
    FALLBACK = "fallback"    # Модели на случай полного отказа


@dataclass
class ModelConfig:
    """Конфигурация модели"""
    name: str
    max_tokens: int
    context_window: int
    temperature: float = 0.7
    top_p: float = 1.0
    role: ModelRole = ModelRole.PRIMARY
    enabled: bool = True
    last_response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0


@dataclass
class ModelResponse:
    """Ответ модели"""
    model_name: str
    content: str
    response_time: float
    success: bool
    error: Optional[str] = None
    score: Optional[float] = None


@dataclass
class ProviderConfig:
    """Конфигурация провайдера"""
    name: str
    base_url: str
    api_key: str
    models: List[Dict[str, Any]]
    timeout: int = 200


@dataclass
class GenerationRequest:
    """Запрос на генерацию"""
    prompt: str
    model_name: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    use_parallel: bool = False
    use_fastest: bool = True


@dataclass
class EvaluationResult:
    """Результат оценки ответа"""
    score: float
    reasoning: Optional[str] = None


@dataclass
class RoutingDecision:
    """Решение о маршрутизации"""
    model_name: str
    strategy: str
    reasoning: str
    confidence: float
    alternatives: List[str] = field(default_factory=list)


# Типы для интеллектуального роутера
class TaskType(Enum):
    """Типы задач для классификации запросов"""
    CREATIVE_WRITING = "creative_writing"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ANALYSIS = "analysis"
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    MATH_PROBLEM = "math_problem"
    LOGIC_REASONING = "logic_reasoning"
    CHAT_CONVERSATION = "chat_conversation"
    JSON_GENERATION = "json_generation"
    TECHNICAL_WRITING = "technical_writing"
    UNKNOWN = "unknown"


class ComplexityLevel(Enum):
    """Уровень сложности запроса"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class RequestAnalysis:
    """Анализ запроса"""
    task_type: TaskType
    complexity: ComplexityLevel
    estimated_tokens: int
    requires_accuracy: bool = False
    requires_creativity: bool = False
    requires_speed: bool = False
    is_structured: bool = False
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


# Интерфейсы компонентов

class IModelRegistry(Protocol):
    """Интерфейс реестра моделей"""

    def get_models_by_role(self, role: ModelRole) -> List[ModelConfig]:
        """Получить модели по роли"""
        ...

    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Получить модель по имени"""
        ...

    def get_all_models(self) -> List[ModelConfig]:
        """Получить все модели"""
        ...

    def update_model_stats(self, model_name: str, success: bool, response_time: float) -> None:
        """Обновить статистику модели"""
        ...

    def get_fastest_model(self, role: ModelRole = ModelRole.PRIMARY) -> Optional[ModelConfig]:
        """Получить самую быструю модель"""
        ...

    def disable_model(self, model_name: str) -> None:
        """Отключить модель"""
        ...

    def enable_model(self, model_name: str) -> None:
        """Включить модель"""
        ...


class IClientManager(Protocol):
    """Интерфейс менеджера клиентов"""

    async def call_model(
        self,
        model_config: ModelConfig,
        prompt: str,
        response_format: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        """Вызвать модель"""
        ...


class IStrategyManager(Protocol):
    """Интерфейс менеджера стратегий генерации"""

    async def generate(
        self,
        request: GenerationRequest,
        registry: IModelRegistry,
        client_manager: IClientManager
    ) -> ModelResponse:
        """Выполнить генерацию по стратегии"""
        ...


class IResponseEvaluator(Protocol):
    """Интерфейс оценщика ответов"""

    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> EvaluationResult:
        """Оценить ответ"""
        ...

    async def compare_responses(
        self,
        prompt: str,
        responses: List[str],
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> List[EvaluationResult]:
        """Сравнить несколько ответов"""
        ...

    async def select_best_response(
        self,
        prompt: str,
        responses: List[str],
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> tuple[int, EvaluationResult]:
        """Выбрать лучший ответ"""
        ...


class IJsonValidator(Protocol):
    """Интерфейс валидатора JSON"""

    def validate_json(self, content: str) -> bool:
        """Проверить валидность JSON"""
        ...

    def extract_json_from_text(self, text: str) -> Optional[str]:
        """Извлечь JSON из текста"""
        ...

    def validate_and_extract(self, content: str) -> tuple[bool, Optional[str]]:
        """Проверить и извлечь JSON из контента"""
        ...


class IHealthMonitor(Protocol):
    """Интерфейс монитора здоровья"""

    async def check_health(self) -> Dict[str, bool]:
        """Проверить здоровье моделей"""
        ...

    def disable_model(self, model_name: str) -> None:
        """Отключить модель"""
        ...

    def enable_model(self, model_name: str) -> None:
        """Включить модель"""
        ...


class IConfigLoader(Protocol):
    """Интерфейс загрузчика конфигурации"""

    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """Загрузить конфигурацию"""
        ...

    def substitute_env_vars(self, obj: Any) -> Any:
        """Подставить переменные окружения"""
        ...


class IIntelligentRouter(Protocol):
    """Интерфейс интеллектуального роутера"""

    def analyze_request(self, request: GenerationRequest) -> 'RequestAnalysis':
        """Анализировать запрос"""
        ...

    def route_request(self, request: GenerationRequest) -> 'RoutingDecision':
        """Определить маршрут для запроса"""
        ...

    def learn_from_result(
        self,
        request: GenerationRequest,
        response: ModelResponse,
        evaluation_score: Optional[float] = None
    ) -> None:
        """Обучаться на результате"""
        ...


class IIntelligentEvaluator(Protocol):
    """Интерфейс интеллектуального оценщика"""

    async def evaluate_intelligent(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        task_type: str = "unknown",
        evaluation_context: Optional['EvaluationContext'] = None,
        method: 'EvaluationMethod' = 'EvaluationMethod.HYBRID'
    ) -> 'DetailedEvaluation':
        """Интеллектуальная оценка ответа"""
        ...

    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> EvaluationResult:
        """Устаревший метод для совместимости"""
        ...


class IAdaptiveStrategyManager(Protocol):
    """Интерфейс адаптивного менеджера стратегий"""

    async def generate_adaptive(self, request: GenerationRequest) -> ModelResponse:
        """Адаптивная генерация"""
        ...

    def get_adaptive_stats(self) -> Dict[str, Any]:
        """Получить статистику адаптивного менеджера"""
        ...

    def get_strategy_recommendations(self, task_type: str) -> List[Dict[str, Any]]:
        """Получить рекомендации по стратегиям"""
        ...


class IErrorLearningSystem(Protocol):
    """Интерфейс системы обучения на ошибках"""

    async def analyze_and_learn_from_error(
        self,
        request_prompt: str,
        model_name: str,
        response: Optional[ModelResponse] = None,
        error_message: Optional[str] = None,
        task_type: str = "unknown"
    ) -> None:
        """Анализировать ошибку и обучаться"""
        ...

    def get_learning_stats(self) -> Dict[str, Any]:
        """Получить статистику обучения"""
        ...

    def get_error_prevention_recommendations(self, request_prompt: str, task_type: str = "unknown") -> List[str]:
        """Получить рекомендации по предотвращению ошибок"""
        ...


# Типы для адаптивной стратегии
class StrategyType(Enum):
    """Типы стратегий генерации"""
    SINGLE = "single"
    PARALLEL = "parallel"
    FALLBACK = "fallback"
    ADAPTIVE = "adaptive"
    CONSENSUS = "consensus"
    ITERATIVE = "iterative"


@dataclass
class StrategyPerformance:
    """Производительность стратегии для конкретного типа задач"""
    strategy: StrategyType
    task_type: str
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
    trigger: str  # Из adaptive_strategy.AdaptationTrigger
    current_strategy: StrategyType
    performance_metrics: Dict[str, float]
    task_characteristics: Dict[str, Any]
    historical_performance: List[StrategyPerformance]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearningInsight:
    """Инсайт обучения"""
    insight_type: str
    description: str
    confidence: float
    affected_components: List[str]
    recommended_actions: List[str]
    expected_impact: str
    timestamp: datetime = field(default_factory=datetime.now)


# Типы для интеллектуального оценщика
class QualityAspect(Enum):
    """Аспекты качества ответа"""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    CLARITY = "clarity"
    STRUCTURE = "structure"
    CREATIVITY = "creativity"
    TECHNICAL_ACCURACY = "technical_accuracy"
    SAFETY = "safety"
    EFFICIENCY = "efficiency"


class EvaluationMethod(Enum):
    """Методы оценки"""
    LLM_BASED = "llm_based"
    RULE_BASED = "rule_based"
    HYBRID = "hybrid"
    COMPARATIVE = "comparative"
    REFERENCE_BASED = "reference_based"


@dataclass
class DetailedEvaluation:
    """Детальная оценка ответа"""
    overall_score: float
    aspect_scores: Dict[QualityAspect, float] = field(default_factory=dict)
    confidence: float = 1.0
    method_used: EvaluationMethod = EvaluationMethod.HYBRID
    reasoning: str = ""
    issues_detected: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationContext:
    """Контекст оценки"""
    task_type: str
    complexity_level: str
    expected_format: Optional[str] = None
    domain_knowledge: Set[str] = field(default_factory=set)
    quality_requirements: Dict[QualityAspect, float] = field(default_factory=dict)
    reference_answers: List[str] = field(default_factory=list)


@dataclass
class EvaluationPattern:
    """Паттерн для оценки"""
    aspect: QualityAspect
    patterns: List[str] = field(default_factory=list)
    keywords_positive: Set[str] = field(default_factory=set)
    keywords_negative: Set[str] = field(default_factory=set)
    weight: float = 1.0


# Типы для системы обучения на ошибках
class ErrorType(Enum):
    """Типы ошибок"""
    API_ERROR = "api_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    CONTENT_POLICY_ERROR = "content_policy_error"
    INVALID_RESPONSE = "invalid_response"
    LOW_QUALITY = "low_quality"
    HALLUCINATION = "hallucination"
    INCOMPLETE_RESPONSE = "incomplete_response"
    IRRELEVANT_RESPONSE = "irrelevant_response"
    FORMATTING_ERROR = "formatting_error"
    NETWORK_ERROR = "network_error"


class ErrorPattern(Enum):
    """Паттерны ошибок"""
    MODEL_OVERLOAD = "model_overload"
    CONTEXT_TOO_LONG = "context_too_long"
    COMPLEX_QUERY = "complex_query"
    UNSUPPORTED_FORMAT = "unsupported_format"
    SENSITIVE_CONTENT = "sensitive_content"
    AMBIGUOUS_REQUEST = "ambiguous_request"
    RESOURCE_EXHAUSTED = "resource_exhausted"


@dataclass
class ErrorAnalysis:
    """Анализ ошибки"""
    error_type: ErrorType
    error_pattern: Optional[ErrorPattern] = None
    severity: float = 1.0
    confidence: float = 0.0
    root_cause: str = ""
    suggested_fix: str = ""
    prevention_measures: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Запись об ошибке"""
    timestamp: datetime
    request_prompt: str
    model_name: str
    response: Optional[ModelResponse] = None
    error_analysis: Optional[ErrorAnalysis] = None
    task_type: str = "unknown"
    retry_successful: bool = False
    user_feedback: Optional[str] = None


@dataclass
class ErrorPatternStats:
    """Статистика паттерна ошибок"""
    pattern: ErrorPattern
    occurrences: int = 0
    affected_models: Set[str] = field(default_factory=set)
    affected_task_types: Set[str] = field(default_factory=set)
    avg_severity: float = 0.0
    last_occurrence: Optional[datetime] = None
    mitigation_attempts: int = 0
    mitigation_success_rate: float = 0.0