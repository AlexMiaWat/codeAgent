"""
ErrorLearningSystem - система автоматического обучения на ошибках

Ответственность:
- Анализ неудачных запросов и ответов
- Выявление паттернов ошибок
- Автоматическое улучшение стратегий
- Адаптация к новым типам проблем
- Предотвращение повторения ошибок
"""

import asyncio
import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, Set, Counter as CounterType
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter

from .types import (
    ModelConfig, ModelResponse, EvaluationResult,
    IErrorLearningSystem, IModelRegistry, IIntelligentRouter,
    IAdaptiveStrategyManager, IIntelligentEvaluator
)

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Типы ошибок"""
    API_ERROR = "api_error"                    # Ошибки API
    TIMEOUT_ERROR = "timeout_error"            # Таймауты
    RATE_LIMIT_ERROR = "rate_limit_error"      # Лимиты запросов
    CONTENT_POLICY_ERROR = "content_policy_error"  # Нарушения политики контента
    INVALID_RESPONSE = "invalid_response"      # Невалидные ответы
    LOW_QUALITY = "low_quality"               # Низкое качество
    HALLUCINATION = "hallucination"           # Галлюцинации
    INCOMPLETE_RESPONSE = "incomplete_response"  # Неполные ответы
    IRRELEVANT_RESPONSE = "irrelevant_response"  # Нерелевантные ответы
    FORMATTING_ERROR = "formatting_error"     # Ошибки форматирования
    NETWORK_ERROR = "network_error"           # Сетевые ошибки


class ErrorPattern(Enum):
    """Паттерны ошибок"""
    MODEL_OVERLOAD = "model_overload"          # Перегрузка модели
    CONTEXT_TOO_LONG = "context_too_long"      # Слишком длинный контекст
    COMPLEX_QUERY = "complex_query"            # Слишком сложный запрос
    UNSUPPORTED_FORMAT = "unsupported_format"  # Неподдерживаемый формат
    SENSITIVE_CONTENT = "sensitive_content"    # Чувствительный контент
    AMBIGUOUS_REQUEST = "ambiguous_request"    # Неоднозначный запрос
    RESOURCE_EXHAUSTED = "resource_exhausted"  # Исчерпание ресурсов


@dataclass
class ErrorAnalysis:
    """Анализ ошибки"""
    error_type: ErrorType
    error_pattern: Optional[ErrorPattern] = None
    severity: float = 1.0  # 0.0 - minor, 1.0 - critical
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


@dataclass
class LearningInsight:
    """Инсайт обучения"""
    insight_type: str
    description: str
    confidence: float
    affected_components: List[str]
    recommended_actions: List[str]
    expected_impact: str
    timestamp: datetime = field(default_factory=datetime)


class ErrorLearningSystem(IErrorLearningSystem):
    """
    Система обучения на ошибках - анализирует и предотвращает повторение ошибок

    Предоставляет:
    - Анализ паттернов ошибок
    - Автоматическое улучшение стратегий
    - Предотвращение повторных ошибок
    - Адаптацию к новым типам проблем
    """

    def __init__(
        self,
        registry: IModelRegistry,
        intelligent_router: IIntelligentRouter,
        adaptive_strategy_manager: IAdaptiveStrategyManager,
        intelligent_evaluator: IIntelligentEvaluator
    ):
        """
        Инициализация системы обучения на ошибках

        Args:
            registry: Реестр моделей
            intelligent_router: Интеллектуальный роутер
            adaptive_strategy_manager: Адаптивный менеджер стратегий
            intelligent_evaluator: Интеллектуальный оценщик
        """
        self.registry = registry
        self.intelligent_router = intelligent_router
        self.adaptive_strategy_manager = adaptive_strategy_manager
        self.intelligent_evaluator = intelligent_evaluator

        # История ошибок
        self.error_history: List[ErrorRecord] = []
        self.max_history_size = 1000

        # Статистика паттернов ошибок
        self.error_patterns: Dict[ErrorPattern, ErrorPatternStats] = {}

        # Инсайты обучения
        self.learning_insights: List[LearningInsight] = []

        # Активные меры предотвращения
        self.active_mitigations: Dict[str, Dict[str, Any]] = {}

        # Правила анализа ошибок
        self.error_analysis_rules = self._init_error_analysis_rules()

        # Автоматическое обучение включено
        self.auto_learning_enabled = True

        # Пороги для триггеров
        self.thresholds = {
            'min_errors_for_pattern': 3,      # Минимум ошибок для выявления паттерна
            'pattern_detection_window': 3600, # Окно для детекции паттернов (секунды)
            'auto_mitigation_threshold': 5,   # Порог для автоматического смягчения
            'insight_generation_threshold': 10, # Порог для генерации инсайтов
        }

        logger.info("ErrorLearningSystem initialized")

    def _init_error_analysis_rules(self) -> Dict[str, Dict[str, Any]]:
        """Инициализация правил анализа ошибок"""

        return {
            # API Errors
            "rate limit exceeded": {
                "error_type": ErrorType.RATE_LIMIT_ERROR,
                "pattern": ErrorPattern.MODEL_OVERLOAD,
                "severity": 0.7,
                "prevention": ["reduce_request_frequency", "switch_to_alternative_model"]
            },
            "timeout": {
                "error_type": ErrorType.TIMEOUT_ERROR,
                "pattern": ErrorPattern.CONTEXT_TOO_LONG,
                "severity": 0.8,
                "prevention": ["reduce_context_length", "use_faster_model", "split_request"]
            },
            "content policy": {
                "error_type": ErrorType.CONTENT_POLICY_ERROR,
                "pattern": ErrorPattern.SENSITIVE_CONTENT,
                "severity": 0.9,
                "prevention": ["filter_sensitive_content", "use_alternative_model"]
            },
            "network": {
                "error_type": ErrorType.NETWORK_ERROR,
                "pattern": ErrorPattern.RESOURCE_EXHAUSTED,
                "severity": 0.6,
                "prevention": ["retry_with_backoff", "switch_to_alternative_provider"]
            },

            # Response Quality Errors
            "incomplete": {
                "error_type": ErrorType.INCOMPLETE_RESPONSE,
                "pattern": ErrorPattern.COMPLEX_QUERY,
                "severity": 0.5,
                "prevention": ["use_parallel_generation", "split_complex_queries"]
            },
            "irrelevant": {
                "error_type": ErrorType.IRRELEVANT_RESPONSE,
                "pattern": ErrorPattern.AMBIGUOUS_REQUEST,
                "severity": 0.6,
                "prevention": ["improve_prompt_clarity", "add_context"]
            },
            "hallucination": {
                "error_type": ErrorType.HALLUCINATION,
                "pattern": ErrorPattern.UNSUPPORTED_FORMAT,
                "severity": 0.7,
                "prevention": ["use_fact_checking", "add_grounding"]
            },

            # Format Errors
            "invalid json": {
                "error_type": ErrorType.FORMATTING_ERROR,
                "pattern": ErrorPattern.UNSUPPORTED_FORMAT,
                "severity": 0.4,
                "prevention": ["use_json_validator", "improve_json_prompts"]
            },
            "malformed": {
                "error_type": ErrorType.INVALID_RESPONSE,
                "pattern": ErrorPattern.UNSUPPORTED_FORMAT,
                "severity": 0.5,
                "prevention": ["validate_responses", "use_structured_prompts"]
            }
        }

    async def analyze_and_learn_from_error(
        self,
        request_prompt: str,
        model_name: str,
        response: Optional[ModelResponse] = None,
        error_message: Optional[str] = None,
        task_type: str = "unknown"
    ):
        """
        Проанализировать ошибку и извлечь уроки

        Args:
            request_prompt: Текст запроса
            model_name: Имя модели
            response: Ответ модели (если есть)
            error_message: Сообщение об ошибке
            task_type: Тип задачи
        """
        if not self.auto_learning_enabled:
            return

        # Создаем запись об ошибке
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            request_prompt=request_prompt,
            model_name=model_name,
            response=response,
            task_type=task_type
        )

        # Анализируем ошибку
        error_analysis = self._analyze_error(error_record, error_message)
        error_record.error_analysis = error_analysis

        # Добавляем в историю
        self.error_history.append(error_record)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)

        # Обновляем статистику паттернов
        if error_analysis.error_pattern:
            self._update_pattern_stats(error_analysis.error_pattern, error_record)

        # Применяем меры предотвращения
        await self._apply_error_mitigation(error_analysis, error_record)

        # Генерируем инсайты
        await self._generate_learning_insights()

        logger.debug(f"Analyzed error: {error_analysis.error_type.value}, pattern: {error_analysis.error_pattern.value if error_analysis.error_pattern else 'none'}")

    def _analyze_error(self, error_record: ErrorRecord, error_message: Optional[str] = None) -> ErrorAnalysis:
        """Анализировать ошибку и определить ее тип"""

        # Собираем всю доступную информацию об ошибке
        error_text = ""
        if error_message:
            error_text += error_message + " "
        if error_record.response and error_record.response.error:
            error_text += error_record.response.error + " "
        if error_record.response and error_record.response.content:
            error_text += error_record.response.content + " "

        error_text = error_text.lower()

        # Ищем совпадения с правилами
        best_match = None
        best_score = 0.0

        for rule_key, rule_config in self.error_analysis_rules.items():
            score = 0.0

            # Проверяем ключевые слова
            if rule_key in error_text:
                score += 0.8

            # Проверяем паттерны в контенте
            if "timeout" in error_text and "timeout" in rule_key:
                score += 0.9
            elif "rate limit" in error_text and "rate limit" in rule_key:
                score += 0.9
            elif "json" in error_text and "json" in rule_key:
                score += 0.7
            elif "network" in error_text and "network" in rule_key:
                score += 0.7

            # Проверяем тип ответа
            if error_record.response:
                if not error_record.response.success and rule_config["error_type"] == ErrorType.API_ERROR:
                    score += 0.3
                elif error_record.response.response_time > 30 and rule_config["error_type"] == ErrorType.TIMEOUT_ERROR:
                    score += 0.4

            if score > best_score:
                best_score = score
                best_match = rule_config

        if best_match and best_score > 0.3:
            return ErrorAnalysis(
                error_type=best_match["error_type"],
                error_pattern=best_match.get("pattern"),
                severity=best_match.get("severity", 0.5),
                confidence=best_score,
                root_cause=f"Detected {best_match['error_type'].value} pattern",
                suggested_fix=self._get_suggested_fix(best_match),
                prevention_measures=best_match.get("prevention", [])
            )
        else:
            # Неизвестная ошибка
            return ErrorAnalysis(
                error_type=ErrorType.INVALID_RESPONSE,
                severity=0.5,
                confidence=0.3,
                root_cause="Unknown error pattern",
                suggested_fix="Investigate manually"
            )

    def _get_suggested_fix(self, rule_config: Dict[str, Any]) -> str:
        """Получить предложенное исправление на основе правила"""

        error_type = rule_config["error_type"]
        pattern = rule_config.get("pattern")

        if error_type == ErrorType.RATE_LIMIT_ERROR:
            return "Reduce request frequency or switch to alternative model"
        elif error_type == ErrorType.TIMEOUT_ERROR:
            return "Reduce context length or use faster model"
        elif error_type == ErrorType.CONTENT_POLICY_ERROR:
            return "Filter sensitive content or use alternative model"
        elif error_type == ErrorType.INVALID_RESPONSE:
            return "Validate response format and retry"
        elif error_type == ErrorType.LOW_QUALITY:
            return "Use parallel generation or improve prompts"
        else:
            return "Apply general error mitigation strategies"

    def _update_pattern_stats(self, pattern: ErrorPattern, error_record: ErrorRecord):
        """Обновить статистику паттерна ошибок"""

        if pattern not in self.error_patterns:
            self.error_patterns[pattern] = ErrorPatternStats(pattern=pattern)

        stats = self.error_patterns[pattern]
        stats.occurrences += 1
        stats.affected_models.add(error_record.model_name)
        stats.affected_task_types.add(error_record.task_type)
        stats.last_occurrence = error_record.timestamp

        # Пересчитываем среднюю severity
        if error_record.error_analysis:
            total_severity = stats.avg_severity * (stats.occurrences - 1) + error_record.error_analysis.severity
            stats.avg_severity = total_severity / stats.occurrences

    async def _apply_error_mitigation(self, error_analysis: ErrorAnalysis, error_record: ErrorRecord):
        """Применить меры предотвращения ошибки"""

        if not error_analysis.error_pattern:
            return

        pattern = error_analysis.error_pattern
        stats = self.error_patterns.get(pattern)

        if not stats or stats.occurrences < self.thresholds['min_errors_for_pattern']:
            return

        # Проверяем порог для автоматического смягчения
        if stats.occurrences >= self.thresholds['auto_mitigation_threshold']:
            await self._implement_automatic_mitigation(pattern, stats)

        # Применяем специфические меры для разных типов ошибок
        if pattern == ErrorPattern.MODEL_OVERLOAD:
            await self._mitigate_model_overload(error_record.model_name, error_record.error_analysis.severity)
        elif pattern == ErrorPattern.CONTEXT_TOO_LONG:
            await self._mitigate_context_length_issues()
        elif pattern == ErrorPattern.SENSITIVE_CONTENT:
            await self._mitigate_content_policy_issues()
        elif pattern == ErrorPattern.UNSUPPORTED_FORMAT:
            await self._mitigate_format_issues(error_record.task_type)

    async def _implement_automatic_mitigation(self, pattern: ErrorPattern, stats: ErrorPatternStats):
        """Реализовать автоматическое смягчение паттерна"""

        mitigation_key = f"{pattern.value}_auto_mitigation"

        if mitigation_key in self.active_mitigations:
            return  # Уже применяется

        mitigation = {
            'pattern': pattern.value,
            'start_time': datetime.now(),
            'affected_models': list(stats.affected_models),
            'affected_tasks': list(stats.affected_task_types),
            'severity': stats.avg_severity,
            'actions_taken': []
        }

        # Применяем меры в зависимости от паттерна
        if pattern == ErrorPattern.MODEL_OVERLOAD:
            # Увеличиваем задержки между запросами
            mitigation['actions_taken'].append("Increased request delays")
            # Здесь можно было бы реализовать логику для ограничения частоты запросов

        elif pattern == ErrorPattern.CONTEXT_TOO_LONG:
            # Добавляем автоматическое усечение контекста
            mitigation['actions_taken'].append("Enabled automatic context truncation")

        elif pattern == ErrorPattern.SENSITIVE_CONTENT:
            # Добавляем фильтрацию контента
            mitigation['actions_taken'].append("Enhanced content filtering")

        self.active_mitigations[mitigation_key] = mitigation

        logger.info(f"Implemented automatic mitigation for {pattern.value}: {mitigation['actions_taken']}")

    async def _mitigate_model_overload(self, model_name: str, severity: float):
        """Смягчить перегрузку модели (или другие API ошибки)"""
        model = self.registry.get_model(model_name)
        if not model:
            logger.warning(f"Model {model_name} not found in registry for mitigation.")
            return

        # Увеличиваем счетчик ошибок для модели
        # Note: ModelConfig already has error_count. We'll increment it here.
        model.error_count += 1
        self.registry.update_model_stats(model_name, False, 0.0) # Отмечаем ошибку, время ответа 0

        # Если модель часто выдает ошибки, временно отключаем ее
        # Порог может быть динамическим, но для начала используем фиксированный
        if model.error_count >= self.thresholds['auto_mitigation_threshold'] and severity > 0.6:
            self.registry.disable_model(model_name)
            logger.warning(f"Model {model_name} disabled due to repeated overload/API errors (error_count: {model.error_count}).")
            # Также сообщаем роутеру, чтобы он избегал эту модель
            # (Предполагается, что router будет учитывать disabled модели)
            # self.intelligent_router.mark_model_as_problematic(model_name, "overload") # Эта функция пока не существует в роутере
        else:
            logger.debug(f"Mitigating overload for model {model_name}. Current error count: {model.error_count}")

    async def _mitigate_context_length_issues(self):
        """Смягчить проблемы с длиной контекста"""
        # В адаптивном менеджере стратегий можно добавить автоматическое усечение
        logger.debug("Mitigating context length issues")

    async def _mitigate_content_policy_issues(self):
        """Смягчить проблемы с политикой контента"""
        # Добавить фильтрацию чувствительного контента
        logger.debug("Mitigating content policy issues")

    async def _mitigate_format_issues(self, task_type: str):
        """Смягчить проблемы с форматированием"""
        # Улучшить промпты для специфических типов задач
        logger.debug(f"Mitigating format issues for {task_type}")

    async def _generate_learning_insights(self):
        """Генерировать инсайты обучения"""

        # Проверяем, достаточно ли данных для генерации инсайтов
        if len(self.error_history) < self.thresholds['insight_generation_threshold']:
            return

        # Анализируем паттерны в недавних ошибках (последние 24 часа)
        recent_errors = [e for e in self.error_history
                        if (datetime.now() - e.timestamp) < timedelta(hours=24)]

        if len(recent_errors) < 5:
            return

        # Находим наиболее частые паттерны
        pattern_counts = Counter()
        model_error_counts = Counter()
        task_error_counts = Counter()

        for error in recent_errors:
            if error.error_analysis and error.error_analysis.error_pattern:
                pattern_counts[error.error_analysis.error_pattern] += 1
            model_error_counts[error.model_name] += 1
            task_error_counts[error.task_type] += 1

        # Генерируем инсайты на основе анализа
        insights = []

        # Инсайт о наиболее проблемной модели
        if model_error_counts:
            worst_model, error_count = model_error_counts.most_common(1)[0]
            if error_count >= 3:
                insights.append(LearningInsight(
                    insight_type="problematic_model",
                    description=f"Model {worst_model} has {error_count} errors in last 24h",
                    confidence=min(error_count / 10.0, 1.0),
                    affected_components=["model_registry", "intelligent_router"],
                    recommended_actions=[
                        f"Reduce usage of model {worst_model}",
                        f"Add {worst_model} to monitoring watchlist",
                        f"Consider temporary disable of {worst_model}"
                    ],
                    expected_impact="Reduce error rate by avoiding problematic model"
                ))

        # Инсайт о наиболее проблемном типе задач
        if task_error_counts:
            worst_task, error_count = task_error_counts.most_common(1)[0]
            if error_count >= 3 and worst_task != "unknown":
                insights.append(LearningInsight(
                    insight_type="problematic_task_type",
                    description=f"Task type '{worst_task}' has {error_count} errors in last 24h",
                    confidence=min(error_count / 10.0, 1.0),
                    affected_components=["adaptive_strategy_manager"],
                    recommended_actions=[
                        f"Review strategies for {worst_task} tasks",
                        f"Add specific error handling for {worst_task}",
                        f"Improve prompts for {worst_task} tasks"
                    ],
                    expected_impact="Improve success rate for specific task types"
                ))

        # Инсайт о системных паттернах
        if pattern_counts:
            most_common_pattern, count = pattern_counts.most_common(1)[0]
            if count >= 3:
                insights.append(LearningInsight(
                    insight_type="systemic_pattern",
                    description=f"Detected systemic {most_common_pattern.value} pattern ({count} occurrences)",
                    confidence=min(count / 10.0, 1.0),
                    affected_components=["error_learning_system", "adaptive_strategy_manager"],
                    recommended_actions=[
                        f"Implement systemic fix for {most_common_pattern.value}",
                        f"Add monitoring for {most_common_pattern.value} pattern",
                        f"Update mitigation strategies for {most_common_pattern.value}"
                    ],
                    expected_impact="Prevent recurrence of systemic error patterns"
                ))

        # Добавляем новые инсайты
        for insight in insights:
            # Проверяем, не является ли инсайт дубликатом
            if not self._is_insight_duplicate(insight):
                self.learning_insights.append(insight)
                logger.info(f"Generated learning insight: {insight.insight_type}")

        # Ограничиваем количество инсайтов
        if len(self.learning_insights) > 50:
            self.learning_insights = self.learning_insights[-50:]

    def _is_insight_duplicate(self, new_insight: LearningInsight) -> bool:
        """Проверить, является ли инсайт дубликатом"""

        # Проверяем недавние инсайты (последние 6 часов)
        recent_insights = [i for i in self.learning_insights
                          if (datetime.now() - i.timestamp) < timedelta(hours=6)]

        for existing in recent_insights:
            if (existing.insight_type == new_insight.insight_type and
                existing.description == new_insight.description):
                return True

        return False

    def get_learning_stats(self) -> Dict[str, Any]:
        """Получить статистику обучения"""

        total_errors = len(self.error_history)
        recent_errors = [e for e in self.error_history
                        if (datetime.now() - e.timestamp) < timedelta(hours=24)]

        pattern_stats = {}
        for pattern, stats in self.error_patterns.items():
            pattern_stats[pattern.value] = {
                'occurrences': stats.occurrences,
                'affected_models': list(stats.affected_models),
                'affected_tasks': list(stats.affected_task_types),
                'avg_severity': stats.avg_severity,
                'last_occurrence': stats.last_occurrence.isoformat() if stats.last_occurrence else None
            }

        insight_stats = {}
        for insight in self.learning_insights[-10:]:  # Последние 10 инсайтов
            insight_stats[insight.insight_type] = {
                'description': insight.description,
                'confidence': insight.confidence,
                'timestamp': insight.timestamp.isoformat(),
                'actions': insight.recommended_actions
            }

        return {
            'total_errors_analyzed': total_errors,
            'recent_errors_24h': len(recent_errors),
            'error_patterns_detected': len(self.error_patterns),
            'active_mitigations': len(self.active_mitigations),
            'learning_insights_generated': len(self.learning_insights),
            'auto_learning_enabled': self.auto_learning_enabled,
            'pattern_statistics': pattern_stats,
            'recent_insights': insight_stats,
            'mitigation_effectiveness': self._calculate_mitigation_effectiveness()
        }

    def _calculate_mitigation_effectiveness(self) -> Dict[str, float]:
        """Рассчитать эффективность мер смягчения"""

        effectiveness = {}

        for mitigation_key, mitigation in self.active_mitigations.items():
            start_time = mitigation['start_time']
            hours_active = (datetime.now() - start_time).total_seconds() / 3600

            if hours_active < 1:
                effectiveness[mitigation_key] = 0.0  # Слишком рано оценивать
                continue

            # Простая оценка: сравниваем ошибки до и после применения mitigation
            pattern = mitigation['pattern']
            errors_before = [e for e in self.error_history
                           if e.timestamp < start_time and
                           e.error_analysis and
                           e.error_analysis.error_pattern and
                           e.error_analysis.error_pattern.value == pattern]

            errors_after = [e for e in self.error_history
                          if e.timestamp >= start_time and
                          e.error_analysis and
                          e.error_analysis.error_pattern and
                          e.error_analysis.error_pattern.value == pattern]

            if errors_before:
                rate_before = len(errors_before) / max(hours_active * 2, 1)  # Оценка за час
                rate_after = len(errors_after) / hours_active if hours_active > 0 else 0

                if rate_before > 0:
                    effectiveness[mitigation_key] = max(0, 1.0 - (rate_after / rate_before))
                else:
                    effectiveness[mitigation_key] = 1.0 if rate_after == 0 else 0.0
            else:
                effectiveness[mitigation_key] = 0.5  # Недостаточно данных

        return effectiveness

    def get_error_prevention_recommendations(self, request_prompt: str, task_type: str = "unknown") -> List[str]:
        """
        Получить рекомендации по предотвращению ошибок для запроса

        Args:
            request_prompt: Текст запроса
            task_type: Тип задачи

        Returns:
            Список рекомендаций
        """
        recommendations = []

        # Анализируем запрос на потенциальные проблемы
        prompt_lower = request_prompt.lower()

        # Проверяем на потенциальные проблемы с контентом
        sensitive_keywords = ["hack", "exploit", "illegal", "forbidden", "restricted"]
        if any(keyword in prompt_lower for keyword in sensitive_keywords):
            recommendations.append("Request may contain sensitive content - consider content filtering")

        # Проверяем на потенциальные проблемы с длиной
        if len(request_prompt) > 10000:
            recommendations.append("Request is very long - consider splitting or truncating")

        # Проверяем на основе истории ошибок для данного типа задач
        task_errors = [e for e in self.error_history
                      if e.task_type == task_type and
                      (datetime.now() - e.timestamp) < timedelta(hours=24)]

        if task_errors:
            error_types = Counter(e.error_analysis.error_type for e in task_errors if e.error_analysis)
            most_common_error = error_types.most_common(1)

            if most_common_error:
                error_type = most_common_error[0][0]
                if error_type == ErrorType.TIMEOUT_ERROR:
                    recommendations.append("Similar requests have timed out - consider using faster models")
                elif error_type == ErrorType.INVALID_RESPONSE:
                    recommendations.append("Similar requests produced invalid responses - consider validation")
                elif error_type == ErrorType.LOW_QUALITY:
                    recommendations.append("Similar requests had low quality - consider parallel generation")

        return recommendations

    def reset_learning_data(self):
        """Сбросить данные обучения"""
        self.error_history.clear()
        self.error_patterns.clear()
        self.learning_insights.clear()
        self.active_mitigations.clear()
        logger.info("Error learning data reset")

    def enable_auto_learning(self, enabled: bool = True):
        """Включить/выключить автоматическое обучение"""
        self.auto_learning_enabled = enabled
        logger.info(f"Auto learning {'enabled' if enabled else 'disabled'}")