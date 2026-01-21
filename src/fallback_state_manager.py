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
        self.state.fallback_active = True
        self.state.request_count = 0
        self.state.last_billing_error = time.time()
        # Устанавливаем время окончания fallback через 1 час (на случай если счетчик не сработает)
        self.state.fallback_until = time.time() + 3600
        self._save_state()
        logger.warning(f"🚨 BILLING ERROR | Активирован fallback режим на {self.state.max_requests} обращений")
        logger.warning(f"🔄 Следующие запросы будут использовать резервную модель для обхода ограничений")
        logger.info(f"⏱️  Fallback активен в течение 1 часа или до {self.state.max_requests} обращений")

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
                # Счетчик превышен - деактивируем fallback
                logger.info("⏰ Fallback деактивирован: превышен лимит обращений")
                self.deactivate_fallback()
                return False

        # Если время истекло - деактивируем
        if self.state.fallback_active and current_time >= self.state.fallback_until:
            logger.info("⏰ Fallback деактивирован: истекло время")
            self.deactivate_fallback()
            return False

        return False

    def deactivate_fallback(self) -> None:
        """Деактивировать fallback режим"""
        if self.state.fallback_active:
            logger.info(f"✅ Fallback режим завершен после {self.state.request_count} обращений")
            logger.info("🔄 Возвращаемся к основной модели")
        self.state.fallback_active = False
        self.state.request_count = 0
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

    def get_status(self) -> Dict[str, Any]:
        """Получить текущий статус fallback"""
        return {
            'fallback_active': self.state.fallback_active,
            'request_count': self.state.request_count,
            'max_requests': self.state.max_requests,
            'time_remaining': max(0, int(self.state.fallback_until - time.time())),
            'last_billing_error': self.state.last_billing_error
        }