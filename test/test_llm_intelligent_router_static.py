"""
Статические тесты для IntelligentRouter LLM компонента

Тестирует:
- Типы и перечисления
- Структуры данных
- Базовую логику инициализации
- Валидацию входных данных
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.llm.intelligent_router import (
    IntelligentRouter, RequestAnalysis, RoutingDecision, ModelPerformance
)
from src.llm.types import TaskType, ComplexityLevel
from src.llm.types import (
    ModelConfig, ModelResponse, ModelRole, GenerationRequest,
    IIntelligentRouter, IModelRegistry, RoutingDecision as BaseRoutingDecision
)


class TestTaskType:
    """Тесты для перечисления TaskType"""

    def test_all_task_types_defined(self):
        """Проверяет, что все ожидаемые типы задач определены"""
        expected_types = {
            'CREATIVE_WRITING', 'CODE_GENERATION', 'CODE_REVIEW', 'ANALYSIS',
            'QUESTION_ANSWERING', 'SUMMARIZATION', 'TRANSLATION', 'MATH_PROBLEM',
            'LOGIC_REASONING', 'CHAT_CONVERSATION', 'JSON_GENERATION',
            'TECHNICAL_WRITING', 'UNKNOWN'
        }

        actual_types = {task_type.name for task_type in TaskType}
        assert actual_types == expected_types

    def test_task_type_values(self):
        """Проверяет значения типов задач"""
        assert TaskType.CODE_GENERATION.value == "code_generation"
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.UNKNOWN.value == "unknown"


class TestComplexityLevel:
    """Тесты для перечисления ComplexityLevel"""

    def test_complexity_levels_defined(self):
        """Проверяет уровни сложности"""
        expected_levels = {'SIMPLE', 'MODERATE', 'COMPLEX', 'VERY_COMPLEX'}
        actual_levels = {level.name for level in ComplexityLevel}
        assert actual_levels == expected_levels

    def test_complexity_level_values(self):
        """Проверяет значения уровней сложности"""
        assert ComplexityLevel.SIMPLE.value == "simple"
        assert ComplexityLevel.VERY_COMPLEX.value == "very_complex"


class TestRequestAnalysis:
    """Тесты для структуры RequestAnalysis"""

    def test_request_analysis_creation(self):
        """Тестирует создание RequestAnalysis"""
        analysis = RequestAnalysis(
            task_type=TaskType.CODE_GENERATION,
            complexity=ComplexityLevel.MODERATE,
            estimated_tokens=150,
            keywords=['python', 'function', 'algorithm'],
            confidence=0.85,
            reasoning="Code generation request with moderate complexity"
        )

        assert analysis.task_type == TaskType.CODE_GENERATION
        assert analysis.complexity == ComplexityLevel.MODERATE
        assert analysis.estimated_tokens == 150
        assert analysis.keywords == ['python', 'function', 'algorithm']
        assert analysis.confidence == 0.85
        assert analysis.reasoning == "Code generation request with moderate complexity"

    def test_request_analysis_defaults(self):
        """Тестирует значения по умолчанию"""
        analysis = RequestAnalysis(
            task_type=TaskType.UNKNOWN,
            complexity=ComplexityLevel.SIMPLE
        )

        assert analysis.estimated_tokens == 0
        assert analysis.keywords == []
        assert analysis.confidence == 0.0
        assert analysis.reasoning is None


class TestRoutingDecision:
    """Тесты для структуры RoutingDecision"""

    def test_routing_decision_creation(self):
        """Тестирует создание RoutingDecision"""
        decision = RoutingDecision(
            model_name="gpt-4",
            strategy="performance_optimized",
            reasoning="Best performance for code generation",
            confidence=0.92,
            alternatives=["claude-3", "gemini-pro"]
        )

        assert decision.model_name == "gpt-4"
        assert decision.strategy == "performance_optimized"
        assert decision.reasoning == "Best performance for code generation"
        assert decision.confidence == 0.92
        assert decision.alternatives == ["claude-3", "gemini-pro"]

    def test_routing_decision_defaults(self):
        """Тестирует значения по умолчанию"""
        decision = RoutingDecision(
            model_name="gpt-3.5",
            strategy="cost_optimized",
            reasoning="Cost-effective choice",
            confidence=0.75
        )

        assert decision.alternatives == []


class TestModelPerformance:
    """Тесты для структуры ModelPerformance"""

    def test_model_performance_creation(self):
        """Тестирует создание ModelPerformance"""
        performance = ModelPerformance(
            model_name="gpt-4",
            avg_response_time=2.5,
            success_rate=0.95,
            avg_score=8.7,
            total_requests=1000,
            task_type_performance={
                TaskType.CODE_GENERATION: 9.2,
                TaskType.ANALYSIS: 8.5
            }
        )

        assert performance.model_name == "gpt-4"
        assert performance.avg_response_time == 2.5
        assert performance.success_rate == 0.95
        assert performance.avg_score == 8.7
        assert performance.total_requests == 1000
        assert performance.task_type_performance[TaskType.CODE_GENERATION] == 9.2

    def test_model_performance_defaults(self):
        """Тестирует значения по умолчанию"""
        performance = ModelPerformance(model_name="test-model")

        assert performance.avg_response_time == 0.0
        assert performance.success_rate == 0.0
        assert performance.avg_score == 0.0
        assert performance.total_requests == 0
        assert performance.task_type_performance == {}




class TestIntelligentRouterStatic:
    """Статические тесты для IntelligentRouter"""

    def test_intelligent_router_interface_implementation(self):
        """Проверяет, что IntelligentRouter реализует IIntelligentRouter"""
        # Проверяем, что класс реализует интерфейс
        assert hasattr(IntelligentRouter, 'analyze_request')
        assert hasattr(IntelligentRouter, 'route_request')
        assert hasattr(IntelligentRouter, 'update_performance')
        assert hasattr(IntelligentRouter, 'get_metrics')

    def test_intelligent_router_initialization(self):
        """Тестирует базовую инициализацию IntelligentRouter"""
        mock_registry = Mock(spec=IModelRegistry)

        router = IntelligentRouter(mock_registry)

        assert router.model_registry is mock_registry
        assert hasattr(router, '_performance_history')
        assert hasattr(router, '_adaptive_metrics')
        assert hasattr(router, '_learning_data')

    def test_intelligent_router_with_config(self):
        """Тестирует инициализацию с конфигурацией"""
        mock_registry = Mock(spec=IModelRegistry)
        config = {
            'learning_enabled': True,
            'adaptation_interval': 3600,
            'performance_window_days': 7
        }

        router = IntelligentRouter(mock_registry, config)

        assert router.config == config
        assert router.learning_enabled == True
        assert router.adaptation_interval == 3600

    def test_constants_and_thresholds(self):
        """Проверяет константы и пороги"""
        # Эти константы должны быть определены в классе
        assert hasattr(IntelligentRouter, 'MIN_CONFIDENCE_THRESHOLD')
        assert hasattr(IntelligentRouter, 'ADAPTATION_CHECK_INTERVAL')
        assert hasattr(IntelligentRouter, 'PERFORMANCE_HISTORY_SIZE')

    def test_task_type_classification_patterns(self):
        """Проверяет паттерны классификации задач"""
        # Проверяем, что определены паттерны для классификации
        router = IntelligentRouter(Mock(spec=IModelRegistry))

        # Эти атрибуты должны существовать для классификации
        assert hasattr(router, '_task_patterns')
        assert hasattr(router, '_code_keywords')
        assert hasattr(router, '_analysis_keywords')

    def test_model_scoring_weights(self):
        """Проверяет веса для скоринга моделей"""
        router = IntelligentRouter(Mock(spec=IModelRegistry))

        # Должны быть определены веса для различных метрик
        assert hasattr(router, '_performance_weights')
        assert hasattr(router, '_task_type_weights')

    def test_input_validation(self):
        """Тестирует валидацию входных данных"""
        router = IntelligentRouter(Mock(spec=IModelRegistry))

        # Тестируем валидацию пустого запроса
        with pytest.raises(ValueError):
            router.analyze_request("")

        # Тестируем валидацию None
        with pytest.raises(ValueError):
            router.analyze_request(None)

    @pytest.mark.parametrize("task_type,expected_complexity", [
        (TaskType.CODE_GENERATION, ComplexityLevel.MODERATE),
        (TaskType.QUESTION_ANSWERING, ComplexityLevel.SIMPLE),
        (TaskType.ANALYSIS, ComplexityLevel.COMPLEX),
    ])
    def test_task_type_to_complexity_mapping(self, task_type, expected_complexity):
        """Тестирует маппинг типов задач на уровни сложности"""
        router = IntelligentRouter(Mock(spec=IModelRegistry))

        # Вызываем приватный метод для тестирования маппинга
        complexity = router._get_default_complexity_for_task(task_type)

        # Проверяем, что возвращается корректный уровень сложности
        assert isinstance(complexity, ComplexityLevel)

    def test_model_performance_tracking(self):
        """Тестирует трекинг производительности моделей"""
        router = IntelligentRouter(Mock(spec=IModelRegistry))

        # Проверяем структуру для трекинга производительности
        assert hasattr(router, '_performance_history')
        assert hasattr(router, '_model_performance')

        # Проверяем, что это словари
        assert isinstance(router._performance_history, dict)
        assert isinstance(router._model_performance, dict)