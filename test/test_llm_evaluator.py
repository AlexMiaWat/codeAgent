"""
Тесты для ResponseEvaluator
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.llm.evaluator import ResponseEvaluator
from src.llm.types import ModelConfig, ModelResponse, EvaluationResult


class TestResponseEvaluator:
    """Тесты оценщика ответов"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.evaluator = ResponseEvaluator()
        self.client_manager = Mock()
        self.model_config = ModelConfig(
            name="gpt-4",
            max_tokens=8192,
            context_window=8192,
            temperature=0.7
        )

    @pytest.mark.asyncio
    async def test_evaluate_response_success(self):
        """Тест успешной оценки ответа"""
        # Mock ответа модели в правильном формате
        mock_response = ModelResponse(
            model_name="gpt-4",
            content='Score: 4.5\nReasoning: Good response',
            response_time=1.0,
            success=True
        )
        self.client_manager.call_model = AsyncMock(return_value=mock_response)

        result = await self.evaluator.evaluate_response(
            prompt="Test prompt",
            response="Test response",
            client_manager=self.client_manager,
            evaluator_model=self.model_config
        )

        assert isinstance(result, EvaluationResult)
        assert result.score == 4.5
        assert result.reasoning == "Good response"

    @pytest.mark.asyncio
    async def test_evaluate_response_model_failure(self):
        """Тест оценки при неудаче модели"""
        # Mock неудачного ответа модели
        mock_response = ModelResponse(
            model_name="gpt-4",
            content="",
            response_time=1.0,
            success=False,
            error="Model error"
        )
        self.client_manager.call_model = AsyncMock(return_value=mock_response)

        result = await self.evaluator.evaluate_response(
            prompt="Test prompt",
            response="Test response",
            client_manager=self.client_manager,
            evaluator_model=self.model_config
        )

        assert result.score == 3.0  # Нейтральная оценка при ошибке
        assert "Evaluation failed" in result.reasoning

    @pytest.mark.asyncio
    async def test_evaluate_response_no_model(self):
        """Тест оценки без модели-оценщика"""
        result = await self.evaluator.evaluate_response(
            prompt="Test prompt",
            response="Test response",
            client_manager=self.client_manager
        )

        assert result.score == 3.0  # Нейтральная оценка
        assert "No evaluator available" in result.reasoning

    @pytest.mark.asyncio
    async def test_compare_responses(self):
        """Тест сравнения нескольких ответов"""
        # Mock ответа модели в правильном формате
        mock_response = ModelResponse(
            model_name="gpt-4",
            content='Score: 4.0\nReasoning: Good',
            response_time=1.0,
            success=True
        )
        self.client_manager.call_model = AsyncMock(return_value=mock_response)

        responses = ["Response 1", "Response 2"]
        results = await self.evaluator.compare_responses(
            prompt="Test prompt",
            responses=responses,
            client_manager=self.client_manager,
            evaluator_model=self.model_config
        )

        assert len(results) == 2
        assert all(isinstance(r, EvaluationResult) for r in results)