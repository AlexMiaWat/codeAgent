"""
IntelligentEvaluator - интеллектуальная оценка качества ответов

Ответственность:
- Многофакторная оценка качества ответов
- Учет контекста и типа задач при оценке
- Сравнение с эталонными ответами
- Адаптивная оценка на основе обратной связи
- Детектирование специфических проблем (галлюцинации, неполнота и т.д.)
"""

import asyncio
import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter

from .types import (
    ModelConfig, EvaluationResult, IIntelligentEvaluator,
    IClientManager, GenerationRequest, ModelResponse
)

logger = logging.getLogger(__name__)


class QualityAspect(Enum):
    """Аспекты качества ответа"""
    ACCURACY = "accuracy"              # Точность и корректность
    COMPLETENESS = "completeness"      # Полнота ответа
    RELEVANCE = "relevance"           # Релевантность запросу
    CLARITY = "clarity"               # Ясность и понятность
    STRUCTURE = "structure"           # Структура и организация
    CREATIVITY = "creativity"          # Креативность (для творческих задач)
    TECHNICAL_ACCURACY = "technical_accuracy"  # Техническая точность
    SAFETY = "safety"                 # Безопасность и этичность
    EFFICIENCY = "efficiency"          # Эффективность решения


class EvaluationMethod(Enum):
    """Методы оценки"""
    LLM_BASED = "llm_based"           # Оценка через LLM
    RULE_BASED = "rule_based"         # Оценка по правилам
    HYBRID = "hybrid"                 # Комбинированная оценка
    COMPARATIVE = "comparative"       # Сравнительная оценка
    REFERENCE_BASED = "reference_based"  # Оценка по эталону


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


class IntelligentEvaluator(IIntelligentEvaluator):
    """
    Интеллектуальный оценщик ответов - многофакторная оценка качества

    Предоставляет:
    - Многоаспектную оценку качества
    - Учет контекста и типа задач
    - Детектирование специфических проблем
    - Адаптивную оценку на основе обучения
    """

    def __init__(self, evaluator_model: Optional[ModelConfig] = None):
        """
        Инициализация интеллектуального оценщика

        Args:
            evaluator_model: Модель для оценки (опционально)
        """
        self.evaluator_model = evaluator_model
        self.evaluation_history: Dict[str, List[DetailedEvaluation]] = defaultdict(list)
        self.evaluation_patterns = self._init_evaluation_patterns()
        self.quality_weights = self._init_quality_weights()
        self.learning_enabled = True

        # Кэш для оценки ответов
        self.evaluation_cache: Dict[str, DetailedEvaluation] = {}
        self.cache_max_size = 500

        logger.info("IntelligentEvaluator initialized")

    def _init_evaluation_patterns(self) -> Dict[str, List[EvaluationPattern]]:
        """Инициализация паттернов оценки для разных типов задач"""

        # Общие паттерны
        common_patterns = [
            EvaluationPattern(
                aspect=QualityAspect.ACCURACY,
                patterns=[
                    r"\b(correct|accurate|right|true)\b",
                    r"\b(incorrect|wrong|false|inaccurate)\b"
                ],
                keywords_positive={"correct", "accurate", "right", "true", "verified"},
                keywords_negative={"incorrect", "wrong", "false", "inaccurate", "mistake"}
            ),
            EvaluationPattern(
                aspect=QualityAspect.COMPLETENESS,
                patterns=[
                    r"\b(complete|comprehensive|thorough|detailed)\b",
                    r"\b(incomplete|partial|missing|insufficient)\b"
                ],
                keywords_positive={"complete", "comprehensive", "thorough", "detailed", "exhaustive"},
                keywords_negative={"incomplete", "partial", "missing", "insufficient", "brief"}
            ),
            EvaluationPattern(
                aspect=QualityAspect.CLARITY,
                patterns=[
                    r"\b(clear|understandable|concise|well.*explained)\b",
                    r"\b(unclear|confusing|vague|ambiguous)\b"
                ],
                keywords_positive={"clear", "understandable", "concise", "well-explained", "straightforward"},
                keywords_negative={"unclear", "confusing", "vague", "ambiguous", "complicated"}
            )
        ]

        # Паттерны для кода
        code_patterns = [
            EvaluationPattern(
                aspect=QualityAspect.TECHNICAL_ACCURACY,
                patterns=[
                    r"def\s+\w+\s*\(",
                    r"class\s+\w+",
                    r"import\s+\w+",
                    r"function\s+\w+",
                    r"```\w*\n.*\n```"
                ],
                keywords_positive={"syntax", "valid", "compilable", "working", "tested"},
                keywords_negative={"syntax error", "bug", "broken", "not working"}
            ),
            EvaluationPattern(
                aspect=QualityAspect.STRUCTURE,
                patterns=[
                    r"```.*\n",
                    r"#\s+\w+",
                    r"//.*\w+",
                    r"/\*\*.*\*/"
                ],
                keywords_positive={"structured", "organized", "readable", "maintainable"},
                keywords_negative={"messy", "unstructured", "hard to read"}
            )
        ]

        # Паттерны для JSON
        json_patterns = [
            EvaluationPattern(
                aspect=QualityAspect.STRUCTURE,
                patterns=[
                    r'\{.*\}',
                    r'".*":\s*["\[\{]',
                    r'\[.*\]'
                ],
                keywords_positive={"valid json", "well-formed", "schema-compliant"},
                keywords_negative={"invalid json", "malformed", "syntax error", "parsing error"}
            )
        ]

        # Паттерны для анализа
        analysis_patterns = [
            EvaluationPattern(
                aspect=QualityAspect.RELEVANCE,
                patterns=[
                    r"\b(data|analysis|insights|findings)\b",
                    r"\b(conclusion|summary|recommendation)\b"
                ],
                keywords_positive={"data-driven", "evidence-based", "insightful", "comprehensive"},
                keywords_negative={"irrelevant", "off-topic", "missing data"}
            )
        ]

        return {
            "code_generation": common_patterns + code_patterns,
            "code_review": common_patterns + code_patterns,
            "json_generation": common_patterns + json_patterns,
            "analysis": common_patterns + analysis_patterns,
            "question_answering": common_patterns,
            "creative_writing": common_patterns,
            "technical_writing": common_patterns,
            "math_problem": common_patterns,
            "default": common_patterns
        }

    def _init_quality_weights(self) -> Dict[str, Dict[QualityAspect, float]]:
        """Инициализация весов качества для разных типов задач"""

        return {
            "code_generation": {
                QualityAspect.TECHNICAL_ACCURACY: 0.4,
                QualityAspect.COMPLETENESS: 0.25,
                QualityAspect.CLARITY: 0.2,
                QualityAspect.STRUCTURE: 0.15
            },
            "code_review": {
                QualityAspect.TECHNICAL_ACCURACY: 0.35,
                QualityAspect.RELEVANCE: 0.3,
                QualityAspect.CLARITY: 0.2,
                QualityAspect.COMPLETENESS: 0.15
            },
            "json_generation": {
                QualityAspect.STRUCTURE: 0.5,
                QualityAspect.ACCURACY: 0.3,
                QualityAspect.COMPLETENESS: 0.2
            },
            "analysis": {
                QualityAspect.RELEVANCE: 0.3,
                QualityAspect.ACCURACY: 0.25,
                QualityAspect.COMPLETENESS: 0.25,
                QualityAspect.CLARITY: 0.2
            },
            "question_answering": {
                QualityAspect.ACCURACY: 0.4,
                QualityAspect.RELEVANCE: 0.3,
                QualityAspect.CLARITY: 0.2,
                QualityAspect.COMPLETENESS: 0.1
            },
            "math_problem": {
                QualityAspect.ACCURACY: 0.6,
                QualityAspect.COMPLETENESS: 0.3,
                QualityAspect.CLARITY: 0.1
            },
            "creative_writing": {
                QualityAspect.CREATIVITY: 0.4,
                QualityAspect.CLARITY: 0.3,
                QualityAspect.STRUCTURE: 0.2,
                QualityAspect.RELEVANCE: 0.1
            },
            "technical_writing": {
                QualityAspect.CLARITY: 0.3,
                QualityAspect.ACCURACY: 0.25,
                QualityAspect.STRUCTURE: 0.25,
                QualityAspect.COMPLETENESS: 0.2
            },
            "default": {
                QualityAspect.ACCURACY: 0.3,
                QualityAspect.RELEVANCE: 0.25,
                QualityAspect.CLARITY: 0.25,
                QualityAspect.COMPLETENESS: 0.2
            }
        }

    async def evaluate_intelligent(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        task_type: str = "unknown",
        evaluation_context: Optional[EvaluationContext] = None,
        method: EvaluationMethod = EvaluationMethod.HYBRID
    ) -> DetailedEvaluation:
        """
        Интеллектуальная оценка ответа

        Args:
            prompt: Исходный запрос
            response: Ответ для оценки
            client_manager: Менеджер клиентов
            task_type: Тип задачи
            evaluation_context: Контекст оценки
            method: Метод оценки

        Returns:
            Детальная оценка ответа
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(prompt, response, task_type)
        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        # Создаем контекст оценки если не предоставлен
        if evaluation_context is None:
            evaluation_context = self._create_evaluation_context(prompt, response, task_type)

        # Выбираем метод оценки
        if method == EvaluationMethod.HYBRID:
            evaluation = await self._evaluate_hybrid(prompt, response, client_manager, evaluation_context)
        elif method == EvaluationMethod.LLM_BASED:
            evaluation = await self._evaluate_llm_based(prompt, response, client_manager, evaluation_context)
        elif method == EvaluationMethod.RULE_BASED:
            evaluation = await self._evaluate_rule_based(prompt, response, evaluation_context)
        elif method == EvaluationMethod.COMPARATIVE:
            evaluation = await self._evaluate_comparative(prompt, response, client_manager, evaluation_context)
        else:
            evaluation = await self._evaluate_hybrid(prompt, response, client_manager, evaluation_context)

        # Кэшируем результат
        if len(self.evaluation_cache) < self.cache_max_size:
            self.evaluation_cache[cache_key] = evaluation

        # Сохраняем в историю для обучения
        if self.learning_enabled:
            self.evaluation_history[task_type].append(evaluation)

        return evaluation

    def _get_cache_key(self, prompt: str, response: str, task_type: str) -> str:
        """Получить ключ для кэширования"""
        return f"{hash(prompt + response)}:{task_type}"

    def _create_evaluation_context(
        self,
        prompt: str,
        response: str,
        task_type: str
    ) -> EvaluationContext:
        """Создать контекст оценки на основе анализа запроса и ответа"""

        # Определяем ожидаемый формат
        expected_format = None
        if "json" in prompt.lower() or "{" in response.strip():
            expected_format = "json"
        elif any(code_marker in prompt.lower() for code_marker in ["def ", "class ", "function"]):
            expected_format = "code"
        elif any(analysis_marker in prompt.lower() for analysis_marker in ["analyze", "data", "statistics"]):
            expected_format = "analysis"

        # Извлекаем ключевые слова для определения домена
        domain_keywords = set()
        tech_keywords = ["programming", "code", "algorithm", "database", "api", "framework"]
        math_keywords = ["calculate", "solve", "equation", "formula", "mathematics"]
        business_keywords = ["business", "marketing", "sales", "strategy", "management"]

        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in tech_keywords):
            domain_keywords.update(["technology", "programming"])
        if any(kw in prompt_lower for kw in math_keywords):
            domain_keywords.update(["mathematics", "logic"])
        if any(kw in prompt_lower for kw in business_keywords):
            domain_keywords.update(["business", "management"])

        # Определяем требования к качеству
        quality_requirements = self.quality_weights.get(task_type, self.quality_weights["default"])

        return EvaluationContext(
            task_type=task_type,
            complexity_level=self._assess_response_complexity(response),
            expected_format=expected_format,
            domain_knowledge=domain_keywords,
            quality_requirements=quality_requirements
        )

    def _assess_response_complexity(self, response: str) -> str:
        """Оценить сложность ответа"""
        length = len(response)
        sentences = len(re.findall(r'[.!?]+', response))
        technical_terms = len(re.findall(r'\b\w{8,}\b', response))

        if length > 2000 or technical_terms > 15:
            return "very_complex"
        elif length > 1000 or technical_terms > 8:
            return "complex"
        elif length > 500 or sentences > 8:
            return "moderate"
        else:
            return "simple"

    async def _evaluate_hybrid(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        context: EvaluationContext
    ) -> DetailedEvaluation:
        """Гибридная оценка - комбинация LLM и rule-based"""

        # Rule-based оценка
        rule_evaluation = self._evaluate_rule_based(prompt, response, context)

        # LLM-based оценка (если доступна модель)
        llm_evaluation = None
        if self.evaluator_model:
            try:
                llm_evaluation = await self._evaluate_llm_based(prompt, response, client_manager, context)
            except Exception as e:
                logger.debug(f"LLM evaluation failed, using rule-based only: {e}")

        # Комбинируем оценки
        if llm_evaluation:
            # Взвешенное среднее: 60% LLM, 40% rules
            combined_score = 0.6 * llm_evaluation.overall_score + 0.4 * rule_evaluation.overall_score
            combined_aspects = {}

            # Комбинируем аспекты
            all_aspects = set(rule_evaluation.aspect_scores.keys()) | set(llm_evaluation.aspect_scores.keys())
            for aspect in all_aspects:
                rule_score = rule_evaluation.aspect_scores.get(aspect, 3.0)
                llm_score = llm_evaluation.aspect_scores.get(aspect, 3.0)
                combined_aspects[aspect] = 0.6 * llm_score + 0.4 * rule_score

            # Комбинируем проблемы и рекомендации
            issues = list(set(rule_evaluation.issues_detected + llm_evaluation.issues_detected))
            strengths = list(set(rule_evaluation.strengths + llm_evaluation.strengths))
            recommendations = list(set(rule_evaluation.recommendations + llm_evaluation.recommendations))

            confidence = min(rule_evaluation.confidence, llm_evaluation.confidence) * 1.2  # Бонус за комбинацию

            return DetailedEvaluation(
                overall_score=combined_score,
                aspect_scores=combined_aspects,
                confidence=min(confidence, 1.0),
                method_used=EvaluationMethod.HYBRID,
                reasoning=f"Hybrid evaluation: LLM ({llm_evaluation.overall_score:.2f}) + Rules ({rule_evaluation.overall_score:.2f})",
                issues_detected=issues,
                strengths=strengths,
                recommendations=recommendations
            )
        else:
            return rule_evaluation

    async def _evaluate_llm_based(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        context: EvaluationContext
    ) -> DetailedEvaluation:
        """Оценка через LLM"""

        if not self.evaluator_model:
            raise ValueError("No evaluator model available for LLM-based evaluation")

        # Создаем детальный промпт для оценки
        evaluation_prompt = self._create_detailed_evaluation_prompt(prompt, response, context)

        try:
            model_response = await client_manager.call_model(
                model_config=self.evaluator_model,
                prompt=evaluation_prompt
            )

            if not model_response.success:
                raise ValueError(f"Evaluator model failed: {model_response.error}")

            # Парсим детальный ответ
            return self._parse_detailed_evaluation_response(model_response.content, context)

        except Exception as e:
            logger.warning(f"LLM-based evaluation failed: {e}")
            # Fallback на rule-based
            return self._evaluate_rule_based(prompt, response, context)

    def _evaluate_rule_based(
        self,
        prompt: str,
        response: str,
        context: EvaluationContext
    ) -> DetailedEvaluation:
        """Rule-based оценка по паттернам"""

        aspect_scores = {}
        issues = []
        strengths = []
        recommendations = []

        # Получаем паттерны для типа задачи
        patterns = self.evaluation_patterns.get(context.task_type, self.evaluation_patterns["default"])

        for pattern in patterns:
            score = self._evaluate_aspect_by_pattern(response, pattern, context)
            aspect_scores[pattern.aspect] = score

            # Детектируем проблемы и сильные стороны
            if score < 2.5:
                issues.append(f"Low {pattern.aspect.value} score: {score:.1f}")
            elif score > 4.0:
                strengths.append(f"Strong {pattern.aspect.value}")

        # Вычисляем общий score на основе весов
        weights = context.quality_requirements
        total_weight = sum(weights.values()) if weights else len(aspect_scores)

        if weights and aspect_scores:
            overall_score = sum(
                score * weights.get(aspect, 1.0)
                for aspect, score in aspect_scores.items()
            ) / total_weight
        else:
            overall_score = sum(aspect_scores.values()) / len(aspect_scores) if aspect_scores else 3.0

        # Генерируем рекомендации
        recommendations = self._generate_rule_based_recommendations(aspect_scores, context)

        return DetailedEvaluation(
            overall_score=overall_score,
            aspect_scores=aspect_scores,
            confidence=0.8,  # Rule-based обычно менее уверена чем LLM
            method_used=EvaluationMethod.RULE_BASED,
            reasoning="Rule-based evaluation using predefined patterns",
            issues_detected=issues,
            strengths=strengths,
            recommendations=recommendations
        )

    async def _evaluate_comparative(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        context: EvaluationContext
    ) -> DetailedEvaluation:
        """Сравнительная оценка с эталонными ответами"""

        if not context.reference_answers:
            # Нет эталонов, fallback на обычную оценку
            return await self._evaluate_llm_based(prompt, response, client_manager, context)

        # Сравниваем с каждым эталонным ответом
        comparison_prompts = []
        for ref_answer in context.reference_answers[:3]:  # Максимум 3 эталона
            comp_prompt = f"""Compare the following response with the reference answer:

Prompt: {prompt}

Response to evaluate: {response}

Reference answer: {ref_answer}

Rate the response on a scale of 1-5 based on how well it matches the quality and accuracy of the reference answer.
Consider: correctness, completeness, clarity, and relevance.

Score: [1-5]
Reasoning: [brief explanation]"""
            comparison_prompts.append(comp_prompt)

        # Получаем оценки
        scores = []
        reasonings = []

        for comp_prompt in comparison_prompts:
            try:
                comp_response = await client_manager.call_model(
                    model_config=self.evaluator_model,
                    prompt=comp_prompt
                )

                if comp_response.success:
                    score, reasoning = self._parse_simple_evaluation(comp_response.content)
                    scores.append(score)
                    reasonings.append(reasoning)
            except Exception as e:
                logger.debug(f"Comparative evaluation failed: {e}")

        if not scores:
            # Fallback
            return await self._evaluate_llm_based(prompt, response, client_manager, context)

        avg_score = sum(scores) / len(scores)

        return DetailedEvaluation(
            overall_score=avg_score,
            confidence=0.9,
            method_used=EvaluationMethod.COMPARATIVE,
            reasoning=f"Compared with {len(scores)} reference answers, average score: {avg_score:.2f}",
            recommendations=["Compare with reference answers for better quality"]
        )

    def _evaluate_aspect_by_pattern(
        self,
        response: str,
        pattern: EvaluationPattern,
        context: EvaluationContext
    ) -> float:
        """Оценить аспект по паттернам"""

        response_lower = response.lower()
        score = 3.0  # Базовый score

        # Проверяем положительные ключевые слова
        positive_matches = sum(1 for word in pattern.keywords_positive if word in response_lower)
        if positive_matches > 0:
            score += min(positive_matches * 0.3, 1.0)

        # Проверяем отрицательные ключевые слова
        negative_matches = sum(1 for word in pattern.keywords_negative if word in response_lower)
        if negative_matches > 0:
            score -= min(negative_matches * 0.5, 2.0)

        # Проверяем регулярные выражения
        pattern_matches = 0
        for regex in pattern.patterns:
            if re.search(regex, response, re.IGNORECASE | re.MULTILINE):
                pattern_matches += 1

        if pattern_matches > 0:
            score += min(pattern_matches * 0.2, 0.8)

        # Специфические проверки для разных аспектов
        if pattern.aspect == QualityAspect.TECHNICAL_ACCURACY and context.expected_format == "code":
            score += self._evaluate_code_quality(response)
        elif pattern.aspect == QualityAspect.STRUCTURE and context.expected_format == "json":
            score += self._evaluate_json_structure(response)

        return max(1.0, min(5.0, score))

    def _evaluate_code_quality(self, response: str) -> float:
        """Оценить качество кода"""
        bonus = 0.0

        # Проверяем на наличие основных элементов кода
        if re.search(r"def\s+\w+\s*\(", response):
            bonus += 0.3  # Функции
        if re.search(r"class\s+\w+", response):
            bonus += 0.3  # Классы
        if re.search(r"import\s+\w+", response):
            bonus += 0.2  # Импорты
        if re.search(r"#.*\w+", response):
            bonus += 0.2  # Комментарии

        # Проверяем на ошибки
        if "syntax error" in response.lower() or "error" in response.lower():
            bonus -= 0.5

        return bonus

    def _evaluate_json_structure(self, response: str) -> float:
        """Оценить структуру JSON"""
        bonus = 0.0

        try:
            # Пытаемся распарсить JSON
            json.loads(response.strip())
            bonus += 0.5  # Валидный JSON
        except json.JSONDecodeError:
            bonus -= 0.8  # Невалидный JSON

        # Проверяем на наличие ключей и значений
        if re.search(r'".*":\s*["\[\{]', response):
            bonus += 0.3

        return bonus

    def _create_detailed_evaluation_prompt(
        self,
        prompt: str,
        response: str,
        context: EvaluationContext
    ) -> str:
        """Создать детальный промпт для оценки"""

        aspects_text = ""
        weights = context.quality_requirements
        for aspect, weight in weights.items():
            aspects_text += f"- {aspect.value}: weight {weight}\n"

        task_info = f"Task type: {context.task_type}"
        if context.expected_format:
            task_info += f", Expected format: {context.expected_format}"
        if context.domain_knowledge:
            task_info += f", Domain: {', '.join(context.domain_knowledge)}"

        return f"""Please evaluate the quality of this response in detail.

{task_info}

Original prompt: {prompt}

Response to evaluate: {response}

Evaluate the response on the following aspects (1-5 scale):
{aspects_text}

Consider the context:
- Task complexity: {context.complexity_level}
- Domain knowledge required: {', '.join(context.domain_knowledge) if context.domain_knowledge else 'general'}

Provide your evaluation in this format:

OVERALL_SCORE: [1-5]
ACCURACY: [1-5] - [brief reasoning]
COMPLETENESS: [1-5] - [brief reasoning]
RELEVANCE: [1-5] - [brief reasoning]
CLARITY: [1-5] - [brief reasoning]
STRUCTURE: [1-5] - [brief reasoning]
ISSUES: [list of detected issues, or "none"]
STRENGTHS: [list of strengths]
RECOMMENDATIONS: [suggestions for improvement]

Be critical but fair. Focus on actual quality rather than style preferences."""

    def _parse_detailed_evaluation_response(self, content: str, context: EvaluationContext) -> DetailedEvaluation:
        """Распарсить детальный ответ оценки"""

        lines = content.strip().split('\n')
        aspect_scores = {}
        overall_score = 3.0
        issues = []
        strengths = []
        recommendations = []

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Парсим общий score
            if line.startswith('OVERALL_SCORE:'):
                try:
                    score_text = line.split(':', 1)[1].strip()
                    overall_score = float(re.search(r'(\d+(?:\.\d+)?)', score_text).group(1))
                except:
                    pass

            # Парсим аспекты
            elif ':' in line and not line.startswith(('ISSUES:', 'STRENGTHS:', 'RECOMMENDATIONS:')):
                try:
                    aspect_name, rest = line.split(':', 1)
                    aspect_name = aspect_name.strip().upper()

                    # Извлекаем score и reasoning
                    score_match = re.search(r'(\d+(?:\.\d+)?)', rest)
                    if score_match:
                        score = float(score_match.group(1))
                        # Маппинг на QualityAspect
                        for aspect in QualityAspect:
                            if aspect.value.upper() == aspect_name:
                                aspect_scores[aspect] = score
                                break
                except:
                    pass

            # Парсим списки
            elif line.startswith('ISSUES:'):
                current_section = 'issues'
            elif line.startswith('STRENGTHS:'):
                current_section = 'strengths'
            elif line.startswith('RECOMMENDATIONS:'):
                current_section = 'recommendations'
            elif current_section and line.startswith('-'):
                item = line[1:].strip()
                if current_section == 'issues' and item and item != "none":
                    issues.append(item)
                elif current_section == 'strengths' and item:
                    strengths.append(item)
                elif current_section == 'recommendations' and item:
                    recommendations.append(item)

        return DetailedEvaluation(
            overall_score=overall_score,
            aspect_scores=aspect_scores,
            confidence=0.95,  # LLM-based обычно более уверена
            method_used=EvaluationMethod.LLM_BASED,
            reasoning="LLM-based detailed evaluation",
            issues_detected=issues,
            strengths=strengths,
            recommendations=recommendations
        )

    def _parse_simple_evaluation(self, content: str) -> Tuple[float, str]:
        """Распарсить простой ответ оценки"""
        score = 3.0
        reasoning = "No reasoning provided"

        lines = content.strip().split('\n')
        for line in lines:
            if line.startswith('Score:'):
                try:
                    score_text = line.split(':', 1)[1].strip()
                    score = float(re.search(r'(\d+(?:\.\d+)?)', score_text).group(1))
                    score = max(1.0, min(5.0, score))
                except:
                    pass
            elif line.startswith('Reasoning:'):
                reasoning = line.split(':', 1)[1].strip()

        return score, reasoning

    def _generate_rule_based_recommendations(
        self,
        aspect_scores: Dict[QualityAspect, float],
        context: EvaluationContext
    ) -> List[str]:
        """Сгенерировать рекомендации на основе rule-based оценки"""

        recommendations = []

        for aspect, score in aspect_scores.items():
            if score < 3.0:
                if aspect == QualityAspect.ACCURACY:
                    recommendations.append("Focus on providing more accurate and correct information")
                elif aspect == QualityAspect.COMPLETENESS:
                    recommendations.append("Provide more complete and comprehensive answers")
                elif aspect == QualityAspect.CLARITY:
                    recommendations.append("Improve clarity and readability of the response")
                elif aspect == QualityAspect.RELEVANCE:
                    recommendations.append("Ensure the response is more relevant to the query")
                elif aspect == QualityAspect.STRUCTURE:
                    if context.expected_format == "json":
                        recommendations.append("Ensure proper JSON structure and formatting")
                    elif context.expected_format == "code":
                        recommendations.append("Improve code structure and organization")
                    else:
                        recommendations.append("Better organize the response structure")
                elif aspect == QualityAspect.TECHNICAL_ACCURACY:
                    recommendations.append("Verify technical accuracy and correctness")

        if context.expected_format and not any(rec.lower().find(context.expected_format) != -1 for rec in recommendations):
            recommendations.append(f"Follow the expected {context.expected_format} format")

        return recommendations[:3]  # Максимум 3 рекомендации

    # Legacy method for backward compatibility
    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        client_manager: 'IClientManager',
        evaluator_model: Optional[ModelConfig] = None
    ) -> EvaluationResult:
        """Устаревший метод для обратной совместимости"""
        detailed_eval = await self.evaluate_intelligent(
            prompt, response, client_manager,
            task_type="unknown"
        )

        return EvaluationResult(
            score=detailed_eval.overall_score,
            reasoning=detailed_eval.reasoning
        )

    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Получить статистику оценок"""
        total_evaluations = sum(len(evals) for evals in self.evaluation_history.values())

        task_stats = {}
        for task_type, evaluations in self.evaluation_history.items():
            if evaluations:
                scores = [e.overall_score for e in evaluations]
                task_stats[task_type] = {
                    'count': len(evaluations),
                    'avg_score': sum(scores) / len(scores),
                    'min_score': min(scores),
                    'max_score': max(scores)
                }

        return {
            'total_evaluations': total_evaluations,
            'tasks_evaluated': len(self.evaluation_history),
            'cache_size': len(self.evaluation_cache),
            'learning_enabled': self.learning_enabled,
            'task_statistics': task_stats
        }

    def reset_evaluation_history(self):
        """Сбросить историю оценок"""
        self.evaluation_history.clear()
        self.evaluation_cache.clear()
        logger.info("Evaluation history reset")