"""
HealthMonitor - мониторинг работоспособности моделей

Ответственность:
- Периодические health checks
- Отключение проблемных моделей
- Автоматическое восстановление
- Метрики производительности
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from .types import ModelConfig, IHealthMonitor, IModelRegistry, IClientManager

logger = logging.getLogger(__name__)


class HealthMonitor(IHealthMonitor):
    """
    Монитор здоровья - отслеживает работоспособность моделей

    Предоставляет:
    - Периодические проверки здоровья моделей
    - Автоматическое отключение проблемных моделей
    - Метрики производительности
    - Восстановление работоспособных моделей
    """

    def __init__(
        self,
        registry: IModelRegistry,
        client_manager: IClientManager,
        check_interval: float = 300.0,  # 5 минут
        failure_threshold: int = 3,     # Отключить после 3 неудач
        recovery_attempts: int = 2      # Попыток восстановления
    ):
        """
        Инициализация монитора здоровья

        Args:
            registry: Реестр моделей
            client_manager: Менеджер клиентов
            check_interval: Интервал проверок в секундах
            failure_threshold: Порог неудач для отключения
            recovery_attempts: Количество попыток восстановления
        """
        self.registry = registry
        self.client_manager = client_manager
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.recovery_attempts = recovery_attempts

        self.last_check: Optional[float] = None
        self.disabled_models: Dict[str, Dict[str, Any]] = {}  # model_name -> info
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start_monitoring(self):
        """Запустить фоновый мониторинг"""
        if self._running:
            logger.warning("Health monitoring is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started health monitoring")

    async def stop_monitoring(self):
        """Остановить мониторинг"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped health monitoring")

    async def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self._running:
            try:
                await self._perform_health_checks()
                await self._try_recover_models()
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")

            await asyncio.sleep(self.check_interval)

    async def _perform_health_checks(self):
        """Выполнить проверки здоровья всех активных моделей"""
        logger.debug("Performing health checks...")

        # Получаем все модели
        all_models = self.registry.get_all_models()

        health_status = {}

        for model in all_models:
            if not model.enabled:
                continue

            is_healthy = await self._check_single_model(model)
            health_status[model.name] = is_healthy

            if not is_healthy:
                self._handle_unhealthy_model(model.name)

        self.last_check = time.time()
        logger.debug(f"Health check completed. Status: {health_status}")

    async def _check_single_model(self, model: ModelConfig) -> bool:
        """
        Проверить здоровье одной модели

        Args:
            model: Модель для проверки

        Returns:
            True если модель здорова
        """
        try:
            # Простой health check - запрос на генерацию короткого ответа
            test_prompt = "Say 'OK' if you are working properly."

            response = await self.client_manager.call_model(
                model_config=model,
                prompt=test_prompt
            )

            # Модель считается здоровой если ответила успешно и содержит ожидаемый текст
            is_healthy = (
                response.success and
                response.response_time < 30.0 and  # Не слишком медленно
                len(response.content.strip()) > 0   # Есть содержимое
            )

            return is_healthy

        except Exception as e:
            logger.warning(f"Health check failed for model {model.name}: {e}")
            return False

    def _handle_unhealthy_model(self, model_name: str):
        """Обработать нездоровую модель"""
        if model_name not in self.disabled_models:
            self.disabled_models[model_name] = {
                'disabled_at': time.time(),
                'failure_count': 1,
                'recovery_attempts': 0
            }
        else:
            self.disabled_models[model_name]['failure_count'] += 1

        # Отключаем модель если превышен порог
        if self.disabled_models[model_name]['failure_count'] >= self.failure_threshold:
            self.disable_model(model_name)
            logger.warning(f"Disabled model {model_name} due to {self.failure_threshold} consecutive failures")

    async def _try_recover_models(self):
        """Попытаться восстановить отключенные модели"""
        models_to_recover = []

        for model_name, info in self.disabled_models.items():
            if info['recovery_attempts'] < self.recovery_attempts:
                # Проверяем не прошло ли достаточно времени с момента отключения
                time_since_disabled = time.time() - info['disabled_at']
                if time_since_disabled > 60:  # Ждем минуту перед первой попыткой восстановления
                    models_to_recover.append(model_name)

        for model_name in models_to_recover:
            await self._attempt_recovery(model_name)

    async def _attempt_recovery(self, model_name: str):
        """Попытаться восстановить модель"""
        model = self.registry.get_model(model_name)
        if not model:
            logger.warning(f"Cannot recover unknown model {model_name}")
            return

        logger.info(f"Attempting to recover model {model_name}")

        is_healthy = await self._check_single_model(model)

        if is_healthy:
            self.enable_model(model_name)
            del self.disabled_models[model_name]
            logger.info(f"Successfully recovered model {model_name}")
        else:
            self.disabled_models[model_name]['recovery_attempts'] += 1
            logger.warning(f"Recovery attempt {self.disabled_models[model_name]['recovery_attempts']} failed for {model_name}")

            # Если исчерпаны попытки восстановления, оставляем отключенной
            if self.disabled_models[model_name]['recovery_attempts'] >= self.recovery_attempts:
                logger.error(f"Failed to recover model {model_name} after {self.recovery_attempts} attempts")

    # Реализация интерфейса IHealthMonitor

    async def check_health(self) -> Dict[str, bool]:
        """Проверить здоровье всех моделей"""
        # Получаем все модели
        all_models = self.registry.get_all_models()

        health_status = {}
        for model in all_models:
            is_healthy = await self._check_single_model(model)
            health_status[model.name] = is_healthy

        return health_status

    def disable_model(self, model_name: str) -> None:
        """Отключить модель"""
        self.registry.disable_model(model_name)

    def enable_model(self, model_name: str) -> None:
        """Включить модель"""
        self.registry.enable_model(model_name)

    def get_health_stats(self) -> Dict[str, Any]:
        """Получить статистику здоровья"""
        return {
            'last_check': self.last_check,
            'disabled_models': list(self.disabled_models.keys()),
            'monitoring_active': self._running
        }