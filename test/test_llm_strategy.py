"""
Тесты для StrategyManager
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.llm.strategy import StrategyManager
from src.llm.types import ModelConfig, ModelResponse, ModelRole, GenerationRequest


class TestStrategyManager:
    """Тесты менеджера стратегий"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        # Мокаем зависимости
        self.registry = Mock()
        self.client_manager = Mock()
        self.evaluator = Mock()
        self.json_validator = Mock()

        # Настраиваем registry
        primary_model = ModelConfig(
            name="gpt-4",
            max_tokens=8192,
            context_window=8192,
            temperature=0.7,
            role=ModelRole.PRIMARY
        )
        self.registry.get_models_by_role.return_value = [primary_model]
        self.registry.get_model.return_value = primary_model
        self.registry.get_fastest_model.return_value = primary_model

        # Создаем менеджер стратегий
        self.strategy_manager = StrategyManager(
            registry=self.registry,
            client_manager=self.client_manager,
            evaluator=self.evaluator,
            json_validator=self.json_validator
        )

    @pytest.mark.asyncio
    async def test_generate_single_success(self):
        """Тест успешной генерации одной модели"""
        # Mock ответа клиента
        mock_response = ModelResponse(
            model_name="gpt-4",
            content="Generated response",
            response_time=1.0,
            success=True
        )
        self.client_manager.call_model = AsyncMock(return_value=mock_response)

        request = GenerationRequest(prompt="Test prompt")

        response = await self.strategy_manager.generate(request)

        assert isinstance(response, ModelResponse)
        assert response.success is True
        assert response.content == "Generated response"
        assert response.model_name == "gpt-4"

    @pytest.mark.asyncio
    async def test_generate_parallel_success(self):
        """Тест успешной параллельной генерации"""
        # Mock ответов клиента
        mock_response1 = ModelResponse(
            model_name="gpt-4",
            content="Response 1",
            response_time=1.0,
            success=True
        )
        mock_response2 = ModelResponse(
            model_name="gpt-3.5-turbo",
            content="Response 2",
            response_time=1.5,
            success=True
        )
        self.client_manager.call_model = AsyncMock(side_effect=[mock_response1, mock_response2])

        # Mock evaluator
        from src.llm.types import EvaluationResult
        eval_result1 = EvaluationResult(score=4.5, reasoning="Good")
        eval_result2 = EvaluationResult(score=3.5, reasoning="OK")
        self.evaluator.evaluate_response = AsyncMock(side_effect=[eval_result1, eval_result2])

        request = GenerationRequest(
            prompt="Test prompt",
            use_parallel=True
        )

        response = await self.strategy_manager.generate(request)

        assert isinstance(response, ModelResponse)
        assert response.success is True
        # Должен выбрать лучший ответ (Response 1 с score 4.5)
        assert response.content == "Response 1"
        assert response.score == 4.5

    @pytest.mark.asyncio
    async def test_generate_with_fallback(self):
        """Тест генерации с fallback"""
        # Первая модель падает, вторая работает
        error_response = ModelResponse(
            model_name="gpt-4",
            content="",
            response_time=1.0,
            success=False,
            error="Model failed"
        )
        success_response = ModelResponse(
            model_name="gpt-3.5-turbo",
            content="Fallback response",
            response_time=1.5,
            success=True
        )

        self.client_manager.call_model = AsyncMock(side_effect=[error_response, success_response])

        # Настраиваем fallback модели
        fallback_model = ModelConfig(
            name="gpt-3.5-turbo",
            max_tokens=4096,
            context_window=4096,
            temperature=0.7,
            role=ModelRole.FALLBACK
        )
        self.registry.get_models_by_role.side_effect = lambda role: {
            ModelRole.PRIMARY: [ModelConfig(name="gpt-4", max_tokens=8192, context_window=8192, temperature=0.7, role=ModelRole.PRIMARY)],
            ModelRole.FALLBACK: [fallback_model]
        }.get(role, [])

        request = GenerationRequest(prompt="Test prompt")

        response = await self.strategy_manager.generate(request)

        assert isinstance(response, ModelResponse)
        assert response.success is True
        assert response.content == "Fallback response"
        assert response.model_name == "gpt-3.5-turbo"