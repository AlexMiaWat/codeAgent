"""
Мониторинг выполнения задач
"""

import logging
import time
import psutil
import threading
from typing import Dict, Any, Optional

from .interfaces import IExecutionMonitor

logger = logging.getLogger(__name__)


class ExecutionMetrics:
    """
    Метрики выполнения задачи
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.start_time = time.time()
        self.last_progress_time = self.start_time
        self.cpu_usage = []
        self.memory_usage = []
        self.progress_updates = []
        self.errors = []
        self.warnings = []
        self.status = "running"

    def update_progress(self, progress_data: Dict[str, Any]) -> None:
        """Обновление прогресса"""
        self.last_progress_time = time.time()
        self.progress_updates.append({
            'timestamp': self.last_progress_time,
            'data': progress_data
        })

    def record_resource_usage(self) -> None:
        """Запись использования ресурсов"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent

            self.cpu_usage.append({
                'timestamp': time.time(),
                'cpu_percent': cpu_percent
            })

            self.memory_usage.append({
                'timestamp': time.time(),
                'memory_percent': memory_percent
            })
        except Exception as e:
            logger.debug(f"Could not record resource usage: {e}")

    def record_error(self, error: str) -> None:
        """Запись ошибки"""
        self.errors.append({
            'timestamp': time.time(),
            'error': error
        })

    def record_warning(self, warning: str) -> None:
        """Запись предупреждения"""
        self.warnings.append({
            'timestamp': time.time(),
            'warning': warning
        })

    def finalize(self) -> Dict[str, Any]:
        """Финализация метрик"""
        end_time = time.time()
        duration = end_time - self.start_time

        return {
            'task_id': self.task_id,
            'duration': duration,
            'start_time': self.start_time,
            'end_time': end_time,
            'status': self.status,
            'cpu_avg': sum(d['cpu_percent'] for d in self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
            'cpu_peak': max((d['cpu_percent'] for d in self.cpu_usage), default=0),
            'memory_avg': sum(d['memory_percent'] for d in self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0,
            'memory_peak': max((d['memory_percent'] for d in self.memory_usage), default=0),
            'progress_updates': len(self.progress_updates),
            'last_progress_time': self.last_progress_time,
            'time_since_last_progress': end_time - self.last_progress_time,
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings),
            'errors': self.errors[-5:],  # Последние 5 ошибок
            'warnings': self.warnings[-5:]  # Последние 5 предупреждений
        }


class ExecutionMonitor(IExecutionMonitor):
    """
    Монитор выполнения задач с сбором метрик производительности
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация монитора выполнения

        Args:
            config: Конфигурация монитора
        """
        self.config = config or {}
        self.monitoring_interval = self.config.get('monitoring_interval', 5.0)  # Интервал мониторинга в секундах
        self.max_monitoring_time = self.config.get('max_monitoring_time', 3600)  # Максимальное время мониторинга
        self.resource_check_enabled = self.config.get('resource_check_enabled', True)

        self._active_monitors: Dict[str, ExecutionMetrics] = {}
        self._monitor_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}

    async def start_monitoring(self, task_id: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Начало мониторинга выполнения задачи

        Args:
            task_id: Идентификатор задачи
            context: Контекст выполнения
        """
        if task_id in self._active_monitors:
            logger.warning(f"Monitoring already active for task {task_id}")
            return

        # Создаем метрики для задачи
        metrics = ExecutionMetrics(task_id)
        self._active_monitors[task_id] = metrics

        # Создаем событие остановки
        stop_event = threading.Event()
        self._stop_events[task_id] = stop_event

        # Запускаем поток мониторинга
        monitor_thread = threading.Thread(
            target=self._monitor_task,
            args=(task_id, stop_event),
            daemon=True
        )
        self._monitor_threads[task_id] = monitor_thread
        monitor_thread.start()

        logger.info(f"Started monitoring for task {task_id}")

    async def update_progress(self, task_id: str, progress_data: Dict[str, Any]) -> None:
        """
        Обновление прогресса выполнения

        Args:
            task_id: Идентификатор задачи
            progress_data: Данные прогресса
        """
        if task_id in self._active_monitors:
            self._active_monitors[task_id].update_progress(progress_data)
            logger.debug(f"Progress updated for task {task_id}: {progress_data}")
        else:
            logger.warning(f"No active monitoring for task {task_id}")

    async def check_execution_health(self, task_id: str) -> Dict[str, Any]:
        """
        Проверка здоровья выполнения задачи

        Args:
            task_id: Идентификатор задачи

        Returns:
            Данные о здоровье выполнения
        """
        if task_id not in self._active_monitors:
            return {'status': 'not_monitoring', 'healthy': False}

        metrics = self._active_monitors[task_id]
        current_time = time.time()

        # Проверяем время без прогресса
        time_since_progress = current_time - metrics.last_progress_time
        progress_timeout = self.config.get('progress_timeout', 300)  # 5 минут по умолчанию

        # Проверяем использование ресурсов
        cpu_threshold = self.config.get('cpu_threshold', 95.0)
        memory_threshold = self.config.get('memory_threshold', 95.0)

        latest_cpu = metrics.cpu_usage[-1]['cpu_percent'] if metrics.cpu_usage else 0
        latest_memory = metrics.memory_usage[-1]['memory_percent'] if metrics.memory_usage else 0

        health_issues = []

        if time_since_progress > progress_timeout:
            health_issues.append(f"no_progress_for_{time_since_progress:.0f}s")

        if latest_cpu > cpu_threshold:
            health_issues.append(f"high_cpu_usage_{latest_cpu:.1f}%")

        if latest_memory > memory_threshold:
            health_issues.append(f"high_memory_usage_{latest_memory:.1f}%")

        return {
            'status': 'monitoring',
            'healthy': len(health_issues) == 0,
            'issues': health_issues,
            'time_since_progress': time_since_progress,
            'cpu_usage': latest_cpu,
            'memory_usage': latest_memory,
            'errors_count': len(metrics.errors),
            'warnings_count': len(metrics.warnings)
        }

    async def stop_monitoring(self, task_id: str) -> Dict[str, Any]:
        """
        Остановка мониторинга и получение финальных метрик

        Args:
            task_id: Идентификатор задачи

        Returns:
            Финальные метрики выполнения
        """
        if task_id not in self._active_monitors:
            logger.warning(f"No active monitoring for task {task_id}")
            return {'error': 'not_monitoring'}

        # Останавливаем мониторинг
        if task_id in self._stop_events:
            self._stop_events[task_id].set()

        # Ждем завершения потока мониторинга
        if task_id in self._monitor_threads:
            self._monitor_threads[task_id].join(timeout=5.0)

        # Получаем финальные метрики
        metrics = self._active_monitors[task_id]
        final_metrics = metrics.finalize()

        # Очищаем ресурсы
        del self._active_monitors[task_id]
        if task_id in self._monitor_threads:
            del self._monitor_threads[task_id]
        if task_id in self._stop_events:
            del self._stop_events[task_id]

        logger.info(f"Stopped monitoring for task {task_id}")
        return final_metrics

    def _monitor_task(self, task_id: str, stop_event: threading.Event) -> None:
        """
        Фоновая функция мониторинга задачи

        Args:
            task_id: Идентификатор задачи
            stop_event: Событие остановки
        """
        try:
            start_time = time.time()

            while not stop_event.is_set():
                if task_id not in self._active_monitors:
                    break

                # Проверяем максимальное время мониторинга
                if time.time() - start_time > self.max_monitoring_time:
                    logger.warning(f"Monitoring timeout for task {task_id}")
                    break

                # Записываем использование ресурсов
                if self.resource_check_enabled:
                    self._active_monitors[task_id].record_resource_usage()

                # Ждем следующего интервала
                if stop_event.wait(self.monitoring_interval):
                    break  # Событие остановки было установлено

        except Exception as e:
            logger.error(f"Error in monitoring thread for task {task_id}: {e}")

    def get_active_tasks(self) -> list[str]:
        """Получение списка активно мониторящихся задач"""
        return list(self._active_monitors.keys())

    def get_task_metrics(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получение текущих метрик задачи"""
        if task_id not in self._active_monitors:
            return None

        metrics = self._active_monitors[task_id]
        current_time = time.time()

        return {
            'task_id': task_id,
            'duration': current_time - metrics.start_time,
            'status': metrics.status,
            'progress_updates': len(metrics.progress_updates),
            'time_since_progress': current_time - metrics.last_progress_time,
            'cpu_current': metrics.cpu_usage[-1]['cpu_percent'] if metrics.cpu_usage else 0,
            'memory_current': metrics.memory_usage[-1]['memory_percent'] if metrics.memory_usage else 0,
            'errors_count': len(metrics.errors),
            'warnings_count': len(metrics.warnings)
        }