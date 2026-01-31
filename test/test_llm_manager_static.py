"""
Статические тесты для LLMManager

Тестирует:
- Архитектуру компонентов
- Инициализацию и конфигурацию
- Интерфейсы и контракты
- Управление жизненным циклом
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.llm.manager import LLMManager
from src.llm.types import (
    ModelConfig, ModelResponse, GenerationRequest, EvaluationResult, RoutingDecision
)


class TestLLMManagerStatic:
    """Статические тесты для LLMManager"""

    def test_llm_manager_initialization(self):
        """Тестирует базовую инициализацию LLMManager"""
        with patch('src.llm.manager.ConfigLoader') as mock_config_loader, \
             patch('src.llm.manager.ModelRegistry') as mock_registry, \
             patch('src.llm.manager.ClientManager') as mock_client, \
             patch('src.llm.manager.StrategyManager') as mock_strategy, \
             patch('src.llm.manager.ResponseEvaluator') as mock_evaluator, \
             patch('src.llm.manager.IntelligentEvaluator') as mock_intelligent_evaluator, \
             patch('src.llm.manager.JsonValidator') as mock_validator, \
             patch('src.llm.manager.HealthMonitor') as mock_monitor, \
             patch('src.llm.manager.IntelligentRouter') as mock_router, \
             patch('src.llm.manager.AdaptiveStrategyManager') as mock_adaptive, \
             patch('src.llm.manager.ErrorLearningSystem') as mock_error_learning:

            # Настраиваем моки
            mock_config_loader.return_value.load_config.return_value = {
                'models': {},
                'providers': {},
                'strategies': {}
            }

            manager = LLMManager()

            # Проверяем, что все компоненты инициализированы
            assert hasattr(manager, 'config_loader')
            assert hasattr(manager, 'registry')
            assert hasattr(manager, 'client_manager')
            assert hasattr(manager, 'strategy_manager')
            assert hasattr(manager, 'evaluator')
            assert hasattr(manager, 'intelligent_evaluator')
            assert hasattr(manager, 'json_validator')
            assert hasattr(manager, 'health_monitor')
            assert hasattr(manager, 'intelligent_router')
            assert hasattr(manager, 'adaptive_strategy')
            assert hasattr(manager, 'error_learning_system')

    def test_llm_manager_with_custom_config(self):
        """Тестирует инициализацию с кастомной конфигурацией"""
        custom_config_path = "custom/llm_config.yaml"

        with patch('src.llm.manager.ConfigLoader') as mock_config_loader:
            mock_config_loader.return_value.load_config.return_value = {
                'custom_setting': True,
                'models': {'test_model': {}}
            }

            manager = LLMManager(config_path=custom_config_path)

            # Проверяем, что ConfigLoader вызван с правильным путем
            mock_config_loader.assert_called_once()
            args, kwargs = mock_config_loader.call_args
            assert custom_config_path in args or custom_config_path in kwargs.get('config_path', '')

    def test_llm_manager_component_interfaces(self):
        """Проверяет, что все компоненты имеют ожидаемые интерфейсы"""
        with patch('src.llm.manager.ConfigLoader'), \
             patch('src.llm.manager.ModelRegistry'), \
             patch('src.llm.manager.ClientManager'), \
             patch('src.llm.manager.StrategyManager'), \
             patch('src.llm.manager.ResponseEvaluator'), \
             patch('src.llm.manager.IntelligentEvaluator'), \
             patch('src.llm.manager.JsonValidator'), \
             patch('src.llm.manager.HealthMonitor'), \
             patch('src.llm.manager.IntelligentRouter'), \
             patch('src.llm.manager.AdaptiveStrategyManager'), \
             patch('src.llm.manager.ErrorLearningSystem'):

            manager = LLMManager()

            # Проверяем основные публичные методы
            assert hasattr(manager, 'generate')
            assert hasattr(manager, 'generate_with_routing')
            assert hasattr(manager, 'evaluate_response')
            assert hasattr(manager, 'get_health_status')
            assert hasattr(manager, 'get_metrics')

    def test_llm_manager_error_handling(self):
        """Тестирует обработку ошибок при инициализации"""
        with patch('src.llm.manager.ConfigLoader') as mock_config_loader:
            # Симулируем ошибку загрузки конфигурации
            mock_config_loader.return_value.load_config.side_effect = FileNotFoundError("Config not found")

            with pytest.raises(FileNotFoundError):
                LLMManager()

    def test_llm_manager_component_dependencies(self):
        """Проверяет зависимости между компонентами"""
        with patch('src.llm.manager.ConfigLoader') as mock_config_loader, \
             patch('src.llm.manager.ModelRegistry') as mock_registry, \
             patch('src.llm.manager.IntelligentRouter') as mock_router:

            mock_config = {'models': {}, 'providers': {}}
            mock_config_loader.return_value.load_config.return_value = mock_config

            manager = LLMManager()

            # Проверяем, что IntelligentRouter получает registry
            mock_router.assert_called_once()
            args, kwargs = mock_router.call_args
            assert manager.registry in args

    def test_llm_manager_async_methods(self):
        """Проверяет асинхронные методы"""
        with patch('src.llm.manager.ConfigLoader'), \
             patch('src.llm.manager.ModelRegistry'), \
             patch('src.llm.manager.ClientManager'), \
             patch('src.llm.manager.StrategyManager'), \
             patch('src.llm.manager.ResponseEvaluator'), \
             patch('src.llm.manager.IntelligentEvaluator'), \
             patch('src.llm.manager.JsonValidator'), \
             patch('src.llm.manager.HealthMonitor'), \
             patch('src.llm.manager.IntelligentRouter'), \
             patch('src.llm.manager.AdaptiveStrategyManager'), \
             patch('src.llm.manager.ErrorLearningSystem'):

            manager = LLMManager()

            # Проверяем, что ключевые методы являются корутинами
            assert asyncio.iscoroutinefunction(manager.generate)
            assert asyncio.iscoroutinefunction(manager.generate_with_routing)
            assert asyncio.iscoroutinefunction(manager.get_health_status)

    def test_llm_manager_configuration_structure(self):
        """Тестирует ожидаемую структуру конфигурации"""
        with patch('src.llm.manager.ConfigLoader') as mock_config_loader:
            config = {
                'models': {
                    'gpt-4': {
                        'provider': 'openai',
                        'max_tokens': 4096,
                        'context_window': 8192
                    }
                },
                'providers': {
                    'openai': {
                        'base_url': 'https://api.openai.com/v1',
                        'timeout': 200
                    }
                },
                'strategies': {
                    'default': 'best_of_two',
                    'fallback': 'fastest'
                },
                'routing': {
                    'enabled': True,
                    'intelligent': True
                },
                'monitoring': {
                    'enabled': True,
                    'metrics_interval': 60
                }
            }

            mock_config_loader.return_value.load_config.return_value = config

            manager = LLMManager()

            # Проверяем, что конфигурация сохранена
            assert hasattr(manager, 'config')
            assert manager.config == config

    def test_llm_manager_component_initialization_order(self):
        """Проверяет порядок инициализации компонентов"""
        init_order = []

        def track_init(component_name):
            def init_mock(*args, **kwargs):
                init_order.append(component_name)
                return Mock()
            return init_mock

        with patch('src.llm.manager.ConfigLoader', side_effect=track_init('ConfigLoader')), \
             patch('src.llm.manager.ModelRegistry', side_effect=track_init('ModelRegistry')), \
             patch('src.llm.manager.ClientManager', side_effect=track_init('ClientManager')), \
             patch('src.llm.manager.StrategyManager', side_effect=track_init('StrategyManager')), \
             patch('src.llm.manager.ResponseEvaluator', side_effect=track_init('ResponseEvaluator')), \
             patch('src.llm.manager.IntelligentEvaluator', side_effect=track_init('IntelligentEvaluator')), \
             patch('src.llm.manager.JsonValidator', side_effect=track_init('JsonValidator')), \
             patch('src.llm.manager.HealthMonitor', side_effect=track_init('HealthMonitor')), \
             patch('src.llm.manager.IntelligentRouter', side_effect=track_init('IntelligentRouter')), \
             patch('src.llm.manager.AdaptiveStrategyManager', side_effect=track_init('AdaptiveStrategyManager')), \
             patch('src.llm.manager.ErrorLearningSystem', side_effect=track_init('ErrorLearningSystem')):

            LLMManager()

            # Проверяем, что ConfigLoader инициализируется первым
            assert init_order[0] == 'ConfigLoader'
            # Проверяем, что все компоненты инициализированы
            assert len(init_order) == 10

    def test_llm_manager_resource_management(self):
        """Тестирует управление ресурсами"""
        with patch('src.llm.manager.ConfigLoader'), \
             patch('src.llm.manager.ModelRegistry'), \
             patch('src.llm.manager.ClientManager'), \
             patch('src.llm.manager.StrategyManager'), \
             patch('src.llm.manager.ResponseEvaluator'), \
             patch('src.llm.manager.IntelligentEvaluator'), \
             patch('src.llm.manager.JsonValidator'), \
             patch('src.llm.manager.HealthMonitor'), \
             patch('src.llm.manager.IntelligentRouter'), \
             patch('src.llm.manager.AdaptiveStrategyManager'), \
             patch('src.llm.manager.ErrorLearningSystem'):

            manager = LLMManager()

            # Проверяем наличие методов для управления ресурсами
            assert hasattr(manager, 'shutdown')
            assert hasattr(manager, 'cleanup')

    def test_llm_manager_type_hints(self):
        """Проверяет корректность type hints в публичных методах"""
        import inspect

        with patch('src.llm.manager.ConfigLoader'), \
             patch('src.llm.manager.ModelRegistry'), \
             patch('src.llm.manager.ClientManager'), \
             patch('src.llm.manager.StrategyManager'), \
             patch('src.llm.manager.ResponseEvaluator'), \
             patch('src.llm.manager.IntelligentEvaluator'), \
             patch('src.llm.manager.JsonValidator'), \
             patch('src.llm.manager.HealthMonitor'), \
             patch('src.llm.manager.IntelligentRouter'), \
             patch('src.llm.manager.AdaptiveStrategyManager'), \
             patch('src.llm.manager.ErrorLearningSystem'):

            manager = LLMManager()

            # Проверяем type hints для основных методов
            sig = inspect.signature(manager.generate)
            assert 'request' in sig.parameters
            assert sig.parameters['request'].annotation == GenerationRequest

            sig = inspect.signature(manager.evaluate_response)
            assert 'response' in sig.parameters
            assert 'request' in sig.parameters

    def test_llm_manager_singleton_pattern(self):
        """Тестирует паттерн singleton для общих ресурсов"""
        # Проверяем, что определенные компоненты могут быть singleton
        # (например, registry, config_loader)

        with patch('src.llm.manager.ConfigLoader') as mock_config_loader, \
             patch('src.llm.manager.ModelRegistry') as mock_registry:

            mock_config_loader.return_value.load_config.return_value = {'test': 'config'}

            manager1 = LLMManager()
            manager2 = LLMManager()

            # Проверяем, что это разные экземпляры (не singleton)
            assert manager1 is not manager2
            # Но конфигурация может быть общей
            assert manager1.config == manager2.config