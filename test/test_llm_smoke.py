"""
Дымовые тесты для LLM компонентов

Проверяют базовую работоспособность:
- Компоненты могут быть созданы без ошибок
- Базовые методы выполняются без исключений
- Компоненты правильно взаимодействуют друг с другом
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import asyncio
from typing import Dict, Any

from src.llm.intelligent_router import IntelligentRouter
from src.llm.manager import LLMManager
from src.llm.types import (
    ModelConfig, ModelResponse, GenerationRequest, RoutingDecision,
    IIntelligentRouter, IModelRegistry
)


class TestIntelligentRouterSmoke:
    """Дымовые тесты для IntelligentRouter"""

    def test_router_creation(self):
        """Проверяет, что роутер может быть создан"""
        mock_registry = Mock(spec=IModelRegistry)
        router = IntelligentRouter(mock_registry)

        assert router is not None
        assert hasattr(router, 'model_registry')
        assert router.model_registry is mock_registry

    def test_router_creation_with_config(self):
        """Проверяет создание роутера с конфигурацией"""
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

    def test_router_analyze_request_basic(self):
        """Проверяет базовую работу анализа запросов"""
        mock_registry = Mock(spec=IModelRegistry)
        router = IntelligentRouter(mock_registry)

        # Мокаем внутренние методы
        with patch.object(router, '_analyze_text', return_value={'task_type': 'code_generation'}), \
             patch.object(router, '_estimate_complexity', return_value=0.7), \
             patch.object(router, '_extract_keywords', return_value=['python', 'function']):

            result = router.analyze_request("Write a Python function to calculate fibonacci")

            assert result is not None
            assert hasattr(result, 'task_type')
            assert hasattr(result, 'complexity')
            assert hasattr(result, 'estimated_tokens')

    def test_router_analyze_request_empty_input(self):
        """Проверяет обработку пустого ввода"""
        mock_registry = Mock(spec=IModelRegistry)
        router = IntelligentRouter(mock_registry)

        with pytest.raises(ValueError):
            router.analyze_request("")

        with pytest.raises(ValueError):
            router.analyze_request(None)

    def test_router_route_request_basic(self):
        """Проверяет базовую работу маршрутизации"""
        mock_registry = Mock(spec=IModelRegistry)

        # Мокаем методы анализа
        with patch('src.llm.intelligent_router.IntelligentRouter.analyze_request') as mock_analyze, \
             patch('src.llm.intelligent_router.IntelligentRouter._select_best_model') as mock_select:

            mock_analyze.return_value = Mock(
                task_type=Mock(value='code_generation'),
                complexity=Mock(value='moderate'),
                estimated_tokens=150
            )
            mock_select.return_value = Mock(
                model_name='gpt-4',
                strategy='performance_optimized',
                reasoning='Best for code generation',
                confidence=0.9
            )

            router = IntelligentRouter(mock_registry)
            result = router.route_request("Write a Python function")

            assert result is not None
            assert hasattr(result, 'model_name')
            assert hasattr(result, 'strategy')
            assert hasattr(result, 'confidence')

    def test_router_update_performance(self):
        """Проверяет обновление производительности"""
        mock_registry = Mock(spec=IModelRegistry)
        router = IntelligentRouter(mock_registry)

        # Создаем моковый ответ модели
        model_response = ModelResponse(
            model_name="gpt-4",
            content="def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)",
            response_time=1.5,
            success=True
        )

        # Метод должен выполниться без ошибок
        router.update_performance(model_response)

        # Проверяем, что данные сохранены
        assert "gpt-4" in router._model_performance

    def test_router_get_metrics(self):
        """Проверяет получение метрик"""
        mock_registry = Mock(spec=IModelRegistry)
        router = IntelligentRouter(mock_registry)

        metrics = router.get_metrics()

        assert metrics is not None
        assert isinstance(metrics, dict)
        assert 'total_requests' in metrics
        assert 'successful_requests' in metrics

    def test_router_adaptation_mechanism(self):
        """Проверяет механизм адаптации"""
        mock_registry = Mock(spec=IModelRegistry)
        config = {'learning_enabled': True}
        router = IntelligentRouter(mock_registry, config)

        # Метод адаптации должен выполниться без ошибок
        router._adapt_routing_strategy()

        # Проверяем, что адаптация работает
        assert hasattr(router, '_adaptive_metrics')


class TestLLMManagerSmoke:
    """Дымовые тесты для LLMManager"""

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_manager_creation(self, mock_error_learning, mock_adaptive, mock_router,
                             mock_monitor, mock_validator, mock_intelligent_evaluator,
                             mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Проверяет создание LLMManager"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {
            'models': {},
            'providers': {},
            'strategies': {}
        }
        mock_config.return_value = mock_config_instance

        manager = LLMManager()

        assert manager is not None
        assert hasattr(manager, 'config_loader')
        assert hasattr(manager, 'registry')
        assert hasattr(manager, 'intelligent_router')

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_manager_generate_basic(self, mock_error_learning, mock_adaptive, mock_router,
                                   mock_monitor, mock_validator, mock_intelligent_evaluator,
                                   mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Проверяет базовую генерацию"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {'models': {}, 'providers': {}}
        mock_config.return_value = mock_config_instance

        mock_client_instance = Mock()
        mock_client_instance.generate = AsyncMock(return_value=ModelResponse(
            model_name="gpt-4",
            content="Test response",
            response_time=1.0,
            success=True
        ))
        mock_client.return_value = mock_client_instance

        manager = LLMManager()

        request = GenerationRequest(prompt="Test prompt")

        # Запускаем в event loop
        async def test():
            response = await manager.generate(request)
            assert response is not None
            assert response.success == True
            assert response.content == "Test response"

        asyncio.run(test())

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_manager_generate_with_routing(self, mock_error_learning, mock_adaptive, mock_router,
                                          mock_monitor, mock_validator, mock_intelligent_evaluator,
                                          mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Проверяет генерацию с маршрутизацией"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {'models': {}, 'providers': {}}
        mock_config.return_value = mock_config_instance

        mock_router_instance = Mock()
        mock_router_instance.route_request = Mock(return_value=RoutingDecision(
            model_name="gpt-4",
            strategy="intelligent",
            reasoning="Best model for this task",
            confidence=0.9
        ))
        mock_router.return_value = mock_router_instance

        mock_client_instance = Mock()
        mock_client_instance.generate = AsyncMock(return_value=ModelResponse(
            model_name="gpt-4",
            content="Routed response",
            response_time=1.2,
            success=True
        ))
        mock_client.return_value = mock_client_instance

        manager = LLMManager()

        request = GenerationRequest(prompt="Complex task")

        async def test():
            response = await manager.generate_with_routing(request)
            assert response is not None
            assert response.success == True
            assert response.content == "Routed response"

        asyncio.run(test())

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_manager_evaluate_response(self, mock_error_learning, mock_adaptive, mock_router,
                                      mock_monitor, mock_validator, mock_intelligent_evaluator,
                                      mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Проверяет оценку ответа"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {'models': {}, 'providers': {}}
        mock_config.return_value = mock_config_instance

        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate_response = AsyncMock(return_value=Mock(score=0.85, reasoning="Good response"))
        mock_evaluator.return_value = mock_evaluator_instance

        manager = LLMManager()

        response = ModelResponse(
            model_name="gpt-4",
            content="Test content",
            response_time=1.0,
            success=True
        )
        request = GenerationRequest(prompt="Test prompt")

        async def test():
            result = await manager.evaluate_response(response, request)
            assert result is not None
            assert hasattr(result, 'score')

        asyncio.run(test())

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_manager_get_health_status(self, mock_error_learning, mock_adaptive, mock_router,
                                      mock_monitor, mock_validator, mock_intelligent_evaluator,
                                      mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Проверяет получение статуса здоровья"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {'models': {}, 'providers': {}}
        mock_config.return_value = mock_config_instance

        mock_monitor_instance = Mock()
        mock_monitor_instance.get_health_status = AsyncMock(return_value={
            'status': 'healthy',
            'components': {'all': 'ok'}
        })
        mock_monitor.return_value = mock_monitor_instance

        manager = LLMManager()

        async def test():
            status = await manager.get_health_status()
            assert status is not None
            assert isinstance(status, dict)
            assert 'status' in status

        asyncio.run(test())

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_manager_get_metrics(self, mock_error_learning, mock_adaptive, mock_router,
                                mock_monitor, mock_validator, mock_intelligent_evaluator,
                                mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Проверяет получение метрик"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {'models': {}, 'providers': {}}
        mock_config.return_value = mock_config_instance

        manager = LLMManager()

        metrics = manager.get_metrics()

        assert metrics is not None
        assert isinstance(metrics, dict)

    def test_manager_custom_config_path(self):
        """Проверяет использование кастомного пути к конфигурации"""
        with patch('src.llm.manager.ConfigLoader') as mock_config_loader:
            mock_config_loader.return_value.load_config.return_value = {'test': 'config'}

            manager = LLMManager(config_path="custom/path/config.yaml")

            assert manager is not None
            mock_config_loader.assert_called_once()


class TestLLMIntegrationSmoke:
    """Дымовые тесты интеграции LLM компонентов"""

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_end_to_end_generation_flow(self, mock_error_learning, mock_adaptive, mock_router,
                                       mock_monitor, mock_validator, mock_intelligent_evaluator,
                                       mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Проверяет полный flow генерации от запроса до ответа"""

        # Настраиваем моки для полного flow
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {
            'models': {'gpt-4': {}},
            'providers': {},
            'routing': {'enabled': True}
        }
        mock_config.return_value = mock_config_instance

        # Мокаем маршрутизацию
        mock_router_instance = Mock()
        mock_router_instance.route_request.return_value = RoutingDecision(
            model_name="gpt-4", strategy="intelligent", reasoning="Best choice", confidence=0.9
        )
        mock_router.return_value = mock_router_instance

        # Мокаем клиента
        mock_client_instance = Mock()
        mock_client_instance.generate = AsyncMock(return_value=ModelResponse(
            model_name="gpt-4", content="Generated code", response_time=1.0, success=True
        ))
        mock_client.return_value = mock_client_instance

        # Мокаем оценщика
        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate_response = AsyncMock(return_value=Mock(score=0.9))
        mock_evaluator.return_value = mock_evaluator_instance

        manager = LLMManager()
        request = GenerationRequest(prompt="Write a hello world function")

        async def test():
            # Генерация с маршрутизацией
            response = await manager.generate_with_routing(request)
            assert response.success == True

            # Оценка ответа
            evaluation = await manager.evaluate_response(response, request)
            assert evaluation.score >= 0

            # Проверка метрик
            metrics = manager.get_metrics()
            assert isinstance(metrics, dict)

        asyncio.run(test())