"""
Модуль управления LLM провайдерами для Code Agent
"""

from .llm_manager import LLMManager, ModelRole
from .llm_test_runner import LLMTestRunner
from .crewai_llm_wrapper import CrewAILLMWrapper, create_llm_for_crewai
from .model_discovery import ModelDiscovery
from .config_updater import ConfigUpdater

__all__ = [
    'LLMManager', 'ModelRole', 'LLMTestRunner', 
    'CrewAILLMWrapper', 'create_llm_for_crewai',
    'ModelDiscovery', 'ConfigUpdater'
]
