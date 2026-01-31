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
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Protocol, TYPE_CHECKING
from datetime import datetime
from collections import defaultdict

from ..core.interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger
from ..quality import QualityGateManager
from ..quality.models.quality_result import QualityCheckType
from ..core.types import TaskType
from ..verification.verification_manager import MultiLevelVerificationManager
from ..verification.interfaces import IMultiLevelVerificationManager

# Новая архитектура LLM
try:
    from ..llm.manager import LLMManager
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    LLMManager = None

if TYPE_CHECKING:
    from ..todo_manager import TodoItem

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

    def __call__(self, todo_item: 'TodoItem', task_number: int, total_tasks: int) -> bool:
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

    # Константы
    DEFAULT_EXECUTION_DELAY = 5  # Задержка между задачами по умолчанию (секунды)

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
        verification_manager: Optional[IMultiLevelVerificationManager] = None,
        llm_manager: Optional[LLMManager] = None,
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
            quality_gate_manager: Менеджер quality gates
            verification_manager: Менеджер многоуровневой верификации
            llm_manager: Менеджер LLM для новой архитектуры (опционально)
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
        self.quality_gate_manager = quality_gate_manager or QualityGateManager(self.config.get('quality_gates', {}))
        self.verification_manager = verification_manager or MultiLevelVerificationManager(self.config.get('verification', {}))
        self.llm_manager = llm_manager
        self.auto_todo_enabled = auto_todo_enabled
        self.task_delay = task_delay

        # Состояние ревизии для текущей сессии
        self._revision_done = False

        # Настройки стратегии выполнения по типам задач
        self._execution_strategies = self._init_execution_strategies()

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

        # Приоритизация задач по типам
        pending_tasks = self._prioritize_tasks(pending_tasks)

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

    async def execute_single_task(self, todo_item: 'TodoItem', task_number: int, total_tasks: int) -> tuple[bool, Dict[str, Any]]:
        """
        Выполнить отдельную задачу с многоуровневой верификацией

        Args:
            todo_item: Задача для выполнения
            task_number: Номер задачи в итерации
            total_tasks: Общее количество задач

        Returns:
            Кортеж (success, verification_result):
            - success: True если выполнение успешно
            - verification_result: Результаты верификации
        """
        self.status_manager.add_separator()

        verification_context = {
            'task_id': todo_item.id,
            'task_type': todo_item.category or 'default',
            'task_description': todo_item.text,
            'project_path': str(self.project_dir),
            'todo_manager': self.todo_manager,
            'iteration_context': {
                'task_number': task_number,
                'total_tasks': total_tasks
            }
        }

        # Инициализируем результат верификации
        verification_result = {
            'task_id': todo_item.id,
            'verification_passed': True,
            'levels_executed': [],
            'scores': {},
            'execution_result': {},
            'decisions': []
        }

        try:
            # Валидация типа задачи перед выполнением
            if not self._validate_task_type(todo_item):
                logger.warning(f"Пропускаем выполнение задачи без определенного типа: {todo_item.text}")
                verification_result['verification_passed'] = False
                verification_result['decisions'].append('task_validation_failed')
                return False, verification_result

            # Уровень 1: Pre-execution verification
            logger.info(f"Running pre-execution verification for task {todo_item.id}")
            pre_result = await self.verification_manager.run_pre_execution_checks(
                todo_item.id, verification_context
            )
            verification_result['levels_executed'].append('pre_execution')
            verification_result['scores']['pre_execution'] = pre_result.overall_score

            # Проверяем порог для pre-execution
            if pre_result.overall_score is not None and pre_result.overall_score < 0.7:
                logger.warning(f"Pre-execution verification failed for task {todo_item.id}: score {pre_result.overall_score}")
                verification_result['verification_passed'] = False
                verification_result['decisions'].append('pre_execution_threshold_not_met')
                return False, verification_result

            # Уровень 2: In-execution monitoring (запускаем параллельно с выполнением)
            logger.info(f"Starting in-execution monitoring for task {todo_item.id}")
            in_execution_task = asyncio.create_task(
                self.verification_manager.run_in_execution_monitoring(todo_item.id, verification_context)
            )

            # Выполнение задачи
            logger.info(f"Executing task {todo_item.id}: {todo_item.text}")
            success = await self.task_executor(todo_item, task_number=task_number, total_tasks=total_tasks)
            verification_result['execution_result'] = {'success': success}

            # Ждем завершения in-execution мониторинга
            in_result = await in_execution_task
            verification_result['levels_executed'].append('in_execution')
            verification_result['scores']['in_execution'] = in_result.overall_score

            # Уровень 3: Post-execution validation
            logger.info(f"Running post-execution validation for task {todo_item.id}")
            post_result = await self.verification_manager.run_post_execution_validation(
                todo_item.id, verification_result['execution_result'], verification_context
            )
            verification_result['levels_executed'].append('post_execution')
            verification_result['scores']['post_execution'] = post_result.overall_score

            # Уровень 4: AI validation (если есть данные для анализа)
            analysis_data = self._prepare_analysis_data(todo_item, verification_result)
            if analysis_data:
                logger.info(f"Running AI validation for task {todo_item.id}")
                ai_result = await self.verification_manager.run_ai_validation(
                    todo_item.id, analysis_data, verification_context
                )
                verification_result['levels_executed'].append('ai_validation')
                verification_result['scores']['ai_validation'] = ai_result.overall_score
            else:
                logger.debug(f"No analysis data available for AI validation of task {todo_item.id}")

            # Принимаем решение на основе результатов верификации
            decision = self._make_verification_decision(verification_result)
            verification_result['decisions'].append(decision)

            if decision == 'block_execution':
                logger.error(f"Task {todo_item.id} blocked due to verification results")
                verification_result['verification_passed'] = False
                success = False
            elif decision == 'warn_but_continue':
                logger.warning(f"Task {todo_item.id} has verification warnings but continuing")
                verification_result['verification_passed'] = True
            else:  # approve_execution
                logger.info(f"Task {todo_item.id} passed all verification levels")
                verification_result['verification_passed'] = True

            # Применяем задержку между задачами (учитывая тип задачи)
            if success and task_number < total_tasks and self.task_delay > 0:
                task_delay = self._calculate_task_delay(todo_item)
                logger.debug(f"Задержка между задачами: {task_delay} сек (тип: {todo_item.effective_task_type.display_name if todo_item.effective_task_type else 'неизвестный'})")
                await asyncio.sleep(task_delay)

            return success, verification_result

        except Exception as e:
            logger.error(f"Error during task execution and verification for {todo_item.id}: {e}")
            verification_result['verification_passed'] = False
            verification_result['decisions'].append('execution_error')
            verification_result['error'] = str(e)
            return False, verification_result

    async def execute_tasks_batch(self, pending_tasks: List['TodoItem'], iteration: int) -> bool:
        """
        Выполнить пакет задач в рамках одной итерации с учетом стратегий выполнения

        Args:
            pending_tasks: Список задач для выполнения
            iteration: Номер итерации

        Returns:
            True если итерация должна продолжаться
        """
        # Группируем задачи по типам для выполнения по стратегиям
        tasks_by_type = defaultdict(list)
        for task in pending_tasks:
            task_type = task.effective_task_type or TaskType.CODE  # По умолчанию CODE
            tasks_by_type[task_type].append(task)

        # Выполняем задачи по типам с учетом batch_size
        for task_type, tasks in tasks_by_type.items():
            strategy = self._execution_strategies.get(task_type, self._execution_strategies[TaskType.CODE])
            batch_size = strategy['batch_size']

            logger.info(f"Выполнение задач типа {task_type.display_name} (batch_size={batch_size})")

            # Выполняем задачи батчами
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                batch_start_idx = i + 1

                for idx_in_batch, todo_item in enumerate(batch, start=1):
                    global_idx = batch_start_idx + idx_in_batch - 1
                    success, verification_result = await self.execute_single_task(todo_item, task_number=global_idx, total_tasks=len(tasks))

                    # Логируем результаты верификации
                    logger.info(f"Task {todo_item.id} verification: passed={verification_result.get('verification_passed', False)}, "
                               f"levels={verification_result.get('levels_executed', [])}")

                    if not success:
                        logger.warning(f"Задача {global_idx}/{len(tasks)} типа {task_type.display_name} завершилась с ошибкой")
                        # Продолжаем выполнение следующих задач

                    # Применяем задержку между задачами в батче (если не последняя задача в батче)
                    if idx_in_batch < len(batch) and self.task_delay > 0:
                        task_delay = self._calculate_task_delay(todo_item)
                        logger.debug(f"Задержка между задачами типа {task_type.display_name}: {task_delay} сек")
                        await asyncio.sleep(task_delay)

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

    def _filter_completed_tasks(self, tasks: List['TodoItem']) -> List['TodoItem']:
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

    def get_verification_manager(self) -> IMultiLevelVerificationManager:
        """
        Получить менеджер многоуровневой верификации

        Returns:
            MultiLevelVerificationManager instance
        """
        return self.verification_manager

    def configure_quality_gates(self, config: Dict[str, Any]):
        """
        Настроить quality gates

        Args:
            config: Конфигурация quality gates
        """
        self.quality_gate_manager.configure(config)
        logger.info("Quality gates configured")

    def configure_verification(self, config: Dict[str, Any]):
        """
        Настроить многоуровневую верификацию

        Args:
            config: Конфигурация верификации
        """
        if hasattr(self.verification_manager, 'config'):
            self.verification_manager.config.update(config)
            # Пересоздаем компоненты с новой конфигурацией
            from ..verification.execution_monitor import ExecutionMonitor
            from ..verification.llm_validator import LLMValidator
            self.verification_manager.execution_monitor = ExecutionMonitor(config.get('execution_monitor', {}))
            self.verification_manager.llm_validator = LLMValidator(config=config.get('llm_validator', {}))
            self.verification_manager.level_configs = config.get('levels', self.verification_manager.level_configs)
            self.verification_manager.overall_threshold = config.get('overall_threshold', self.verification_manager.overall_threshold)
        logger.info("Multi-level verification configured")

    def get_llm_manager(self) -> Optional[LLMManager]:
        """
        Получить менеджер LLM

        Returns:
            LLMManager instance или None если недоступен
        """
        return self.llm_manager

    def is_llm_available(self) -> bool:
        """
        Проверить доступность LLM Manager

        Returns:
            True если LLM Manager доступен
        """
        return self.llm_manager is not None and LLM_AVAILABLE

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

    def _init_execution_strategies(self) -> Dict[TaskType, Dict[str, Any]]:
        """
        Инициализация стратегий выполнения для разных типов задач

        Returns:
            Словарь стратегий выполнения по типам задач
        """
        return {
            TaskType.CODE: {
                'priority': 1,
                'batch_size': 3,  # Выполняем по 3 задачи разработки за раз
                'delay_multiplier': 1.0,  # Стандартная задержка
                'quality_gates_required': True,  # Обязательные quality gates
                'max_failures': 2,  # Максимум 2 неудачи подряд
            },
            TaskType.TEST: {
                'priority': 2,
                'batch_size': 2,  # Выполняем по 2 тестовые задачи за раз
                'delay_multiplier': 0.5,  # Уменьшенная задержка
                'quality_gates_required': True,
                'max_failures': 1,  # Максимум 1 неудача подряд
            },
            TaskType.REFACTOR: {
                'priority': 3,
                'batch_size': 1,  # Выполняем по 1 задаче рефакторинга за раз
                'delay_multiplier': 1.5,  # Увеличенная задержка
                'quality_gates_required': True,
                'max_failures': 1,
            },
            TaskType.DOCS: {
                'priority': 4,
                'batch_size': 5,  # Выполняем по 5 документационных задач за раз
                'delay_multiplier': 0.3,  # Минимальная задержка
                'quality_gates_required': False,  # Quality gates не обязательны
                'max_failures': 3,  # Максимум 3 неудачи подряд
            },
            TaskType.RELEASE: {
                'priority': 5,
                'batch_size': 1,  # Выполняем по 1 задаче релиза за раз
                'delay_multiplier': 2.0,  # Значительная задержка
                'quality_gates_required': True,
                'max_failures': 0,  # Никаких неудач
            },
            TaskType.DEVOPS: {
                'priority': 6,
                'batch_size': 2,  # Выполняем по 2 devops задачи за раз
                'delay_multiplier': 1.2,  # Немного увеличенная задержка
                'quality_gates_required': True,
                'max_failures': 1,
            }
        }

    def _prioritize_tasks(self, tasks: List['TodoItem']) -> List['TodoItem']:
        """
        Приоритизация задач на основе их типов

        Args:
            tasks: Список задач для приоритизации

        Returns:
            Отсортированный список задач по приоритету
        """
        def get_task_priority(task: 'TodoItem') -> int:
            task_type = task.effective_task_type
            if task_type and task_type in self._execution_strategies:
                return self._execution_strategies[task_type]['priority']
            else:
                return 99  # Задачи без типа имеют самый низкий приоритет

        # Сортируем по приоритету (меньше число = выше приоритет)
        return sorted(tasks, key=get_task_priority)

    def _get_execution_strategy(self, task: 'TodoItem') -> Dict[str, Any]:
        """
        Получить стратегию выполнения для задачи

        Args:
            task: Задача

        Returns:
            Стратегия выполнения
        """
        task_type = task.effective_task_type
        if task_type and task_type in self._execution_strategies:
            return self._execution_strategies[task_type]
        else:
            # Стратегия по умолчанию для задач без типа
            return {
                'priority': 99,
                'batch_size': 1,
                'delay_multiplier': 1.0,
                'quality_gates_required': False,
                'max_failures': 3,
            }

    def _should_apply_quality_gates(self, task: 'TodoItem') -> bool:
        """
        Определить, нужно ли применять quality gates для задачи

        Args:
            task: Задача

        Returns:
            True если quality gates нужно применять
        """
        if not self._is_quality_gates_enabled():
            return False

        # Всегда проверяем тип задачи (TaskTypeChecker)
        # Для других чекеров применяем стратегию типа задачи
        strategy = self._get_execution_strategy(task)
        return strategy.get('quality_gates_required', False)

    def _get_quality_gates_for_task(self, task: 'TodoItem') -> List[QualityCheckType]:
        """
        Определить, какие quality gates применять для задачи

        Args:
            task: Задача

        Returns:
            Список типов quality gates для применения
        """
        gates_to_run = []

        # TaskTypeChecker всегда применяется
        gates_to_run.append(QualityCheckType.TASK_TYPE)

        # Другие чекеры применяются в зависимости от типа задачи и условий
        task_type = task.effective_task_type
        if task_type:
            if task_type in [TaskType.CODE, TaskType.REFACTOR]:
                # Для задач разработки применяем complexity и style чекеры
                gates_to_run.extend([QualityCheckType.COMPLEXITY, QualityCheckType.STYLE])
            elif task_type == TaskType.RELEASE:
                # Для релизов применяем все чекеры
                gates_to_run.extend([
                    QualityCheckType.COVERAGE,
                    QualityCheckType.COMPLEXITY,
                    QualityCheckType.SECURITY,
                    QualityCheckType.STYLE
                ])
            elif task_type == TaskType.TEST:
                # Для тестовых задач применяем coverage и style
                gates_to_run.extend([QualityCheckType.COVERAGE, QualityCheckType.STYLE])

        return gates_to_run

    def _calculate_task_delay(self, task: 'TodoItem') -> int:
        """
        Рассчитать задержку между задачами с учетом типа задачи

        Args:
            task: Задача

        Returns:
            Задержка в секундах
        """
        strategy = self._get_execution_strategy(task)
        multiplier = strategy.get('delay_multiplier', 1.0)
        return int(self.task_delay * multiplier)

    def _validate_task_type(self, task: 'TodoItem') -> bool:
        """
        Валидация типа задачи перед выполнением

        Args:
            task: Задача для валидации

        Returns:
            True если задача может быть выполнена
        """
        task_type = task.effective_task_type

        if task_type is None:
            logger.warning(f"Задача не имеет определенного типа: {task.text}")
            # Пока не блокируем выполнение задач без типа,
            # но логируем предупреждение для улучшения системы типов
            return True

        # Задача имеет корректный тип
        logger.debug(f"Задача типа {task_type.display_name}: {task.text}")
        return True

    def _prepare_analysis_data(self, todo_item: 'TodoItem', verification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготовка данных для AI анализа

        Args:
            todo_item: Задача
            verification_result: Результаты верификации

        Returns:
            Данные для анализа
        """
        analysis_data = {
            'task_description': todo_item.text,
            'task_type': todo_item.category,
            'execution_result': verification_result.get('execution_result', {})
        }

        # Добавляем информацию об изменениях в коде если доступна
        if hasattr(todo_item, 'code_changes') and todo_item.code_changes:
            analysis_data['code_changes'] = todo_item.code_changes

        # Добавляем метрики выполнения если доступны
        if 'execution_metrics' in verification_result.get('execution_result', {}):
            analysis_data['execution_metrics'] = verification_result['execution_result']['execution_metrics']

        return analysis_data

    def _make_verification_decision(self, verification_result: Dict[str, Any]) -> str:
        """
        Принятие решения на основе результатов верификации

        Args:
            verification_result: Результаты верификации

        Returns:
            Решение: 'approve_execution', 'warn_but_continue', 'block_execution'
        """
        scores = verification_result.get('scores', {})

        # Критические пороги
        pre_threshold = 0.7
        in_threshold = 0.8
        post_threshold = 0.75
        ai_threshold = 0.6

        # Проверяем критические уровни
        if scores.get('pre_execution', 1.0) < pre_threshold:
            return 'block_execution'
        if scores.get('in_execution', 1.0) < in_threshold:
            return 'block_execution'
        if scores.get('post_execution', 1.0) < post_threshold:
            return 'block_execution'

        # Проверяем AI валидацию если доступна
        if 'ai_validation' in scores and scores['ai_validation'] < ai_threshold:
            return 'warn_but_continue'

        # Все проверки пройдены
        return 'approve_execution'

    async def execute_task_via_intelligent_llm(self, todo_item: 'TodoItem') -> tuple[bool, Dict[str, Any]]:
        """
        Выполнить задачу через интеллектуальную LLM систему

        Использует все компоненты интеллектуальной интеграции:
        - IntelligentRouter для анализа задачи
        - AdaptiveStrategyManager для выбора стратегии
        - LLMManager для выполнения
        - IntelligentEvaluator для оценки результата
        - ErrorLearningSystem для обучения на ошибках

        Args:
            todo_item: Задача для выполнения

        Returns:
            Кортеж (success, execution_result):
            - success: True если выполнение успешно
            - execution_result: Детальные результаты выполнения
        """
        if not self.llm_manager or not self.is_llm_available():
            logger.warning("LLM Manager недоступен, используем fallback на Cursor")
            # Fallback на старый метод
            return await self._execute_task_via_cursor_fallback(todo_item)

        execution_result = {
            'intelligent_components_used': [],
            'analysis': {},
            'strategy': {},
            'execution': {},
            'evaluation': {},
            'learning': {},
            'errors': []
        }

        try:
            # Шаг 1: Анализ задачи через IntelligentRouter
            logger.info(f"Анализ задачи через IntelligentRouter: {todo_item.text[:100]}...")
            try:
                from ..llm.types import GenerationRequest
                analysis_request = GenerationRequest(
                    prompt=todo_item.text,
                    use_fastest=False  # Для анализа используем качественные модели
                )
                analysis = self.llm_manager.intelligent_router.analyze_request(analysis_request)
                execution_result['intelligent_components_used'].append('IntelligentRouter')
                execution_result['analysis'] = {
                    'task_type': analysis.task_type.value if hasattr(analysis.task_type, 'value') else str(analysis.task_type),
                    'complexity': analysis.complexity.value if hasattr(analysis.complexity, 'value') else str(analysis.complexity),
                    'estimated_tokens': analysis.estimated_tokens,
                    'requires_accuracy': analysis.requires_accuracy,
                    'requires_creativity': analysis.requires_creativity,
                    'confidence': analysis.confidence
                }
                logger.info(f"Анализ завершен: тип={analysis.task_type}, сложность={analysis.complexity}, уверенность={analysis.confidence:.2f}")
            except Exception as e:
                logger.error(f"Ошибка анализа через IntelligentRouter: {e}")
                execution_result['errors'].append(f"IntelligentRouter error: {e}")
                # Продолжаем с базовым анализом
                execution_result['analysis'] = {
                    'task_type': 'unknown',
                    'fallback': True,
                    'error': str(e)
                }

            # Шаг 2: Выбор стратегии через AdaptiveStrategyManager
            logger.info("Выбор стратегии через AdaptiveStrategyManager...")
            try:
                # Создаем более полный запрос для стратегии
                strategy_request = GenerationRequest(
                    prompt=todo_item.text,
                    use_parallel=False,  # Начинаем с последовательного выполнения
                    use_fastest=False
                )

                # Используем adaptive стратегию
                strategy_response = await self.llm_manager.adaptive_strategy_manager.generate_adaptive(strategy_request)
                execution_result['intelligent_components_used'].append('AdaptiveStrategyManager')
                execution_result['strategy'] = {
                    'strategy_used': 'adaptive',
                    'model_used': strategy_response.model_name,
                    'response_time': strategy_response.response_time,
                    'success': strategy_response.success
                }
                logger.info(f"Стратегия выбрана: {strategy_response.model_name}, время={strategy_response.response_time:.2f}s")

                # Сохраняем результат выполнения как основной результат задачи
                task_result = strategy_response.content

            except Exception as e:
                logger.error(f"Ошибка выбора стратегии через AdaptiveStrategyManager: {e}")
                execution_result['errors'].append(f"AdaptiveStrategyManager error: {e}")
                # Fallback на простой LLM вызов
                try:
                    simple_request = GenerationRequest(
                        prompt=f"Выполни следующую задачу: {todo_item.text}\n\nПредоставь подробный и качественный результат.",
                        use_fastest=True
                    )
                    fallback_response = await self.llm_manager.generate_response(simple_request)
                    task_result = fallback_response.content
                    execution_result['strategy'] = {
                        'strategy_used': 'fallback_simple',
                        'model_used': fallback_response.model_name,
                        'response_time': fallback_response.response_time,
                        'success': fallback_response.success
                    }
                    logger.info("Использован fallback на простой LLM вызов")
                except Exception as e2:
                    logger.error(f"Ошибка и fallback LLM вызова: {e2}")
                    execution_result['errors'].append(f"Fallback LLM error: {e2}")
                    # Полный fallback на Cursor
                    return await self._execute_task_via_cursor_fallback(todo_item)

            execution_result['execution'] = {
                'result_length': len(task_result) if task_result else 0,
                'has_content': bool(task_result and task_result.strip())
            }

            # Шаг 3: Оценка результата через IntelligentEvaluator
            logger.info("Оценка результата через IntelligentEvaluator...")
            try:
                evaluation = await self.llm_manager.intelligent_evaluator.evaluate_intelligent(
                    prompt=todo_item.text,
                    response=task_result,
                    client_manager=self.llm_manager.client_manager,
                    task_type=execution_result['analysis'].get('task_type', 'unknown')
                )
                execution_result['intelligent_components_used'].append('IntelligentEvaluator')
                execution_result['evaluation'] = {
                    'overall_score': evaluation.overall_score,
                    'quality_score': evaluation.quality_score,
                    'relevance_score': evaluation.relevance_score,
                    'completeness_score': evaluation.completeness_score,
                    'efficiency_score': evaluation.efficiency_score,
                    'reasoning': evaluation.reasoning
                }
                logger.info(f"Оценка завершена: общий балл={evaluation.overall_score:.2f}")

                # Проверяем порог качества
                quality_threshold = 0.6  # Можно вынести в конфиг
                if evaluation.overall_score < quality_threshold:
                    logger.warning(f"Качество результата ниже порога ({evaluation.overall_score:.2f} < {quality_threshold})")
                    execution_result['quality_below_threshold'] = True
                else:
                    execution_result['quality_acceptable'] = True

            except Exception as e:
                logger.error(f"Ошибка оценки через IntelligentEvaluator: {e}")
                execution_result['errors'].append(f"IntelligentEvaluator error: {e}")
                # Задаем базовую оценку
                execution_result['evaluation'] = {
                    'overall_score': 0.5,  # Нейтральная оценка
                    'fallback': True,
                    'error': str(e)
                }

            # Шаг 4: Обучение через ErrorLearningSystem (если есть ошибки или низкое качество)
            if execution_result.get('quality_below_threshold') or execution_result['errors']:
                logger.info("Обучение через ErrorLearningSystem...")
                try:
                    # Готовим данные для обучения
                    error_data = {
                        'task_description': todo_item.text,
                        'task_type': execution_result['analysis'].get('task_type', 'unknown'),
                        'execution_result': task_result,
                        'evaluation_score': execution_result['evaluation'].get('overall_score', 0.0),
                        'errors': execution_result['errors'],
                        'quality_below_threshold': execution_result.get('quality_below_threshold', False)
                    }

                    # Обучаемся на ошибке
                    await self.llm_manager.error_learning_system.learn_from_error(error_data)
                    execution_result['intelligent_components_used'].append('ErrorLearningSystem')
                    execution_result['learning'] = {
                        'performed': True,
                        'error_data_processed': True
                    }
                    logger.info("Обучение на ошибке выполнено")
                except Exception as e:
                    logger.error(f"Ошибка обучения через ErrorLearningSystem: {e}")
                    execution_result['errors'].append(f"ErrorLearningSystem error: {e}")
                    execution_result['learning'] = {
                        'performed': False,
                        'error': str(e)
                    }

            # Сохраняем результат в файл
            success = await self._save_task_result_to_file(todo_item, task_result, execution_result)

            # Логируем использование интеллектуальных компонентов
            components_used = execution_result.get('intelligent_components_used', [])
            logger.info(f"Использовано интеллектуальных компонентов: {len(components_used)} - {', '.join(components_used)}")

            return success, execution_result

        except Exception as e:
            logger.error(f"Критическая ошибка в интеллектуальном выполнении задачи: {e}")
            execution_result['errors'].append(f"Critical error: {e}")

            # Fallback на Cursor при критических ошибках
            logger.info("Переход на fallback выполнение через Cursor")
            return await self._execute_task_via_cursor_fallback(todo_item)

    async def _execute_task_via_cursor_fallback(self, todo_item: 'TodoItem') -> tuple[bool, Dict[str, Any]]:
        """
        Fallback выполнение задачи через Cursor интерфейс

        Args:
            todo_item: Задача для выполнения

        Returns:
            Кортеж (success, execution_result)
        """
        logger.warning(f"Использование fallback выполнения через Cursor для задачи: {todo_item.text[:100]}...")

        execution_result = {
            'fallback_used': True,
            'fallback_reason': 'LLM system unavailable or failed',
            'execution_method': 'cursor_fallback'
        }

        try:
            # Импортируем и используем cursor интерфейс как fallback
            # Это упрощенная версия - в реальности нужно интегрировать с существующей логикой
            success = False  # Placeholder - нужно реализовать реальный fallback

            # TODO: Реализовать полный fallback на Cursor интерфейс
            logger.warning("Fallback на Cursor не полностью реализован - возвращаем неудачу")

            return success, execution_result

        except Exception as e:
            logger.error(f"Ошибка fallback выполнения: {e}")
            execution_result['fallback_error'] = str(e)
            return False, execution_result

    async def _save_task_result_to_file(self, todo_item: 'TodoItem', result: str, execution_result: Dict[str, Any]) -> bool:
        """
        Сохранить результат выполнения задачи в файл

        Args:
            todo_item: Задача
            result: Результат выполнения
            execution_result: Детали выполнения

        Returns:
            True если сохранение успешно
        """
        try:
            import time
            task_id = f"task_{int(time.time())}"

            # Создаем директорию для результатов если не существует
            results_dir = self.project_dir / "docs" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)

            # Сохраняем основной результат
            result_file = results_dir / f"intelligent_result_{task_id}.md"
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(f"# Результат выполнения задачи\n\n")
                f.write(f"**Задача:** {todo_item.text}\n\n")
                f.write(f"**ID задачи:** {task_id}\n\n")
                f.write(f"**Метод выполнения:** Интеллектуальная LLM система\n\n")

                if execution_result.get('intelligent_components_used'):
                    f.write(f"**Использованные компоненты:** {', '.join(execution_result['intelligent_components_used'])}\n\n")

                f.write("## Результат\n\n")
                f.write(result)
                f.write("\n\n")

                # Добавляем информацию об оценке если есть
                if 'evaluation' in execution_result:
                    eval_data = execution_result['evaluation']
                    f.write("## Оценка качества\n\n")
                    if 'overall_score' in eval_data:
                        f.write(f"**Общий балл:** {eval_data['overall_score']:.2f}\n\n")
                    if eval_data.get('reasoning'):
                        f.write(f"**Обоснование:** {eval_data['reasoning']}\n\n")

                # Добавляем информацию об ошибках если есть
                if execution_result.get('errors'):
                    f.write("## Ошибки выполнения\n\n")
                    for error in execution_result['errors']:
                        f.write(f"- {error}\n")
                    f.write("\n")

            logger.info(f"Результат сохранен в файл: {result_file}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения результата в файл: {e}")
            return False

    async def execute_full_iteration(
        self,
        iteration: int,
        should_stop_callback: Optional[Callable[[], bool]] = None,
        should_reload_callback: Optional[Callable[[], bool]] = None,
        reload_exception_class: Optional[type] = None
    ) -> tuple[bool, list]:
        """
        Выполнить полную итерацию цикла с учетом остановки и перезапуска

        Args:
            iteration: Номер итерации
            should_stop_callback: Callback для проверки запроса на остановку
            should_reload_callback: Callback для проверки необходимости перезапуска
            reload_exception_class: Класс исключения для перезапуска

        Returns:
            Кортеж (has_more_tasks, executed_tasks):
            - has_more_tasks: True если есть еще задачи для выполнения
            - executed_tasks: Список выполненных задач в формате [(task, success, verification_result), ...]
        """
        logger.info(f"Начало полной итерации {iteration} в ServerCore")

        # Проверяем запрос на остановку перед началом итерации
        if should_stop_callback and should_stop_callback():
            logger.warning("Получен запрос на остановку перед началом итерации")
            return False, []

        # Проверяем необходимость перезапуска перед итерацией
        if should_reload_callback and should_reload_callback():
            logger.warning("Обнаружено изменение кода перед началом итерации")
            if reload_exception_class:
                raise reload_exception_class("Перезапуск из-за изменения кода перед началом итерации")
            return False, []

        try:
            # Получаем задачи для выполнения
            has_more_tasks, pending_tasks = self.execute_iteration(iteration)

            executed_tasks = []

            # Если есть задачи для выполнения, выполняем их с контролем остановки
            if pending_tasks:
                total_tasks = len(pending_tasks)
                for idx, todo_item in enumerate(pending_tasks, start=1):
                    # Проверяем запрос на остановку перед каждой задачей
                    if should_stop_callback and should_stop_callback():
                        logger.warning(f"Получен запрос на остановку перед выполнением задачи {idx}/{total_tasks}")
                        break

                    # Проверяем необходимость перезапуска перед задачей
                    if should_reload_callback and should_reload_callback():
                        logger.warning(f"Обнаружено изменение кода перед выполнением задачи {idx}/{total_tasks}")
                        if reload_exception_class:
                            raise reload_exception_class("Перезапуск из-за изменения кода перед выполнением задачи")
                        break

                    # Выполняем задачу
                    success, verification_result = await self.execute_single_task(todo_item, task_number=idx, total_tasks=total_tasks)
                    executed_tasks.append((todo_item, success, verification_result))

                    # Проверяем запрос на остановку после выполнения задачи
                    if should_stop_callback and should_stop_callback():
                        logger.warning(f"Получен запрос на остановку после выполнения задачи {idx}/{total_tasks}")
                        break

                    # Если задача завершилась неудачно из-за критической ошибки, проверяем флаг остановки
                    if not success and should_stop_callback and should_stop_callback():
                        logger.warning("Задача завершилась из-за критической ошибки - прерывание итерации")
                        break

                    # Проверяем необходимость перезапуска после задачи
                    if should_reload_callback and should_reload_callback():
                        logger.warning(f"Обнаружено изменение кода после выполнения задачи {idx}/{total_tasks}")
                        if reload_exception_class:
                            raise reload_exception_class("Перезапуск из-за изменения кода после выполнения задачи")
                        break

            return has_more_tasks, executed_tasks

        except Exception as e:
            logger.error(f"Ошибка выполнения полной итерации {iteration}: {e}", exc_info=True)
            return False, []