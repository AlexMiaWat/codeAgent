"""
Модуль управления LLM провайдерами для Code Agent

Новая модульная архитектура:
- LLMManager: Фасад для всех операций
- ModelRegistry: Управление моделями
- ClientManager: Управление API клиентами
- StrategyManager: Стратегии генерации
- ResponseEvaluator: Оценка ответов
- JsonValidator: Валидация JSON
- HealthMonitor: Мониторинг здоровья
- ConfigLoader: Загрузка конфигурации
"""

# Новый модульный LLM Manager
from .manager import LLMManager

# Компоненты новой архитектуры
from .registry import ModelRegistry
from .client import ClientManager
from .strategy import StrategyManager
from .evaluator import ResponseEvaluator
from .validator import JsonValidator
from .monitor import HealthMonitor
from .config_loader import ConfigLoader

# Общие типы и интерфейсы
from .types import (
    ModelRole, ModelConfig, ModelResponse, ProviderConfig,
    GenerationRequest, EvaluationResult,
    IModelRegistry, IClientManager, IStrategyManager,
    IResponseEvaluator, IJsonValidator, IHealthMonitor, IConfigLoader
)

# Старые компоненты (для совместимости)
from .llm_manager import LLMManager as LegacyLLMManager
from .llm_test_runner import LLMTestRunner
from .crewai_llm_wrapper import CrewAILLMWrapper, create_llm_for_crewai
from .model_discovery import ModelDiscovery
from .config_updater import ConfigUpdater

__all__ = [
    # Новый модульный LLM Manager
    'LLMManager',

    # Компоненты новой архитектуры
    'ModelRegistry', 'ClientManager', 'StrategyManager',
    'ResponseEvaluator', 'JsonValidator', 'HealthMonitor', 'ConfigLoader',

    # Типы и интерфейсы
    'ModelRole', 'ModelConfig', 'ModelResponse', 'ProviderConfig',
    'GenerationRequest', 'EvaluationResult',
    'IModelRegistry', 'IClientManager', 'IStrategyManager',
    'IResponseEvaluator', 'IJsonValidator', 'IHealthMonitor', 'IConfigLoader',

    # Старые компоненты (для совместимости)
    'LegacyLLMManager', 'LLMTestRunner',
    'CrewAILLMWrapper', 'create_llm_for_crewai',
    'ModelDiscovery', 'ConfigUpdater'
]
