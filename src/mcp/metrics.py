"""
Metrics Manager для MCP сервера.

Сбор метрик производительности и мониторинга.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict, deque

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import ConfigLoader


class MetricsManager:
    """
    Менеджер метрик для MCP сервера.

    Собирает метрики производительности, использования и ошибок.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.logger = logging.getLogger(__name__)

        # Счетчики
        self.counters: Dict[str, int] = defaultdict(int)

        # Таймеры
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Гистограммы
        self.histograms: Dict[str, Dict[str, Any]] = {}

        # Метрики по времени
        self.time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Запуск времени
        self.start_time = datetime.utcnow()

    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        Инкремент счетчика.

        Args:
            name: Имя счетчика
            value: Значение для добавления
        """
        self.counters[name] += value

    def decrement_counter(self, name: str, value: int = 1) -> None:
        """
        Декремент счетчика.

        Args:
            name: Имя счетчика
            value: Значение для вычитания
        """
        self.counters[name] -= value

    def set_gauge(self, name: str, value: float) -> None:
        """
        Установка значения gauge метрики.

        Args:
            name: Имя метрики
            value: Значение
        """
        self.counters[name] = value

    def record_timer(self, name: str, duration_seconds: float) -> None:
        """
        Запись времени выполнения операции.

        Args:
            name: Имя таймера
            duration_seconds: Длительность в секундах
        """
        self.timers[name].append({
            'timestamp': datetime.utcnow(),
            'duration': duration_seconds
        })

    def time_operation(self, name: str):
        """
        Декоратор для измерения времени выполнения операции.

        Args:
            name: Имя операции

        Returns:
            Декоратор
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.record_timer(name, duration)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.record_timer(f"{name}_error", duration)
                    raise e
            return wrapper
        return decorator

    def start_timer(self, name: str) -> str:
        """
        Начало измерения времени.

        Args:
            name: Имя таймера

        Returns:
            ID таймера для завершения
        """
        timer_id = f"{name}_{int(time.time() * 1000000)}"
        self.counters[f"timer_{timer_id}_start"] = time.time()
        return timer_id

    def stop_timer(self, timer_id: str) -> float:
        """
        Завершение измерения времени.

        Args:
            timer_id: ID таймера

        Returns:
            Длительность в секундах
        """
        start_key = f"timer_{timer_id}_start"
        if start_key not in self.counters:
            return 0.0

        start_time = self.counters[start_key]
        duration = time.time() - start_time

        # Удаление ключа старта
        del self.counters[start_key]

        # Запись длительности
        name = timer_id.split('_')[0]
        self.record_timer(name, duration)

        return duration

    def record_histogram(self, name: str, value: float) -> None:
        """
        Запись значения в гистограмму.

        Args:
            name: Имя гистограммы
            value: Значение
        """
        if name not in self.histograms:
            self.histograms[name] = {
                'count': 0,
                'sum': 0.0,
                'min': float('inf'),
                'max': float('-inf'),
                'values': deque(maxlen=1000)
            }

        hist = self.histograms[name]
        hist['count'] += 1
        hist['sum'] += value
        hist['min'] = min(hist['min'], value)
        hist['max'] = max(hist['max'], value)
        hist['values'].append(value)

    def get_counter_value(self, name: str) -> int:
        """
        Получение значения счетчика.

        Args:
            name: Имя счетчика

        Returns:
            Значение счетчика
        """
        return self.counters.get(name, 0)

    def get_timer_stats(self, name: str) -> Dict[str, Any]:
        """
        Получение статистики таймера.

        Args:
            name: Имя таймера

        Returns:
            Статистика таймера
        """
        if name not in self.timers:
            return {}

        entries = list(self.timers[name])
        if not entries:
            return {}

        durations = [entry['duration'] for entry in entries]

        return {
            'count': len(durations),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'last_duration': durations[-1] if durations else 0,
            'p95_duration': self._percentile(durations, 95),
            'p99_duration': self._percentile(durations, 99),
        }

    def _percentile(self, data: list, percentile: float) -> float:
        """Расчет перцентиля."""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_histogram_stats(self, name: str) -> Dict[str, Any]:
        """
        Получение статистики гистограммы.

        Args:
            name: Имя гистограммы

        Returns:
            Статистика гистограммы
        """
        if name not in self.histograms:
            return {}

        hist = self.histograms[name]
        if hist['count'] == 0:
            return {}

        return {
            'count': hist['count'],
            'sum': hist['sum'],
            'avg': hist['sum'] / hist['count'],
            'min': hist['min'],
            'max': hist['max'],
            'last_value': hist['values'][-1] if hist['values'] else None,
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Получение всех метрик.

        Returns:
            Все метрики системы
        """
        metrics = {
            'counters': dict(self.counters),
            'timers': {},
            'histograms': {},
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
        }

        # Статистика таймеров
        for name in self.timers.keys():
            metrics['timers'][name] = self.get_timer_stats(name)

        # Статистика гистограмм
        for name in self.histograms.keys():
            metrics['histograms'][name] = self.get_histogram_stats(name)

        return metrics

    def reset_metrics(self) -> None:
        """Сброс всех метрик."""
        self.counters.clear()
        self.timers.clear()
        self.histograms.clear()
        self.time_series.clear()
        self.start_time = datetime.utcnow()
        self.logger.info("Metrics reset")

    def export_prometheus(self) -> str:
        """
        Экспорт метрик в формате Prometheus.

        Returns:
            Метрики в формате Prometheus
        """
        lines = []

        # Counters
        for name, value in self.counters.items():
            if not name.startswith('timer_'):  # Пропускаем внутренние таймеры
                lines.append(f"# HELP {name} Counter metric")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")

        # Histograms
        for name, stats in self.get_all_metrics()['histograms'].items():
            if stats:
                lines.append(f"# HELP {name} Histogram metric")
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count {stats['count']}")
                lines.append(f"{name}_sum {stats['sum']}")
                lines.append(f"{name}_bucket{{le=\"+Inf\"}} {stats['count']}")

        return "\n".join(lines)

    def log_summary(self) -> None:
        """Логирование сводки метрик."""
        metrics = self.get_all_metrics()

        self.logger.info("=== MCP Server Metrics Summary ===")
        self.logger.info(f"Uptime: {metrics['uptime_seconds']:.2f} seconds")
        self.logger.info(f"Counters: {len(metrics['counters'])} metrics")

        # Логирование основных счетчиков
        for name, value in metrics['counters'].items():
            if 'request' in name.lower() or 'error' in name.lower():
                self.logger.info(f"  {name}: {value}")

        # Логирование производительности
        for name, stats in metrics['timers'].items():
            if stats:
                self.logger.info(f"  {name}: avg={stats['avg_duration']:.3f}s, "
                               f"p95={stats['p95_duration']:.3f}s, "
                               f"count={stats['count']}")

        self.logger.info("=== End Metrics Summary ===")