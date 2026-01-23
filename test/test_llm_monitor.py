"""
Тесты для HealthMonitor
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.llm.monitor import HealthMonitor
from src.llm.types import ModelConfig, ModelResponse, ModelRole


class TestHealthMonitor:
    """Тесты монитора здоровья"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.registry = Mock()
        self.client_manager = Mock()

        # Настраиваем модели в registry
        model1 = ModelConfig(
            name="gpt-4",
            max_tokens=8192,
            context_window=8192,
            temperature=0.7,
            role=ModelRole.PRIMARY,
            enabled=True
        )
        model2 = ModelConfig(
            name="gpt-3.5-turbo",
            max_tokens=4096,
            context_window=4096,
            temperature=0.7,
            role=ModelRole.FALLBACK,
            enabled=True
        )
        self.registry.get_all_models.return_value = [model1, model2]

        self.monitor = HealthMonitor(
            registry=self.registry,
            client_manager=self.client_manager,
            check_interval=0.1,  # Быстрые тесты
            failure_threshold=2
        )

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Тест запуска и остановки мониторинга"""
        # Запускаем мониторинг
        await self.monitor.start_monitoring()
        assert self.monitor._running is True
        assert self.monitor._task is not None

        # Останавливаем мониторинг
        await self.monitor.stop_monitoring()
        assert self.monitor._running is False

        # Задача должна быть отменена
        await asyncio.sleep(0.01)  # Даем время на отмену
        assert self.monitor._task.cancelled() or self.monitor._task.done()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Тест успешной проверки здоровья"""
        # Mock успешного ответа
        success_response = ModelResponse(
            model_name="gpt-4",
            content="OK",
            response_time=0.5,
            success=True
        )
        self.client_manager.call_model = AsyncMock(return_value=success_response)

        results = await self.monitor.check_health()

        assert "gpt-4" in results
        assert results["gpt-4"] is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Тест неудачной проверки здоровья"""
        # Mock неудачного ответа
        error_response = ModelResponse(
            model_name="gpt-4",
            content="",
            response_time=1.0,
            success=False,
            error="Connection failed"
        )
        self.client_manager.call_model = AsyncMock(return_value=error_response)

        results = await self.monitor.check_health()

        assert "gpt-4" in results
        assert results["gpt-4"] is False

    def test_disable_model(self):
        """Тест отключения модели"""
        model_name = "gpt-4"
        self.monitor.disable_model(model_name)

        # Проверим что registry.disable_model был вызван
        self.registry.disable_model.assert_called_once_with(model_name)

    @pytest.mark.asyncio
    async def test_monitoring_loop_disables_failed_models(self):
        """Тест что мониторинг отключает провалившиеся модели"""
        # Mock постоянных ошибок
        error_response = ModelResponse(
            model_name="gpt-4",
            content="",
            response_time=1.0,
            success=False,
            error="Persistent error"
        )
        self.client_manager.call_model = AsyncMock(return_value=error_response)

        # Запускаем мониторинг на короткое время
        await self.monitor.start_monitoring()
        await asyncio.sleep(0.5)  # Даем время на несколько проверок
        await self.monitor.stop_monitoring()

        # Модель должна быть отключена после нескольких неудач
        assert self.registry.disable_model.call_count > 0