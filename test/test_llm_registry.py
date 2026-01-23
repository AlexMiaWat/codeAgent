"""
Тесты для ModelRegistry
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.llm.registry import ModelRegistry
from src.llm.types import ModelConfig, ModelRole


class TestModelRegistry:
    """Тесты реестра моделей"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.config_loader = Mock()
        self.config_loader.load_config.return_value = {
            'llm': {
                'default_provider': 'openai',
                'model_roles': {
                    'primary': ['gpt-4'],
                    'fallback': ['gpt-3.5-turbo']
                }
            },
            'providers': {
                'openai': {
                    'models': {
                        'openai': [
                            {
                                'name': 'gpt-4',
                                'max_tokens': 8192,
                                'context_window': 8192,
                                'temperature': 0.7
                            },
                            {
                                'name': 'gpt-3.5-turbo',
                                'max_tokens': 4096,
                                'context_window': 4096,
                                'temperature': 0.7
                            }
                        ]
                    }
                }
            }
        }

    def test_initialization(self):
        """Тест инициализации реестра"""
        registry = ModelRegistry(self.config_loader, "config/llm_settings.yaml")

        assert str(registry.config_path) == "config/llm_settings.yaml"
        assert len(registry.models) > 0
        assert 'gpt-4' in registry.models

    def test_get_model(self):
        """Тест получения модели по имени"""
        registry = ModelRegistry(self.config_loader, "config/llm_settings.yaml")

        model = registry.get_model('gpt-4')
        assert model is not None
        assert model.name == 'gpt-4'
        assert model.max_tokens == 8192

    def test_get_models_by_role(self):
        """Тест получения моделей по роли"""
        registry = ModelRegistry(self.config_loader, "config/llm_settings.yaml")

        primary_models = registry.get_models_by_role(ModelRole.PRIMARY)
        fallback_models = registry.get_models_by_role(ModelRole.FALLBACK)

        assert len(primary_models) > 0
        assert len(fallback_models) > 0
        assert primary_models[0].name == 'gpt-4'
        assert fallback_models[0].name == 'gpt-3.5-turbo'

    def test_get_fastest_model(self):
        """Тест получения самой быстрой модели"""
        registry = ModelRegistry(self.config_loader, "config/llm_settings.yaml")

        # Модели не имеют response_time, но возвращается модель с эвристикой
        fastest = registry.get_fastest_model()
        assert fastest is not None  # Должен вернуться gpt-4 (меньше токенов, быстрее по эвристике)

        # Добавим модель с временем ответа
        registry.models['gpt-4'].last_response_time = 1.0
        registry.models['gpt-3.5-turbo'].last_response_time = 2.0

        fastest = registry.get_fastest_model()
        assert fastest is not None
        assert fastest.name == 'gpt-4'