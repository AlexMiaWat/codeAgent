"""
Cache Manager для MCP сервера.

Реализует кэширование ресурсов для улучшения производительности.
"""

import asyncio
import logging
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import ConfigLoader


@dataclass
class CacheEntry:
    """Запись в кэше."""
    key: str
    data: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0


class CacheManager:
    """
    Менеджер кэширования для MCP сервера.

    Поддерживает TTL, LRU eviction и мониторинг производительности.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.logger = logging.getLogger(__name__)

        # Настройки кэша
        self.max_size_mb = 100  # Максимальный размер кэша в MB
        self.default_ttl_seconds = 300  # 5 минут по умолчанию
        self.cleanup_interval_seconds = 60  # Очистка каждую минуту

        # Хранилище кэша
        self.cache: Dict[str, CacheEntry] = {}
        self.current_size_bytes = 0

        # Статистика
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        # Запуск cleanup task
        self.cleanup_task = None

    def start_cleanup_task(self):
        """Запуск фоновой задачи очистки кэша."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_cleanup_task(self):
        """Остановка фоновой задачи очистки."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            self.cleanup_task = None

    async def _cleanup_loop(self):
        """Фоновая задача очистки истекших записей."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                self._cleanup_expired()
                self._evict_if_needed()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

    def _cleanup_expired(self):
        """Очистка истекших записей."""
        now = datetime.utcnow()
        expired_keys = []

        for key, entry in self.cache.items():
            if entry.expires_at and entry.expires_at < now:
                expired_keys.append(key)
                self.current_size_bytes -= entry.size_bytes

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _evict_if_needed(self):
        """Выселение записей если превышен лимит размера."""
        max_size_bytes = self.max_size_mb * 1024 * 1024

        if self.current_size_bytes <= max_size_bytes:
            return

        # LRU eviction - удаляем самые старые записи
        entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )

        evicted_count = 0
        for key, entry in entries:
            if self.current_size_bytes <= max_size_bytes:
                break

            del self.cache[key]
            self.current_size_bytes -= entry.size_bytes
            evicted_count += 1
            self.evictions += 1

        if evicted_count > 0:
            self.logger.debug(f"Evicted {evicted_count} cache entries due to size limit")

    def _calculate_size(self, data: Any) -> int:
        """Расчет размера данных в байтах."""
        if isinstance(data, str):
            return len(data.encode('utf-8'))
        elif isinstance(data, dict):
            return len(str(data).encode('utf-8'))
        elif isinstance(data, list):
            return len(str(data).encode('utf-8'))
        else:
            return len(str(data).encode('utf-8'))

    def _generate_key(self, *args, **kwargs) -> str:
        """Генерация ключа кэша."""
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """
        Получение данных из кэша.

        Args:
            key: Ключ кэша

        Returns:
            Данные или None если ключ не найден
        """
        entry = self.cache.get(key)
        if entry is None:
            self.misses += 1
            return None

        # Проверка срока действия
        if entry.expires_at and entry.expires_at < datetime.utcnow():
            self._remove_entry(key)
            self.misses += 1
            return None

        # Обновление статистики доступа
        entry.access_count += 1
        entry.last_accessed = datetime.utcnow()
        self.hits += 1

        return entry.data

    async def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Сохранение данных в кэше.

        Args:
            key: Ключ кэша
            data: Данные для сохранения
            ttl_seconds: Время жизни в секундах (опционально)
        """
        now = datetime.utcnow()
        expires_at = None

        if ttl_seconds:
            expires_at = now + timedelta(seconds=ttl_seconds)
        elif self.default_ttl_seconds:
            expires_at = now + timedelta(seconds=self.default_ttl_seconds)

        size_bytes = self._calculate_size(data)

        # Проверка лимита размера перед добавлением
        if self.current_size_bytes + size_bytes > self.max_size_mb * 1024 * 1024:
            self._evict_if_needed()

            # Если после eviction все равно не хватает места, пропускаем кэширование
            if self.current_size_bytes + size_bytes > self.max_size_mb * 1024 * 1024:
                self.logger.debug(f"Skipping cache for key {key}: size limit exceeded")
                return

        # Удаление старой записи если существует
        if key in self.cache:
            old_entry = self.cache[key]
            self.current_size_bytes -= old_entry.size_bytes

        # Создание новой записи
        entry = CacheEntry(
            key=key,
            data=data,
            created_at=now,
            expires_at=expires_at,
            last_accessed=now,
            size_bytes=size_bytes
        )

        self.cache[key] = entry
        self.current_size_bytes += size_bytes

    async def delete(self, key: str) -> bool:
        """
        Удаление записи из кэша.

        Args:
            key: Ключ кэша

        Returns:
            True если запись была удалена
        """
        return self._remove_entry(key)

    def _remove_entry(self, key: str) -> bool:
        """Удаление записи из кэша."""
        if key in self.cache:
            entry = self.cache[key]
            self.current_size_bytes -= entry.size_bytes
            del self.cache[key]
            return True
        return False

    async def clear(self) -> None:
        """Очистка всего кэша."""
        self.cache.clear()
        self.current_size_bytes = 0
        self.logger.info("Cache cleared")

    async def get_or_set(self, key: str, fetch_func: Callable, ttl_seconds: Optional[int] = None) -> Any:
        """
        Получение данных из кэша или установка новых.

        Args:
            key: Ключ кэша
            fetch_func: Функция для получения данных если их нет в кэше
            ttl_seconds: Время жизни в секундах

        Returns:
            Данные
        """
        # Попытка получить из кэша
        cached_data = await self.get(key)
        if cached_data is not None:
            return cached_data

        # Получение новых данных
        data = await fetch_func()

        # Сохранение в кэш
        await self.set(key, data, ttl_seconds)

        return data

    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики кэша.

        Returns:
            Статистика использования кэша
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) * 100 if total_requests > 0 else 0

        return {
            "entries_count": len(self.cache),
            "current_size_mb": self.current_size_bytes / (1024 * 1024),
            "max_size_mb": self.max_size_mb,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self.evictions,
            "oldest_entry_age_seconds": self._get_oldest_entry_age(),
        }

    def _get_oldest_entry_age(self) -> Optional[int]:
        """Получение возраста самой старой записи."""
        if not self.cache:
            return None

        now = datetime.utcnow()
        oldest = min(entry.created_at for entry in self.cache.values())
        return int((now - oldest).total_seconds())

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Инвалидация записей по шаблону.

        Args:
            pattern: Шаблон для поиска ключей

        Returns:
            Количество удаленных записей
        """
        keys_to_remove = []

        for key in self.cache.keys():
            if pattern in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self._remove_entry(key)

        if keys_to_remove:
            self.logger.debug(f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}")

        return len(keys_to_remove)

    async def warmup(self, keys_and_fetchers: Dict[str, Callable]) -> None:
        """
        Предварительная загрузка кэша.

        Args:
            keys_and_fetchers: Словарь ключ -> функция получения данных
        """
        self.logger.info(f"Starting cache warmup with {len(keys_and_fetchers)} entries")

        for key, fetch_func in keys_and_fetchers.items():
            try:
                data = await fetch_func()
                await self.set(key, data)
            except Exception as e:
                self.logger.error(f"Error warming up cache for key {key}: {e}")

        self.logger.info("Cache warmup completed")

    def is_enabled(self) -> bool:
        """Проверка включен ли кэш."""
        return True  # Можно добавить настройку для отключения кэша