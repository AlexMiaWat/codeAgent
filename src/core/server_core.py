"""
ServerCore - базовый компонент для цикла выполнения задач

НАСТОЯЩАЯ РЕАЛИЗАЦИЯ: содержит всю базовую логику цикла выполнения,
а не является прокси-объектом как в предыдущей версии.

Отвечает за основную логику цикла выполнения:
- Получение и фильтрация задач
- Управление итерациями
- Обработка сценариев отсутствия задач (ревизия, генерация TODO)
- Координация выполнения задач через внешние обработчики
- Управление задержками между задачами
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Protocol
from datetime import datetime

from ..core.interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger
from ..todo_manager import TodoItem
from ..quality import QualityGateManager
from ..quality.models.quality_result import QualityGateResult

logger = logging.getLogger(__name__)


class QualityGateException(Exception):
    """
    Исключение, выбрасываемое при неудачной проверке Quality Gates
    """

    def __init__(self, message: str, gate_result: Any = None):
        """
        Инициализация исключения

        Args:
            message: Сообщение об ошибке
            gate_result: Результат проверки quality gates
        """
        super().__init__(message)
        self.gate_result = gate_result


class TaskExecutor(Protocol):
    """Протокол для выполнения задач"""

    def __call__(self, todo_item: TodoItem, task_number: int, total_tasks: int) -> bool:
        """
        Выполнить задачу

        Args:
            todo_item: Задача для выполнения
            task_number: Номер задачи в итерации
            total_tasks: Общее количество задач

        Returns:
            True если выполнение успешно
        """
        ...


class RevisionExecutor(Protocol):
    """Протокол для выполнения ревизии проекта"""

    def __call__(self) -> bool:
        """
        Выполнить ревизию проекта

        Returns:
            True если ревизия успешна
        """
        ...


class TodoGenerator(Protocol):
    """Протокол для генерации нового TODO списка"""

    def __call__(self) -> bool:
        """
        Сгенерировать новый TODO список

        Returns:
            True если генерация успешна
        """
        ...


class ServerCore:
    """
    Базовый цикл выполнения задач Code Agent

    НАСТОЯЩАЯ РЕАЛИЗАЦИЯ: содержит всю логику цикла выполнения,
    а не делегирует вызовы внешним методам.

    Отвечает за:
    - Управление итерациями выполнения
    - Синхронизацию задач с checkpoint системой
    - Обработку сценариев отсутствия задач
    - Выполнение задач с правильной координацией
    """

    def __init__(
        self,
        todo_manager: ITodoManager,
        checkpoint_manager: ICheckpointManager,
        status_manager: IStatusManager,
        server_logger: ILogger,
        task_executor: TaskExecutor,
        revision_executor: RevisionExecutor,
        todo_generator: TodoGenerator,
        config: Dict[str, Any],
        project_dir: Path,
        quality_gate_manager: Optional[QualityGateManager] = None,
        auto_todo_enabled: bool = True,
        task_delay: int = 5
    ):
        """
        Инициализация ServerCore

        Args:
            todo_manager: Менеджер задач
            checkpoint_manager: Менеджер контрольных точек
            status_manager: Менеджер статусов
            server_logger: Логгер сервера
            task_executor: Обработчик выполнения задач
            revision_executor: Обработчик ревизии проекта
            todo_generator: Обработчик генерации TODO
            config: Конфигурация сервера
            project_dir: Директория проекта
            auto_todo_enabled: Включена ли автоматическая генерация TODO
            task_delay: Задержка между задачами в секундах
        """
        self.todo_manager = todo_manager
        self.checkpoint_manager = checkpoint_manager
        self.status_manager = status_manager
        self.server_logger = server_logger
        self.project_dir = Path(project_dir)
        self.task_executor = task_executor
        self.revision_executor = revision_executor
        self.todo_generator = todo_generator
        self.config = config
        self.quality_gate_manager = quality_gate_manager or QualityGateManager()
        self.auto_todo_enabled = auto_todo_enabled
        self.task_delay = task_delay

        # Состояние ревизии для текущей сессии
        self._revision_done = False

    def execute_iteration(self, iteration: int) -> tuple[bool, list]:
        """
        Выполнить одну итерацию цикла

        Args:
            iteration: Номер итерации

        Returns:
            Кортеж (has_more_tasks, pending_tasks):
            - has_more_tasks: True если есть еще задачи для выполнения
            - pending_tasks: Список задач для выполнения (может быть пустым после обработки сценария "нет задач")
        """
        logger.info(f"Начало итерации {iteration} в ServerCore")

        # Увеличиваем счетчик итераций в checkpoint
        self.checkpoint_manager.increment_iteration()

        # Синхронизируем TODO с checkpoint перед получением задач
        self._sync_todos_with_checkpoint()

        # Получаем непройденные задачи
        pending_tasks = self.todo_manager.get_pending_tasks()

        # Дополнительная фильтрация: исключаем задачи, которые уже выполнены в checkpoint
        pending_tasks = self._filter_completed_tasks(pending_tasks)

        # Обрабатываем сценарий отсутствия задач
        if not pending_tasks:
            has_more_tasks = self._handle_no_tasks_scenario()
            # После обработки сценария "нет задач" получаем актуальный список задач
            pending_tasks = self.todo_manager.get_pending_tasks()
            pending_tasks = self._filter_completed_tasks(pending_tasks)
            return has_more_tasks, pending_tasks

        # Quality gates теперь проверяются индивидуально для каждой задачи в execute_single_task

        # Логируем начало итерации
        self.server_logger.log_iteration_start(iteration, len(pending_tasks))
        logger.info(f"Найдено непройденных задач: {len(pending_tasks)}")

        return True, pending_tasks

    def execute_single_task(self, todo_item: TodoItem, task_number: int, total_tasks: int) -> bool:
        """
        Выполнить отдельную задачу

        Args:
            todo_item: Задача для выполнения
            task_number: Номер задачи в итерации
            total_tasks: Общее количество задач

        Returns:
            True если выполнение успешно
        """
        self.status_manager.add_separator()

        # Проверка Quality Gates перед выполнением задачи
        if self.quality_gate_manager and self._is_quality_gates_enabled():
            try:
                import asyncio
                try:
                    # Check if we're already in an event loop
                    loop = asyncio.get_running_loop()
                    # If we are, create a task instead
                    gate_result = loop.create_task(self.quality_gate_manager.run_all_gates(context={
                        'task_type': todo_item.category or 'default',
                        'task_id': todo_item.id,
                        'project_path': str(self.project_dir)
                    }))
                    # For simplicity, we'll run it synchronously in this context
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, gate_result)
                        gate_result = future.result()
                except RuntimeError:
                    # No running event loop, use asyncio.run
                    gate_result = asyncio.run(self.quality_gate_manager.run_all_gates(context={
                        'task_type': todo_item.category or 'default',
                        'task_id': todo_item.id,
                        'project_path': str(self.project_dir)
                    }))

                logger.info(f"Quality gates check completed: {gate_result.overall_status.value}")

                # Проверяем нужно ли блокировать выполнение
                if self.quality_gate_manager.should_block_execution(gate_result):
                    error_msg = f"Quality gates failed for task {todo_item.id}: {gate_result.overall_status.value}"
                    logger.error(error_msg)
                    raise QualityGateException(error_msg, gate_result)

            except QualityGateException:
                raise  # Перебрасываем исключение дальше
            except Exception as e:
                logger.error(f"Error during quality gates check: {e}")
                # В случае ошибки проверки качества - продолжаем выполнение (fail-open)
                logger.warning("Continuing execution despite quality gates error (fail-open policy)")

        # Выполнение задачи
        success = self.task_executor(todo_item, task_number=task_number, total_tasks=total_tasks)

        # Применяем задержку между задачами
        if success and task_number < total_tasks and self.task_delay > 0:
            logger.debug(f"Задержка между задачами: {self.task_delay} сек")
            time.sleep(self.task_delay)

        return success

    async def execute_tasks_batch(self, pending_tasks: List[TodoItem], iteration: int) -> bool:
        """
        Выполнить пакет задач в рамках одной итерации

        Args:
            pending_tasks: Список задач для выполнения
            iteration: Номер итерации

        Returns:
            True если итерация должна продолжаться
        """
        total_tasks = len(pending_tasks)

        for idx, todo_item in enumerate(pending_tasks, start=1):
            success = self.execute_single_task(todo_item, task_number=idx, total_tasks=total_tasks)
            if not success:
                logger.warning(f"Задача {idx}/{total_tasks} завершилась с ошибкой")
                # Продолжаем выполнение следующих задач

        return True  # Итерация завершена успешно

    def _handle_no_tasks_scenario(self) -> bool:
        """
        Обработка сценария отсутствия задач

        Returns:
            True если есть новые задачи после обработки, False иначе
        """
        logger.info("Все задачи выполнены")

        self.status_manager.append_status(
            f"Все задачи выполнены. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            level=2
        )

        # Выполняем ревизию проекта если она еще не выполнялась в этой сессии
        if not self._revision_done:
            logger.info("=" * 80)
            logger.info("ВЫПОЛНЕНИЕ РЕВИЗИИ ПРОЕКТА (все задачи выполнены)")
            logger.info("=" * 80)

            revision_success = self.revision_executor()

            if revision_success:
                self._revision_done = True
                logger.info("Ревизия проекта успешно завершена")

                # После ревизии перезагружаем задачи
                self._reload_todos_and_check_for_new_tasks()
                return True  # Есть новые задачи после ревизии
            else:
                logger.warning("Ревизия не завершена полностью, но продолжаем работу")
                self._reload_todos_and_check_for_new_tasks()
                return True
        else:
            logger.info("Ревизия уже выполнена в этой сессии, пропускаем")
            self._reload_todos_and_check_for_new_tasks()
            return True

        # Если после ревизии все еще нет задач, пробуем сгенерировать новый TODO
        if not self._has_pending_tasks_after_reload():
            if self.auto_todo_enabled:
                logger.info("=" * 80)
                logger.info("ГЕНЕРАЦИЯ НОВОГО TODO ЛИСТА (все todo выполнены и ревизия завершена)")
                logger.info("=" * 80)

                generation_success = self.todo_generator()

                if generation_success:
                    logger.info("Новый TODO лист успешно сгенерирован, перезагрузка задач")
                    self._reload_todos_and_check_for_new_tasks()
                    return True
                else:
                    logger.warning("Генерация TODO не выполнена")
                    return False
            else:
                logger.info("Генерация TODO отключена")
                return False

        return False

    def _sync_todos_with_checkpoint(self):
        """
        Синхронизация TODO задач с checkpoint - помечает задачи как выполненные в TODO файле,
        если они помечены как completed в checkpoint
        """
        try:
            # Получаем все задачи из TODO
            all_todo_items = self.todo_manager.get_all_tasks()

            # Получаем все завершенные задачи из checkpoint
            completed_tasks_in_checkpoint = self.checkpoint_manager.get_completed_tasks()

            # Создаем словарь завершенных задач для быстрого поиска
            completed_task_texts = set()
            for task in completed_tasks_in_checkpoint:
                task_text = task.get("task_text", "")
                if task_text:
                    completed_task_texts.add(task_text)

            # Синхронизируем: помечаем задачи как done в TODO, если они completed в checkpoint
            synced_count = 0
            for todo_item in all_todo_items:
                if not todo_item.done and todo_item.text in completed_task_texts:
                    # Задача выполнена в checkpoint, но не отмечена в TODO файле
                    todo_item.done = True
                    synced_count += 1
                    logger.debug(f"Синхронизация: задача '{todo_item.text}' помечена как выполненная в TODO")

            # Сохраняем изменения в TODO файл
            if synced_count > 0:
                self.todo_manager._save_todos()
                logger.info(f"Синхронизация TODO с checkpoint: {synced_count} задач помечено как выполненные")
            else:
                logger.debug("Синхронизация TODO с checkpoint: изменений не требуется")

        except Exception as e:
            logger.error(f"Ошибка при синхронизации TODO с checkpoint: {e}", exc_info=True)

    def _filter_completed_tasks(self, tasks: List[TodoItem]) -> List[TodoItem]:
        """
        Фильтрация задач: исключает задачи, которые уже выполнены в checkpoint

        Args:
            tasks: Список задач для фильтрации

        Returns:
            Отфильтрованный список задач
        """
        try:
            # Получаем все завершенные задачи из checkpoint
            completed_tasks_in_checkpoint = self.checkpoint_manager.get_completed_tasks()

            # Создаем множество текстов завершенных задач для быстрого поиска
            completed_task_texts = set()
            for task in completed_tasks_in_checkpoint:
                task_text = task.get("task_text", "")
                if task_text:
                    completed_task_texts.add(task_text)

            # Фильтруем задачи
            filtered_tasks = []
            for task in tasks:
                if task.text not in completed_task_texts:
                    filtered_tasks.append(task)
                else:
                    logger.debug(f"Задача '{task.text}' уже выполнена в checkpoint, пропускаем")

            filtered_count = len(tasks) - len(filtered_tasks)
            if filtered_count > 0:
                logger.info(f"Отфильтровано {filtered_count} уже выполненных задач из checkpoint")

            return filtered_tasks

        except Exception as e:
            logger.error(f"Ошибка при фильтрации выполненных задач: {e}", exc_info=True)
            return tasks  # Возвращаем исходный список в случае ошибки

    def _reload_todos_and_check_for_new_tasks(self):
        """
        Перезагрузка TODO и проверка на наличие новых задач
        """
        # Перезагружаем задачи через интерфейс
        self.todo_manager.load_todos()

        # Синхронизируем с checkpoint после перезагрузки
        self._sync_todos_with_checkpoint()

    def _has_pending_tasks_after_reload(self) -> bool:
        """
        Проверка наличия ожидающих задач после перезагрузки

        Returns:
            True если есть ожидающие задачи
        """
        pending_tasks = self.todo_manager.get_pending_tasks()
        pending_tasks = self._filter_completed_tasks(pending_tasks)
        return len(pending_tasks) > 0

    def _apply_task_delay(self):
        """
        Применить задержку между задачами
        """
        import time
        if self.task_delay > 0:
            logger.debug(f"Задержка между задачами: {self.task_delay} сек")
            time.sleep(self.task_delay)

    def mark_revision_done(self):
        """
        Отметить, что ревизия выполнена в текущей сессии
        """
        self._revision_done = True

    def is_revision_done(self) -> bool:
        """
        Проверить, выполнена ли ревизия в текущей сессии

        Returns:
            True если ревизия выполнена
        """
        return self._revision_done

    def sync_revision_state(self, revision_done: bool):
        """
        Синхронизировать состояние ревизии с внешним компонентом

        Args:
            revision_done: Текущее состояние ревизии
        """
        self._revision_done = revision_done



    def get_quality_gate_manager(self) -> QualityGateManager:
        """
        Получить менеджер quality gates

        Returns:
            QualityGateManager instance
        """
        return self.quality_gate_manager

    def configure_quality_gates(self, config: Dict[str, Any]):
        """
        Настроить quality gates

        Args:
            config: Конфигурация quality gates
        """
        self.quality_gate_manager.configure(config)
        logger.info("Quality gates configured")

    def _is_quality_gates_enabled(self) -> bool:
        """
        Проверить, включены ли quality gates

        Returns:
            True если quality gates включены
        """
        if not self.quality_gate_manager:
            return False

        # Проверяем глобальную настройку enabled
        quality_config = self.config.get('quality_gates', {})
        return quality_config.get('enabled', False)