"""
Тесты для ClientManager
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.llm.client import ClientManager
from src.llm.types import ModelConfig, ModelResponse


class TestClientManager:
    """Тесты менеджера клиентов"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.config_loader = Mock()
        self.config_loader.load_config.return_value = {
            'llm': {
                'providers': {
                    'openai': {
                        'api_key': 'test-key',
                        'base_url': 'https://api.openai.com/v1'
                    }
                }
            }
        }

    @patch('src.llm.client.load_dotenv')
    def test_initialization(self, mock_load_dotenv):
        """Тест инициализации клиента"""
        manager = ClientManager(self.config_loader, "config/llm_settings.yaml")

        assert manager.config_loader == self.config_loader
        assert manager.config_path == "config/llm_settings.yaml"
        assert isinstance(manager.clients, dict)
        assert isinstance(manager.providers, dict)

    @patch('src.llm.client.AsyncOpenAI')
    @patch('src.llm.client.load_dotenv')
    def test_init_clients(self, mock_load_dotenv, mock_openai):
        """Тест инициализации клиентов API"""
        mock_client = Mock()
        mock_openai.return_value = mock_client

        manager = ClientManager(self.config_loader, "config/llm_settings.yaml")

        # Проверим что клиент был создан
        mock_openai.assert_called_once()
        assert len(manager.clients) > 0

    @pytest.mark.asyncio
    @patch('src.llm.client.AsyncOpenAI')
    @patch('src.llm.client.load_dotenv')
    async def test_call_model_success(self, mock_load_dotenv, mock_openai):
        """Тест успешного вызова модели"""
        # Mock OpenAI клиента
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        manager = ClientManager(self.config_loader, "config/llm_settings.yaml")

        model_config = ModelConfig(
            name="gpt-4",
            max_tokens=8192,
            context_window=8192,
            temperature=0.7
        )

        response = await manager.call_model(
            model_config=model_config,
            prompt="Test prompt"
        )

        assert isinstance(response, ModelResponse)
        assert response.success is True
        assert response.content == "Test response"
        assert response.model_name == "gpt-4"

    @pytest.mark.asyncio
    @patch('src.llm.client.AsyncOpenAI')
    @patch('src.llm.client.load_dotenv')
    async def test_call_model_failure(self, mock_load_dotenv, mock_openai):
        """Тест неудачного вызова модели"""
        # Mock OpenAI клиента с исключением
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_openai.return_value = mock_client

        manager = ClientManager(self.config_loader, "config/llm_settings.yaml")

        model_config = ModelConfig(
            name="gpt-4",
            max_tokens=8192,
            context_window=8192,
            temperature=0.7
        )

        response = await manager.call_model(
            model_config=model_config,
            prompt="Test prompt"
        )

        assert isinstance(response, ModelResponse)
        assert response.success is False
        assert "API Error" in response.error