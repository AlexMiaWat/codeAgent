"""
Менеджер состояния fallback для автоматического переключения на резервную модель
после billing ошибок на следующие 25 обращений.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FallbackState:
    """Класс для хранения состояния fallback"""

    def __init__(self):
        self.fallback_active: bool = False
        self.fallback_until: float = 0.0  # timestamp
        self.request_count: int = 0
        self.max_requests: int = 25
        self.last_billing_error: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'fallback_active': self.fallback_active,
            'fallback_until': self.fallback_until,
            'request_count': self.request_count,
            'max_requests': self.max_requests,
            'last_billing_error': self.last_billing_error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FallbackState':
        state = cls()
        state.fallback_active = data.get('fallback_active', False)
        state.fallback_until = data.get('fallback_until', 0.0)
        state.request_count = data.get('request_count', 0)
        state.max_requests = data.get('max_requests', 25)
        state.last_billing_error = data.get('last_billing_error', 0.0)
        return state


class FallbackStateManager:
    """Менеджер состояния fallback с файловым хранилищем"""

    def __init__(self, state_file: str = ".codeagent_fallback_state.json"):
        self.state_file = Path(state_file)
        self.state = FallbackState()
        self._load_state()

    def _load_state(self) -> None:
        """Загрузить состояние из файла"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state = FallbackState.from_dict(data)
                logger.debug(f"Загружено состояние fallback: {self.state.to_dict()}")
            else:
                logger.debug("Файл состояния fallback не найден, используется состояние по умолчанию")
        except Exception as e:
            logger.warning(f"Не удалось загрузить состояние fallback: {e}. Используется состояние по умолчанию.")

    def _save_state(self) -> None:
        """Сохранить состояние в файл"""
        try:
            # Создать директорию если не существует
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Сохранено состояние fallback: {self.state.to_dict()}")
        except Exception as e:
            logger.error(f"Не удалось сохранить состояние fallback: {e}")

    def activate_fallback(self) -> None:
        """Активировать fallback режим после billing error"""
        current_time = time.time()

        # Если мы в режиме тестирования основной модели, активируем fallback
        if not self.state.fallback_active and current_time < self.state.fallback_until:
            logger.warning("🚨 BILLING ERROR | Основная модель все еще недоступна, возвращаемся к fallback режиму")
        elif self.state.fallback_active:
            logger.warning("🚨 BILLING ERROR | Fallback уже активен, продолжаем использовать резервную модель")
            return
        else:
            logger.warning("🚨 BILLING ERROR | Активируем fallback режим после неудачи основной модели")

        self.state.fallback_active = True
        self.state.request_count = 0
        self.state.last_billing_error = current_time
        # Устанавливаем время окончания fallback через 1 час (на случай если счетчик не сработает)
        self.state.fallback_until = current_time + 3600
        self._save_state()
        logger.warning(f"🔄 Следующие {self.state.max_requests} обращений будут использовать резервную модель. Fallback активен в течение 1 часа или до {self.state.max_requests} обращений.")

    def should_use_fallback(self) -> bool:
        """Проверить, нужно ли использовать fallback"""
        current_time = time.time()

        # Если fallback активен и не истекло время
        if self.state.fallback_active and current_time < self.state.fallback_until:
            # Если счетчик обращений не превышен
            if self.state.request_count < self.state.max_requests:
                remaining = self.state.max_requests - self.state.request_count
                time_left = int(self.state.fallback_until - current_time)
                logger.debug(f"🔄 Fallback активен: {remaining} обращений осталось, {time_left} сек")
                return True
            else:
                # Счетчик превышен - переводим в режим тестирования основной модели
                logger.info("⏰ Fallback лимит достигнут - переходим к тестированию основной модели")
                self._enter_test_primary_mode()
                return False

        # Если время истекло - переводим в режим тестирования основной модели
        if self.state.fallback_active and current_time >= self.state.fallback_until:
            logger.info("⏰ Fallback время истекло - переходим к тестированию основной модели")
            self._enter_test_primary_mode()
            return False

        return False

    def _enter_test_primary_mode(self) -> None:
        """Перейти в режим тестирования основной модели"""
        self.state.fallback_active = False
        self.state.request_count = 0
        self.state.fallback_until = time.time() + 300  # 5 минут на тестирование основной модели
        self._save_state()
        logger.info("🔄 Тестируем основную модель 'auto' в течение 5 минут (1 попытка)")

    def deactivate_fallback(self) -> None:
        """Деактивировать fallback режим"""
        if self.state.fallback_active:
            logger.info(f"✅ Fallback режим завершен после {self.state.request_count} обращений")
            logger.info("🔄 Переходим к тестированию основной модели")
        self.state.fallback_active = False
        # Не сбрасываем request_count, оставляем для статистики
        # self.state.request_count = 0
        self.state.fallback_until = 0.0
        self._save_state()

    def record_request(self) -> None:
        """Записать обращение в fallback режиме"""
        if self.state.fallback_active:
            self.state.request_count += 1
            self._save_state()
            remaining = self.state.max_requests - self.state.request_count
            logger.info(f"🔄 Fallback обращение #{self.state.request_count}/{self.state.max_requests} (осталось: {remaining})")

            # Если достигли лимита - деактивируем
            if self.state.request_count >= self.state.max_requests:
                logger.warning(f"🚨 Достигнут лимит fallback обращений ({self.state.max_requests})")
                logger.warning("💰 Возможно, требуется пополнить баланс OpenRouter или проверить API ключ")
                self.deactivate_fallback()

    def is_testing_primary_model(self) -> bool:
        """Проверить, находится ли система в режиме тестирования основной модели"""
        current_time = time.time()
        return (not self.state.fallback_active and
                current_time < self.state.fallback_until and
                self.state.fallback_until > time.time() + 300)  # Время тестирования = 5 минут

    def get_status(self) -> Dict[str, Any]:
        """Получить текущий статус fallback"""
        current_time = time.time()
        is_testing = self.is_testing_primary_model()

        return {
            'fallback_active': self.state.fallback_active,
            'testing_primary_model': is_testing,
            'request_count': self.state.request_count,
            'max_requests': self.state.max_requests,
            'time_remaining': max(0, int(self.state.fallback_until - current_time)),
            'last_billing_error': self.state.last_billing_error
        }