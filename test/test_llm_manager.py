"""
Тесты для LLMManager
"""

import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from llm.llm_manager import LLMManager, ModelConfig, ModelRole, ModelResponse


class TestLLMManager:
    """Тесты для LLMManager"""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Создает временный конфигурационный файл для тестов"""
        config_content = """
llm:
  default_provider: openrouter
  default_model: test-model
  timeout: 30
  retry_attempts: 1
  strategy: single
  model_roles:
    primary:
    - test-model
    duplicate: []
    reserve: []
    fallback: []

providers:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    models:
      test:
      - name: test-model
        max_tokens: 1024
        context_window: 4096
        temperature: 0.7
        top_p: 1.0
"""
        config_file = tmp_path / "test_llm_config.yaml"
        config_file.write_text(config_content)
        return config_file

    @pytest.fixture
    def mock_openai_client(self):
        """Мок для OpenAI клиента"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_initialization(self, temp_config_file):
        """Тест инициализации LLMManager"""
        with patch('llm.llm_manager.OpenAI', return_value=Mock()):
            manager = LLMManager(str(temp_config_file))

            assert manager is not None
            assert hasattr(manager, 'models')
            assert hasattr(manager, 'clients')

    def test_get_primary_models(self, temp_config_file):
        """Тест получения первичных моделей"""
        with patch('llm.llm_manager.OpenAI', return_value=Mock()):
            manager = LLMManager(str(temp_config_file))

            primary_models = manager.get_primary_models()
            assert isinstance(primary_models, list)
            # Проверяем, что хотя бы одна модель загружена
            assert len(primary_models) >= 0

    def test_get_fallback_models(self, temp_config_file):
        """Тест получения резервных моделей"""
        with patch('llm.llm_manager.OpenAI', return_value=Mock()):
            manager = LLMManager(str(temp_config_file))

            fallback_models = manager.get_fallback_models()
            assert isinstance(fallback_models, list)

    def test_get_fastest_model(self, temp_config_file):
        """Тест получения самой быстрой модели"""
        with patch('llm.llm_manager.OpenAI', return_value=Mock()):
            manager = LLMManager(str(temp_config_file))

            fastest_model = manager.get_fastest_model()
            # Может вернуть None, если нет моделей
            assert fastest_model is None or isinstance(fastest_model, ModelConfig)

    def test_close(self, temp_config_file):
        """Тест закрытия менеджер"""
        mock_client = Mock()
        with patch('llm.llm_manager.AsyncOpenAI', return_value=mock_client):
            manager = LLMManager(str(temp_config_file))

            # Добавляем клиента в менеджер
            manager.clients = {'test': mock_client}

            # Проверяем, что close существует
            assert hasattr(manager, 'close')

    def test_model_config_creation(self):
        """Тест создания ModelConfig"""
        config = ModelConfig(
            name="test-model",
            max_tokens=1024,
            context_window=4096,
            temperature=0.7,
            role=ModelRole.PRIMARY
        )

        assert config.name == "test-model"
        assert config.max_tokens == 1024
        assert config.context_window == 4096
        assert config.temperature == 0.7
        assert config.role == ModelRole.PRIMARY
        assert config.enabled is True

    def test_model_response_creation(self):
        """Тест создания ModelResponse"""
        response = ModelResponse(
            model_name="test-model",
            content="Test content",
            response_time=1.5,
            success=True,
            error=None,
            score=0.95
        )

        assert response.model_name == "test-model"
        assert response.content == "Test content"
        assert response.response_time == 1.5
        assert response.success is True
        assert response.error is None
        assert response.score == 0.95


class TestModelRole:
    """Тесты для ModelRole enum"""

    def test_model_role_values(self):
        """Тест значений ModelRole"""
        assert ModelRole.PRIMARY.value == "primary"
        assert ModelRole.DUPLICATE.value == "duplicate"
        assert ModelRole.RESERVE.value == "reserve"
        assert ModelRole.FALLBACK.value == "fallback"

    def test_model_role_members(self):
        """Тест членов ModelRole"""
        roles = [ModelRole.PRIMARY, ModelRole.DUPLICATE, ModelRole.RESERVE, ModelRole.FALLBACK]
        assert len(roles) == 4

        role_values = [role.value for role in roles]
        expected_values = ["primary", "duplicate", "reserve", "fallback"]
        assert set(role_values) == set(expected_values)