"""
Интеграционные тесты для LLM Manager
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.llm.manager import LLMManager
from src.llm.types import ModelResponse


class TestLLMManagerIntegration:
    """Интеграционные тесты LLM Manager"""

    @patch('src.llm.manager.ConfigLoader')
    def setup_method(self, mock_config_loader):
        """Настройка перед каждым тестом"""
        # Mock конфигурации
        mock_config = {
            'llm': {
                'models': {
                    'gpt-4': {
                        'name': 'gpt-4',
                        'max_tokens': 8192,
                        'context_window': 8192,
                        'temperature': 0.7,
                        'role': 'primary'
                    }
                },
                'parallel': {
                    'evaluator_model': 'gpt-4'
                }
            }
        }

        mock_loader_instance = Mock()
        mock_loader_instance.load_config.return_value = mock_config
        mock_config_loader.return_value = mock_loader_instance

        self.manager = LLMManager("config/test.yaml")

    @pytest.mark.asyncio
    async def test_full_generation_pipeline(self):
        """Тест полного цикла генерации"""
        # Mock ответа клиента
        mock_response = ModelResponse(
            model_name="gpt-4",
            content="Generated response",
            response_time=1.0,
            success=True
        )

        # Mock client_manager.call_model
        self.manager.client_manager.call_model = AsyncMock(return_value=mock_response)

        # Тестируем генерацию
        response = await self.manager.generate_response("Test prompt")

        assert isinstance(response, ModelResponse)
        assert response.success is True
        assert response.content == "Generated response"
        assert response.model_name == "gpt-4"

    @pytest.mark.asyncio
    async def test_parallel_generation_with_evaluation(self):
        """Тест параллельной генерации с оценкой"""
        # Mock ответов для параллельной генерации
        response1 = ModelResponse(
            model_name="gpt-4",
            content="Response 1",
            response_time=1.0,
            success=True
        )
        response2 = ModelResponse(
            model_name="gpt-4",
            content="Response 2",
            response_time=1.2,
            success=True
        )

        # Mock оценки
        from src.llm.types import EvaluationResult
        eval1 = EvaluationResult(score=4.5, reasoning="Excellent")
        eval2 = EvaluationResult(score=3.5, reasoning="Good")

        self.manager.client_manager.call_model = AsyncMock(side_effect=[response1, response2])
        self.manager.evaluator.evaluate_response = AsyncMock(side_effect=[eval1, eval2])

        # Тестируем параллельную генерацию
        response = await self.manager.generate_response(
            prompt="Test prompt",
            use_parallel=True
        )

        assert isinstance(response, ModelResponse)
        assert response.success is True
        # Должен выбрать лучший ответ
        assert response.content == "Response 1"
        assert response.score == 4.5

    @pytest.mark.asyncio
    async def test_json_validation_integration(self):
        """Тест интеграции с JSON валидацией"""
        # Mock ответа с JSON
        json_response = ModelResponse(
            model_name="gpt-4",
            content='```json\n{"result": "success"}\n```',
            response_time=1.0,
            success=True
        )

        self.manager.client_manager.call_model = AsyncMock(return_value=json_response)

        # Тестируем генерацию с JSON форматом
        response = await self.manager.generate_response(
            prompt="Generate JSON",
            response_format={"type": "json_object"}
        )

        assert response.success is True

        # Тестируем валидацию
        is_valid = self.manager.validate_json('{"test": "data"}')
        assert is_valid is True

        is_invalid = self.manager.validate_json('{"test": }')
        assert is_invalid is False

    @pytest.mark.asyncio
    async def test_initialization_and_shutdown(self):
        """Тест инициализации и завершения работы"""
        # Mock для health monitor
        self.manager.health_monitor.start_monitoring = AsyncMock()
        self.manager.health_monitor.stop_monitoring = AsyncMock()

        # Тестируем инициализацию
        await self.manager.initialize()

        # Проверим что мониторинг запущен
        self.manager.health_monitor.start_monitoring.assert_called_once()

        # Тестируем завершение
        await self.manager.shutdown()

        # Проверим что мониторинг остановлен
        self.manager.health_monitor.stop_monitoring.assert_called_once()

    def test_component_initialization(self):
        """Тест что все компоненты правильно инициализированы"""
        assert self.manager.registry is not None
        assert self.manager.client_manager is not None
        assert self.manager.strategy_manager is not None
        assert self.manager.evaluator is not None
        assert self.manager.json_validator is not None
        assert self.manager.health_monitor is not None

        # Проверим связи между компонентами
        assert self.manager.strategy_manager.registry == self.manager.registry
        assert self.manager.strategy_manager.client_manager == self.manager.client_manager
        assert self.manager.health_monitor.registry == self.manager.registry
        assert self.manager.health_monitor.client_manager == self.manager.client_manager