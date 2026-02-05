"""
Базовый цикл выполнения задач с Dependency Injection
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from .interfaces.itask_executor import ITaskExecutor
from .interfaces.irevision_executor import IRevisionExecutor
from .interfaces.itodo_generator import ITodoGenerator

from config_loader import ConfigLoader
from session_tracker import SessionTracker
from task_logger import Colors, TaskLogger, TaskPhase
from .interfaces import ICheckpointManager, ILogger, IStatusManager, ITodoManager
from todo_manager import TodoItem
from llm.manager import LLMManager as NewLLMManager
from llm.llm_manager import LLMManager as LegacyLLMManager
from verification.interfaces import IMultiLevelVerificationManager

logger = logging.getLogger(__name__)


class ServerCore:
    """
    Базовый цикл выполнения задач Code Agent.
    Отвечает за координацию менеджеров и выполнение задач.
    """

    def __init__(
        self,
        todo_manager: ITodoManager,
        checkpoint_manager: ICheckpointManager,
        status_manager: IStatusManager,
        server_logger: ILogger,
        task_executor: ITaskExecutor,
        revision_executor: IRevisionExecutor,
        todo_generator: ITodoGenerator,
        config: Dict[str, Any],
        project_dir: Path,
        verification_manager: IMultiLevelVerificationManager,
        llm_manager: Optional[Any],  # Может быть NewLLMManager или LegacyLLMManager
        auto_todo_enabled: bool,
        task_delay: int,
    ):
        self.todo_manager = todo_manager
        self.checkpoint_manager = checkpoint_manager
        self.status_manager = status_manager
        self.server_logger = server_logger
        self.task_executor = task_executor
        self.revision_executor = revision_executor
        self.todo_generator = todo_generator
        self.config = config
        self.project_dir = project_dir
        self.verification_manager = verification_manager
        self.llm_manager = llm_manager
        self.auto_todo_enabled = auto_todo_enabled
        self.task_delay = task_delay

        self._revision_done = False  # Флаг выполнения ревизии в текущей сессии
        self._llm_manager_initialized = False # Флаг инициализации LLMManager

        # Настройки LLM
        llm_config = self.config.get('llm', {})
        self.llm_enabled = llm_config.get('enabled', True)

        logger.info("ServerCore initialized.")
        logger.debug(f"LLM Manager type: {type(self.llm_manager)}")

    def get_llm_manager(self) -> Optional[Any]:
        """Возвращает экземпляр LLMManager."""
        return self.llm_manager

    async def execute_full_iteration(
        self,
        iteration: int,
        should_stop_callback: Callable[[], bool],
        should_reload_callback: Callable[[], bool],
        reload_exception_class: Type[Exception],
    ) -> Tuple[bool, List[Tuple[str, bool]]]:
        """
        Выполняет одну полную итерацию цикла сервера.

        Args:
            iteration: Текущий номер итерации.
            should_stop_callback: Callback для проверки запроса на остановку.
            should_reload_callback: Callback для проверки запроса на перезапуск.
            reload_exception_class: Класс исключения для перезапуска.

        Returns:
            Кортеж (есть ли еще задачи для выполнения, список выполненных задач (текст, успех)).
        """
        self.server_logger.log_iteration_start(iteration)
        logger.info(f"Starting full iteration {iteration}")

        if should_stop_callback():
            logger.warning("Остановка итерации по запросу.")
            return False, []

        if should_reload_callback():
            logger.warning("Перезапуск итерации по запросу.")
            raise reload_exception_class("Перезапуск из-за изменения кода.")

        # 1. Загрузка задач
        all_todo_items = self.todo_manager.get_all_tasks()
        pending_tasks = self.todo_manager.get_pending_tasks()
        pending_tasks = self._filter_completed_tasks(pending_tasks)

        if not pending_tasks:
            logger.info("No pending tasks found.")
            # Обновляем прогресс для текущей сессии, если задач нет, но ревизия не была
            if not self._revision_done:
                self.checkpoint_manager.update_session_progress(iteration, 0, 0)
            return await self._handle_no_tasks_scenario()

        logger.info(f"Found {len(pending_tasks)} pending tasks.")

        # 2. Выполнение задач
        executed_tasks_results: List[Tuple[str, bool]] = []
        total_tasks_in_iteration = len(pending_tasks)

        for i, todo_item in enumerate(pending_tasks):
            if should_stop_callback():
                logger.warning(f"Остановка выполнения задач по запросу во время задачи {i+1}/{total_tasks_in_iteration}.")
                break
            if should_reload_callback():
                logger.warning(f"Перезапуск выполнения задач по запросу во время задачи {i+1}/{total_tasks_in_iteration}.")
                raise reload_exception_class("Перезапуск из-за изменения кода во время выполнения задачи.")

            # Обновляем checkpoint перед каждой задачей
            self.checkpoint_manager.update_session_progress(iteration, i + 1, total_tasks_in_iteration)

            # Выполнение задачи
            task_success = await self.task_executor(todo_item, i + 1, total_tasks_in_iteration)
            executed_tasks_results.append((todo_item.text, task_success))

            if task_success:
                logger.info(f"Task \'{todo_item.text}\' completed successfully.")
            else:
                logger.warning(f"Task \'{todo_item.text}\' failed.")

            # Задержка между задачами
            if i < total_tasks_in_iteration - 1:
                logger.debug(f"Sleeping for {self.task_delay} seconds before next task...")
                # Проверяем остановку/перезапуск во время задержки
                for _ in range(self.task_delay):
                    if should_stop_callback():
                        logger.warning("Остановка во время задержки между задачами.")
                        return False, executed_tasks_results
                    if should_reload_callback():
                        logger.warning("Перезапуск во время задержки между задачами.")
                        raise reload_exception_class("Перезапуск из-за изменения кода во время задержки.")
                    time.sleep(1)

        # 3. Синхронизация с checkpoint (на случай, если задачи были выполнены внешне)
        self._sync_todos_with_checkpoint()

        # 4. Проверка наличия оставшихся задач
        remaining_tasks = self.todo_manager.get_pending_tasks()
        remaining_tasks = self._filter_completed_tasks(remaining_tasks)

        has_more_tasks = len(remaining_tasks) > 0
        logger.info(f"Iteration {iteration} finished. Has more tasks: {has_more_tasks}")
        self.server_logger.log_iteration_end(iteration, has_more_tasks)

        return has_more_tasks, executed_tasks_results

    def _filter_completed_tasks(self, tasks: List[TodoItem]) -> List[TodoItem]:
        """
        Фильтрация задач: исключает задачи, которые уже выполнены в checkpoint
        
        Args:
            tasks: Список задач для фильтрации
            
        Returns:
            Отфильтрованный список задач (только невыполненные)
        """
        filtered_tasks = []
        for task in tasks:
            if not self.checkpoint_manager.is_task_completed(task.text):
                filtered_tasks.append(task)
            else:
                logger.debug(f"Задача '{task.text}' уже выполнена в checkpoint, пропускаем")
                # Помечаем задачу как done в TODO для синхронизации
                self.todo_manager.mark_task_done(task.text)
        return filtered_tasks
    
    def _sync_todos_with_checkpoint(self):
        """
        Синхронизация TODO задач с checkpoint - помечает задачи как выполненные в TODO файле,
        если они помечены как completed в checkpoint
        """
        try:
            # Получаем все задачи из TODO
            all_todo_items = self.todo_manager.get_all_tasks()
            
            # Получаем все завершенные задачи из checkpoint
            completed_tasks_in_checkpoint = [
                task for task in self.checkpoint_manager.checkpoint_data.get("tasks", [])
                if task.get("state") == "completed"
            ]
            
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
            # Не прерываем инициализацию из-за ошибки синхронизации
    
    async def _handle_no_tasks_scenario(self) -> bool:
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

            revision_success = await self.revision_executor()

            if revision_success:
                self._revision_done = True
                logger.info("Ревизия проекта успешно завершена")

                # После ревизии перезагружаем задачи
                await self._reload_todos_and_check_for_new_tasks()
                return True  # Есть новые задачи после ревизии
            else:
                logger.warning("Ревизия не завершена полностью, но продолжаем работу")
                await self._reload_todos_and_check_for_new_tasks()
                return True
        else:
            logger.info("Ревизия уже выполнена в этой сессии, пропускаем")
            await self._reload_todos_and_check_for_new_tasks()
            return True

    async def _reload_todos_and_check_for_new_tasks(self):
        """
        Перезагрузка TODO и проверка на наличие новых задач.
        Если задач нет, и auto_todo_enabled, будет попытка сгенерировать новые.
        """
        self.todo_manager.load_todos()
        self._sync_todos_with_checkpoint()

        if not self._has_pending_tasks():
            if self.auto_todo_enabled:
                logger.info("Все задачи выполнены, ревизия завершена. Пытаемся сгенерировать новые TODO.")
                generation_success = await self.todo_generator()
                if generation_success:
                    logger.info("Новый TODO лист успешно сгенерирован, перезагрузка задач.")
                    self.todo_manager.load_todos()
                    self._sync_todos_with_checkpoint()
            else:
                logger.info("Автоматическая генерация TODO отключена.")

    def _has_pending_tasks(self) -> bool:
        """
        Проверка наличия ожидающих задач.

        Returns:
            True если есть ожидающие задачи.
        """
        pending_tasks = self.todo_manager.get_pending_tasks()
        pending_tasks = self._filter_completed_tasks(pending_tasks)
        return len(pending_tasks) > 0

    # Existing methods for task execution, LLM interaction, etc., will be moved here
    # from server.py, or delegated to other injected components.
    
    # For now, placeholder for _check_task_usefulness
    async def _check_task_usefulness(self, todo_item: TodoItem) -> Tuple[float, Optional[str]]:
        # This will contain the actual logic moved from server.py
        logger.debug(f"_check_task_usefulness called for: {todo_item.text}")
        # Placeholder logic:
        if self.llm_manager and self.llm_manager.is_llm_available():
            logger.info("LLMManager available for usefulness check.")
            # This part needs the LLMManager and its related methods from server.py
            # For now, return a default value
            return 75.0, "LLM check (placeholder)"
        return 75.0, "LLMManager unavailable (placeholder)"

    async def _check_todo_matches_plan(self, task_id: str, todo_item: TodoItem) -> Tuple[bool, Optional[str]]:
        # This will contain the actual logic moved from server.py
        logger.debug(f"_check_todo_matches_plan called for: {todo_item.text}")
        # Placeholder logic:
        if self.llm_manager and self.llm_manager.is_llm_available():
            logger.info("LLMManager available for plan match check.")
            # This part needs the LLMManager and its related methods from server.py
            # For now, return a default value
            return True, None
        return True, "LLMManager unavailable (placeholder)"

    async def _analyze_error_llm(self, error_message: str, task_description: str, project_context: str) -> str:
        # This will contain the actual logic moved from server.py
        logger.debug("_analyze_error_llm called.")
        # Placeholder logic:
        if self.llm_manager and self.llm_manager.is_llm_available():
            logger.info("LLMManager available for error analysis.")
            return f"LLM analysis (placeholder) for: {error_message[:50]}"
        return f"LLMManager unavailable for error analysis: {error_message[:50]}"

    def _load_documentation(self) -> str:
        """
        Загрузка документации проекта из папки docs
        
        Returns:
            Контент документации в виде строки
        """
        if not self.project_dir.exists():
            logger.warning(f"Project directory not found: {self.project_dir}")
            return ""

        docs_dir = self.project_dir / "docs"
        if not docs_dir.exists():
            logger.warning(f"Documentation directory not found: {docs_dir}")
            return ""
        
        docs_content = []
        supported_extensions = self.config.get('docs.supported_extensions', ['.md', '.txt'])
        max_file_size = self.config.get('docs.max_file_size', 1_000_000) # Default 1 MB
        
        for file_path in docs_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                try:
                    file_size = file_path.stat().st_size
                    if file_size > max_file_size:
                        logger.warning(f"File too large, skipped: {file_path}")
                        continue
                    
                    content = file_path.read_text(encoding='utf-8')
                    docs_content.append(f"\n## {file_path.name}\n\n{content}\n")
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
        
        return "\n".join(docs_content)

    def _create_task_execution_prompt(self, todo_item: TodoItem, task_type: str) -> str:
        """
        Создать промпт для выполнения задачи через LLM

        Args:
            todo_item: Задача для выполнения
            task_type: Тип задачи

        Returns:
            Промпт для LLM
        """
        documentation = self._load_documentation()
        context = f"""
Ты - опытный разработчик ПО, выполняющий задачи в проекте Code Agent.

КОНТЕКСТ ПРОЕКТА:
{documentation[:2000]}... (сокращено для краткости)

ТИП ЗАДАЧИ: {task_type}
ОПИСАНИЕ ЗАДАЧИ: {todo_item.text}

ТРЕБОВАНИЯ К ВЫПОЛНЕНИЮ:
1. Проанализируй задачу и ее контекст
2. Предоставь детальное решение
3. Создай необходимые файлы или модифицируй существующие
4. Обеспечь высокое качество кода/документации
5. Следуй лучшим практикам разработки

ФОРМАТ ОТВЕТА:
- Опиши анализ проблемы
- Предоставь решение с кодом/изменениями
- Укажи файлы, которые нужно создать/изменить
- Создай отчет в соответствующем формате

Задача должна быть выполнена качественно и полностью.
"""
        return context

    def _process_llm_task_result(self, todo_item: TodoItem, result_content: str, task_logger: TaskLogger) -> bool:
        """
        Обработать результат выполнения задачи от LLM

        Args:
            todo_item: Исходная задача
            result_content: Результат от LLM
            task_logger: Логгер задачи

        Returns:
            True если обработка успешна
        """
        try:
            results_dir = self.project_dir / "docs" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            task_id = task_logger.task_id
            result_file = results_dir / f"llm_task_result_{task_id}.md"
            report_content = f"""# Результат выполнения задачи

**Задача:** {todo_item.text}
**ID:** {task_id}
**Время выполнения:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Результат от интеллектуальной LLM системы

{result_content}

## Статус
✅ Задача выполнена через интеллектуальную LLM систему с использованием компонентов:
- IntelligentRouter (маршрутизация запросов)
- AdaptiveStrategyManager (адаптивный выбор стратегии)
- IntelligentEvaluator (оценка качества)
- ErrorLearningSystem (обучение на ошибках)

---
*Отчет создан автоматически системой LLM выполнения задач*
"""
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Результат выполнения сохранен в: {result_file}")
            task_logger.log_info(f"Результат сохранен: {result_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обработке результата LLM: {e}")
            task_logger.log_error(f"Ошибка обработки результата: {str(e)}")
            return False

    def _verify_real_work_done(self, task_id: str, todo_item: TodoItem, result_content: str) -> bool:
        """
        Проверка, что была выполнена реальная работа, а не только создан план
        
        Args:
            task_id: ID задачи
            todo_item: Элемент todo-листа
            result_content: Содержимое файла результата
            
        Returns:
            True если работа выполнена, False если только план
        """
        # Проверяем по ключевым словам в отчете
        result_lower = result_content.lower()
        
        # Индикаторы реальной работы
        work_indicators = [
            "создан файл",
            "изменен файл",
            "добавлен код",
            "реализован",
            "выполнен",
            "созданы тесты",
            "добавлена функциональность",
            "изменения в",
            "modified",
            "created",
            "implemented",
            "added"
        ]
        
        # Индикаторы только плана
        plan_only_indicators = [
            "только план",
            "план выполнения",
            "планирование",
            "буду выполнить",
            "будет выполнено",
            "следующие шаги",
            "рекомендации"
        ]
        
        # Проверяем наличие индикаторов работы
        has_work = any(indicator in result_lower for indicator in work_indicators)
        # Дополнительно убеждаемся, что это не просто план
        is_plan_only = any(indicator in result_lower for indicator in plan_only_indicators) and not has_work
        
        # Дополнительная проверка - наличие изменений в git (если доступен)
        try:
            import subprocess
            git_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if git_status.returncode == 0:
                has_git_changes = bool(git_status.stdout.strip())
                if has_git_changes:
                    logger.info(f"Обнаружены изменения в git для задачи {task_id}")
                    return True
        except Exception as e:
            logger.debug(f"Не удалось проверить git статус: {e}")
        
        if has_work and not is_plan_only:
            logger.info(f"Обнаружены индикаторы выполненной работы для задачи {task_id}")
            return True
        
        logger.warning(f"Для задачи {task_id} выполнен только план или реальная работа не обнаружена")
        return False

    def _determine_task_type(self, todo_item: TodoItem) -> str:
        """
        Определение типа задачи для выбора инструкции
        
        Args:
            todo_item: Элемент todo-листа
        
        Returns:
            Тип задачи (default, frontend-task, backend-task, etc.)
        """
        task_text = todo_item.text.lower()
        
        if any(word in task_text for word in ['тест', 'test', 'тестирование']):
            return 'test'
        elif any(word in task_text for word in ['документация', 'docs', 'readme']):
            return 'documentation'
        elif any(word in task_text for word in ['рефакторинг', 'refactor']):
            return 'refactoring'
        elif any(word in task_text for word in ['разработка', 'реализация', 'implement']):
            return 'development'
        else:
            return 'default'

    async def _execute_task_via_llm(self, todo_item: TodoItem, task_type: str, task_logger: TaskLogger) -> bool:
        """
        Выполнение задачи через интеллектуальную LLM систему

        Args:
            todo_item: Элемент todo-листа
            task_type: Тип задачи
            task_logger: Логгер задачи

        Returns:
            True если задача выполнена успешно
        """
        logger.info(f"Выполнение задачи через интеллектуальную LLM систему: {todo_item.text}")
        task_logger.log_info("Выполнение через интеллектуальную LLM систему")

        try:
            if not self.llm_manager or not self.llm_manager.is_llm_available():
                logger.error("LLM Manager недоступен - невозможно выполнить задачу через LLM систему")
                task_logger.log_error("LLM Manager недоступен")
                return False

            prompt = self._create_task_execution_prompt(todo_item, task_type)
            task_logger.log_debug(f"Создан промпт для выполнения задачи (длина: {len(prompt)} символов)")

            logger.info("Запуск адаптивной генерации с использованием интеллектуальных компонентов")
            task_logger.log_info("Запуск адаптивной генерации")

            response = await self.llm_manager.generate_adaptive(
                prompt=prompt,
                response_format={"type": "text"}
            )

            if not response.success:
                logger.error(f"LLM генерация завершилась неудачно: {response.error}")
                task_logger.log_error(f"LLM генерация неудачна: {response.error}")
                root_cause_analysis = await self._analyze_error_llm(
                    error_message=response.error,
                    task_description=todo_item.text,
                    project_context=self._load_documentation()
                )
                logger.error(f"Анализ основной причины ошибки: {root_cause_analysis}")
                task_logger.log_error(f"Анализ основной причины ошибки: {root_cause_analysis}")
                self.status_manager.update_task_status(
                    task_name=todo_item.text,
                    status="Ошибка LLM",
                    details=f"LLM генерация неудачна: {response.error}. Анализ причины: {root_cause_analysis}"
                )
                return False

            result_content = response.content.strip()
            task_logger.log_info(f"Получен результат от LLM (длина: {len(result_content)} символов)")

            success = self._process_llm_task_result(todo_item, result_content, task_logger)

            if success:
                logger.info("Задача успешно выполнена через интеллектуальную LLM систему")
                task_logger.log_success("Задача выполнена успешно через LLM систему")
            else:
                logger.warning("LLM система вернула результат, но обработка завершилась с предупреждениями")
                task_logger.log_warning("Результат обработан с предупреждениями")

            return success

        except Exception as e:
            logger.error(f"Ошибка при выполнении задачи через LLM систему: {e}", exc_info=True)
            task_logger.log_error(f"Ошибка выполнения: {str(e)}")
            root_cause_analysis = await self._analyze_error_llm(
                error_message=str(e),
                task_description=todo_item.text,
                project_context=self._load_documentation()
            )
            logger.error(f"Анализ основной причины ошибки: {root_cause_analysis}")
            task_logger.log_error(f"Анализ основной причины ошибки: {root_cause_analysis}")
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Критическая ошибка LLM",
                details=f"Критическая ошибка LLM: {str(e)}. Анализ причины: {root_cause_analysis}"
            )
            return False
