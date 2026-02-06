"""
Network resilience tests for LLMManager

Тестирует:
- Retry logic с exponential backoff
- Timeout handling
- Connection failures
- Rate limit handling
- Service unavailability
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

from src.llm.llm_manager import LLMManager, ModelConfig, ModelResponse


class TestRetryLogic:
    """Тесты логики retry"""

    @pytest.fixture
    def manager_with_retry(self):
        """Менеджер с настроенным retry"""
        mgr = LLMManager.__new__(LLMManager)
        mgr.models = {
            'test-model': ModelConfig('test-model', 1024, 4096),
        }
        mgr.clients = {'test': MagicMock()}
        mgr._json_mode_blacklist = set()
        mgr._credits_error_blacklist = set()
        return mgr

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self, manager_with_retry):
        """Тест успешного вызова без retry"""
        success_response = ModelResponse("test-model", "Success", 1.0, True)
        model_config = manager_with_retry.models['test-model']

        with patch.object(manager_with_retry, '_call_model', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = success_response

            result = await manager_with_retry._call_model_with_retry("test prompt", model_config)

            assert result.success is True
            assert result.content == "Success"
            assert mock_call.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, manager_with_retry):
        """Тест retry при ошибке"""
        # Первая попытка падает, вторая успешна
        model_config = manager_with_retry.models['test-model']

        with patch.object(manager_with_retry, '_call_model_internal', new_callable=AsyncMock) as mock_call:
            # Первая попытка - исключение
            mock_call.side_effect = [Exception("Network error"), ModelResponse("test-model", "Success", 1.0, True)]

            result = await manager_with_retry._call_model_with_retry("test prompt", model_config, max_retries=2)

            assert result.success is True
            assert result.content == "Success"
            assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, manager_with_retry):
        """Тест превышения максимального количества retry"""
        model_config = manager_with_retry.models['test-model']

        with patch.object(manager_with_retry, '_call_model_internal', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Persistent error")

            result = await manager_with_retry._call_model_with_retry("test prompt", model_config, max_retries=3)

            assert result.success is False
            assert "failed after 3 attempts" in result.error
            assert mock_call.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_validation_error(self, manager_with_retry):
        """Тест отсутствия retry при validation ошибках"""
        validation_error = ValueError("Validation error: invalid input")
        model_config = manager_with_retry.models['test-model']

        with patch.object(manager_with_retry, '_call_model_internal', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = validation_error

            result = await manager_with_retry._call_model_with_retry("test prompt", model_config, max_retries=3)

            assert result.success is False
            assert "failed after 1 attempts" in result.error  # Только 1 попытка для validation errors
            assert mock_call.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, manager_with_retry):
        """Тест exponential backoff timing"""
        model_config = manager_with_retry.models['test-model']

        with patch.object(manager_with_retry, '_call_model_internal', new_callable=AsyncMock) as mock_call, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_call.side_effect = Exception("Error")

            result = await manager_with_retry._call_model_with_retry("test prompt", model_config, max_retries=3)

            # Проверяем что sleep был вызван с правильными задержками
            assert mock_sleep.call_count == 2  # 2 retry попытки
            calls = mock_sleep.call_args_list

            # Первая задержка ~1s (base_delay * 2^0)
            first_delay = calls[0][0][0]
            assert 0.75 <= first_delay <= 1.25  # С учетом jitter

            # Вторая задержка ~2s (base_delay * 2^1)
            second_delay = calls[1][0][0]
            assert 1.5 <= second_delay <= 2.5


class TestTimeoutHandling:
    """Тесты обработки timeout"""

    @pytest.fixture
    def manager_for_timeout(self):
        """Менеджер для тестирования timeout"""
        mgr = LLMManager.__new__(LLMManager)
        mgr.models = {
            'model1': ModelConfig('model1', 1024, 4096),
            'model2': ModelConfig('model2', 2048, 8192),
        }
        mgr.clients = {'test': MagicMock()}
        mgr._json_mode_blacklist = set()
        mgr._credits_error_blacklist = set()
        mgr.config = {'llm': {'parallel': {'models': ['model1', 'model2']}}}
        return mgr

    @pytest.mark.asyncio
    async def test_parallel_timeout(self, manager_for_timeout):
        """Тест timeout в параллельной генерации"""
        with patch('asyncio.wait_for', new_callable=AsyncMock) as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()

            result = await manager_for_timeout._generate_parallel("test prompt")

            assert result.success is False
            assert "timed out" in result.error
            assert result.response_time == 60.0

    @pytest.mark.asyncio
    async def test_parallel_success_within_timeout(self, manager_for_timeout):
        """Тест успешного выполнения параллельной генерации в рамках timeout"""
        responses = [
            ModelResponse("model1", "Response 1", 1.0, True),
            ModelResponse("model2", "Response 2", 1.5, True)
        ]

        with patch('asyncio.wait_for', new_callable=AsyncMock) as mock_wait_for, \
             patch.object(manager_for_timeout, '_call_model_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = responses
            mock_wait_for.return_value = responses

            result = await manager_for_timeout._generate_parallel("test prompt")

            assert result.success is True
            assert result.model_name in ["model1", "model2"]


class TestErrorRecovery:
    """Тесты восстановления после ошибок"""

    @pytest.fixture
    def manager_for_recovery(self):
        """Менеджер для тестирования восстановления"""
        from src.llm.llm_manager import ModelRole

        mgr = LLMManager.__new__(LLMManager)
        mgr.models = {
            'primary-model': ModelConfig('primary-model', 1024, 4096, role=ModelRole.PRIMARY),
            'fallback-model': ModelConfig('fallback-model', 512, 2048, role=ModelRole.FALLBACK),
        }

        mgr.clients = {'test': MagicMock()}
        mgr._json_mode_blacklist = set()
        mgr._credits_error_blacklist = set()
        mgr.config = {'llm': {}}
        return mgr

    @pytest.mark.asyncio
    async def test_fallback_after_primary_failure(self, manager_for_recovery):
        """Тест fallback после отказа первичной модели"""
        # Имитируем отказ первичной модели
        primary_error = ModelResponse("primary-model", "", 0.5, False, error="API down")
        fallback_success = ModelResponse("fallback-model", "Fallback response", 1.0, True)

        with patch.object(manager_for_recovery, '_call_model_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [primary_error, fallback_success]

            result = await manager_for_recovery._generate_with_fallback("test prompt", manager_for_recovery.models['primary-model'])

            assert result.success is True
            assert result.content == "Fallback response"
            assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_all_models_fail(self, manager_for_recovery):
        """Тест когда все модели проваливаются"""
        error_response = ModelResponse("primary-model", "", 0.5, False, error="All models down")

        with patch.object(manager_for_recovery, '_call_model_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = error_response

            result = await manager_for_recovery._generate_with_fallback("test prompt", manager_for_recovery.models['primary-model'])

            assert result.success is False
            assert "All models failed" in result.error


class TestRateLimitHandling:
    """Тесты обработки rate limits"""

    @pytest.fixture
    def manager_for_rate_limits(self):
        """Менеджер для тестирования rate limits"""
        mgr = LLMManager.__new__(LLMManager)
        mgr.models = {
            'rate-limited-model': ModelConfig('rate-limited-model', 1024, 4096),
        }
        mgr.clients = {'test': MagicMock()}
        mgr._json_mode_blacklist = set()
        mgr._credits_error_blacklist = set()
        return mgr

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, manager_for_rate_limits):
        """Тест retry при rate limit ошибке"""
        # Rate limit ошибка, затем успех
        rate_limit_error = Exception("Rate limit exceeded")
        success_response = ModelResponse("rate-limited-model", "Success after rate limit", 2.0, True)
        model_config = manager_for_rate_limits.models['rate-limited-model']

        with patch.object(manager_for_rate_limits, '_call_model_internal', new_callable=AsyncMock) as mock_call, \
             patch('asyncio.sleep', new_callable=AsyncMock):
            mock_call.side_effect = [rate_limit_error, success_response]

            result = await manager_for_rate_limits._call_model_with_retry("test prompt", model_config, max_retries=2)

            assert result.success is True
            assert result.content == "Success after rate limit"
            assert mock_call.call_count == 2


class TestNetworkEdgeCases:
    """Тесты граничных случаев сети"""

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """Тест истощения connection pool"""
        # Этот тест проверяет что система правильно обрабатывает
        # ситуации когда все connections заняты

        mgr = LLMManager.__new__(LLMManager)
        mgr.models = {'test-model': ModelConfig('test-model', 1024, 4096)}
        mgr.clients = {'test': MagicMock()}
        mgr._json_mode_blacklist = set()
        mgr._credits_error_blacklist = set()
        model_config = mgr.models['test-model']

        # Имитируем connection pool exhaustion
        pool_error = Exception("Connection pool exhausted")

        with patch.object(mgr, '_call_model_internal', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = pool_error

            result = await mgr._call_model_with_retry("test prompt", model_config, max_retries=2)

            assert result.success is False
            assert "failed after 2 attempts" in result.error

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self):
        """Тест ошибки DNS resolution"""
        mgr = LLMManager.__new__(LLMManager)
        mgr.models = {'test-model': ModelConfig('test-model', 1024, 4096)}
        mgr.clients = {'test': MagicMock()}
        mgr._json_mode_blacklist = set()
        mgr._credits_error_blacklist = set()
        model_config = mgr.models['test-model']

        dns_error = Exception("DNS resolution failed")

        with patch.object(mgr, '_call_model_internal', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = dns_error

            result = await mgr._call_model_with_retry("test prompt", model_config, max_retries=1)

            assert result.success is False
            assert "DNS resolution failed" in str(result.error)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])