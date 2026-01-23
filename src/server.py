"""
Основной сервер Code Agent
"""

import os
import sys
import time
import logging
import socket
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from crewai import Task, Crew

try:
    from flask import Flask, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

from .config_loader import ConfigLoader
from .todo_manager import TodoItem
from .agents.executor_agent import create_executor_agent
from .cursor_cli_interface import CursorCLIInterface, create_cursor_cli_interface
from .cursor_file_interface import CursorFileInterface
from .task_logger import TaskLogger, TaskPhase, Colors
from .session_tracker import SessionTracker
from .git_utils import auto_push_after_commit
from .core import ServerCore, create_default_container

# ServerCore logic is now extracted into separate ServerCore component


# Настройка кодировки для Windows консоли
if sys.platform == 'win32':
    # Устанавливаем UTF-8 для stdout
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    else:
        # Для старых версий Python
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')

# Настройка логирования будет выполнена после очистки логов
# Временно отключаем автоматическую настройку, чтобы не создавать файл при импорте
# logging.basicConfig() вызывается в _setup_logging() после очистки логов

# Создаем директорию для логов если не существует
Path('logs').mkdir(exist_ok=True)

logger = logging.getLogger(__name__)


class ServerReloadException(Exception):
    """Исключение для инициации перезапуска сервера"""
    pass


def _setup_logging():
    """Настройка логирования (вызывается после очистки логов)"""
    # Удаляем существующий FileHandler для code_agent.log если есть
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            # baseFilename может быть строкой с абсолютным путем
            base_filename = str(handler.baseFilename)
            if base_filename.endswith('code_agent.log') or 'code_agent.log' in base_filename:
                root_logger.removeHandler(handler)
                handler.close()
    
    # Удаляем файл code_agent.log если он существует
    log_file = Path('logs/code_agent.log')
    if log_file.exists():
        try:
            log_file.unlink()
        except Exception:
            pass
    
    # Настраиваем логирование (force=True доступен с Python 3.8+)
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/code_agent.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True  # Переопределяем существующую конфигурацию (Python 3.8+)
        )
    except TypeError:
        # Для старых версий Python без force=True
        # Очищаем handlers и настраиваем заново
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(logging.FileHandler('logs/code_agent.log', encoding='utf-8'))
        root_logger.addHandler(logging.StreamHandler(sys.stdout))
        root_logger.setLevel(logging.INFO)


class CodeAgentServer:
    """Основной сервер Code Agent"""
    
    # Константы для обработки ошибок Cursor
    MAX_CURSOR_ERRORS = 3  # Максимальное количество последовательных ошибок перед перезапуском
    CURSOR_ERROR_DELAY_INITIAL = 30  # Начальная задержка при ошибке (секунды)
    CURSOR_ERROR_DELAY_INCREMENT = 30  # Увеличение задержки при каждой новой ошибке (секунды)
    
    # Константы таймаутов
    DEFAULT_CURSOR_CLI_TIMEOUT = 300  # Таймаут по умолчанию для Cursor CLI (секунды)
    
    # Константы интервалов по умолчанию
    DEFAULT_CHECK_INTERVAL = 60  # Интервал проверки задач по умолчанию (секунды)
    DEFAULT_TASK_DELAY = 5  # Задержка между задачами по умолчанию (секунды)
    
    # Константы для работы с файлами
    DEFAULT_MAX_FILE_SIZE = 1_000_000  # Максимальный размер файла по умолчанию (1 MB)
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация сервера агента
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        # Загрузка конфигурации
        self.config = ConfigLoader(config_path or "config/config.yaml")
        
        # Получение путей
        self.project_dir = self.config.get_project_dir()
        self.docs_dir = self.config.get_docs_dir()
        self.status_file = self.config.get_status_file()
        
        # Валидация конфигурации
        self._validate_config()

        # Инициализация DI контейнера для dependency injection
        self.di_container = create_default_container(self.project_dir, self.config.config, self.status_file)

        # Получение менеджеров из DI контейнера
        from .core.interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger
        self.todo_manager = self.di_container.resolve(ITodoManager)
        self.status_manager = self.di_container.resolve(IStatusManager)
        self.checkpoint_manager = self.di_container.resolve(ICheckpointManager)
        self.server_logger = self.di_container.resolve(ILogger)

        # Создание агента
        agent_config = self.config.get('agent', {})
        self.agent = create_executor_agent(
            project_dir=self.project_dir,
            docs_dir=self.docs_dir,
            role=agent_config.get('role'),
            goal=agent_config.get('goal'),
            backstory=agent_config.get('backstory'),
            allow_code_execution=agent_config.get('allow_code_execution', True),
            verbose=agent_config.get('verbose', True)
        )
        
        # Настройки сервера
        server_config = self.config.get('server', {})
        self.check_interval = server_config.get('check_interval', self.DEFAULT_CHECK_INTERVAL)
        self.task_delay = server_config.get('task_delay', self.DEFAULT_TASK_DELAY)
        self.max_iterations = server_config.get('max_iterations')
        
        # Настройки HTTP сервера
        self.http_port = server_config.get('http_port', 3456)
        self.http_enabled = server_config.get('http_enabled', True)
        self.flask_app = None
        self.http_thread = None
        self.http_server = None  # Ссылка на werkzeug сервер для управления
        
        # Настройки автоперезапуска
        self.auto_reload = server_config.get('auto_reload', True)
        self.reload_on_py_changes = server_config.get('reload_on_py_changes', True)
        self.file_observer = None
        self._should_reload = False
        self._reload_after_instruction = False  # Флаг для перезапуска после текущей инструкции
        self._reload_lock = threading.Lock()
        
        # Счетчик перезапусков
        self._restart_count = 0
        self._restart_count_lock = threading.Lock()
        
        # Флаг для остановки сервера через API
        self._should_stop = False
        self._stop_lock = threading.Lock()
        
        # Текущее состояние сервера
        self._current_iteration = 0
        self._is_running = False
        
        # Флаг отслеживания активной задачи (для отложенного перезапуска)
        self._task_in_progress = False
        self._task_in_progress_lock = threading.Lock()
        
        # Отслеживание повторяющихся ошибок Cursor
        self._cursor_error_count = 0  # Счетчик последовательных ошибок
        self._cursor_error_lock = threading.Lock()
        self._last_cursor_error = None  # Последняя ошибка Cursor
        self._cursor_error_delay = 0  # Дополнительная задержка при ошибках (секунды)
        self._max_cursor_errors = self.MAX_CURSOR_ERRORS  # Максимальное количество ошибок перед перезапуском
        
        # Отслеживание выполнения ревизии
        self._revision_done = False  # Флаг выполнения ревизии в текущей сессии
        self._revision_lock = threading.Lock()
        
        # Инициализация Cursor интерфейсов
        cursor_config = self.config.get('cursor', {})
        interface_type = cursor_config.get('interface_type', 'cli')
        
        # Инициализация Cursor CLI интерфейса (если доступен)
        self.cursor_cli = self._init_cursor_cli()
        
        # Инициализация файлового интерфейса (fallback)
        self.cursor_file = CursorFileInterface(self.project_dir)
        
        # Определяем приоритетный интерфейс
        self.use_cursor_cli = (
            interface_type == 'cli' and 
            self.cursor_cli and 
            self.cursor_cli.is_available()
        )
        
        # Инициализация трекера сессий для автоматической генерации TODO
        # Session файлы хранятся в каталоге codeAgent, а не в целевом проекте
        auto_todo_config = server_config.get('auto_todo_generation', {})
        self.auto_todo_enabled = auto_todo_config.get('enabled', True)
        self.max_todo_generations = auto_todo_config.get('max_generations_per_session', 5)
        tracker_file = auto_todo_config.get('session_tracker_file', '.codeagent_sessions.json')
        codeagent_dir = Path(__file__).parent.parent  # Директория codeAgent
        self.session_tracker = SessionTracker(codeagent_dir, tracker_file)
        
        # Инициализация менеджера контрольных точек для восстановления после сбоев
        # Checkpoint файлы хранятся в каталоге codeAgent, а не в целевом проекте
        # Инициализация DI контейнера для dependency injection (уже создана выше)
        self.di_container = create_default_container(self.project_dir, self.config.config, self.status_file)

        # Проверяем, нужно ли восстановление после сбоя
        self._check_recovery_needed()
        
        # Синхронизируем TODO задачи с checkpoint (помечаем выполненные задачи)
        self._sync_todos_with_checkpoint()
        
        # Логируем инициализацию
        self.server_logger.log_initialization({
            'project_dir': str(self.project_dir),
            'docs_dir': str(self.docs_dir),
            'cursor_cli_available': self.use_cursor_cli,
            'auto_todo_enabled': self.auto_todo_enabled,
            'max_todo_generations': self.max_todo_generations,
            'checkpoint_enabled': True
        })
        
        logger.info("Code Agent Server инициализирован")
        logger.info(f"Проект: {self.project_dir}")
        logger.info(f"Документация: {self.docs_dir}")
        logger.info(f"Статус файл: {self.status_file}")
        if self.use_cursor_cli:
            logger.info("Cursor CLI интерфейс доступен (приоритетный)")
        else:
            logger.info("Cursor CLI недоступен, будет использоваться файловый интерфейс")
        if self.auto_todo_enabled:
            logger.info(f"Автоматическая генерация TODO включена (макс. {self.max_todo_generations} раз за сессию)")
        logger.info("Checkpoint система активирована для защиты от сбоев")

        # Register real implementations in DI container now that server is fully initialized
        from src.core.implementations import ServerImpl, AgentManagerImpl, TaskManagerImpl
        from src.core.interfaces import IServer, IAgent, ITaskManager

        # Register ServerImpl
        self.di_container.register_instance(IServer, ServerImpl(self))

        # Replace mock implementations with real ones
        agent_manager = AgentManagerImpl(config=self.config.config.get('agent_manager', {}))
        self.di_container.register_instance(IAgent, agent_manager)

        task_manager = TaskManagerImpl(config=self.config.config.get('task_manager', {}))
        self.di_container.register_instance(ITaskManager, task_manager)

        # Создание ServerCore для управления циклом выполнения
        self._create_server_core()

    def _create_server_core(self):
        """
        Создание экземпляра ServerCore для управления циклом выполнения задач с использованием DI контейнера
        """
        try:
            from .core.interfaces import ITodoManager, IStatusManager, ICheckpointManager, ILogger
            from .verification.interfaces import IMultiLevelVerificationManager

            # Создаем обработчики для ServerCore - передаем callable объекты вместо протоколов
            task_executor = self._execute_task
            revision_executor = self._execute_revision
            todo_generator = self._generate_new_todo_list

            # Создаем ServerCore с использованием DI контейнера
            self.server_core = ServerCore(
                todo_manager=self.di_container.resolve(ITodoManager),
                checkpoint_manager=self.di_container.resolve(ICheckpointManager),
                status_manager=self.di_container.resolve(IStatusManager),
                server_logger=self.di_container.resolve(ILogger),
                task_executor=task_executor,
                revision_executor=revision_executor,
                todo_generator=todo_generator,
                config=self.config.config,
                project_dir=self.project_dir,
                verification_manager=self.di_container.resolve(IMultiLevelVerificationManager),
                auto_todo_enabled=self.auto_todo_enabled,
                task_delay=self.task_delay
            )

            logger.info("ServerCore успешно инициализирован")

        except Exception as e:
            logger.error(f"Ошибка при создании ServerCore: {e}", exc_info=True)
            raise

    def _validate_config(self):
        """
        Валидация конфигурации при инициализации сервера
        
        Проверяет наличие обязательных параметров и их корректность.
        Выбрасывает исключения с понятными сообщениями об ошибках.
        
        Raises:
            ValueError: Если обязательные параметры не установлены или некорректны
            FileNotFoundError: Если директории или файлы не найдены
        """
        errors = []
        
        # Проверка project_dir
        if not self.project_dir:
            errors.append("PROJECT_DIR не установлен в переменных окружения или .env файле")
        elif not self.project_dir.exists():
            errors.append(
                f"Директория проекта не найдена: {self.project_dir}\n"
                f"  Убедитесь, что путь указан правильно в .env файле:\n"
                f"  PROJECT_DIR={self.project_dir}"
            )
        elif not self.project_dir.is_dir():
            errors.append(f"Путь не является директорией: {self.project_dir}")
        else:
            # Проверка прав доступа на чтение
            if not os.access(self.project_dir, os.R_OK):
                errors.append(f"Нет прав на чтение директории проекта: {self.project_dir}")
            # Проверка прав доступа на запись (для создания файлов статусов)
            if not os.access(self.project_dir, os.W_OK):
                errors.append(
                    f"Нет прав на запись в директорию проекта: {self.project_dir}\n"
                    f"  Агенту нужны права на запись для создания файлов статусов"
                )
        
        # Проверка docs_dir (опционально, но желательно)
        if self.docs_dir and self.docs_dir.exists():
            if not os.access(self.docs_dir, os.R_OK):
                errors.append(f"Нет прав на чтение директории документации: {self.docs_dir}")
        
        # Проверка конфигурационного файла
        if not self.config.config_path.exists():
            errors.append(f"Конфигурационный файл не найден: {self.config.config_path}")
        
        # Если есть ошибки, выбрасываем исключение с понятным сообщением
        if errors:
            error_msg = "Ошибки конфигурации:\n\n" + "\n\n".join(f"  • {e}" for e in errors)
            error_msg += "\n\n" + "=" * 70
            error_msg += "\n\nДля решения проблем:\n"
            error_msg += "  1. Проверьте наличие .env файла в корне codeAgent/\n"
            error_msg += "  2. Убедитесь, что PROJECT_DIR указан правильно\n"
            error_msg += "  3. Проверьте права доступа к директориям\n"
            error_msg += "  4. См. документацию: docs/guides/setup.md\n"
            error_msg += "  5. См. шаблон: .env.example"
            
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Логируем успешную валидацию
        logger.debug("Валидация конфигурации пройдена успешно")
        logger.debug(f"  Project dir: {self.project_dir}")
        logger.debug(f"  Docs dir: {self.docs_dir}")
        logger.debug(f"  Status file: {self.status_file}")
    
    def _check_recovery_needed(self):
        """
        Проверка необходимости восстановления после сбоя
        """
        recovery_info = self.checkpoint_manager.get_recovery_info()
        
        if not recovery_info["was_clean_shutdown"]:
            logger.warning("=" * 80)
            logger.warning("ОБНАРУЖЕН НЕКОРРЕКТНЫЙ ОСТАНОВ СЕРВЕРА")
            logger.warning("=" * 80)
            logger.warning(f"Последний запуск: {recovery_info['last_start_time']}")
            logger.warning(f"Последний останов: {recovery_info['last_stop_time']}")
            logger.warning(f"Сессия: {recovery_info['session_id']}")
            logger.warning(f"Итераций выполнено: {recovery_info['iteration_count']}")
            
            # Проверяем прерванную задачу
            current_task = recovery_info.get("current_task")
            if current_task:
                logger.warning(f"Прерванная задача: {current_task['task_text']}")
                logger.warning(f"  - ID: {current_task['task_id']}")
                logger.warning(f"  - Попыток: {current_task['attempts']}")
                logger.warning(f"  - Начало: {current_task['start_time']}")
                
                # Сбрасываем прерванную задачу для повторного выполнения
                self.checkpoint_manager.reset_interrupted_task()
                logger.info("Прерванная задача сброшена для повторного выполнения")
            
            # Показываем незавершенные задачи (ограничиваем вывод для избежания блокировки)
            incomplete_count = recovery_info["incomplete_tasks_count"]
            if incomplete_count > 0:
                logger.warning(f"Незавершенных задач: {incomplete_count}")
                # Показываем только первые 3 задачи, чтобы не блокировать вывод
                for task in recovery_info["incomplete_tasks"][:3]:
                    try:
                        task_text = str(task.get('task_text', 'N/A'))[:100]  # Ограничиваем длину
                        task_state = str(task.get('state', 'unknown'))
                        logger.warning(f"  - {task_text} (состояние: {task_state})")
                    except Exception as e:
                        # Защита от ошибок при выводе
                        logger.warning(f"  - [Ошибка при выводе задачи: {e}]")
            
            # Показываем задачи с ошибками (ограничиваем вывод)
            failed_count = recovery_info["failed_tasks_count"]
            if failed_count > 0:
                logger.warning(f"Задач с ошибками: {failed_count}")
                # Показываем только первые 2 задачи, чтобы не блокировать вывод
                for task in recovery_info["failed_tasks"][:2]:
                    try:
                        task_text = str(task.get('task_text', 'N/A'))[:100]  # Ограничиваем длину
                        error_msg = str(task.get('error_message', 'N/A'))[:200]  # Ограничиваем длину
                        logger.warning(f"  - {task_text}")
                        logger.warning(f"    Ошибка: {error_msg}")
                    except Exception as e:
                        # Защита от ошибок при выводе
                        logger.warning(f"  - [Ошибка при выводе задачи с ошибкой: {e}]")
            
            logger.warning("=" * 80)
            logger.info("Сервер продолжит работу с последней контрольной точки")
            logger.warning("=" * 80)
            logger.info("Восстановление завершено, продолжаем инициализацию сервера...")
            
            # Обновляем статус
            self.status_manager.append_status(
                f"Восстановление после сбоя. Незавершенных задач: {incomplete_count}, "
                f"с ошибками: {failed_count}",
                level=2
            )
        else:
            logger.info("Предыдущий останов был корректным. Восстановление не требуется.")
            
            # Показываем статистику
            stats = self.checkpoint_manager.get_statistics()
            logger.info(f"Статистика: выполнено {stats['completed']} задач, "
                       f"ошибок {stats['failed']}, итераций {stats['iteration_count']}")
    
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
    
    def _init_cursor_cli(self) -> Optional[CursorCLIInterface]:
        """
        Инициализация Cursor CLI интерфейса
        
        Returns:
            Экземпляр CursorCLIInterface или None если недоступен
        """
        try:
            cursor_config = self.config.get('cursor', {})
            cli_config = cursor_config.get('cli', {})
            
            cli_path = cli_config.get('cli_path')
            timeout = cli_config.get('timeout', self.DEFAULT_CURSOR_CLI_TIMEOUT)
            headless = cli_config.get('headless', True)
            
            logger.debug(f"Инициализация Cursor CLI: timeout={timeout} секунд (из конфига: {cli_config.get('timeout', 'не указан')}, дефолт: {self.DEFAULT_CURSOR_CLI_TIMEOUT})")
            
            # Передаем директорию проекта и роль агента для настройки контекста
            agent_config = self.config.get('agent', {})
            cli_interface = create_cursor_cli_interface(
                cli_path=cli_path,
                timeout=timeout,
                headless=headless,
                project_dir=str(self.project_dir),
                agent_role=agent_config.get('role')
            )
            
            if cli_interface and cli_interface.is_available():
                version = cli_interface.check_version()
                if version:
                    logger.info(f"Cursor CLI версия: {version}")
                return cli_interface
            else:
                logger.info("Cursor CLI не найден в системе")
                return cli_interface
                
        except Exception as e:
            logger.warning(f"Ошибка при инициализации Cursor CLI: {e}")
            return None
    
    def execute_cursor_instruction(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int] = None
    ) -> dict:
        """
        Выполнить инструкцию через Cursor CLI (если доступен)
        
        Args:
            instruction: Текст инструкции для выполнения
            task_id: Идентификатор задачи
            timeout: Таймаут выполнения (если None - используется из конфига)
            
        Returns:
            Словарь с результатом выполнения
        """
        if not self.cursor_cli or not self.cursor_cli.is_available():
            logger.warning("Cursor CLI недоступен, инструкция не может быть выполнена")
            return {
                "task_id": task_id,
                "success": False,
                "error": "Cursor CLI недоступен",
                "cli_available": False
            }
        
        logger.info(f"Выполнение инструкции для задачи {task_id} через Cursor CLI")
        
        result = self.cursor_cli.execute_instruction(
            instruction=instruction,
            task_id=task_id,
            working_dir=str(self.project_dir),
            timeout=timeout
        )
        
        if result["success"]:
            logger.info(f"Инструкция для задачи {task_id} выполнена успешно")
        else:
            logger.warning(f"Инструкция для задачи {task_id} завершилась с ошибкой: {result.get('error_message')}")
        
        return result
    
    def _execute_cursor_instruction_with_retry(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int],
        task_logger: TaskLogger,
        instruction_num: int
    ) -> dict:
        """
        Выполнить инструкцию через Cursor с обработкой повторяющихся ошибок
        
        Args:
            instruction: Текст инструкции
            task_id: ID задачи
            timeout: Таймаут выполнения
            task_logger: Логгер задачи
            instruction_num: Номер инструкции
            
        Returns:
            Словарь с результатом выполнения
        """
        return self.execute_cursor_instruction(
            instruction=instruction,
            task_id=task_id,
            timeout=timeout
        )
    
    def _is_critical_cursor_error(self, error_message: str) -> bool:
        """
        Проверка, является ли ошибка критической (не исправится перезапуском)
        
        Args:
            error_message: Сообщение об ошибке
            
        Returns:
            True если ошибка критическая
        """
        error_lower = error_message.lower()
        critical_keywords = [
            "неоплаченный счет",
            "unpaid",
            "billing",
            "payment required",
            "subscription",
            "account suspended",
            "аккаунт заблокирован",
            "доступ запрещен",
            "access denied",
            "authentication failed",
            "invalid api key",
            "api key expired"
        ]
        return any(keyword in error_lower for keyword in critical_keywords)
    
    def _is_unexpected_cursor_error(self, error_message: str) -> bool:
        """
        Проверка, является ли ошибка непредвиденной (требует перезапуска Docker)
        
        Непредвиденные ошибки - это ошибки, которые могут быть исправлены перезапуском Docker,
        например, когда Cursor CLI недоступен или возвращает неизвестную ошибку.
        
        Args:
            error_message: Сообщение об ошибке
            
        Returns:
            True если ошибка непредвиденная и может быть исправлена перезапуском Docker
        """
        if not error_message:
            return False
        
        error_lower = error_message.lower()
        unexpected_keywords = [
            "неизвестная ошибка",
            "unknown error",
            "cursor cli недоступен",
            "cursor cli unavailable",
            "cli недоступен",
            "cli unavailable"
        ]
        
        # Проверяем на ключевые слова
        if any(keyword in error_lower for keyword in unexpected_keywords):
            return True
        
        # Проверяем на ошибки вида "CLI вернул код X" (кроме специальных кодов)
        # Коды 137 (SIGKILL) и 143 (SIGTERM) обрабатываются специально и не требуют перезапуска
        import re
        cli_code_pattern = r"cli вернул код (\d+)"
        match = re.search(cli_code_pattern, error_lower)
        if match:
            return_code = int(match.group(1))
            logger.debug(f"Найдена ошибка 'CLI вернул код {return_code}' в сообщении: {error_message}")
            # Игнорируем специальные коды, которые обрабатываются отдельно
            if return_code not in [137, 143]:
                # Коды ошибок (не 0) могут указывать на проблемы с контейнером
                logger.debug(f"Код возврата {return_code} не является специальным, считаем ошибку непредвиденной")
                return True
            else:
                logger.debug(f"Код возврата {return_code} является специальным (SIGKILL/SIGTERM), не считаем непредвиденной")
        
        return False
    
    def _handle_cursor_error(self, error_message: str, task_logger: TaskLogger) -> bool:
        """
        Обработка ошибки Cursor с учетом повторяющихся ошибок
        
        Args:
            error_message: Сообщение об ошибке
            task_logger: Логгер задачи
            
        Returns:
            True если можно продолжать работу, False если нужно остановить сервер
        """
        # Проверяем, является ли ошибка критической
        is_critical = self._is_critical_cursor_error(error_message)
        
        # Проверяем, является ли ошибка непредвиденной (требует немедленного перезапуска Docker)
        is_unexpected = self._is_unexpected_cursor_error(error_message)
        logger.info(f"Обработка ошибки Cursor: error_message='{error_message}', is_critical={is_critical}, is_unexpected={is_unexpected}")
        
        with self._cursor_error_lock:
            # Проверяем, та же ли ошибка (сравниваем по первым 100 символам для группировки похожих ошибок)
            error_key = error_message[:100] if error_message else ""
            if self._last_cursor_error == error_key:
                self._cursor_error_count += 1
            else:
                # Новая ошибка - сбрасываем счетчик и задержку
                self._cursor_error_count = 1
                self._last_cursor_error = error_key
                self._cursor_error_delay = self.CURSOR_ERROR_DELAY_INITIAL  # Начинаем с начальной задержки для новой ошибки
            
            # Для критических ошибок - останавливаем сервер сразу (не ждем повторений)
            if is_critical:
                logger.error("=" * 80)
                logger.error(f"КРИТИЧЕСКАЯ ОШИБКА CURSOR: {error_message}")
                logger.error("Критическая ошибка не исправится перезапуском - останавливаем сервер немедленно")
                logger.error("=" * 80)
                task_logger.log_error(f"Критическая ошибка Cursor (не исправится): {error_message}", Exception(error_message))
                # Останавливаем сервер немедленно для критических ошибок
                self._stop_server_due_to_cursor_errors(error_message)
                return False
            
            # Для непредвиденных ошибок - перезапускаем Docker при первой или второй ошибке (если используется Docker)
            # Это позволяет перезапустить Docker даже если первая ошибка была другой
            logger.info(f"Проверка непредвиденной ошибки: is_unexpected={is_unexpected}, счетчик={self._cursor_error_count}")
            if is_unexpected and self._cursor_error_count <= 2:
                logger.info(f"Обнаружена непредвиденная ошибка (счетчик: {self._cursor_error_count}), проверяем использование Docker...")
                # Проверяем, используется ли Docker
                if self.cursor_cli and hasattr(self.cursor_cli, 'cli_command'):
                    logger.debug(f"Cursor CLI доступен, cli_command: {self.cursor_cli.cli_command}")
                    if self.cursor_cli.cli_command == "docker-compose-agent":
                        logger.warning("=" * 80)
                        logger.warning(f"НЕПРЕДВИДЕННАЯ ОШИБКА CURSOR (#{self._cursor_error_count}): {error_message}")
                        logger.warning("Перезапускаем Docker контейнер из-за непредвиденной ошибки...")
                        logger.warning("=" * 80)
                        task_logger.log_warning(f"Непредвиденная ошибка Cursor - перезапуск Docker: {error_message}")
                        
                        # Сначала проверяем, установлен ли агент в контейнере
                        container_name = "cursor-agent-life"
                        logger.info(f"Проверка установки Cursor Agent в контейнере {container_name}...")
                        import subprocess
                        agent_check = subprocess.run(
                            ["docker", "exec", container_name, "/root/.local/bin/agent", "--version"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if agent_check.returncode != 0:
                            logger.warning("Cursor Agent не найден в контейнере, пытаемся переустановить...")
                            self._safe_print("Переустановка Cursor Agent в контейнере...")
                            reinstall_result = subprocess.run(
                                ["docker", "exec", container_name, "bash", "-c", "curl https://cursor.com/install -fsS | bash"],
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            if reinstall_result.returncode == 0:
                                logger.info("✓ Cursor Agent переустановлен")
                                self._safe_print("✓ Cursor Agent переустановлен")
                            else:
                                logger.warning(f"Не удалось переустановить агент: {reinstall_result.stderr[:200]}")
                        
                        # Перезапускаем Docker контейнер и очищаем диалоги
                        self._safe_print("Попытка перезапуска Docker контейнера из-за непредвиденной ошибки...")
                        if self._restart_cursor_environment():
                            success_msg = "Docker контейнер перезапущен после непредвиденной ошибки. Сбрасываем счетчик ошибок."
                            self._safe_print(success_msg)
                            logger.info(success_msg)
                            task_logger.log_info("Docker контейнер перезапущен после непредвиденной ошибки")
                            # Сбрасываем счетчик после перезапуска
                            self._cursor_error_count = 0
                            self._cursor_error_delay = 0
                            self._last_cursor_error = None
                            return True
                        else:
                            logger.warning("Перезапуск Docker не удался, продолжаем с обычной обработкой ошибки")
                            # Продолжаем с обычной обработкой ошибки
                    else:
                        logger.warning(f"Docker не используется (cli_command='{self.cursor_cli.cli_command}'), пропускаем перезапуск для непредвиденной ошибки")
                else:
                    logger.warning("Cursor CLI недоступен или не имеет cli_command, пропускаем перезапуск для непредвиденной ошибки")
            elif is_unexpected:
                logger.debug(f"Непредвиденная ошибка обнаружена, но счетчик ошибок ({self._cursor_error_count}) > 2, пропускаем перезапуск")
            else:
                logger.debug("Ошибка не является непредвиденной (is_unexpected=False), обычная обработка")
            
            # Увеличиваем задержку на +30 секунд при каждой повторяющейся ошибке
            # При первой ошибке задержка уже установлена в 30 секунд выше
            # При каждой следующей повторяющейся ошибке добавляем еще 30 секунд
            if self._cursor_error_count > 1:
                self._cursor_error_delay += self.CURSOR_ERROR_DELAY_INCREMENT
            
            logger.warning(f"Ошибка Cursor #{self._cursor_error_count}: {error_message}")
            logger.warning(f"Дополнительная задержка перед следующим запросом: {self._cursor_error_delay} секунд")
            task_logger.log_warning(f"Ошибка Cursor #{self._cursor_error_count}, задержка перед следующим запросом: {self._cursor_error_delay}с")
            
            # Если ошибка повторилась 3 раза - перезапускаем Docker и очищаем диалоги
            if self._cursor_error_count >= self._max_cursor_errors:
                # Выводим в консоль и в лог
                critical_msg = "=" * 80 + "\n"
                critical_msg += f"КРИТИЧЕСКАЯ СИТУАЦИЯ: Ошибка Cursor повторилась {self._cursor_error_count} раз\n"
                critical_msg += f"Последняя ошибка: {error_message}\n"
                critical_msg += "=" * 80
                
                self._safe_print("\n" + critical_msg + "\n")
                logger.error(critical_msg)
                
                task_logger.log_error(f"Критическая ошибка: повтор {self._cursor_error_count} раз", Exception(error_message))
                
                # Перезапускаем Docker контейнер и очищаем диалоги
                self._safe_print("Попытка перезапуска Docker контейнера и очистки диалогов...")
                if self._restart_cursor_environment():
                    success_msg = "Docker контейнер и диалоги перезапущены. Сбрасываем счетчик ошибок."
                    self._safe_print(success_msg)
                    logger.info(success_msg)
                    task_logger.log_info("Docker контейнер перезапущен после критической ошибки")
                    # Сбрасываем счетчик после перезапуска
                    self._cursor_error_count = 0
                    self._cursor_error_delay = 0
                    self._last_cursor_error = None
                    return True
                else:
                    # Перезапуск не помог - останавливаем сервер
                    self._safe_print("Перезапуск не помог. Останавливаем сервер...")
                    task_logger.log_error("Критическая ошибка: перезапуск не помог, сервер остановлен", Exception(error_message))
                    
                    # Останавливаем сервер
                    self._stop_server_due_to_cursor_errors(error_message)
                    return False
            
            return True
    
    def _restart_cursor_environment(self) -> bool:
        """
        Перезапустить Docker контейнер и очистить открытые диалоги Cursor
        
        Returns:
            True если перезапуск успешен, False иначе
        """
        logger.info("=" * 80)
        logger.info("ПЕРЕЗАПУСК CURSOR ENVIRONMENT")
        logger.info("=" * 80)
        
        try:
            # 1. Очищаем открытые диалоги
            logger.info("Шаг 1: Очистка открытых диалогов Cursor...")
            if self.cursor_cli:
                cleanup_result = self.cursor_cli.prepare_for_new_task()
                if cleanup_result:
                    logger.info("  ✓ Диалоги очищены")
                else:
                    logger.warning("  ⚠ Не удалось полностью очистить диалоги")
            
            # 2. Перезапускаем Docker контейнер (если используется)
            logger.info("Шаг 2: Перезапуск Docker контейнера...")
            if self.cursor_cli and hasattr(self.cursor_cli, 'cli_command'):
                if self.cursor_cli.cli_command == "docker-compose-agent":
                    # Перезапускаем Docker контейнер
                    compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
                    container_name = "cursor-agent-life"  # Имя из docker-compose.agent.yml
                    
                    try:
                        import subprocess
                        
                        # Останавливаем контейнер
                        logger.info(f"  Остановка контейнера {container_name}...")
                        stop_result = subprocess.run(
                            ["docker", "stop", container_name],
                            capture_output=True,
                            text=True,
                            timeout=15
                        )
                        if stop_result.returncode == 0:
                            logger.info(f"  ✓ Контейнер {container_name} остановлен")
                        else:
                            logger.warning(f"  ⚠ Не удалось остановить контейнер: {stop_result.stderr[:200]}")
                        
                        # Ждем немного
                        time.sleep(2)
                        
                        # Запускаем контейнер заново
                        logger.info(f"  Запуск контейнера {container_name}...")
                        up_result = subprocess.run(
                            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if up_result.returncode == 0:
                            logger.info(f"  ✓ Контейнер {container_name} запущен")
                            # Ждем, пока контейнер запустится
                            time.sleep(5)
                            
                            # Проверяем, что контейнер работает
                            check_result = subprocess.run(
                                ["docker", "exec", container_name, "echo", "ok"],
                                capture_output=True,
                                timeout=5
                            )
                            
                            if check_result.returncode == 0:
                                logger.info("  ✓ Контейнер работает корректно")
                                
                                # Проверяем, установлен ли Cursor Agent
                                logger.info("  Проверка установки Cursor Agent...")
                                agent_check = subprocess.run(
                                    ["docker", "exec", container_name, "/root/.local/bin/agent", "--version"],
                                    capture_output=True,
                                    text=True,
                                    timeout=10
                                )
                                
                                if agent_check.returncode == 0:
                                    agent_version = agent_check.stdout.strip()[:50] if agent_check.stdout else "unknown"
                                    logger.info(f"  ✓ Cursor Agent установлен: {agent_version}")
                                else:
                                    logger.warning("  ⚠ Cursor Agent не найден, пытаемся переустановить...")
                                    reinstall_result = subprocess.run(
                                        ["docker", "exec", container_name, "bash", "-c", "curl https://cursor.com/install -fsS | bash"],
                                        capture_output=True,
                                        text=True,
                                        timeout=60
                                    )
                                    if reinstall_result.returncode == 0:
                                        logger.info("  ✓ Cursor Agent переустановлен")
                                        # Проверяем снова
                                        verify_result = subprocess.run(
                                            ["docker", "exec", container_name, "/root/.local/bin/agent", "--version"],
                                            capture_output=True,
                                            text=True,
                                            timeout=10
                                        )
                                        if verify_result.returncode == 0:
                                            logger.info("  ✓ Cursor Agent подтвержден после переустановки")
                                        else:
                                            logger.warning("  ⚠ Cursor Agent все еще не работает после переустановки")
                                    else:
                                        logger.error(f"  ✗ Не удалось переустановить Cursor Agent: {reinstall_result.stderr[:200]}")
                                
                                logger.info("=" * 80)
                                logger.info("ПЕРЕЗАПУСК УСПЕШЕН")
                                logger.info("=" * 80)
                                return True
                            else:
                                logger.warning(f"  ⚠ Контейнер запущен, но не отвечает: {check_result.stderr[:200]}")
                        else:
                            logger.error(f"  ✗ Не удалось запустить контейнер: {up_result.stderr[:200]}")
                    except Exception as e:
                        logger.error(f"  ✗ Ошибка при перезапуске Docker: {e}", exc_info=True)
                        return False
                else:
                    logger.info("  Docker не используется, пропускаем перезапуск контейнера")
                    # Если не Docker, просто очищаем диалоги
                    logger.info("=" * 80)
                    logger.info("ПЕРЕЗАПУСК ЗАВЕРШЕН (без Docker)")
                    logger.info("=" * 80)
                    return True
            else:
                logger.warning("  Cursor CLI недоступен, пропускаем перезапуск")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при перезапуске Cursor environment: {e}", exc_info=True)
            return False
    
    def _safe_print(self, message: str, end: str = "\n") -> None:
        """
        Безопасный вывод в консоль с защитой от ошибок потока
        
        Args:
            message: Сообщение для вывода
            end: Символ окончания строки (по умолчанию \n)
        """
        try:
            print(message, end=end, flush=True)
        except (OSError, IOError, ValueError):
            # Если stdout недоступен (закрыт или обернут), используем stderr
            try:
                sys.stderr.write(message + (end if end else ""))
                sys.stderr.flush()
            except (OSError, IOError, ValueError):
                # Если и stderr недоступен, просто пропускаем вывод в консоль
                # Логирование все равно произойдет через logger
                pass
    
    def _stop_server_due_to_cursor_errors(self, error_message: str):
        """
        Остановить сервер из-за критических ошибок Cursor
        
        Args:
            error_message: Сообщение об ошибке
        """
        # Выводим в консоль и в лог
        error_msg = "=" * 80 + "\n"
        error_msg += "ОСТАНОВКА СЕРВЕРА ИЗ-ЗА КРИТИЧЕСКИХ ОШИБОК CURSOR\n"
        error_msg += "=" * 80 + "\n"
        error_msg += f"Ошибка повторяется: {error_message}\n"
        error_msg += f"Количество повторений: {self._cursor_error_count}\n"
        error_msg += "Перезапуск Docker контейнера не помог\n"
        error_msg += "=" * 80 + "\n"
        error_msg += "РЕКОМЕНДАЦИИ:\n"
        error_msg += "1. Проверьте состояние Cursor аккаунта: https://cursor.com/dashboard\n"
        error_msg += "2. Проверьте доступность Docker контейнера\n"
        error_msg += "3. Проверьте логи Cursor для деталей ошибки\n"
        error_msg += "4. Перезапустите сервер вручную после устранения проблемы\n"
        error_msg += "=" * 80
        
        # Выводим в консоль (с защитой от ошибок потока)
        self._safe_print("\n" + error_msg + "\n")
        
        # Логируем
        logger.error(error_msg)
        
        # Обновляем статус
        self.status_manager.append_status(
            f"КРИТИЧЕСКАЯ ОШИБКА: Cursor ошибка повторяется ({self._cursor_error_count} раз). "
            f"Ошибка: {error_message}. Сервер остановлен.",
            level=2
        )
        
        # Устанавливаем флаг остановки
        with self._stop_lock:
            self._should_stop = True
        
        # Отмечаем некорректный останов
        self.checkpoint_manager.mark_server_stop(clean=False)
        
        # Логируем остановку
        self.server_logger.log_server_shutdown(
            f"Остановка из-за критических ошибок Cursor: {error_message} (повтор {self._cursor_error_count} раз)"
        )
    
    def is_cursor_cli_available(self) -> bool:
        """
        Проверка доступности Cursor CLI
        
        Returns:
            True если CLI доступен, False иначе
        """
        return self.cursor_cli is not None and self.cursor_cli.is_available()
    
    def _determine_task_type(self, todo_item: TodoItem) -> str:
        """
        Определение типа задачи для выбора инструкции
        
        Args:
            todo_item: Элемент todo-листа
        
        Returns:
            Тип задачи (default, frontend-task, backend-task, etc.)
        """
        task_text = todo_item.text.lower()
        
        # Определяем тип задачи по ключевым словам
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
    
    def _get_instruction_template(self, task_type: str, instruction_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Получить шаблон инструкции из конфигурации
        
        Args:
            task_type: Тип задачи
            instruction_id: ID инструкции (1-8 для последовательного выполнения)
        
        Returns:
            Словарь с шаблоном инструкции или None
        """
        instructions = self.config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))
        
        # Ищем инструкцию с нужным ID
        for instruction in task_instructions:
            if isinstance(instruction, dict) and instruction.get('instruction_id') == instruction_id:
                return instruction
        
        # Если не найдена, берем первую доступную (только для backward compatibility)
        if task_instructions and isinstance(task_instructions[0], dict):
            return task_instructions[0]
        
        return None
    
    def _get_all_instruction_templates(self, task_type: str) -> List[Dict[str, Any]]:
        """
        Получить все шаблоны инструкций для типа задачи (последовательно 1-8)
        
        Args:
            task_type: Тип задачи
        
        Returns:
            Список шаблонов инструкций, отсортированный по instruction_id
        """
        instructions = self.config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))
        
        # Фильтруем только словари с instruction_id и сортируем по ID
        valid_instructions = [
            instr for instr in task_instructions
            if isinstance(instr, dict) and 'instruction_id' in instr
        ]
        
        # Сортируем по instruction_id (1, 2, 3, ...)
        valid_instructions.sort(key=lambda x: x.get('instruction_id', 999))
        
        return valid_instructions
    
    def _format_instruction(self, template: Dict[str, Any], todo_item: TodoItem, task_id: str, instruction_num: int = 1) -> str:
        """
        Форматирование инструкции из шаблона
        
        Args:
            template: Шаблон инструкции
            todo_item: Элемент todo-листа
            task_id: Идентификатор задачи
            instruction_num: Номер инструкции в последовательности
        
        Returns:
            Отформатированная инструкция
        """
        instruction_text = template.get('template', '')
        
        # Подстановка значений
        replacements = {
            'task_name': todo_item.text,
            'task_id': task_id,
            'task_description': todo_item.text,
            'date': datetime.now().strftime('%Y%m%d'),
            'plan_item_number': str(instruction_num),  # Номер инструкции
            'plan_item_text': todo_item.text
        }
        
        for key, value in replacements.items():
            instruction_text = instruction_text.replace(f'{{{key}}}', str(value))
        
        return instruction_text
    
    def _wait_for_result_file(
        self,
        task_id: str,
        wait_for_file: Optional[str] = None,
        control_phrase: Optional[str] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Ожидание файла результата от Cursor
        
        Args:
            task_id: Идентификатор задачи
            wait_for_file: Путь к ожидаемому файлу (относительно project_dir)
            control_phrase: Контрольная фраза для проверки
            timeout: Таймаут ожидания (секунды)
        
        Returns:
            Словарь с результатом ожидания
        """
        if not wait_for_file:
            # Формируем путь по умолчанию
            wait_for_file = f"docs/results/result_{task_id}.md"
        
        # Подстановка task_id и date в путь
        wait_for_file = wait_for_file.replace('{task_id}', task_id)
        wait_for_file = wait_for_file.replace('{date}', datetime.now().strftime('%Y%m%d'))
        
        file_path = self.project_dir / wait_for_file
        
        # ДОПОЛНИТЕЛЬНО: Проверяем также cursor_results/ на случай, если файл создан через файловый интерфейс
        cursor_results_dir = self.project_dir / "cursor_results"
        cursor_result_patterns = [
            f"result_{task_id}.txt",
            f"result_{task_id}.md",
            f"{task_id}.txt",
            f"{task_id}.md",
            f"result_full_cycle_{task_id}.txt",
            f"result_full_cycle_{task_id}.md"
        ]
        
        logger.info(f"Ожидание файла результата: {file_path} (timeout: {timeout}s)")
        logger.debug(f"Контрольная фраза: '{control_phrase}'")
        logger.debug(f"Также проверяем cursor_results/ на наличие файлов: {cursor_result_patterns}")

        # Во время ожидания результата считаем, что "инструкция выполняется",
        # чтобы автоперезапуск не обрывал ожидание (перезапуск будет отложен).
        with self._task_in_progress_lock:
            prev_task_in_progress = self._task_in_progress
            self._task_in_progress = True

        start_time = time.time()
        check_interval = 2
        last_log_time = 0
        log_interval = 10  # Логируем каждые 10 секунд

        try:
            while time.time() - start_time < timeout:
                elapsed = time.time() - start_time
                
                # Периодическое логирование для диагностики
                if elapsed - last_log_time >= log_interval:
                    logger.info(f"Ожидание файла {file_path.name}... (прошло {elapsed:.0f}s из {timeout}s)")
                    # Проверяем также cursor_results/
                    if cursor_results_dir.exists():
                        found_in_cursor_results = []
                        for pattern in cursor_result_patterns:
                            candidate = cursor_results_dir / pattern
                            if candidate.exists():
                                found_in_cursor_results.append(str(candidate))
                        if found_in_cursor_results:
                            logger.info(f"Найдены файлы в cursor_results/: {found_in_cursor_results}")
                    last_log_time = elapsed
                
                # Проверяем запрос на остановку
                with self._stop_lock:
                    if self._should_stop:
                        logger.warning("Получен запрос на остановку во время ожидания файла результата")
                        return {
                            "success": False,
                            "file_path": str(file_path),
                            "content": None,
                            "wait_time": time.time() - start_time,
                            "error": "Остановка сервера по запросу"
                        }
                
                # Проверяем необходимость перезапуска
                if self._check_reload_needed():
                    logger.warning("Обнаружено изменение кода во время ожидания файла результата")
                    return {
                        "success": False,
                        "file_path": str(file_path),
                        "content": None,
                        "wait_time": time.time() - start_time,
                        "error": "Перезапуск сервера из-за изменения кода"
                    }
                
                # Сначала проверяем cursor_results/ (файловый интерфейс)
                if cursor_results_dir.exists():
                    for pattern in cursor_result_patterns:
                        cursor_result_path = cursor_results_dir / pattern
                        if cursor_result_path.exists():
                            logger.info(f"Найден файл результата в cursor_results/: {cursor_result_path}")
                            try:
                                content = cursor_result_path.read_text(encoding='utf-8')
                                if control_phrase:
                                    if control_phrase in content:
                                        logger.info("Файл из cursor_results/ содержит контрольную фразу")
                                        return {
                                            "success": True,
                                            "file_path": str(cursor_result_path),
                                            "content": content,
                                            "wait_time": time.time() - start_time
                                        }
                                    else:
                                        logger.debug("Файл найден в cursor_results/, но контрольная фраза еще не появилась")
                                else:
                                    # Контрольная фраза не требуется
                                    logger.info("Файл результата найден в cursor_results/")
                                    return {
                                        "success": True,
                                        "file_path": str(cursor_result_path),
                                        "content": content,
                                        "wait_time": time.time() - start_time
                                    }
                            except Exception as e:
                                logger.warning(f"Ошибка чтения файла из cursor_results/ {cursor_result_path}: {e}")
                
                # Затем проверяем основной путь (docs/results/)
                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        
                        # Проверяем контрольную фразу если указана
                        if control_phrase:
                            if control_phrase in content:
                                logger.info("Файл результата найден и содержит контрольную фразу")
                                return {
                                    "success": True,
                                    "file_path": str(file_path),
                                    "content": content,
                                    "wait_time": time.time() - start_time
                                }
                            else:
                                logger.debug("Файл найден, но контрольная фраза еще не появилась")
                        else:
                            # Контрольная фраза не требуется
                            logger.info("Файл результата найден")
                            return {
                                "success": True,
                                "file_path": str(file_path),
                                "content": content,
                                "wait_time": time.time() - start_time
                            }
                    except Exception as e:
                        logger.warning(f"Ошибка чтения файла {file_path}: {e}")
                
                # Дополнительная проверка: для инструкции 3 (тестирование) проверяем альтернативные имена
                # Если ожидаем test_{task_id}.md, проверяем также test_task_{task_id}.md и другие варианты
                if "test_" in wait_for_file.lower() and "docs/results" in wait_for_file:
                    results_dir = self.project_dir / "docs" / "results"
                    if results_dir.exists():
                        # Проверяем альтернативные варианты имен файлов
                        alternative_patterns = [
                            f"test_{task_id}.md",
                            f"test_{task_id}.txt",
                            f"test_task_{task_id}.md",
                            f"test_task_{task_id}.txt",
                        ]
                        for alt_pattern in alternative_patterns:
                            alt_path = results_dir / alt_pattern
                            if alt_path.exists() and alt_path != file_path:
                                logger.info(f"Найден альтернативный файл результата: {alt_path}")
                                try:
                                    content = alt_path.read_text(encoding='utf-8')
                                    if control_phrase:
                                        if control_phrase in content:
                                            logger.info("Альтернативный файл содержит контрольную фразу")
                                            return {
                                                "success": True,
                                                "file_path": str(alt_path),
                                                "content": content,
                                                "wait_time": time.time() - start_time
                                            }
                                    else:
                                        return {
                                            "success": True,
                                            "file_path": str(alt_path),
                                            "content": content,
                                            "wait_time": time.time() - start_time
                                        }
                                except Exception as e:
                                    logger.warning(f"Ошибка чтения альтернативного файла {alt_path}: {e}")
                
                # Проверяем запрос на остановку перед ожиданием
                with self._stop_lock:
                    if self._should_stop:
                        logger.warning("Получен запрос на остановку во время ожидания файла результата")
                        return {
                            "success": False,
                            "file_path": str(file_path),
                            "content": None,
                            "wait_time": time.time() - start_time,
                            "error": "Остановка сервера по запросу"
                        }
                
                # Проверяем необходимость перезапуска
                if self._check_reload_needed():
                    logger.warning("Обнаружено изменение кода во время ожидания файла результата")
                    return {
                        "success": False,
                        "file_path": str(file_path),
                        "content": None,
                        "wait_time": time.time() - start_time,
                        "error": "Перезапуск сервера из-за изменения кода"
                    }
                
                # Ждем перед следующей проверкой
                time.sleep(check_interval)

            # Таймаут
            logger.warning(f"Таймаут ожидания файла результата ({timeout}s)")
            return {
                "success": False,
                "file_path": str(file_path),
                "content": None,
                "wait_time": timeout,
                "error": f"Таймаут ожидания файла ({timeout} секунд)"
            }
        finally:
            with self._task_in_progress_lock:
                self._task_in_progress = prev_task_in_progress
    
    def _check_task_usefulness(self, todo_item: TodoItem) -> Tuple[float, Optional[str]]:
        """
        Проверка полезности задачи - является ли она реальной задачей или мусором в тексте туду
        
        Args:
            todo_item: Элемент todo-листа для проверки
            
        Returns:
            Кортеж (процент полезности 0-100, комментарий если есть)
        """
        try:
            from src.llm.llm_manager import LLMManager
            import asyncio
            import json
            import re
            
            def _extract_json_object(text: str) -> Optional[dict]:
                """
                Надежно извлекает JSON-объект из ответа LLM.
                Поддерживает ситуации, когда модель возвращает текст/markdown и JSON внутри.
                """
                if not text:
                    return None
                
                t = text.strip()
                # Убираем code fences вида ```json ... ```
                if t.startswith("```"):
                    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
                    t = re.sub(r"\s*```$", "", t)
                    t = t.strip()
                
                decoder = json.JSONDecoder()
                # Ищем первый валидный JSON объект, начиная с '{' или '['
                for i, ch in enumerate(t):
                    if ch not in "{[":
                        continue
                    try:
                        obj, _end = decoder.raw_decode(t[i:])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        return obj
                return None
            
            # Инициализируем LLMManager (логи инициализации моделей будут подавлены)
            # Используем временное изменение уровня логирования для LLMManager
            llm_logger = logging.getLogger('src.llm.llm_manager')
            original_level = llm_logger.level
            llm_logger.setLevel(logging.WARNING)  # Подавляем INFO логи инициализации
            
            # Временно убираем префиксы (asctime, name, levelname) для блока LLM Manager
            # Применяем простой форматтер ко всем handlers root logger
            # Все дочерние логгеры (src.server, src.llm.llm_manager) используют propagate=True
            # и передают записи в root logger, поэтому изменение root logger достаточно
            root_logger = logging.getLogger()
            original_formatters = []
            simple_format = logging.Formatter('%(message)s')
            
            # Сохраняем и изменяем форматеры для всех handlers root logger
            # Важно: обрабатываем handlers даже если у них нет форматера (устанавливаем новый)
            for handler in root_logger.handlers[:]:  # Копируем список
                original_formatter = handler.formatter
                original_formatters.append((handler, original_formatter))
                # Устанавливаем простой форматтер (даже если был None)
                handler.setFormatter(simple_format)
            
            # Функция для восстановления форматеров (вызывается перед return)
            def restore_formatters():
                llm_logger.setLevel(original_level)
                # Восстанавливаем оригинальные форматеры (включая None, если его не было)
                for handler, original_formatter in original_formatters:
                    handler.setFormatter(original_formatter)
            
            try:
                llm_manager = LLMManager(config_path="config/llm_settings.yaml")
                
                # Выводим компактную информацию о LLM Manager (без префиксов)
                logger.info(Colors.colorize(
                    "┌─ LLM Manager ─────────────────────────────────────────────",
                    Colors.BRIGHT_CYAN
                ))
                logger.info(Colors.colorize(
                    "│ Инициализирован для проверки полезности задачи",
                    Colors.BRIGHT_CYAN
                ))
            except Exception:
                # Восстанавливаем форматеры при ошибке инициализации
                restore_formatters()
                raise
            
            # Формируем промпт для проверки полезности
            # Загружаем документацию проекта для контекста
            project_docs = self._load_documentation()
            project_docs_preview = project_docs[:2000] if len(project_docs) > 2000 else project_docs
            
            check_prompt = f"""Оцени полезность этого пункта из TODO списка проекта.

КОНТЕКСТ ПРОЕКТА (документация):
{project_docs_preview}

ПУНКТ TODO:
{todo_item.text}

Оцени полезность задачи в процентах от 0% до 100%:
- 0-15% - это мусор/шум, не является реальной задачей (случайный текст, личные заметки, дубликаты, пустые строки)
- 16-50% - слабая полезность, возможно неполная или неясная задача
- 51-80% - средняя полезность, задача понятна но может быть улучшена
- 81-100% - высокая полезность, четкая и конкретная техническая задача

Учитывай контекст проекта из документации при оценке. Технические задачи, связанные с проектом, должны иметь высокую полезность.

Верни JSON объект со следующей структурой:
{{
  "usefulness_percent": число от 0 до 100,
  "comment": "краткий комментарий о полезности задачи"
}}"""
            
            # Выполняем проверку через LLMManager с JSON mode (асинхронно)
            # ВАЖНО: Используем best_of_two для надежности (не самую быструю модель)
            # Это критичная проверка, нужна качественная модель
            json_response_format = {"type": "json_object"}
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если loop уже запущен, создаем задачу в отдельном потоке
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(llm_manager.generate_response(
                                prompt=check_prompt,
                                use_fastest=False,  # НЕ используем самую быструю - нужна качественная модель
                                use_parallel=True,  # Используем best_of_two для надежности
                                response_format=json_response_format
                            ))
                        )
                        response = future.result(timeout=90)  # Увеличиваем таймаут для best_of_two
                else:
                    # Loop существует, но не запущен
                    response = loop.run_until_complete(llm_manager.generate_response(
                        prompt=check_prompt,
                        use_fastest=False,  # НЕ используем самую быструю - нужна качественная модель
                        use_parallel=True,  # Используем best_of_two для надежности
                        response_format=json_response_format
                    ))
            except RuntimeError:
                # Нет event loop, создаем новый
                response = asyncio.run(llm_manager.generate_response(
                    prompt=check_prompt,
                    use_fastest=False,  # НЕ используем самую быструю - нужна качественная модель
                    use_parallel=True,  # Используем best_of_two для надежности
                    response_format=json_response_format
                ))
            
            # Парсим ответ LLM (с JSON mode ответ должен быть валидным JSON)
            # ВАЖНО: Даже если response.success = False, пытаемся использовать content если он есть
            content = response.content.strip() if response.content else ""
            
            if not response.success:
                if content:
                    logger.warning(
                        f"│ ⚠️ LLM вернул ошибку, но есть контент. Пытаемся использовать его. "
                        f"Ошибка: {response.error}, контент: {content[:200]}..."
                    )
                else:
                    logger.warning(
                        f"│ ❌ Не удалось выполнить проверку полезности для задачи: {response.error}"
                    )
                    logger.info(Colors.colorize(
                        "└───────────────────────────────────────────────────────────",
                        Colors.BRIGHT_CYAN
                    ))
                    restore_formatters()
                    return 50.0, "Ошибка проверки, считаем средней полезности"  # По умолчанию средняя полезность
            
            if not content:
                logger.warning(
                    f"│ ❌ Пустой ответ LLM при проверке полезности (model={getattr(response, 'model_name', 'unknown')})"
                )
                logger.info(Colors.colorize(
                    "└───────────────────────────────────────────────────────────",
                    Colors.BRIGHT_CYAN
                ))
                restore_formatters()
                return 50.0, "Пустой ответ LLM, считаем средней полезности"
            
            # Логируем ответ LLM компактно, но с сохранением текста от LLM
            model_name = getattr(response, 'model_name', 'unknown')
            response_time = getattr(response, 'response_time', 0.0)
            
            # Выводим итоговую информацию о результате всех попыток
            status_icon = "✅" if response.success else "❌"
            status_text = "УСПЕШНО" if response.success else "НЕУДАЧНО"
            
            logger.info(Colors.colorize(
                f"│ ИТОГ: {status_icon} {status_text} | Модель: {model_name} | Время: {response_time:.2f}s",
                Colors.BRIGHT_CYAN if response.success else Colors.BRIGHT_YELLOW
            ))
            
            # Выводим полный текст ответа LLM (важно для диагностики)
            if content:
                # Извлекаем JSON для красивого отображения
                response_data_preview = _extract_json_object(content)
                if response_data_preview:
                    usefulness_preview = response_data_preview.get('usefulness_percent', '?')
                    comment_preview = response_data_preview.get('comment', '')[:100]
                    logger.info(Colors.colorize(
                        f"│ Результат: usefulness={usefulness_preview}%, comment=\"{comment_preview}\"",
                        Colors.BRIGHT_CYAN
                    ))
                else:
                    # Если не удалось извлечь JSON, показываем первые 200 символов
                    logger.info(Colors.colorize(
                        f"│ Ответ LLM (текст): {content[:200]}...",
                        Colors.BRIGHT_CYAN
                    ))
            
            # С JSON mode ответ должен быть валидным JSON, но не все модели/провайдеры строго соблюдают
            # — поэтому извлекаем JSON устойчиво с несколькими попытками.
            response_data = _extract_json_object(content)
            
            # Если не удалось извлечь, пробуем более агрессивные методы
            if response_data is None:
                # Попытка 1: Прямой парсинг всего текста
                try:
                    response_data = json.loads(content)
                except json.JSONDecodeError:
                    # Попытка 2: Ищем JSON объект в тексте более гибко
                    import re
                    # Ищем паттерн вида {"usefulness_percent": число, "comment": "текст"}
                    json_pattern = r'\{[^{}]*"usefulness_percent"[^{}]*\}'
                    match = re.search(json_pattern, content, re.DOTALL)
                    if match:
                        try:
                            response_data = json.loads(match.group())
                            logger.info("✓ JSON извлечен из текста через regex паттерн")
                        except json.JSONDecodeError:
                            pass
                    
                    # Попытка 3: Пытаемся создать JSON из найденных чисел и текста
                    if response_data is None:
                        numbers = re.findall(r'\d+\.?\d*', content)
                        # Ищем процентное значение (0-100)
                        usefulness_value = None
                        for num_str in numbers:
                            num = float(num_str)
                            if 0 <= num <= 100:
                                usefulness_value = num
                                break
                        
                        if usefulness_value is not None:
                            # Извлекаем комментарий (текст после "comment" или в кавычках)
                            comment_match = re.search(r'comment["\']?\s*[:=]\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                            comment_text = comment_match.group(1) if comment_match else "Извлечено из текста"
                            response_data = {
                                "usefulness_percent": usefulness_value,
                                "comment": comment_text
                            }
                            logger.info(f"✓ JSON создан из извлеченных значений: {usefulness_value}%")
            
            # Если все попытки не удались - используем дефолтное значение
            if response_data is None:
                logger.warning(
                    f"│ ⚠️ Не удалось извлечь JSON из ответа LLM (модель: {getattr(response, 'model_name', 'unknown')}). "
                    f"Ответ: {content[:500]}. Используем дефолтное значение 75% (техническая задача по умолчанию)"
                )
                logger.info(Colors.colorize(
                    "└───────────────────────────────────────────────────────────",
                    Colors.BRIGHT_CYAN
                ))
                restore_formatters()
                # ВАЖНО: Для технических задач используем 75% по умолчанию, а не 50%
                # Это предотвращает ложное отбрасывание валидных задач
                return 75.0, "Не удалось определить полезность из ответа LLM, считаем технической задачей (75%)"
            
            # Валидируем что response_data это dict
            if not isinstance(response_data, dict):
                logger.warning(
                    f"│ ⚠️ response_data не является dict: {type(response_data)}. Используем дефолт 75%"
                )
                logger.info(Colors.colorize(
                    "└───────────────────────────────────────────────────────────",
                    Colors.BRIGHT_CYAN
                ))
                restore_formatters()
                return 75.0, "Неверный формат ответа LLM, считаем технической задачей (75%)"
            
            try:
                usefulness = float(response_data.get('usefulness_percent', 75.0))
                comment = response_data.get('comment', response_data.get('reason', 'Нет комментария'))
                
                # Самопроверка LLM: если оценка подозрительно низкая (особенно 0%), 
                # перепроверяем с использованием контекста проекта
                if usefulness < 20.0:  # Подозрительно низкая оценка
                    logger.info(Colors.colorize(
                        "│",
                        Colors.BRIGHT_CYAN
                    ))
                    logger.info(Colors.colorize(
                        f"│ ⚠️  Самопроверка LLM: подозрительно низкая оценка ({usefulness}%)",
                        Colors.BRIGHT_YELLOW
                    ))
                    
                    # Загружаем документацию проекта для контекста
                    project_docs = self._load_documentation()
                    # Ограничиваем размер документации для промпта (чтобы не превысить лимиты токенов)
                    project_docs_preview = project_docs[:3000] if len(project_docs) > 3000 else project_docs
                    
                    # Формируем промпт для самопроверки
                    self_check_prompt = f"""Проверь адекватность оценки полезности задачи, используя контекст проекта.

КОНТЕКСТ ПРОЕКТА (документация):
{project_docs_preview}

ЗАДАЧА ИЗ TODO:
{todo_item.text}

ПЕРВОНАЧАЛЬНАЯ ОЦЕНКА:
- Полезность: {usefulness}%
- Комментарий: {comment}

ВОПРОС: Учитывая контекст проекта и содержание задачи, является ли оценка {usefulness}% адекватной?

ВАЖНО:
- Если задача связана с техническими аспектами проекта (MCP, API, архитектура, рефакторинг, оптимизация, документация, поиск, индексация и т.д.) - она должна иметь высокую полезность (50-100%)
- Если задача действительно является мусором/шумом (случайный текст, личные заметки, дубликаты) - низкая оценка оправдана
- Учитывай специфику проекта из документации

Верни JSON объект:
{{
  "is_adequate": true/false,
  "corrected_usefulness_percent": число от 0 до 100 (если is_adequate=false, предложи правильную оценку),
  "reason": "краткое объяснение почему оценка адекватна или нет"
}}"""
                    
                    # Выполняем самопроверку
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    lambda: asyncio.run(llm_manager.generate_response(
                                        prompt=self_check_prompt,
                                        use_fastest=False,
                                        use_parallel=True,
                                        response_format=json_response_format
                                    ))
                                )
                                self_check_response = future.result(timeout=90)
                        else:
                            self_check_response = loop.run_until_complete(llm_manager.generate_response(
                                prompt=self_check_prompt,
                                use_fastest=False,
                                use_parallel=True,
                                response_format=json_response_format
                            ))
                    except RuntimeError:
                        self_check_response = asyncio.run(llm_manager.generate_response(
                            prompt=self_check_prompt,
                            use_fastest=False,
                            use_parallel=True,
                            response_format=json_response_format
                        ))
                    
                    # Парсим ответ самопроверки
                    if self_check_response.success and self_check_response.content:
                        self_check_content = self_check_response.content.strip()
                        self_check_data = _extract_json_object(self_check_content)
                        
                        if self_check_data and isinstance(self_check_data, dict):
                            is_adequate = self_check_data.get('is_adequate', True)
                            corrected_usefulness = self_check_data.get('corrected_usefulness_percent')
                            reason = self_check_data.get('reason', 'Нет объяснения')
                            
                            if not is_adequate and corrected_usefulness is not None:
                                original_usefulness = usefulness  # Сохраняем первоначальное значение
                                corrected_usefulness = float(corrected_usefulness)
                                # Ограничиваем значение
                                corrected_usefulness = max(0.0, min(100.0, corrected_usefulness))
                                
                                logger.info(Colors.colorize(
                                    f"│ ✓ Самопроверка: {original_usefulness}% → {corrected_usefulness}%",
                                    Colors.BRIGHT_GREEN
                                ))
                                logger.info(Colors.colorize(
                                    f"│   Причина: {reason}",
                                    Colors.BRIGHT_CYAN
                                ))
                                
                                usefulness = corrected_usefulness
                                comment = f"Самопроверка LLM: {reason} (исправлено с {original_usefulness}%)"
                            else:
                                logger.info(Colors.colorize(
                                    f"│ ✓ Самопроверка: оценка {usefulness}% подтверждена",
                                    Colors.BRIGHT_CYAN
                                ))
                        else:
                            logger.warning("Не удалось распарсить ответ самопроверки LLM, используем первоначальную оценку")
                    else:
                        logger.warning(f"Самопроверка LLM не удалась: {getattr(self_check_response, 'error', 'unknown error')}, используем первоначальную оценку")
                
                # Ограничиваем значение от 0 до 100
                usefulness = max(0.0, min(100.0, usefulness))
                
                # Закрываем блок LLM Manager
                logger.info(Colors.colorize(
                    "└───────────────────────────────────────────────────────────",
                    Colors.BRIGHT_CYAN
                ))
                restore_formatters()
                
                logger.debug(f"Успешно распарсен JSON: usefulness={usefulness}%, comment={comment}")
                return usefulness, comment
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    f"│ ⚠️ Ошибка при обработке ответа: {e}, содержимое: {content[:300]}, response_data: {response_data}"
                )
                logger.info(Colors.colorize(
                    "└───────────────────────────────────────────────────────────",
                    Colors.BRIGHT_CYAN
                ))
                restore_formatters()
                return 75.0, f"Ошибка обработки ответа, считаем технической задачей (75%): {str(e)[:100]}"
            
        except ImportError:
            logger.warning("LLMManager не доступен, пропускаем проверку полезности")
            # Форматеры не были изменены при ImportError, но на всякий случай проверим
            if 'restore_formatters' in locals():
                restore_formatters()
            return 75.0, "LLMManager недоступен, считаем технической задачей (75%)"
        except Exception as e:
            logger.error(
                f"│ ❌ Ошибка при проверке полезности задачи через LLMManager: {e}", exc_info=True
            )
            logger.info(Colors.colorize(
                "└───────────────────────────────────────────────────────────",
                Colors.BRIGHT_CYAN
            ))
            # Восстанавливаем форматеры при исключении
            if 'restore_formatters' in locals():
                restore_formatters()
            # ВАЖНО: При ошибке считаем задачу технической (75%), а не мусором (50%)
            # Это предотвращает ложное отбрасывание валидных задач при сбоях LLM
            return 75.0, f"Ошибка проверки, считаем технической задачей (75%): {str(e)[:100]}"
    
    def _check_todo_matches_plan(self, task_id: str, todo_item: TodoItem) -> Tuple[bool, Optional[str]]:
        """
        Проверка соответствия пункта туду пунктам плана через LLM агентов Code Agent (OpenRouter)
        
        Args:
            task_id: ID задачи
            todo_item: Элемент todo-листа для проверки
            
        Returns:
            Кортеж (соответствует ли туду плану, причина несоответствия если есть)
        """
        # Ищем файл плана
        plan_file = self.project_dir / "docs" / "results" / f"current_plan_{task_id}.md"
        
        if not plan_file.exists():
            # Если плана нет, считаем что соответствует (будет создан при выполнении)
            logger.debug(f"План для задачи {task_id} не найден, считаем что туду соответствует")
            return True, None
        
        try:
            plan_content = plan_file.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Не удалось прочитать план для задачи {task_id}: {e}")
            return True, None  # Если не можем прочитать план, считаем что соответствует
        
        # Используем LLMManager через OpenRouter для проверки соответствия
        try:
            from src.llm.llm_manager import LLMManager
            import asyncio
            import json
            import re
            
            def _extract_json_object(text: str) -> Optional[dict]:
                """
                Надежно извлекает JSON-объект из ответа LLM (может быть внутри markdown/текста).
                """
                if not text:
                    return None
                
                t = text.strip()
                if t.startswith("```"):
                    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
                    t = re.sub(r"\s*```$", "", t)
                    t = t.strip()
                
                decoder = json.JSONDecoder()
                for i, ch in enumerate(t):
                    if ch not in "{[":
                        continue
                    try:
                        obj, _end = decoder.raw_decode(t[i:])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        return obj
                return None
            
            # Инициализируем LLMManager
            llm_manager = LLMManager(config_path="config/llm_settings.yaml")
            
            # Формируем промпт для проверки
            check_prompt = f"""Проверь, соответствует ли пункт туду пунктам плана.

ПУНКТ ТУДУ:
{todo_item.text}

ПЛАН ВЫПОЛНЕНИЯ:
{plan_content}

Ответь ТОЛЬКО в формате JSON:
{{
  "matches": true/false,
  "reason": "краткая причина несоответствия (если matches=false)"
}}

Если пункт туду соответствует хотя бы одному пункту плана, верни matches=true.
Если пункт туду НЕ соответствует ни одному пункту плана, верни matches=false с причиной."""
            
            # Выполняем проверку через LLMManager (асинхронно)
            # Используем безопасный способ вызова асинхронной функции
            # Пытаемся получить текущий event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если loop уже запущен, создаем задачу в отдельном потоке
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(llm_manager.generate_response(
                                prompt=check_prompt,
                                use_fastest=True,
                                use_parallel=False
                            ))
                        )
                        response = future.result(timeout=120)
                else:
                    # Loop существует, но не запущен
                    response = loop.run_until_complete(llm_manager.generate_response(
                        prompt=check_prompt,
                        use_fastest=True,
                        use_parallel=False
                    ))
            except RuntimeError:
                # Нет event loop, создаем новый
                response = asyncio.run(llm_manager.generate_response(
                    prompt=check_prompt,
                    use_fastest=True,
                    use_parallel=False
                ))
            
            # Парсим ответ LLM
            # ВАЖНО: Даже если response.success = False, пытаемся использовать content если он есть
            content = response.content.strip() if response.content else ""
            model_name = getattr(response, 'model_name', 'unknown')
            
            logger.debug(f"Ответ LLM для проверки соответствия от модели {model_name}: {content[:300]}")
            
            if not response.success:
                if content:
                    logger.warning(
                        f"LLM вернул ошибку, но есть контент. Пытаемся использовать его. "
                        f"Модель: {model_name}, ошибка: {response.error}, контент: {content[:200]}..."
                    )
                else:
                    logger.warning(f"Не удалось выполнить проверку соответствия для задачи {task_id}: {response.error}")
                    return True, None  # Если проверка не удалась, считаем что соответствует
            
            if not content:
                logger.warning(
                    f"Пустой ответ LLM при проверке соответствия туду плану (task_id={task_id}, model={model_name})"
                )
                return True, None  # при пустом ответе не блокируем выполнение
            
            response_data = _extract_json_object(content)
            if response_data is None:
                # Последняя попытка — прямой json.loads (если ответ полностью JSON)
                try:
                    response_data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"Не удалось распарсить JSON ответ для проверки соответствия: {e}")
                    response_data = None
            
            if isinstance(response_data, dict) and "matches" in response_data:
                matches = response_data.get('matches', True)
                reason = response_data.get('reason', None)
                
                if not matches:
                    logger.info(f"Пункт туду '{todo_item.text[:50]}...' не соответствует плану: {reason}")
                    return False, reason
                else:
                    logger.debug(f"Пункт туду '{todo_item.text[:50]}...' соответствует плану")
                    return True, None
            
            # Если не нашли JSON, проверяем текстовый ответ
            content_lower = content.lower()
            if "не соответствует" in content_lower or "does not match" in content_lower or "false" in content_lower:
                reason = content[:200]  # Берем первые 200 символов как причину
                logger.info(f"Пункт туду не соответствует плану (по текстовому ответу): {reason}")
                return False, reason
            
            # По умолчанию считаем что соответствует
            logger.debug("Проверка соответствия завершена, считаем что соответствует")
            return True, None
            
        except ImportError:
            logger.warning("LLMManager не доступен, пропускаем проверку соответствия")
            return True, None
        except Exception as e:
            logger.error(f"Ошибка при проверке соответствия туду плану через LLMManager: {e}", exc_info=True)
            return True, None  # При ошибке считаем что соответствует
    
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
        all(indicator not in result_lower or "план" not in result_lower[:200] for indicator in plan_only_indicators)
        
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
        
        # Если есть индикаторы работы - считаем выполненным
        if has_work:
            logger.info(f"Обнаружены индикаторы выполненной работы для задачи {task_id}")
            return True
        
        # Если только план без реальной работы
        logger.warning(f"Для задачи {task_id} выполнен только план, реальная работа не обнаружена")
        return False
    
    def _should_use_cursor(self, todo_item: TodoItem) -> bool:
        """
        Определить, нужно ли использовать Cursor для задачи
        
        Args:
            todo_item: Элемент todo-листа
        
        Returns:
            True если нужно использовать Cursor, False для CrewAI
        """
        # По умолчанию используем Cursor для всех задач
        # Файловый интерфейс всегда доступен, CLI - если установлен
        cursor_config = self.config.get('cursor', {})
        prefer_cursor = cursor_config.get('prefer_cursor', True)
        
        # Используем Cursor если prefer_cursor=True (по умолчанию True)
        return prefer_cursor
    
    def _load_documentation(self) -> str:
        """
        Загрузка документации проекта из папки docs
        
        Returns:
            Контент документации в виде строки
        """
        if not self.docs_dir.exists():
            logger.warning(f"Директория документации не найдена: {self.docs_dir}")
            return ""
        
        docs_content = []
        supported_extensions = self.config.get('docs.supported_extensions', ['.md', '.txt'])
        max_file_size = self.config.get('docs.max_file_size', self.DEFAULT_MAX_FILE_SIZE)
        
        for file_path in self.docs_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                try:
                    file_size = file_path.stat().st_size
                    if file_size > max_file_size:
                        logger.warning(f"Файл слишком большой, пропущен: {file_path}")
                        continue
                    
                    content = file_path.read_text(encoding='utf-8')
                    docs_content.append(f"\n## {file_path.name}\n\n{content}\n")
                except Exception as e:
                    logger.error(f"Ошибка чтения файла {file_path}: {e}")
        
        return "\n".join(docs_content)
    
    def _create_task_for_agent(self, todo_item: TodoItem, documentation: str) -> Task:
        """
        Создание задачи CrewAI для агента
        
        Args:
            todo_item: Элемент todo-листа
            documentation: Документация проекта
        
        Returns:
            Задача CrewAI
        """
        # Формируем описание задачи с контекстом документации
        context = f"""Выполнить задачу проекта:

**Задача:** {todo_item.text}

**Контекст проекта:**
{documentation[:5000]}  # Ограничиваем размер контекста

**Инструкции:**
1. Изучите документацию проекта для понимания контекста
2. Выполните задачу согласно лучшим практикам проекта
3. Обновите статус выполнения в файле codeAgentProjectStatus.md
4. Убедитесь, что код соответствует стандартам проекта
"""
        
        task = Task(
            description=context,
            agent=self.agent,
            expected_output="Отчет о выполнении задачи с деталями и результатами"
        )
        
        return task
    
    def _execute_task(self, todo_item: TodoItem, task_number: int = 1, total_tasks: int = 1) -> bool:
        """
        Выполнение одной задачи через Cursor или CrewAI
        
        Args:
            todo_item: Элемент todo-листа для выполнения
            task_number: Номер задачи в текущей итерации
            total_tasks: Общее количество задач
        
        Returns:
            True если задача выполнена успешно
        """
        # Проверяем полезность задачи - является ли она реальной задачей или мусором
        logger.info(f"Проверка полезности задачи: '{todo_item.text[:60]}...'")
        usefulness_percent, usefulness_comment = self._check_task_usefulness(todo_item)
        
        # Выводим результат проверки в консоль с цветовым выделением
        if usefulness_percent < 15:
            color_status = "🔴 МУСОР"
            color = Colors.BRIGHT_RED
        elif usefulness_percent < 50:
            color_status = "🟡 СЛАБАЯ ПОЛЕЗНОСТЬ"
            color = Colors.BRIGHT_YELLOW
        elif usefulness_percent < 80:
            color_status = "🟢 СРЕДНЯЯ ПОЛЕЗНОСТЬ"
            color = Colors.BRIGHT_GREEN
        else:
            color_status = "✅ ВЫСОКАЯ ПОЛЕЗНОСТЬ"
            color = Colors.BRIGHT_GREEN
        
        usefulness_msg = f"Полезность задачи: {usefulness_percent:.1f}% - {color_status}"
        logger.info(Colors.colorize(usefulness_msg, color))
        if usefulness_comment:
            logger.info(f"  Комментарий: {usefulness_comment}")
        
        # Если полезность менее 15% - помечаем задачу как выполненную с комментарием
        if usefulness_percent < 15:
            skip_reason = f"Пропущено: низкая полезность ({usefulness_percent:.1f}%) - {usefulness_comment if usefulness_comment else 'мусор/шум в тексте'}"
            logger.warning(f"Задача имеет низкую полезность ({usefulness_percent:.1f}%), помечаем как выполненную: {skip_reason}")
            
            if self.todo_manager.mark_task_done(todo_item.text, comment=skip_reason):
                logger.info(f"✓ Задача '{todo_item.text[:50]}...' отмечена как пропущенная в TODO файле")
            else:
                logger.warning(f"Не удалось отметить задачу '{todo_item.text[:50]}...' как пропущенную в TODO файле")
            
            # Генерируем task_id для статуса
            task_id = f"task_{int(time.time())}"
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Пропущено",
                details=f"Пропущено: низкая полезность ({usefulness_percent:.1f}%). {usefulness_comment if usefulness_comment else 'Мусор/шум в тексте'} (task_id: {task_id})"
            )
            return False  # Задача пропущена, не выполняем
        
        # Проверяем, не была ли задача уже выполнена
        # ВАЖНО: Проверяем не только статус в checkpoint, но и реальное выполнение всех инструкций
        # Если выполнена только инструкция 1 (создание плана) - считаем задачу не выполненной
        is_completed_in_checkpoint = self.checkpoint_manager.is_task_completed(todo_item.text)
        if is_completed_in_checkpoint:
            # ВАЖНО: Проверяем последнюю попытку задачи - время выполнения и наличие результатов
            # Находим последнюю попытку задачи
            matching_tasks = [
                task for task in self.checkpoint_manager.checkpoint_data.get("tasks", [])
                if task.get("task_text") == todo_item.text and task.get("state") == "completed"
            ]
            
            last_completed_task = None
            last_time = None
            
            for task in matching_tasks:
                start_time_str = task.get("start_time")
                task.get("end_time")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        if last_time is None or start_time > last_time:
                            last_time = start_time
                            last_completed_task = task
                    except (ValueError, TypeError):
                        pass
            
            # Если нашли последнюю завершенную попытку, проверяем время выполнения
            execution_too_short = False
            if last_completed_task and last_completed_task.get("start_time") and last_completed_task.get("end_time"):
                try:
                    start_time = datetime.fromisoformat(last_completed_task.get("start_time"))
                    end_time = datetime.fromisoformat(last_completed_task.get("end_time"))
                    duration_minutes = (end_time - start_time).total_seconds() / 60
                    # Если выполнение заняло меньше 10 минут - скорее всего выполнена только инструкция 1
                    # (реальное выполнение 7-8 инструкций занимает минимум 20-30 минут)
                    if duration_minutes < 10:
                        execution_too_short = True
                        logger.warning(f"Последняя попытка задачи завершена за {duration_minutes:.1f} минут - слишком быстро для полного выполнения всех инструкций")
                except (ValueError, TypeError):
                    pass
            
            # Проверяем наличие файлов результатов других инструкций (не только планов)
            # Но учитываем, что файлы могут быть от других задач
            results_dir = self.project_dir / "docs" / "results"
            reviews_dir = self.project_dir / "docs" / "reviews"
            
            test_files = list(results_dir.glob("test*.md")) if results_dir.exists() else []
            review_files = list(reviews_dir.glob("skeptic_*.md")) if reviews_dir.exists() else []
            plan_result_files = list(results_dir.glob("plan_result_*.md")) if results_dir.exists() else []
            test_full_files = list(results_dir.glob("test_full_*.md")) if results_dir.exists() else []
            
            has_other_results = len(test_files) > 0 or len(review_files) > 0 or len(plan_result_files) > 0 or len(test_full_files) > 0
            
            # ВАЖНО: Если выполнение было слишком коротким, всегда перевыполняем, даже если есть файлы результатов
            # (файлы могли быть созданы другими задачами)
            if execution_too_short or not has_other_results:
                # Задача помечена как completed, но нет подтверждения выполнения всех инструкций
                reason = "выполнение слишком короткое" if execution_too_short else "нет файлов результатов инструкций 2-7"
                logger.warning(f"Задача помечена как completed, но {reason}. Перевыполняем со всеми инструкциями: {todo_item.text}")
                # Сбрасываем статус последней завершенной задачи в checkpoint для перевыполнения
                if last_completed_task:
                    last_completed_task["state"] = "pending"
                    logger.info(f"Статус задачи '{todo_item.text}' (task_id: {last_completed_task.get('task_id')}) сброшен с completed на pending для перевыполнения")
                    self.checkpoint_manager._save_checkpoint()
                # Продолжаем выполнение задачи (не возвращаем True)
            else:
                # Есть подтверждение выполнения других инструкций - задача действительно выполнена
                logger.info(f"Задача уже выполнена (пропуск): {todo_item.text}")
                return True
        
        # Логируем начало задачи
        self.server_logger.log_task_start(task_number, total_tasks, todo_item.text)
        logger.info(f"Выполнение задачи: {todo_item.text}")
        
        # Устанавливаем флаг активной задачи
        with self._task_in_progress_lock:
            self._task_in_progress = True
        
        # ВАЖНО: Проверяем, есть ли незавершенная задача с тем же текстом
        # Если есть, используем ее task_id для продолжения выполнения
        existing_task = None
        matching_tasks = [
            task for task in self.checkpoint_manager.checkpoint_data.get("tasks", [])
            if task.get("task_text") == todo_item.text 
            and task.get("state") in ["pending", "in_progress"]
        ]
        
        if matching_tasks:
            # Находим последнюю незавершенную задачу по времени начала
            last_time = None
            for task in matching_tasks:
                start_time_str = task.get("start_time")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        if last_time is None or start_time > last_time:
                            last_time = start_time
                            existing_task = task
                    except (ValueError, TypeError):
                        pass
            
            # Если не нашли задачу с start_time, берем последнюю в списке
            if existing_task is None and matching_tasks:
                existing_task = matching_tasks[-1]
        
        # Используем существующую задачу или создаем новую
        if existing_task:
            task_id = existing_task.get("task_id")
            existing_progress = existing_task.get("instruction_progress", {})
            last_completed = existing_progress.get("last_completed_instruction", 0) if existing_progress else 0
            logger.info(f"✓ Используем существующую незавершенную задачу: {task_id} (state: {existing_task.get('state')}, последняя инструкция: {last_completed})")
            
            # Если задача в состоянии PENDING, отмечаем начало выполнения
            if existing_task.get("state") == "pending":
                self.checkpoint_manager.mark_task_start(task_id)
        else:
            # Генерируем новый ID задачи
            task_id = f"task_{int(time.time())}"
            
            # Добавляем задачу в checkpoint
            self.checkpoint_manager.add_task(
                task_id=task_id,
                task_text=todo_item.text,
                metadata={
                    "task_number": task_number,
                    "total_tasks": total_tasks
                }
            )
            
            # Отмечаем начало выполнения
            self.checkpoint_manager.mark_task_start(task_id)
        
        # Создаем логгер для задачи
        task_logger = TaskLogger(task_id, todo_item.text)
        
        try:
            # Фаза: Анализ задачи
            task_logger.set_phase(TaskPhase.TASK_ANALYSIS)
            
            # Определяем тип задачи
            task_type = self._determine_task_type(todo_item)
            task_logger.log_debug(f"Тип задачи определен: {task_type}")
            
            # Определяем, использовать ли Cursor
            use_cursor = self._should_use_cursor(todo_item)
            task_logger.log_debug(f"Интерфейс: {'Cursor' if use_cursor else 'CrewAI'}")
            
            # Обновляем статус: задача начата
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="В процессе",
                details=f"Начало выполнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (тип: {task_type}, интерфейс: {'Cursor' if use_cursor else 'CrewAI'})"
            )
            
            if use_cursor:
                # Выполнение через Cursor
                result = self._execute_task_via_cursor(todo_item, task_type, task_logger)
                task_logger.log_completion(result, "Задача выполнена через Cursor")
                task_logger.close()
                
                # Проверяем флаг остановки после выполнения задачи
                with self._stop_lock:
                    if self._should_stop:
                        logger.warning("Получен запрос на остановку после выполнения задачи через Cursor")
                        # Отмечаем задачу как прерванную
                        self.checkpoint_manager.mark_task_failed(task_id, "Задача прервана из-за остановки сервера")
                        return False
                
                # Отмечаем в checkpoint
                if result:
                    self.checkpoint_manager.mark_task_completed(task_id)
                    # ВАЖНО: Отмечаем задачу как done в TODO файле
                    # mark_task_done() уже вызывает _save_todos() внутри
                    if self.todo_manager.mark_task_done(todo_item.text):
                        logger.info(f"✓ Задача '{todo_item.text}' отмечена как выполненная в TODO файле")
                    else:
                        logger.warning(f"Не удалось отметить задачу '{todo_item.text}' как выполненную в TODO файле")
                else:
                    self.checkpoint_manager.mark_task_failed(task_id, "Задача не выполнена через Cursor")
                
                return result
            else:
                # Выполнение через CrewAI (старый способ)
                result = self._execute_task_via_crewai(todo_item, task_logger)
                task_logger.log_completion(result, "Задача выполнена через CrewAI")
                task_logger.close()
                
                # Отмечаем в checkpoint
                if result:
                    self.checkpoint_manager.mark_task_completed(task_id)
                    # ВАЖНО: Отмечаем задачу как done в TODO файле
                    self.todo_manager.mark_task_done(todo_item.text)
                    logger.debug(f"Задача '{todo_item.text}' отмечена как выполненная в TODO файле")
                else:
                    self.checkpoint_manager.mark_task_failed(task_id, "Задача не выполнена через CrewAI")
                
                return result
            
        except ServerReloadException:
            # Перезапуск из-за изменений в коде - пробрасываем дальше
            logger.warning(f"Перезапуск сервера во время выполнения задачи {task_id}")
            task_logger.log_warning("Перезапуск сервера - задача будет прервана")
            task_logger.close()
            # Отмечаем задачу как прерванную
            self.checkpoint_manager.mark_task_failed(task_id, "Задача прервана из-за перезапуска сервера")
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Прервано",
                details="Задача прервана из-за перезапуска сервера"
            )
            # Сбрасываем флаг активной задачи
            with self._task_in_progress_lock:
                self._task_in_progress = False
            raise  # Пробрасываем исключение дальше
            
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи '{todo_item.text}': {e}", exc_info=True)
            
            # Логируем ошибку
            task_logger.log_error("Критическая ошибка при выполнении задачи", e)
            task_logger.log_completion(False, f"Ошибка: {str(e)}")
            task_logger.close()
            
            # Отмечаем ошибку в checkpoint
            self.checkpoint_manager.mark_task_failed(task_id, str(e))
            
            # Обновляем статус: ошибка
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Ошибка",
                details=f"Ошибка: {str(e)}"
            )
            # Сбрасываем флаг активной задачи
            with self._task_in_progress_lock:
                self._task_in_progress = False
            return False
        finally:
            # Всегда сбрасываем флаг активной задачи при завершении
            with self._task_in_progress_lock:
                self._task_in_progress = False
            
            # Проверяем, был ли запрошен перезапуск во время выполнения задачи
            # Если да, инициируем его после завершения задачи
            with self._reload_lock:
                if self._should_reload:
                    logger.warning("=" * 80)
                    logger.warning("ОБНАРУЖЕН ОТЛОЖЕННЫЙ ПЕРЕЗАПУСК - ЗАДАЧА ЗАВЕРШЕНА")
                    logger.warning("Перезапуск будет выполнен на следующей проверке")
                    logger.warning("=" * 80)
                    # Не сбрасываем флаг здесь - он будет обработан в run_iteration или start()
    
    def _execute_task_via_cursor(self, todo_item: TodoItem, task_type: str, task_logger: TaskLogger) -> bool:
        """
        Выполнение задачи через Cursor (CLI или файловый интерфейс)
        
        Args:
            todo_item: Элемент todo-листа
            task_type: Тип задачи
            task_logger: Логгер задачи
        
        Returns:
            True если задача выполнена успешно
        """
        # Генерируем ID задачи
        task_id = task_logger.task_id
        
        # Фаза: Генерация инструкции
        task_logger.set_phase(TaskPhase.INSTRUCTION_GENERATION)
        
        # Получаем ВСЕ инструкции для последовательного выполнения (1-8)
        all_templates = self._get_all_instruction_templates(task_type)
        
        if not all_templates:
            logger.warning(f"Инструкции для типа '{task_type}' не найдены, используется базовый шаблон")
            task_logger.log_debug("Инструкции не найдены, используется базовый")
            # Используем базовый шаблон
            all_templates = [{
                'instruction_id': 1,
                'template': f'Выполни задачу: "{todo_item.text}"\n\nСоздай отчет в docs/results/last_result.md, в конце напиши "Отчет завершен!"',
                'wait_for_file': 'docs/results/last_result.md',
                'control_phrase': 'Отчет завершен!',
                'timeout': 600
            }]
        
        logger.info(f"Найдено {len(all_templates)} инструкций для последовательного выполнения")
        task_logger.log_info(f"Последовательное выполнение {len(all_templates)} инструкций")
        
        # Проверяем соответствие туду плану (если план уже существует)
        # Это проверка выполняется только если план был создан ранее
        plan_file = self.project_dir / "docs" / "results" / f"current_plan_{task_id}.md"
        if plan_file.exists():
            logger.info(f"Проверка соответствия туду плану для задачи {task_id}")
            task_logger.log_info("Проверка соответствия туду плану")
            
            matches_plan, reason = self._check_todo_matches_plan(task_id, todo_item)
            
            if not matches_plan:
                logger.warning(f"Пункт туду '{todo_item.text}' не соответствует плану: {reason}")
                task_logger.log_warning(f"Пункт туду не соответствует плану: {reason}")
                
                # Отмечаем задачу как выполненную с комментарием о пропуске
                skip_reason = f"Пропущено по причине: {reason}" if reason else "Пропущено по причине: не соответствует плану"
                if self.todo_manager.mark_task_done(todo_item.text, comment=skip_reason):
                    logger.info(f"✓ Задача '{todo_item.text}' отмечена как пропущенная в TODO файле")
                    task_logger.log_info(f"Задача пропущена: {skip_reason}")
                else:
                    logger.warning(f"Не удалось отметить задачу '{todo_item.text}' как пропущенную в TODO файле")
                
                self.status_manager.update_task_status(
                    task_name=todo_item.text,
                    status="Пропущено",
                    details=f"Пропущено: не соответствует плану. {reason if reason else ''} (task_id: {task_id})"
                )
                return False  # Задача пропущена, не выполняем
        
        # Проверяем, есть ли сохраненный прогресс выполнения инструкций для этой задачи
        # Сначала проверяем текущий task_id, затем ищем последнюю попытку с тем же текстом
        instruction_progress = self.checkpoint_manager.get_instruction_progress(task_id)
        start_from_instruction = 1
        
        logger.debug(f"Проверка прогресса инструкций для задачи {task_id}: {instruction_progress}")
        
        # Если для текущего task_id нет прогресса, ищем последнюю попытку с тем же текстом задачи
        if not instruction_progress or instruction_progress.get("last_completed_instruction", 0) == 0:
            # Ищем последнюю попытку задачи с тем же текстом (исключая текущий task_id)
            matching_tasks = [
                task for task in self.checkpoint_manager.checkpoint_data.get("tasks", [])
                if task.get("task_text") == todo_item.text and task.get("task_id") != task_id
            ]
            
            logger.debug(f"Найдено {len(matching_tasks)} предыдущих попыток задачи '{todo_item.text[:50]}...'")
            
            if matching_tasks:
                # Находим последнюю задачу по времени начала (start_time)
                last_task = None
                last_time = None
                
                for task in matching_tasks:
                    start_time_str = task.get("start_time")
                    if start_time_str:
                        try:
                            start_time = datetime.fromisoformat(start_time_str)
                            if last_time is None or start_time > last_time:
                                last_time = start_time
                                last_task = task
                        except (ValueError, TypeError):
                            pass
                
                # Если не нашли задачу с start_time, берем последнюю в списке
                if last_task is None and matching_tasks:
                    last_task = matching_tasks[-1]
                    logger.debug(f"Не найдена задача с start_time, берем последнюю в списке: {last_task.get('task_id')}")
                
                # Если нашли последнюю задачу, проверяем ее прогресс
                if last_task:
                    last_progress = last_task.get("instruction_progress", {})
                    last_completed = last_progress.get("last_completed_instruction", 0) if last_progress else 0
                    last_state = last_task.get("state", "unknown")
                    logger.info(f"Последняя попытка: task_id={last_task.get('task_id')}, state={last_state}, last_completed={last_completed}, total={last_progress.get('total_instructions', 0) if last_progress else 0}")
                    
                    if last_progress and last_completed > 0:
                        instruction_progress = last_progress
                        logger.info(f"✓ Найден прогресс из предыдущей попытки задачи (task_id: {last_task.get('task_id')}, state: {last_state}, последняя инструкция: {last_completed})")
                        
                        # ВАЖНО: Копируем прогресс в текущую задачу, чтобы он сохранялся при следующих перезапусках
                        current_task = self.checkpoint_manager._find_task(task_id)
                        if current_task:
                            current_task["instruction_progress"] = last_progress.copy()
                            self.checkpoint_manager._save_checkpoint(create_backup=False)
                            logger.debug(f"Прогресс инструкций скопирован в текущую задачу {task_id}")
                    else:
                        logger.debug("У предыдущей попытки нет прогресса инструкций или прогресс пустой")
        
        if instruction_progress and instruction_progress.get("last_completed_instruction", 0) > 0:
            last_completed = instruction_progress.get("last_completed_instruction", 0)
            total_saved = instruction_progress.get("total_instructions", 0)
            
            logger.info(f"Восстановление прогресса: последняя выполненная инструкция={last_completed}, всего инструкций={total_saved}, текущее количество={len(all_templates)}")
            
            # Если количество инструкций совпадает, продолжаем с последней выполненной + 1
            if total_saved == len(all_templates) and last_completed < len(all_templates):
                start_from_instruction = last_completed + 1
                logger.info(f"✓ Восстановление прогресса: продолжаем с инструкции {start_from_instruction}/{len(all_templates)} (последняя выполненная: {last_completed})")
                task_logger.log_info(f"Восстановление прогресса: продолжаем с инструкции {start_from_instruction}")
            elif total_saved != len(all_templates):
                # Количество инструкций изменилось - начинаем сначала
                logger.warning(f"Количество инструкций изменилось ({total_saved} -> {len(all_templates)}), начинаем сначала")
                task_logger.log_warning("Количество инструкций изменилось, начинаем сначала")
                start_from_instruction = 1
            else:
                # Все инструкции уже выполнены
                logger.info(f"Все инструкции уже выполнены ({last_completed}/{total_saved}), начинаем сначала")
                start_from_instruction = 1
        else:
            logger.debug("Прогресс инструкций не найден или пустой, начинаем с инструкции 1")
        
        # Проверяем доступность CLI
        if not self.use_cursor_cli:
            logger.error(f"Cursor CLI недоступен для задачи {task_id}")
            task_logger.log_error("Cursor CLI недоступен")
            return False
        
        # КРИТИЧНО: Останавливаем активные диалоги и очищаем очередь перед новой задачей
        logger.debug(f"Подготовка к задаче {task_id}: остановка активных диалогов...")
        
        if self.cursor_cli:
            cleanup_result = self.cursor_cli.prepare_for_new_task()
            if not cleanup_result:
                logger.warning("Не удалось полностью очистить активные диалоги, продолжаем...")
        
        # Логируем создание нового диалога (один раз для всей последовательности)
        # Chat ID будет получен после выполнения первой инструкции
        task_logger.log_new_chat()
        
        # Отслеживаем успешно выполненные инструкции
        successful_instructions = 0
        failed_instructions = 0
        critical_instructions = min(3, len(all_templates))  # Минимум 3 инструкции для завершения задачи
        first_instruction_executed = False  # Флаг для логирования chat_id после первой инструкции
        
        # Выполняем все инструкции последовательно (1, 2, 3, ...)
        # Начинаем с start_from_instruction если есть сохраненный прогресс
        for instruction_num, template in enumerate(all_templates, start=1):
            # Получаем информацию об инструкции для логирования
            instruction_id = template.get('instruction_id', instruction_num)
            instruction_name = template.get('name', f'Инструкция {instruction_id}')
            
            # Пропускаем уже выполненные инструкции
            if instruction_num < start_from_instruction:
                logger.info(f"Пропуск инструкции {instruction_num}/{len(all_templates)}: {instruction_name} (уже выполнена)")
                task_logger.log_info(f"Пропуск инструкции {instruction_num}: {instruction_name} (уже выполнена)")
                successful_instructions += 1  # Учитываем уже выполненную инструкцию
                continue
            # Проверяем запрос на остановку перед каждой инструкцией
            with self._stop_lock:
                if self._should_stop:
                    logger.warning(f"Получен запрос на остановку во время выполнения задачи {task_id}")
                    task_logger.log_warning("Запрос на остановку сервера - прерывание выполнения задачи")
                    self.status_manager.update_task_status(
                        task_name=todo_item.text,
                        status="Прервано",
                        details="Выполнение прервано по запросу остановки сервера"
                    )
                    return False
            
            # Проверяем необходимость перезапуска перед каждой инструкцией
            if self._check_reload_needed():
                logger.warning(f"Обнаружено изменение кода во время выполнения задачи {task_id}")
                task_logger.log_warning("Обнаружено изменение кода - требуется перезапуск")
                self.status_manager.update_task_status(
                    task_name=todo_item.text,
                    status="Прервано",
                    details="Выполнение прервано из-за изменения кода (требуется перезапуск)"
                )
                # Инициируем перезапуск
                raise ServerReloadException("Перезапуск из-за изменения кода во время выполнения задачи")
            
            logger.info(f"[{instruction_num}/{len(all_templates)}] Выполнение инструкции: {instruction_name} (ID: {instruction_id})")
            task_logger.log_info(f"Инструкция {instruction_num}/{len(all_templates)}: {instruction_name}")
            
            # Форматируем инструкцию из шаблона
            instruction_text = self._format_instruction(template, todo_item, task_id, instruction_num)
            wait_for_file = template.get('wait_for_file', '')
            control_phrase = template.get('control_phrase', '')
            timeout = template.get('timeout', 600)
            
            # Подстановка переменных в wait_for_file
            original_wait_for_file = wait_for_file
            if wait_for_file:
                wait_for_file = wait_for_file.replace('{task_id}', task_id)
                wait_for_file = wait_for_file.replace('{date}', datetime.now().strftime('%Y%m%d'))
                wait_for_file = wait_for_file.replace('{plan_item_number}', str(instruction_num))
                logger.debug(f"Инструкция {instruction_num}: wait_for_file '{original_wait_for_file}' -> '{wait_for_file}'")
            else:
                logger.warning(f"⚠️ Инструкция {instruction_num}: wait_for_file не указан в шаблоне!")
            
            # Логируем инструкцию
            task_logger.log_instruction(instruction_num, instruction_text, task_type)
            logger.debug(f"Инструкция {instruction_num} для Cursor: {instruction_text[:200]}...")
            
            # ВАЖНО: Перед инструкцией коммита (instruction_id 8) сохраняем TODO файл с отмеченными задачами
            # Это нужно, чтобы изменения в TODO попали в коммит
            if instruction_id == 8:
                logger.info("Инструкция 8 (коммит) - сохраняем TODO файл с отмеченными задачами перед коммитом")
                try:
                    # Отмечаем текущую задачу как выполненную в TODO файле с комментарием
                    # Комментарий будет добавлен позже при полном завершении, здесь только предварительная отметка
                    if not self.todo_manager.mark_task_done(todo_item.text, comment="Выполняется"):
                        logger.warning(f"Не удалось отметить задачу '{todo_item.text}' как выполненную в TODO файле")
                    else:
                        logger.info(f"✓ Задача '{todo_item.text}' отмечена как выполненная в TODO файле")
                    
                    # Сохраняем TODO файл
                    self.todo_manager._save_todos()
                    logger.info(f"✓ TODO файл сохранен: {self.todo_manager.todo_file}")
                    
                    # Также синхронизируем с checkpoint для полноты
                    self._sync_todos_with_checkpoint()
                except Exception as e:
                    logger.error(f"Ошибка при сохранении TODO файла перед коммитом: {e}", exc_info=True)
                    # Не прерываем выполнение из-за ошибки сохранения TODO
            
            # Фаза: Выполнение через Cursor
            task_logger.set_phase(TaskPhase.CURSOR_EXECUTION, stage=instruction_num, instruction_num=instruction_num)
            
            # Сохраняем время начала выполнения инструкции для корректного расчета времени
            instruction_start_time = time.time()
            
            # Используем Cursor CLI для выполнения инструкции с обработкой повторяющихся ошибок
            result = self._execute_cursor_instruction_with_retry(
                instruction=instruction_text,
                task_id=task_id,
                timeout=timeout,
                task_logger=task_logger,
                instruction_num=instruction_num
            )
            
            # Логируем ответ от Cursor
            task_logger.log_cursor_response(result, brief=True)
            
            # Логируем chat_id после выполнения первой инструкции (если еще не залогирован)
            if not first_instruction_executed and self.cursor_cli and self.cursor_cli.current_chat_id:
                chat_id = self.cursor_cli.current_chat_id
                logger.info(f"💬 ID диалога: {chat_id}")
                task_logger.log_new_chat(chat_id)  # Обновляем лог с chat_id
                first_instruction_executed = True
            
            # ДОПОЛНИТЕЛЬНОЕ ЛОГИРОВАНИЕ для диагностики
            logger.debug(f"Результат выполнения инструкции {instruction_num}: success={result.get('success')}, wait_for_file='{wait_for_file}', control_phrase='{control_phrase}'")
            
            if not result.get("success"):
                failed_instructions += 1
                error_message = result.get('error_message', 'Неизвестная ошибка')
                logger.warning(f"Инструкция {instruction_num}/{len(all_templates)} завершилась с ошибкой: {error_message}")
                task_logger.log_error(f"Инструкция {instruction_num} не выполнена: {error_message}")
                
                # Обрабатываем повторяющиеся ошибки
                can_continue = self._handle_cursor_error(error_message, task_logger)
                
                # Проверяем флаг остановки после обработки ошибки
                with self._stop_lock:
                    if self._should_stop:
                        logger.error("=" * 80)
                        logger.error("СЕРВЕР ОСТАНОВЛЕН ИЗ-ЗА КРИТИЧЕСКИХ ОШИБОК CURSOR")
                        logger.error("=" * 80)
                        task_logger.log_error("Критическая ошибка Cursor - выполнение задачи прервано", Exception(error_message))
                        self.status_manager.update_task_status(
                            task_name=todo_item.text,
                            status="Прервано",
                            details=f"Критическая ошибка Cursor: {error_message}"
                        )
                        return False
                
                if not can_continue:
                    # Критическая ошибка - сервер должен быть остановлен
                    logger.error("=" * 80)
                    logger.error("КРИТИЧЕСКАЯ ОШИБКА CURSOR - ПРЕРЫВАНИЕ ВЫПОЛНЕНИЯ ЗАДАЧИ")
                    logger.error("=" * 80)
                    task_logger.log_error("Критическая ошибка Cursor - выполнение задачи прервано", Exception(error_message))
                    self.status_manager.update_task_status(
                        task_name=todo_item.text,
                        status="Прервано",
                        details=f"Критическая ошибка Cursor: {error_message}"
                    )
                    # Убеждаемся, что флаг остановки установлен
                    with self._stop_lock:
                        if not self._should_stop:
                            logger.warning("Флаг остановки не был установлен, устанавливаем вручную")
                            self._should_stop = True
                    return False
                
                # Проверяем флаг остановки перед задержкой
                with self._stop_lock:
                    if self._should_stop:
                        logger.warning("Получен запрос на остановку после обработки ошибки Cursor")
                        return False
                
                # Применяем задержку перед следующей попыткой (накопленная задержка из-за ошибок)
                # Но проверяем флаг остановки во время задержки
                if self._cursor_error_delay > 0:
                    logger.info(f"Ожидание {self._cursor_error_delay} секунд перед следующей инструкцией (из-за предыдущих ошибок Cursor)")
                    task_logger.log_info(f"Задержка {self._cursor_error_delay} сек перед следующей инструкцией из-за ошибок Cursor")
                    
                    # Проверяем флаг остановки во время задержки
                    for i in range(self._cursor_error_delay):
                        with self._stop_lock:
                            if self._should_stop:
                                logger.warning(f"Получен запрос на остановку во время задержки из-за ошибок Cursor (через {i+1} секунд)")
                                return False
                        time.sleep(1)
                
                # Проверяем флаг остановки после задержки
                with self._stop_lock:
                    if self._should_stop:
                        logger.warning("Получен запрос на остановку после задержки из-за ошибок Cursor")
                        return False
                
                # Проверяем необходимость перезапуска после завершения текущей инструкции (с ошибкой)
                with self._reload_lock:
                    if self._reload_after_instruction:
                        logger.info(f"Инструкция {instruction_num} завершена (с ошибкой) - инициируем перезапуск из-за изменения кода")
                        task_logger.log_warning("Перезапуск после завершения инструкции из-за изменения кода")
                        self.status_manager.update_task_status(
                            task_name=todo_item.text,
                            status="Прервано",
                            details=f"Перезапуск после инструкции {instruction_num} из-за изменения кода"
                        )
                        raise ServerReloadException("Перезапуск из-за изменения кода после завершения инструкции")
                
                # Продолжаем со следующей инструкцией (некоторые могут быть опциональными)
                continue
            else:
                # Успешное выполнение - проверяем, был ли использован fallback
                fallback_used = result.get('fallback_used', False)
                primary_model_failed = result.get('primary_model_failed', False)
                
                if fallback_used or primary_model_failed:
                    # Fallback был использован - это признак проблемы с основной моделью
                    # Увеличиваем счетчик ошибок, даже если fallback помог
                    error_message = "Основная модель не смогла выполнить команду, использован fallback"
                    logger.warning("⚠️ Fallback использован для успешного выполнения - это признак проблемы с основной моделью")
                    can_continue = self._handle_cursor_error(error_message, task_logger)
                    
                    if not can_continue:
                        # Критическая ситуация - слишком много использований fallback
                        logger.error("=" * 80)
                        logger.error("КРИТИЧЕСКАЯ СИТУАЦИЯ: Слишком часто используется fallback")
                        logger.error("=" * 80)
                        task_logger.log_error("Критическая ситуация: слишком часто используется fallback", Exception(error_message))
                        self.status_manager.update_task_status(
                            task_name=todo_item.text,
                            status="Прервано",
                            details="Критическая ситуация: слишком часто используется fallback"
                        )
                        return False
                else:
                    # Успешное выполнение без fallback - сбрасываем счетчик ошибок
                    with self._cursor_error_lock:
                        if self._cursor_error_count > 0:
                            logger.info(f"Инструкция выполнена успешно, счетчик ошибок Cursor сброшен (было {self._cursor_error_count})")
                            self._cursor_error_count = 0
                            self._cursor_error_delay = 0
                            self._last_cursor_error = None
            
            # Инструкция выполнена успешно на уровне команды - проверяем ожидание результата
            instruction_successful = False
            
            # Проверяем запрос на остановку перед ожиданием результата
            with self._stop_lock:
                if self._should_stop:
                    logger.warning(f"Получен запрос на остановку перед ожиданием результата для инструкции {instruction_num}")
                    task_logger.log_warning("Запрос на остановку - прерывание ожидания результата")
                    break
            
            # Проверяем необходимость перезапуска перед ожиданием результата
            if self._check_reload_needed():
                logger.warning(f"Обнаружено изменение кода перед ожиданием результата для инструкции {instruction_num}")
                task_logger.log_warning("Обнаружено изменение кода - требуется перезапуск")
                raise ServerReloadException("Перезапуск из-за изменения кода перед ожиданием результата")
            
            # Фаза: Ожидание результата (если указан wait_for_file)
            wait_result = None
            if wait_for_file:
                logger.info(f"Начинаем ожидание файла результата для инструкции {instruction_num}: {wait_for_file}")
                task_logger.set_phase(TaskPhase.WAITING_RESULT, stage=instruction_num, instruction_num=instruction_num)
                task_logger.log_waiting_result(wait_for_file, timeout)
                
                wait_result = self._wait_for_result_file(
                    task_id=task_id,
                    wait_for_file=wait_for_file,
                    control_phrase=control_phrase,
                    timeout=timeout
                )
                
                logger.debug(f"Результат ожидания файла для инструкции {instruction_num}: success={wait_result.get('success')}, error={wait_result.get('error')}")
                
                # Проверяем, была ли остановка или перезапуск во время ожидания
                if wait_result.get("error") == "Остановка сервера по запросу":
                    logger.warning("Ожидание результата прервано по запросу остановки")
                    task_logger.log_warning("Ожидание результата прервано по запросу остановки")
                    break
                elif wait_result.get("error") == "Перезапуск сервера из-за изменения кода":
                    logger.warning("Ожидание результата прервано из-за изменения кода")
                    task_logger.log_warning("Ожидание результата прервано - требуется перезапуск")
                    raise ServerReloadException("Перезапуск из-за изменения кода во время ожидания результата")
                
                if wait_result and wait_result.get("success"):
                    result_content = wait_result.get("content", "")
                    # ВАЖНО: Используем реальное время выполнения инструкции (с момента начала выполнения),
                    # а не только время ожидания файла (которое может быть 0.0 если файл уже существовал)
                    instruction_execution_time = time.time() - instruction_start_time
                    # Используем большее значение: либо время ожидания файла, либо время выполнения инструкции
                    actual_wait_time = max(wait_result['wait_time'], instruction_execution_time)
                    task_logger.log_result_received(
                        wait_result['file_path'],
                        actual_wait_time,
                        result_content[:500],
                        execution_time=instruction_execution_time if instruction_execution_time > wait_result['wait_time'] else None
                    )
                    logger.info(f"Файл результата получен для инструкции {instruction_num}: {wait_result['file_path']}")
                    instruction_successful = True
                    
                    # После первой инструкции (создание плана) проверяем соответствие туду плану
                    if instruction_num == 1:
                        plan_file = self.project_dir / "docs" / "results" / f"current_plan_{task_id}.md"
                        if plan_file.exists():
                            logger.info(f"План создан, проверяем соответствие туду плану для задачи {task_id}")
                            task_logger.log_info("Проверка соответствия туду плану после создания плана")
                            
                            matches_plan, reason = self._check_todo_matches_plan(task_id, todo_item)
                            
                            if not matches_plan:
                                logger.warning(f"Пункт туду '{todo_item.text}' не соответствует созданному плану: {reason}")
                                task_logger.log_warning(f"Пункт туду не соответствует плану: {reason}")
                                
                                # Отмечаем задачу как выполненную с комментарием о пропуске
                                skip_reason = f"Пропущено по причине: {reason}" if reason else "Пропущено по причине: не соответствует плану"
                                if self.todo_manager.mark_task_done(todo_item.text, comment=skip_reason):
                                    logger.info(f"✓ Задача '{todo_item.text}' отмечена как пропущенная в TODO файле")
                                    task_logger.log_info(f"Задача пропущена: {skip_reason}")
                                else:
                                    logger.warning(f"Не удалось отметить задачу '{todo_item.text}' как пропущенную в TODO файле")
                                
                                self.status_manager.update_task_status(
                                    task_name=todo_item.text,
                                    status="Пропущено",
                                    details=f"Пропущено: не соответствует плану. {reason if reason else ''} (task_id: {task_id})"
                                )
                                return False  # Задача пропущена, не выполняем остальные инструкции
                    
                    # Для последней инструкции проверяем, была ли выполнена реальная работа
                    if instruction_num == len(all_templates):
                        work_done = self._verify_real_work_done(task_id, todo_item, result_content)
                        if not work_done and instruction_num == 1:  # Только для первой инструкции требуем реальную работу
                            logger.warning(f"Инструкция {instruction_num} выполнила только план, реальная работа не обнаружена")
                            task_logger.log_warning("Выполнен только план, реальная работа не обнаружена")
                            # Продолжаем со следующими инструкциями - они могут выполнить реальную работу
                else:
                    logger.warning(f"Файл результата для инструкции {instruction_num} не получен: {wait_result.get('error')}")
                    task_logger.log_warning(f"Файл результата не получен для инструкции {instruction_num}")
                    # Инструкция не считается успешной если файл результата не получен
                    
                    # Проверяем необходимость перезапуска после завершения текущей инструкции
                    with self._reload_lock:
                        if self._reload_after_instruction:
                            logger.info(f"Инструкция {instruction_num} завершена (с ошибкой) - инициируем перезапуск из-за изменения кода")
                            task_logger.log_warning("Перезапуск после завершения инструкции из-за изменения кода")
                            self.status_manager.update_task_status(
                                task_name=todo_item.text,
                                status="Прервано",
                                details=f"Перезапуск после инструкции {instruction_num} из-за изменения кода"
                            )
                            raise ServerReloadException("Перезапуск из-за изменения кода после завершения инструкции")
                    
                    continue
            else:
                # Если wait_for_file не указан, считаем инструкцию успешной если команда выполнена успешно
                instruction_successful = True
            
            if instruction_successful:
                successful_instructions += 1
                logger.info(f"Инструкция {instruction_num}/{len(all_templates)} выполнена успешно")
                
                # Сохраняем прогресс выполнения инструкций в checkpoint
                self.checkpoint_manager.update_instruction_progress(
                    task_id=task_id,
                    instruction_num=instruction_num,
                    total_instructions=len(all_templates)
                )
                
                # Автоматический push после успешного выполнения инструкции с контрольной фразой "Коммит выполнен!"
                # Это работает для инструкции 8 (default) и инструкции 6 (revision)
                if control_phrase and control_phrase.strip() == "Коммит выполнен!":
                    logger.info(f"Инструкция {instruction_num} с коммитом выполнена успешно - выполняем автоматический push из сервера")
                    task_logger.log_info("Автоматический push после успешного коммита")

                    try:
                        # Получаем настройки smart_git из конфигурации
                        git_config = self.config.get('git', {})
                        smart_git_config = git_config.get('smart_git', {})
                        allowed_branches = smart_git_config.get('allowed_branches', ['smart'])
                        push_timeout = smart_git_config.get('auto_push_timeout', 60)

                        push_result = auto_push_after_commit(
                            working_dir=Path(self.project_dir),
                            remote="origin",
                            timeout=push_timeout,
                            allowed_branches=allowed_branches
                        )
                        
                        if push_result.get("success"):
                            logger.info(f"✅ Автоматический push выполнен успешно: {push_result.get('branch')} -> origin/{push_result.get('branch')}")
                            task_logger.log_info(f"Push выполнен: {push_result.get('branch')}")

                            commit_info = push_result.get("commit_info")
                            if commit_info:
                                logger.info(f"Коммит: {commit_info.get('hash_short')} - {commit_info.get('message')}")
                        elif not push_result.get("push_allowed", True):
                            # Push не разрешен для данной ветки - это не ошибка
                            branch = push_result.get('branch', 'неизвестная')
                            logger.info(f"ℹ️ Автоматический push пропущен: ветка '{branch}' не разрешена для авто-push")
                            task_logger.log_info(f"Push пропущен: ветка '{branch}' не в списке разрешенных")
                        else:
                            error_msg = push_result.get("error", "Неизвестная ошибка")
                            logger.warning(f"⚠️ Автоматический push не удался: {error_msg}")
                            task_logger.log_warning(f"Push не удался: {error_msg}")

                            # Push не удался, но это не критично - коммит уже создан
                            # Логируем предупреждение, но не прерываем выполнение задачи
                    except Exception as e:
                        logger.error(f"Ошибка при автоматическом push: {e}", exc_info=True)
                        task_logger.log_error("Ошибка при автоматическом push", e)
                        # Не прерываем выполнение задачи из-за ошибки push
            
            # Проверяем необходимость перезапуска после завершения текущей инструкции
            with self._reload_lock:
                if self._reload_after_instruction:
                    logger.info(f"Инструкция {instruction_num} завершена - инициируем перезапуск из-за изменения кода")
                    task_logger.log_warning("Перезапуск после завершения инструкции из-за изменения кода")
                    self.status_manager.update_task_status(
                        task_name=todo_item.text,
                        status="Прервано",
                        details=f"Перезапуск после инструкции {instruction_num} из-за изменения кода"
                    )
                    raise ServerReloadException("Перезапуск из-за изменения кода после завершения инструкции")
        
        # Фаза: Завершение - проверяем, достаточно ли инструкций выполнено
        task_logger.set_phase(TaskPhase.COMPLETION)
        
        # ВАЖНО: Задача считается выполненной только если выполнено минимум critical_instructions инструкций
        # Если выполнена только инструкция 1 (план), задача НЕ считается выполненной
        if successful_instructions < critical_instructions:
            logger.warning(f"Задача {task_id} не выполнена полностью: выполнено только {successful_instructions}/{len(all_templates)} инструкций (требуется минимум {critical_instructions})")
            task_logger.log_warning(f"Выполнено только {successful_instructions} из {len(all_templates)} инструкций")
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Частично выполнено",
                details=f"Выполнено только {successful_instructions}/{len(all_templates)} инструкций. Требуется минимум {critical_instructions} для завершения (task_id: {task_id})"
            )
            # НЕ отмечаем задачу как выполненную, возвращаем False
            return False
        
        # Отмечаем задачу как выполненную только если выполнено достаточно инструкций
        # ВАЖНО: mark_task_done() уже вызывает _save_todos() внутри
        # Добавляем краткий комментарий о выполнении
        completion_comment = f"Выполнено успешно ({successful_instructions}/{len(all_templates)} инструкций)"
        if self.todo_manager.mark_task_done(todo_item.text, comment=completion_comment):
            logger.info(f"✓ Задача '{todo_item.text}' отмечена как выполненная в TODO файле (после выполнения всех инструкций)")
        else:
            logger.warning(f"Не удалось отметить задачу '{todo_item.text}' как выполненную в TODO файле")
        
        self.status_manager.update_task_status(
            task_name=todo_item.text,
            status="Выполнено",
            details=f"Выполнено через Cursor CLI, успешно выполнено {successful_instructions}/{len(all_templates)} инструкций (task_id: {task_id})"
        )
        
        logger.info(f"Задача {task_id} выполнена: успешно выполнено {successful_instructions}/{len(all_templates)} инструкций")
        return True
        
        # Если CLI недоступен - возвращаем ошибку (НЕ используем файловый интерфейс)
        logger.error(f"Cursor CLI недоступен для задачи {task_id}")
        task_logger.log_error("Cursor CLI недоступен")
        
        self.status_manager.update_task_status(
            task_name=todo_item.text,
            status="Ошибка",
            details="Cursor CLI недоступен"
        )
        return False
        
        # УДАЛЕНО: Код файлового интерфейса (fallback отключен)
        # Файловый интерфейс требует ручного выполнения, что не допускается при автоматической работе
    
    def _execute_task_via_crewai(self, todo_item: TodoItem, task_logger: TaskLogger) -> bool:
        """
        Выполнение задачи через CrewAI (старый способ, fallback)
        
        Args:
            todo_item: Элемент todo-листа для выполнения
            task_logger: Логгер задачи
        
        Returns:
            True если задача выполнена успешно
        """
        logger.info(f"Выполнение задачи через CrewAI: {todo_item.text}")
        task_logger.log_info("Выполнение через CrewAI")
        
        # Загружаем документацию
        task_logger.set_phase(TaskPhase.TASK_ANALYSIS)
        documentation = self._load_documentation()
        
        # Создаем задачу для агента
        task_logger.set_phase(TaskPhase.INSTRUCTION_GENERATION)
        task = self._create_task_for_agent(todo_item, documentation)
        
        # Создаем crew и выполняем задачу
        task_logger.set_phase(TaskPhase.CURSOR_EXECUTION)
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Логируем результат
        task_logger.log_cursor_response({
            'success': True,
            'stdout': str(result),
            'return_code': 0
        }, brief=True)
        
        # Обновляем статус: задача выполнена
        result_summary = str(result)[:500]  # Ограничиваем размер
        self.status_manager.update_task_status(
            task_name=todo_item.text,
            status="Выполнено",
            details=f"Результат: {result_summary}"
        )
        
        # Отмечаем задачу как выполненную
        self.todo_manager.mark_task_done(todo_item.text)
        
        task_logger.set_phase(TaskPhase.COMPLETION)
        logger.info(f"Задача выполнена через CrewAI: {todo_item.text}")
        return True
    
    def _execute_revision(self) -> bool:
        """
        Выполнение ревизии проекта через Cursor
        
        Returns:
            True если ревизия успешна, False иначе
        """
        logger.info("=" * 80)
        logger.info("НАЧАЛО РЕВИЗИИ ПРОЕКТА")
        logger.info("=" * 80)
        
        # Получаем инструкции для ревизии
        instructions = self.config.get('instructions', {})
        revision_instructions = instructions.get('revision', [])
        
        if not revision_instructions:
            logger.error("Инструкции для ревизии не найдены в конфигурации")
            return False
        
        # Создаем специальный task_id для ревизии
        revision_task_id = f"revision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Создаем TaskLogger для ревизии
        task_logger = TaskLogger(
            task_id=revision_task_id,
            task_name="Ревизия проекта"
        )
        
        try:
            # Получаем все инструкции ревизии и сортируем по instruction_id
            valid_instructions = [
                instr for instr in revision_instructions
                if isinstance(instr, dict) and 'instruction_id' in instr
            ]
            valid_instructions.sort(key=lambda x: x.get('instruction_id', 999))
            
            logger.info(f"Найдено {len(valid_instructions)} инструкций для ревизии")
            
            successful_instructions = 0
            critical_instructions = min(3, len(valid_instructions))  # Минимум 3 инструкции для завершения
            
            for instruction_num, template in enumerate(valid_instructions, start=1):
                template.get('instruction_id', instruction_num)
                instruction_name = template.get('name', f'Инструкция {instruction_num}')
                instruction_text = template.get('template', '')
                wait_for_file = template.get('wait_for_file', '')
                control_phrase = template.get('control_phrase', '')
                timeout = template.get('timeout', 600)
                
                # Заменяем плейсхолдеры
                instruction_text = instruction_text.replace('{task_id}', revision_task_id)
                if wait_for_file:
                    wait_for_file = wait_for_file.replace('{task_id}', revision_task_id)
                
                logger.info(f"[{instruction_num}/{len(valid_instructions)}] Выполнение ревизии: {instruction_name}")
                task_logger.log_info(f"Ревизия {instruction_num}/{len(valid_instructions)}: {instruction_name}")
                
                # Логируем "запрос" (инструкцию) в консоль так же, как в default-потоке
                task_logger.log_instruction(instruction_num, instruction_text, task_type="revision")
                task_logger.set_phase(TaskPhase.CURSOR_EXECUTION, stage=instruction_num, instruction_num=instruction_num)

                # Выполняем инструкцию через Cursor
                result = self._execute_cursor_instruction_with_retry(
                    instruction=instruction_text,
                    task_id=revision_task_id,
                    timeout=timeout,
                    task_logger=task_logger,
                    instruction_num=instruction_num
                )

                # Логируем "ответ" в консоль
                task_logger.log_cursor_response(result, brief=True)
                
                if not result.get("success"):
                    logger.warning(f"Инструкция ревизии {instruction_num} завершилась с ошибкой")
                    continue
                
                # Ожидаем результат, если указан wait_for_file
                if wait_for_file:
                    wait_result = self._wait_for_result_file(
                        task_id=revision_task_id,
                        wait_for_file=wait_for_file,
                        control_phrase=control_phrase,
                        timeout=timeout
                    )
                    
                    if wait_result and wait_result.get("success"):
                        successful_instructions += 1
                        logger.info(f"Инструкция ревизии {instruction_num} выполнена успешно")
                        
                        # Автоматический push после коммита в ревизии
                        if control_phrase and control_phrase.strip() == "Коммит выполнен!":
                            logger.info("Ревизия: коммит выполнен - выполняем автоматический push из сервера")
                            try:
                                # Получаем настройки smart_git из конфигурации
                                git_config = self.config.get('git', {})
                                smart_git_config = git_config.get('smart_git', {})
                                allowed_branches = smart_git_config.get('allowed_branches', ['smart'])
                                push_timeout = smart_git_config.get('auto_push_timeout', 60)

                                push_result = auto_push_after_commit(
                                    working_dir=Path(self.project_dir),
                                    remote="origin",
                                    timeout=push_timeout,
                                    allowed_branches=allowed_branches
                                )
                                
                                if push_result.get("success"):
                                    logger.info(f"✅ Автоматический push выполнен успешно: {push_result.get('branch')} -> origin/{push_result.get('branch')}")
                                elif not push_result.get("push_allowed", True):
                                    # Push не разрешен для данной ветки - это не ошибка
                                    branch = push_result.get('branch', 'неизвестная')
                                    logger.info(f"ℹ️ Автоматический push пропущен: ветка '{branch}' не разрешена для авто-push")
                                else:
                                    error_msg = push_result.get("error", "Неизвестная ошибка")
                                    logger.warning(f"⚠️ Автоматический push не удался: {error_msg}")
                            except Exception as e:
                                logger.error(f"Ошибка при автоматическом push: {e}", exc_info=True)
                    else:
                        logger.warning(f"Файл результата для инструкции ревизии {instruction_num} не получен")
                else:
                    # Если wait_for_file не указан, считаем успешным если команда выполнена
                    successful_instructions += 1
            
            if successful_instructions >= critical_instructions:
                logger.info("=" * 80)
                logger.info(f"РЕВИЗИЯ ЗАВЕРШЕНА: выполнено {successful_instructions}/{len(valid_instructions)} инструкций")
                logger.info("=" * 80)
                task_logger.set_phase(TaskPhase.COMPLETION)
                return True
            else:
                logger.warning(f"Ревизия не завершена полностью: выполнено только {successful_instructions}/{len(valid_instructions)} инструкций")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при выполнении ревизии: {e}", exc_info=True)
            task_logger.log_error("Ошибка при выполнении ревизии", e)
            return False
    
    def _generate_new_todo_list(self) -> bool:
        """
        Генерация нового TODO листа через Cursor при пустом списке задач
        
        Returns:
            True если генерация успешна, False иначе
        """
        # Проверяем, можно ли генерировать
        if not self.auto_todo_enabled:
            logger.info("Автоматическая генерация TODO отключена")
            return False
        
        if not self.session_tracker.can_generate_todo(self.max_todo_generations):
            logger.warning(
                f"Достигнут лимит генераций TODO для текущей сессии "
                f"({self.max_todo_generations})"
            )
            return False
        
        logger.info("Начало генерации нового TODO листа")
        session_id = self.session_tracker.current_session_id
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Получаем инструкции для empty_todo сценария
        instructions = self.config.get('instructions', {})
        empty_todo_instructions = instructions.get('empty_todo', [])
        
        if not empty_todo_instructions:
            logger.error("Инструкции для empty_todo не найдены в конфигурации")
            return False
        
        # Выполняем инструкцию 1: Создание TODO листа
        logger.info("Шаг 1: Архитектурный анализ и создание TODO листа")
        instruction_1 = empty_todo_instructions[0]
        
        instruction_text = instruction_1.get('template', '')
        instruction_text = instruction_text.replace('{date}', date_str)
        instruction_text = instruction_text.replace('{session_id}', session_id)
        
        wait_for_file = instruction_1.get('wait_for_file', '').replace('{session_id}', session_id)
        control_phrase = instruction_1.get('control_phrase', '')
        timeout = instruction_1.get('timeout', 600)
        
        # Выполняем через Cursor
        result = self._execute_cursor_instruction_direct(
            instruction_text,
            wait_for_file,
            control_phrase,
            timeout,
            f"todo_gen_{session_id}_step1"
        )
        
        if not result:
            logger.error("Ошибка при создании TODO листа")
            return False
        
        # Парсим созданный TODO файл для получения списка задач
        todo_file = self.project_dir / f"todo/GENERATED_{date_str}_{session_id}.md"
        if not todo_file.exists():
            logger.warning(f"Сгенерированный TODO файл не найден: {todo_file}")
            # Пробуем найти в других местах
            possible_locations = [
                self.project_dir / "todo" / "CURRENT.md",
                self.project_dir / f"GENERATED_{date_str}_{session_id}.md"
            ]
            for loc in possible_locations:
                if loc.exists():
                    todo_file = loc
                    logger.info(f"TODO файл найден: {todo_file}")
                    break
        
        # Читаем задачи из сгенерированного TODO
        try:
            content = todo_file.read_text(encoding='utf-8')
            # Простой подсчет задач (строки с - [ ])
            task_count = content.count('- [ ]')
            logger.info(f"Сгенерировано задач: {task_count}")
        except Exception as e:
            logger.warning(f"Не удалось прочитать сгенерированный TODO: {e}")
            task_count = 0
        
        # Если задач мало, используем значение по умолчанию
        if task_count == 0:
            task_count = 5  # Предполагаем минимум 5 задач
        
        # Выполняем инструкцию 2: Создание документации для каждой задачи
        # (Упрощенная версия - создаем документацию для первых 3 задач)
        logger.info("Шаг 2: Создание документации для задач")
        max_docs = min(3, task_count)  # Ограничиваем количество для экономии времени
        
        for task_num in range(1, max_docs + 1):
            logger.info(f"Создание документации для задачи {task_num}/{max_docs}")
            
            if len(empty_todo_instructions) < 2:
                logger.warning("Инструкция для создания документации не найдена")
                break
            
            instruction_2 = empty_todo_instructions[1]
            instruction_text = instruction_2.get('template', '')
            instruction_text = instruction_text.replace('{task_num}', str(task_num))
            instruction_text = instruction_text.replace('{session_id}', session_id)
            instruction_text = instruction_text.replace('{task_text}', f'Задача #{task_num} из TODO')
            
            wait_for_file = instruction_2.get('wait_for_file', '').replace('{task_num}', str(task_num)).replace('{session_id}', session_id)
            control_phrase = instruction_2.get('control_phrase', '').replace('{task_num}', str(task_num))
            
            result = self._execute_cursor_instruction_direct(
                instruction_text,
                wait_for_file,
                control_phrase,
                timeout,
                f"todo_gen_{session_id}_step2_{task_num}"
            )
            
            if not result:
                logger.warning(f"Ошибка при создании документации для задачи {task_num}")
        
        # Выполняем инструкцию 3: Финализация TODO листа
        logger.info("Шаг 3: Финализация TODO листа")
        if len(empty_todo_instructions) >= 3:
            instruction_3 = empty_todo_instructions[2]
            instruction_text = instruction_3.get('template', '')
            instruction_text = instruction_text.replace('{date}', date_str)
            instruction_text = instruction_text.replace('{session_id}', session_id)
            
            wait_for_file = instruction_3.get('wait_for_file', '').replace('{session_id}', session_id)
            control_phrase = instruction_3.get('control_phrase', '')
            
            result = self._execute_cursor_instruction_direct(
                instruction_text,
                wait_for_file,
                control_phrase,
                timeout,
                f"todo_gen_{session_id}_step3"
            )
        
        # Выполняем инструкцию 4: Коммит
        logger.info("Шаг 4: Коммит нового TODO листа")
        if len(empty_todo_instructions) >= 4:
            instruction_4 = empty_todo_instructions[3]
            instruction_text = instruction_4.get('template', '')
            instruction_text = instruction_text.replace('{date}', date_str)
            instruction_text = instruction_text.replace('{session_id}', session_id)
            instruction_text = instruction_text.replace('{task_count}', str(task_count))
            
            wait_for_file = instruction_4.get('wait_for_file', '')
            control_phrase = instruction_4.get('control_phrase', '')
            
            result = self._execute_cursor_instruction_direct(
                instruction_text,
                wait_for_file,
                control_phrase,
                300,
                f"todo_gen_{session_id}_step4"
            )
        
        # Записываем информацию о генерации
        self.session_tracker.record_generation(
            str(todo_file),
            task_count,
            {
                "date": date_str,
                "session_id": session_id,
                "docs_created": max_docs
            }
        )
        
        logger.info(f"Генерация TODO листа завершена: {todo_file}, задач: {task_count}")
        
        # Перезагружаем TODO менеджер для чтения новых задач
        self.todo_manager = self.di_container.resolve(ITodoManager)
        
        return True
    
    def _execute_cursor_instruction_direct(
        self,
        instruction: str,
        wait_for_file: str,
        control_phrase: str,
        timeout: int,
        task_id: str
    ) -> bool:
        """
        Прямое выполнение инструкции через Cursor (упрощенная версия)
        
        Args:
            instruction: Текст инструкции
            wait_for_file: Файл для ожидания
            control_phrase: Контрольная фраза
            timeout: Таймаут
            task_id: ID задачи
        
        Returns:
            True если успешно
        """
        logger.info(f"Выполнение инструкции: {task_id}")
        
        if self.use_cursor_cli:
            result = self.execute_cursor_instruction(
                instruction=instruction,
                task_id=task_id,
                timeout=timeout
            )
            
            if result.get("success"):
                # Ожидаем файл результата
                if wait_for_file:
                    wait_result = self._wait_for_result_file(
                        task_id=task_id,
                        wait_for_file=wait_for_file,
                        control_phrase=control_phrase,
                        timeout=timeout
                    )
                    return wait_result.get("success", False)
                return True
            else:
                logger.warning(f"Ошибка выполнения через CLI: {result.get('error_message')}")
        
        # Fallback на файловый интерфейс
        self.cursor_file.write_instruction(
            instruction=instruction,
            task_id=task_id,
            metadata={
                "wait_for_file": wait_for_file,
                "control_phrase": control_phrase
            },
            new_chat=True
        )
        
        wait_result = self.cursor_file.wait_for_result(
            task_id=task_id,
            timeout=timeout,
            control_phrase=control_phrase
        )
        
        return wait_result.get("success", False)

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
            completed_tasks_in_checkpoint = [
                task for task in self.checkpoint_manager.checkpoint_data.get("tasks", [])
                if task.get("state") == "completed"
            ]

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

            revision_success = self._execute_revision()

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

                generation_success = self._generate_new_todo_list()

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

    def _reload_todos_and_check_for_new_tasks(self):
        """
        Перезагрузка TODO и проверка на наличие новых задач
        """
        # Делегируем вызов ServerCore, который использует фабрику
        if hasattr(self, 'server_core') and self.server_core:
            # ServerCore уже имеет свой менеджер, просто перезагрузим его
            self.server_core._reload_todos_and_check_for_new_tasks()
            # Синхронизируем наш локальный менеджер
            self.todo_manager = self.server_core.todo_manager
        else:
            # Fallback: получаем новый экземпляр из DI контейнера
            self.todo_manager = self.di_container.resolve(ITodoManager)

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

    async def run_iteration(self, iteration: int = 1):
        """
        Выполнение одной итерации цикла с делегированием полного контроля ServerCore

        Args:
            iteration: Номер итерации

        Returns:
            True если есть еще задачи для выполнения, False иначе
        """
        logger.info(f"Начало итерации {iteration}")

        # Создаем callbacks для проверки остановки и перезапуска
        def should_stop():
            with self._stop_lock:
                return self._should_stop

        def should_reload():
            return self._check_reload_needed()

        try:
            # Делегируем полный контроль выполнения итерации ServerCore
            has_more_tasks, executed_tasks = await self.server_core.execute_full_iteration(
                iteration=iteration,
                should_stop_callback=should_stop,
                should_reload_callback=should_reload,
                reload_exception_class=ServerReloadException
            )

            # Логируем результаты выполнения задач
            if executed_tasks:
                successful_count = sum(1 for _, success in executed_tasks if success)
                total_count = len(executed_tasks)
                logger.info(f"Итерация {iteration} завершена: {successful_count}/{total_count} задач выполнено успешно")

            return has_more_tasks

        except ServerReloadException:
            # Перебрасываем исключение перезапуска дальше
            raise
        except Exception as e:
            logger.error(f"Ошибка выполнения итерации {iteration}: {e}", exc_info=True)
            return False
    
    def _check_port_in_use(self, port: int) -> bool:
        """
        Проверка, занят ли порт
        
        Args:
            port: Номер порта для проверки
            
        Returns:
            True если порт занят, False иначе
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0
        except Exception as e:
            logger.debug(f"Ошибка проверки порта {port}: {e}")
            return False
    
    def _kill_process_on_port(self, port: int) -> bool:
        """
        Завершить процесс, использующий указанный порт
        
        Args:
            port: Номер порта
            
        Returns:
            True если процесс найден и завершен, False иначе
        """
        try:
            if sys.platform == 'win32':
                # Windows: используем netstat для поиска PID
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if f':{port}' in line and 'LISTENING' in line:
                            parts = line.split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                try:
                                    # Завершаем процесс
                                    subprocess.run(
                                        ['taskkill', '/F', '/PID', pid],
                                        capture_output=True,
                                        timeout=3
                                    )
                                    logger.info(f"Завершен процесс {pid}, использующий порт {port}")
                                    # Даем время процессу завершиться
                                    time.sleep(2)
                                    return True
                                except Exception as e:
                                    logger.warning(f"Не удалось завершить процесс {pid}: {e}")
            else:
                # Linux/Mac: используем lsof
                try:
                    result = subprocess.run(
                        ['lsof', '-ti', f':{port}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            try:
                                subprocess.run(
                                    ['kill', '-9', pid],
                                    capture_output=True,
                                    timeout=3
                                )
                                logger.info(f"Завершен процесс {pid}, использующий порт {port}")
                            except Exception as e:
                                logger.warning(f"Не удалось завершить процесс {pid}: {e}")
                        # Даем время процессу завершиться
                        time.sleep(2)
                        return True
                except FileNotFoundError:
                    # lsof не установлен, пробуем через fuser
                    try:
                        result = subprocess.run(
                            ['fuser', '-k', f'{port}/tcp'],
                            capture_output=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            logger.info(f"Завершены процессы на порту {port}")
                            time.sleep(2)
                            return True
                    except FileNotFoundError:
                        pass
        except Exception as e:
            logger.warning(f"Ошибка при завершении процесса на порту {port}: {e}")
        
        return False
    
    def _setup_http_server(self):
        """Настройка и запуск HTTP сервера на порту"""
        if not FLASK_AVAILABLE:
            logger.warning("Flask не установлен, HTTP сервер недоступен")
            return
        
        if not self.http_enabled:
            logger.info("HTTP сервер отключен в конфигурации")
            return
        
        # Проверяем занятость порта
        if self._check_port_in_use(self.http_port):
            logger.warning(f"Порт {self.http_port} занят, пытаемся завершить старый процесс...")
            if self._kill_process_on_port(self.http_port):
                # Ждем освобождения порта
                for _ in range(10):
                    if not self._check_port_in_use(self.http_port):
                        break
                    time.sleep(1)
                else:
                    logger.error(f"Порт {self.http_port} все еще занят после попытки завершения процесса")
                    return
            else:
                logger.error(f"Не удалось завершить процесс на порту {self.http_port}")
                return
        
        # Создаем Flask приложение
        self.flask_app = Flask(__name__)
        
        @self.flask_app.route('/')
        def index():
            """Главная страница с информацией о сервере"""
            try:
                stats = self.checkpoint_manager.get_statistics()
                iteration = self.checkpoint_manager.get_iteration_count()
            except Exception as e:
                logger.warning(f"Ошибка при получении статистики для /: {e}")
                stats = {'completed': 0, 'failed': 0, 'pending': 0, 'in_progress': 0, 'total_tasks': 0, 'iteration_count': 0}
                iteration = 0
            
            return jsonify({
                'status': 'running',
                'port': self.http_port,
                'session_id': self.session_tracker.current_session_id,
                'iteration': iteration,
                'statistics': stats,
                'project_dir': str(self.project_dir),
                'cursor_cli_available': self.use_cursor_cli,
                'auto_todo_enabled': self.auto_todo_enabled
            })
        
        @self.flask_app.route('/status')
        def status():
            """Статус сервера с подробной информацией"""
            try:
                recovery_info = self.checkpoint_manager.get_recovery_info()
            except Exception as e:
                logger.warning(f"Ошибка при получении recovery_info для /status: {e}")
                recovery_info = {
                    'was_clean_shutdown': True,
                    'last_start_time': None,
                    'last_stop_time': None,
                    'session_id': self.session_tracker.current_session_id,
                    'iteration_count': 0
                }
            
            try:
                stats = self.checkpoint_manager.get_statistics()
            except Exception as e:
                logger.warning(f"Ошибка при получении статистики для /status: {e}")
                stats = {'completed': 0, 'failed': 0, 'pending': 0, 'in_progress': 0, 'total_tasks': 0, 'iteration_count': 0}
            
            try:
                current_task = self.checkpoint_manager.get_current_task()
            except Exception as e:
                logger.warning(f"Ошибка при получении текущей задачи для /status: {e}")
                current_task = None
            
            # Получаем текущие задачи из todo_manager
            try:
                pending_tasks = self.todo_manager.get_pending_tasks()
            except Exception as e:
                logger.warning(f"Ошибка при получении pending_tasks для /status: {e}")
                pending_tasks = []
            
            # Определяем, что делает сервер
            current_activity = "Ожидание"
            if current_task:
                current_activity = f"Выполнение задачи: {current_task.get('task_text', 'N/A')[:100]}"
            elif pending_tasks:
                current_activity = f"Ожидание выполнения {len(pending_tasks)} задач"
            else:
                current_activity = "Все задачи выполнены"
            
            # Проверяем, есть ли запрос на перезапуск
            pending_restart = False
            with self._reload_lock:
                pending_restart = self._should_reload
            
            return jsonify({
                'server': {
                    'status': 'running' if self._is_running else 'stopped',
                    'running': self._is_running,
                    'port': self.http_port,
                    'project_dir': str(self.project_dir),
                    'cursor_cli_available': self.use_cursor_cli,
                    'auto_todo_enabled': self.auto_todo_enabled
                },
                'server_state': {
                    'clean_shutdown': recovery_info['was_clean_shutdown'],
                    'last_start_time': recovery_info['last_start_time'],
                    'last_stop_time': recovery_info['last_stop_time'],
                    'session_id': recovery_info['session_id'],
                    'iteration_count': self._current_iteration or recovery_info['iteration_count'],
                    'current_activity': current_activity,
                    'restart_count': self._restart_count,
                    'pending_restart': pending_restart
                },
                'tasks': {
                    'in_progress': stats['in_progress'],
                    'completed': stats['completed'],
                    'failed': stats['failed'],
                    'pending': stats['pending'],
                    'total': stats['total_tasks'],
                    'pending_in_todo': len(pending_tasks)
                },
                'current_task': {
                    'task_id': current_task.get('task_id') if current_task else None,
                    'task_text': current_task.get('task_text', '')[:200] if current_task else None,
                    'state': current_task.get('state') if current_task else None,
                    'start_time': current_task.get('start_time') if current_task else None,
                    'attempts': current_task.get('attempts', 0) if current_task else 0
                } if current_task else None
            })
        
        @self.flask_app.route('/health')
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
        
        @self.flask_app.route('/stop', methods=['POST'])
        def stop():
            """Остановить сервер немедленно"""
            with self._stop_lock:
                self._should_stop = True
            logger.warning("=" * 80)
            logger.warning("ПОЛУЧЕН ЗАПРОС НА НЕМЕДЛЕННУЮ ОСТАНОВКУ СЕРВЕРА ЧЕРЕЗ API")
            logger.warning("=" * 80)
            logger.warning("Сервер будет остановлен немедленно, текущая задача будет прервана")
            logger.warning("=" * 80)
            return jsonify({
                'status': 'stopping',
                'message': 'Сервер будет остановлен немедленно',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.flask_app.route('/restart', methods=['POST'])
        def restart():
            """Перезапустить сервер"""
            logger.warning("=" * 80)
            logger.warning("ПОЛУЧЕН ЗАПРОС НА ПЕРЕЗАПУСК СЕРВЕРА ЧЕРЕЗ API")
            logger.warning("=" * 80)
            with self._reload_lock:
                self._should_reload = True
            logger.warning(f"Флаг перезапуска установлен. Текущий счетчик перезапусков: {self._restart_count}")
            logger.warning("=" * 80)
            return jsonify({
                'status': 'restarting',
                'message': 'Сервер будет перезапущен после завершения текущей итерации',
                'timestamp': datetime.now().isoformat(),
                'restart_count': self._restart_count
            })
        
        # Запускаем Flask в отдельном потоке
        def run_flask():
            try:
                from werkzeug.serving import make_server
                
                # Объединяем все логи инициализации в один цветной блок
                separator = '-' * 60
                http_info_lines = [
                    Colors.colorize(separator, Colors.BRIGHT_CYAN),
                    Colors.colorize("🌐 HTTP СЕРВЕР", Colors.BRIGHT_CYAN + Colors.BOLD),
                    f"Порт: {self.http_port}",
                    f"Адрес: http://127.0.0.1:{self.http_port}",
                    Colors.colorize(separator, Colors.BRIGHT_CYAN)
                ]
                logger.info('\n'.join(http_info_lines))
                
                # Создаем сервер через werkzeug
                try:
                    self.http_server = make_server(
                        '127.0.0.1',
                        self.http_port,
                        self.flask_app,
                        threaded=True
                    )
                except OSError as e:
                    # Правильная обработка ошибок с UTF-8 кодировкой
                    error_msg = f"Ошибка создания HTTP сервера на порту {self.http_port}"
                    if e.errno == 22:  # Invalid argument
                        error_msg += ": порт может быть занят или недоступен"
                    elif e.errno == 10048:  # Address already in use (Windows)
                        error_msg += ": порт уже занят другим процессом"
                    elif e.errno == 98:  # Address already in use (Linux)
                        error_msg += ": порт уже занят другим процессом"
                    else:
                        error_msg += f" (errno: {e.errno})"
                    
                    logger.error(error_msg)
                    logger.error(f"Детали ошибки: {str(e)}")
                    return
                except Exception as e:
                    logger.error(f"Неожиданная ошибка при создании HTTP сервера: {e}", exc_info=True)
                    return
                try:
                    self.http_server.serve_forever()
                except Exception as e:
                    logger.error(f"Ошибка при работе HTTP сервера: {e}", exc_info=True)
                    raise
                
            except KeyboardInterrupt:
                logger.info("HTTP сервер получил сигнал остановки")
            except Exception as e:
                # Общая обработка ошибок с правильной кодировкой
                error_msg = f"Критическая ошибка HTTP сервера: {str(e)}"
                logger.error(error_msg, exc_info=True)
        
        self.http_thread = threading.Thread(target=run_flask, daemon=True, name="HTTP-Server")
        self.http_thread.start()
        
        # Ждем запуска сервера с более длительным таймаутом (логируем только в debug)
        max_attempts = 20  # Увеличиваем до 20 попыток (10 секунд)
        server_started = False
        
        for attempt in range(max_attempts):
            if self._check_port_in_use(self.http_port):
                # Дополнительно проверяем доступность HTTP
                try:
                    try:
                        import requests
                        response = requests.get(f'http://127.0.0.1:{self.http_port}/health', timeout=1)
                        if response.status_code == 200:
                            server_started = True
                            break
                    except ImportError:
                        # requests не установлен - используем только проверку порта
                        server_started = True
                        break
                except Exception as e:
                    # Порт занят, но HTTP еще не отвечает - продолжаем ждать
                    if attempt % 4 == 0:  # Логируем каждые 2 секунды
                        logger.debug(f"Порт {self.http_port} занят, но HTTP еще не отвечает: {e}")
            
            if attempt < max_attempts - 1:
                time.sleep(0.5)
            elif attempt % 4 == 0:  # Логируем каждые 2 секунды
                logger.debug(f"Ожидание запуска HTTP сервера... (попытка {attempt + 1}/{max_attempts})")
        
        if not server_started:
            logger.warning(f"HTTP сервер не смог запуститься на порту {self.http_port} после {max_attempts} попыток.")
            logger.warning("Проверьте логи выше на наличие ошибок. Сервер продолжит работу без HTTP API.")
    
    def _setup_file_watcher(self):
        """Настройка отслеживания изменений .py файлов для автоперезапуска"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("Watchdog не установлен, автоперезапуск недоступен")
            return
        
        if not self.auto_reload or not self.reload_on_py_changes:
            logger.info("Автоперезапуск отключен в конфигурации")
            return
        
        class PyFileHandler(FileSystemEventHandler):
            """Обработчик изменений .py файлов"""
            def __init__(self, server_instance):
                self.server = server_instance
                self.last_reload_time = 0
                self.reload_cooldown = 10  # Минимальный интервал между перезапусками (секунды) - увеличено для защиты от ложных срабатываний
                self.file_hashes = {}  # Кэш хешей файлов для проверки реальных изменений
                self.pending_changes = set()  # Множество файлов с изменениями в процессе обработки
                self.ignored_patterns = [
                    # Игнорируемые директории и паттерны
                    '__pycache__',
                    '.pyc',
                    '/test/',
                    '\\test\\',
                    'test_cursor_cli',
                    'test_',
                    '/examples/',
                    '\\examples\\',
                    '/docs/',
                    '\\docs\\',
                    '/logs/',
                    '\\logs\\',
                    '.git',
                    'venv',
                    'env',
                    'node_modules'
                ]
            
            def _should_ignore_file(self, file_path: str) -> bool:
                """Проверка, нужно ли игнорировать файл"""
                file_path_lower = file_path.lower()
                
                # Проверяем игнорируемые паттерны
                for pattern in self.ignored_patterns:
                    if pattern in file_path_lower:
                        return True
                
                # Игнорируем временные файлы редакторов (Windows и Unix)
                temp_patterns = [
                    '~$',  # Windows временные файлы (например, ~$file.py)
                    '.tmp',  # Временные файлы
                    '.swp',  # Vim swap файлы
                    '.swo',  # Vim swap файлы
                    '.bak',  # Backup файлы
                    '.orig',  # Merge conflict файлы
                    '.rej',  # Rejected patch файлы
                    '.pyc',  # Python bytecode (на всякий случай)
                    '.pyo',  # Python optimized bytecode
                    '__pycache__',  # Python cache
                    '.git/',  # Git файлы
                    '.vscode/',  # VS Code настройки
                    '.idea/',  # IntelliJ/PyCharm настройки
                    '.cursor/',  # Cursor настройки
                ]
                for pattern in temp_patterns:
                    if pattern in file_path_lower:
                        return True
                
                # Проверяем, существует ли файл (может быть временный файл, который уже удален)
                try:
                    if not Path(file_path).exists():
                        return True
                except Exception:
                    return True
                
                # Игнорируем файлы, которые не в src/ директории (если это не main.py или другие важные файлы в корне)
                src_dir = str(Path(__file__).parent).lower()
                str(Path(__file__).parent.parent).lower()
                file_path_normalized = file_path.lower()
                
                # Разрешаем только файлы в src/ или важные файлы в корне (main.py, setup.py и т.д.)
                if not file_path_normalized.startswith(src_dir):
                    # Разрешаем только main.py и другие критичные файлы в корне
                    filename = Path(file_path).name.lower()
                    allowed_root_files = ['main.py', 'setup.py', 'setup.cfg']
                    if filename not in allowed_root_files:
                        return True
                
                return False
            
            def _get_file_hash(self, file_path: str) -> Optional[str]:
                """Получить хеш файла для проверки реальных изменений"""
                try:
                    import hashlib
                    file = Path(file_path)
                    if not file.exists():
                        return None
                    
                    # Используем MD5 хеш содержимого файла для более надежной проверки
                    # Это гарантирует, что мы реагируем только на реальные изменения содержимого
                    md5 = hashlib.md5()
                    try:
                        with open(file_path, 'rb') as f:
                            # Читаем файл по частям для больших файлов
                            for chunk in iter(lambda: f.read(4096), b''):
                                md5.update(chunk)
                        return md5.hexdigest()
                    except (OSError, IOError, PermissionError):
                        # Если не можем прочитать файл (например, он заблокирован), используем fallback
                        # Но только если файл действительно существует
                        stat = file.stat()
                        return f"fallback_{stat.st_size}_{stat.st_mtime}"
                except Exception:
                    return None
            
            def on_modified(self, event):
                if event.is_directory:
                    return
                
                # Проверяем, что это .py файл
                if not event.src_path.endswith('.py'):
                    return
                
                # Проверяем, нужно ли игнорировать файл (включая временные файлы редакторов)
                if self._should_ignore_file(event.src_path):
                    logger.debug(f"Игнорируем изменение файла: {event.src_path}")
                    return
                
                # Проверяем, не обрабатывается ли уже этот файл
                if event.src_path in self.pending_changes:
                    logger.debug(f"Файл уже в процессе обработки: {event.src_path}")
                    return
                
                # Проверяем cooldown - защита от частых срабатываний
                current_time = time.time()
                if current_time - self.last_reload_time < self.reload_cooldown:
                    logger.debug(f"Cooldown активен, игнорируем изменение: {event.src_path}")
                    return
                
                # Добавляем файл в обработку
                self.pending_changes.add(event.src_path)
                
                try:
                    # Небольшая задержка для стабилизации файла (редакторы могут сохранять в несколько этапов)
                    time.sleep(0.5)
                    
                    # Проверяем, действительно ли файл изменился (сравниваем хеш содержимого)
                    file_hash = self._get_file_hash(event.src_path)
                    if file_hash is None:
                        # Не удалось получить хеш - возможно, файл удален или недоступен
                        logger.debug(f"Не удалось получить хеш файла (возможно, временный файл): {event.src_path}")
                        return
                    
                    # Проверяем, действительно ли содержимое изменилось
                    if event.src_path in self.file_hashes:
                        if self.file_hashes[event.src_path] == file_hash:
                            # Содержимое файла не изменилось - ложное срабатывание
                            logger.debug(f"Игнорируем ложное срабатывание (содержимое не изменилось): {event.src_path}")
                            return
                    
                    # Сохраняем новый хеш только после подтверждения реального изменения
                    self.file_hashes[event.src_path] = file_hash
                    
                    logger.info(f"Обнаружено РЕАЛЬНОЕ изменение файла: {event.src_path}")
                    self.last_reload_time = current_time
                    
                    # Проверяем, выполняется ли сейчас задача
                    with self.server._task_in_progress_lock:
                        task_in_progress = self.server._task_in_progress
                    
                    if task_in_progress:
                        # Если задача выполняется, откладываем перезапуск до завершения текущей инструкции
                        logger.info("Обнаружено изменение кода во время выполнения задачи - перезапуск будет выполнен после завершения текущей инструкции")
                        with self.server._reload_lock:
                            self.server._should_reload = True
                            self.server._reload_after_instruction = True
                    else:
                        # Если задачи нет, перезапускаем немедленно
                        with self.server._reload_lock:
                            self.server._should_reload = True
                            logger.warning("=" * 80)
                            logger.warning("ОБНАРУЖЕНО ИЗМЕНЕНИЕ .py ФАЙЛА - ТРЕБУЕТСЯ ПЕРЕЗАПУСК")
                            logger.warning(f"Изменен файл: {event.src_path}")
                            logger.warning("=" * 80)
                finally:
                    # Удаляем файл из обработки через некоторое время
                    def remove_pending():
                        time.sleep(2)
                        self.pending_changes.discard(event.src_path)
                    threading.Thread(target=remove_pending, daemon=True).start()
        
        # Определяем директории для отслеживания
        watch_dirs = []
        
        # Добавляем директорию src
        src_dir = Path(__file__).parent
        if src_dir.exists():
            watch_dirs.append(str(src_dir))
        
        if not watch_dirs:
            logger.warning("Не найдены директории для отслеживания изменений")
            return
        
        # Создаем observer
        self.file_observer = Observer()
        handler = PyFileHandler(self)
        
        for watch_dir in watch_dirs:
            try:
                self.file_observer.schedule(handler, watch_dir, recursive=True)
                logger.info(f"Отслеживание изменений .py файлов в: {watch_dir}")
            except Exception as e:
                logger.warning(f"Не удалось добавить директорию для отслеживания {watch_dir}: {e}")
        
        # Запускаем observer
        self.file_observer.start()
        logger.info("File watcher запущен для автоперезапуска при изменении .py файлов")
    
    def _check_reload_needed(self) -> bool:
        """
        Проверка необходимости перезапуска
        
        Returns:
            True если требуется перезапуск
        """
        with self._reload_lock:
            if self._should_reload:
                # Если перезапуск помечен как "после инструкции" — никогда не выполняем его немедленно.
                # Это защищает ожидание файлов результатов и длинные шаги от обрыва.
                if self._reload_after_instruction:
                    logger.warning("=" * 80)
                    logger.warning("ПЕРЕЗАПУСК ОТЛОЖЕН - ОЖИДАЕМ ЗАВЕРШЕНИЯ ТЕКУЩЕЙ ИНСТРУКЦИИ")
                    logger.warning("=" * 80)
                    return False

                # Проверяем, выполняется ли сейчас задача
                with self._task_in_progress_lock:
                    if self._task_in_progress:
                        # Задача выполняется - перезапуск будет выполнен после завершения текущей инструкции
                        # (проверка _reload_after_instruction происходит после завершения инструкции)
                        logger.warning("=" * 80)
                        logger.warning("ПЕРЕЗАПУСК ОТЛОЖЕН - ВЫПОЛНЯЕТСЯ ЗАДАЧА")
                        logger.warning("Перезапуск произойдет после завершения текущей инструкции")
                        logger.warning("=" * 80)
                        return False
                
                # Задачи нет - можно перезапускать
                logger.warning("=" * 80)
                logger.warning("НАЧАЛО ПЕРЕЗАПУСКА СЕРВЕРА")
                logger.warning(f"Счетчик перезапусков до перезапуска: {self._restart_count}")
                logger.warning("=" * 80)
                
                # Увеличиваем счетчик перезапусков
                with self._restart_count_lock:
                    self._restart_count += 1
                
                # Перезапускаем Docker контейнер перед перезапуском сервера
                logger.info("Перезапуск Docker контейнера перед перезапуском сервера...")
                docker_restart_success = self._restart_cursor_environment()
                if not docker_restart_success:
                    logger.warning("Не удалось перезапустить Docker контейнер, но продолжаем перезапуск сервера")
                
                logger.warning("=" * 80)
                logger.warning(f"ПЕРЕЗАПУСК ИНИЦИИРОВАН. Новый счетчик: {self._restart_count}")
                logger.warning("=" * 80)
                
                self._should_reload = False
                self._reload_after_instruction = False
                return True
            return False
    
    async def start(self):
        """Запуск сервера агента в бесконечном цикле"""
        logger.info("Запуск Code Agent Server")
        logger.info("Инициализация завершена, начинаем запуск HTTP сервера...")
        
        # Запускаем HTTP сервер
        self._setup_http_server()
        logger.info("HTTP сервер настроен, продолжаем запуск...")
        
        # Запускаем file watcher для автоперезапуска
        self._setup_file_watcher()
        
        # Проверяем статус компонентов системы
        self._log_system_status()

        # Отмечаем запуск в checkpoint
        session_id = self.session_tracker.current_session_id
        self.checkpoint_manager.mark_server_start(session_id)

        self.status_manager.append_status(
            f"Code Agent Server запущен. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            level=1
        )

        # Запускаем основной цикл сервера
        await self._run_server_loop()

    def _log_system_status(self):
        """Логирует статус компонентов системы для пользователя"""
        logger.info("=" * 60)
        logger.info("📊 СТАТУС КОМПОНЕНТОВ СИСТЕМЫ")
        logger.info("=" * 60)

        # Проверяем Docker
        try:
            from .tools.docker_utils import is_docker_available
            docker_available = is_docker_available()
            if docker_available:
                logger.info("🐳 Docker: ✅ Доступен")
            else:
                logger.warning("🐳 Docker: ⚠️  Недоступен (code execution отключен)")
        except Exception as e:
            logger.warning(f"🐳 Docker: ❌ Ошибка проверки ({e})")

        # Проверяем LLM
        try:
            from .llm.crewai_llm_wrapper import create_llm_for_crewai
            llm = create_llm_for_crewai(use_fastest=True, use_parallel=False)
            if llm:
                logger.info("🧠 LLM: ✅ Настроен")
            else:
                logger.warning("🧠 LLM: ⚠️  Недоступен (работа в tool-only режиме)")
        except Exception as e:
            logger.warning(f"🧠 LLM: ❌ Ошибка настройки ({e})")

        # Проверяем Cursor CLI
        try:
            cursor_available = self.is_cursor_cli_available()
            if cursor_available:
                logger.info("🎯 Cursor CLI: ✅ Доступен")
            else:
                logger.warning("🎯 Cursor CLI: ⚠️  Недоступен (интеграция ограничена)")
        except Exception as e:
            logger.warning(f"🎯 Cursor CLI: ❌ Ошибка проверки ({e})")

        # Проверяем Smart Agent
        try:
            from .agents.smart_agent import create_smart_agent
            smart_agent = create_smart_agent(
                project_dir=self.config.get('project', {}).get('base_dir', '.'),
                use_docker=False,  # Не проверяем Docker повторно
                use_llm=False,     # Не проверяем LLM повторно
                verbose=False
            )
            if smart_agent and len(smart_agent.tools) >= 2:
                logger.info(f"🤖 Smart Agent: ✅ Готов ({len(smart_agent.tools)} инструментов)")
            else:
                logger.warning("🤖 Smart Agent: ⚠️  Ограниченная функциональность")
        except Exception as e:
            logger.warning(f"🤖 Smart Agent: ❌ Ошибка инициализации ({e})")

        logger.info("=" * 60)
        logger.info("💡 Советы по улучшению:")
        logger.info("   - Установите Docker для выполнения кода")
        logger.info("   - Настройте API ключи для LLM в .env файле")
        logger.info("   - Убедитесь, что Cursor установлен и доступен")
        logger.info("=" * 60)

    async def _run_server_loop(self):
        """Основной цикл работы сервера"""
        # Получаем начальную итерацию из checkpoint (для восстановления)
        iteration = self.checkpoint_manager.get_iteration_count()
        self._current_iteration = iteration
        self._is_running = True
        
        try:
            while True:
                # Проверяем запрос на остановку (через API или из-за критических ошибок Cursor)
                with self._stop_lock:
                    if self._should_stop:
                        # Проверяем, это остановка через API или из-за ошибок Cursor
                        with self._cursor_error_lock:
                            cursor_error_stop = self._cursor_error_count >= self._max_cursor_errors
                        
                        if cursor_error_stop:
                            logger.error("=" * 80)
                            logger.error("ОСТАНОВКА СЕРВЕРА ИЗ-ЗА КРИТИЧЕСКИХ ОШИБОК CURSOR")
                            logger.error("=" * 80)
                            self.checkpoint_manager.mark_server_stop(clean=False)
                        else:
                            logger.warning("=" * 80)
                            logger.warning("ОСТАНОВКА СЕРВЕРА ПО ЗАПРОСУ ЧЕРЕЗ API")
                            logger.warning("=" * 80)
                            logger.warning("Текущая задача будет прервана, checkpoint будет сохранен")
                            logger.warning("=" * 80)
                            self.checkpoint_manager.mark_server_stop(clean=True)
                        
                        self._is_running = False
                        self.status_manager.append_status(
                            f"Code Agent Server остановлен по запросу через API. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            level=2
                        )
                        # Прерываем выполнение немедленно
                        break
                
                # Проверяем необходимость перезапуска
                if self._check_reload_needed():
                    logger.warning("=" * 80)
                    logger.warning("ВЫПОЛНЯЕТСЯ ПЕРЕЗАПУСК СЕРВЕРА")
                    logger.warning(f"Счетчик перезапусков: {self._restart_count}")
                    logger.warning("=" * 80)
                    logger.warning("Текущая задача будет прервана, checkpoint будет сохранен")
                    logger.warning("=" * 80)
                    self.checkpoint_manager.mark_server_stop(clean=True)
                    self._is_running = False
                    # Инициируем перезапуск через исключение
                    # main.py перехватит это и перезапустит сервер
                    raise ServerReloadException("Перезапуск сервера")
                
                iteration += 1
                self._current_iteration = iteration
                logger.info(f"Итерация {iteration}")
                
                # Выполняем итерацию
                try:
                    has_tasks = await self.run_iteration(iteration)
                except ServerReloadException:
                    # Перезапуск из-за изменений в коде во время выполнения итерации
                    logger.warning("Перезапуск сервера во время выполнения итерации")
                    self.checkpoint_manager.mark_server_stop(clean=True)
                    self._is_running = False
                    raise  # Пробрасываем исключение дальше
                
                # Проверяем флаг остановки после итерации (может быть установлен из-за ошибок Cursor)
                with self._stop_lock:
                    if self._should_stop:
                        break
                
                # Проверяем необходимость перезапуска после итерации
                if self._check_reload_needed():
                    logger.warning("=" * 80)
                    logger.warning("ВЫПОЛНЯЕТСЯ ПЕРЕЗАПУСК СЕРВЕРА ПОСЛЕ ИТЕРАЦИИ")
                    logger.warning(f"Счетчик перезапусков: {self._restart_count}")
                    logger.warning("=" * 80)
                    self.checkpoint_manager.mark_server_stop(clean=True)
                    self._is_running = False
                    raise ServerReloadException("Перезапуск сервера")
                
                # Проверяем ограничение итераций
                if self.max_iterations and iteration >= self.max_iterations:
                    logger.info(f"Достигнуто максимальное количество итераций: {self.max_iterations}")
                    self.server_logger.log_server_shutdown(f"Достигнуто максимальное количество итераций: {self.max_iterations}")
                    break
                
                # Периодически очищаем старые задачи из checkpoint
                if iteration % 10 == 0:
                    self.checkpoint_manager.clear_old_tasks(keep_last_n=100)
                
                # Если нет задач, проверяем снова через интервал
                if not has_tasks:
                    logger.info(f"Ожидание {self.check_interval} секунд перед следующей проверкой")
                    # Проверяем перезапуск и остановку во время ожидания
                    for _ in range(self.check_interval):
                        with self._stop_lock:
                            if self._should_stop:
                                break
                        if self._check_reload_needed():
                            logger.warning("Обнаружено изменение кода во время ожидания - перезапуск")
                            self.checkpoint_manager.mark_server_stop(clean=True)
                            raise ServerReloadException("Перезапуск из-за изменения кода")
                        time.sleep(1)
                else:
                    # Если задачи были, ждем интервал перед следующей итерацией
                    # Проверяем перезапуск и остановку во время ожидания
                    for _ in range(self.check_interval):
                        with self._stop_lock:
                            if self._should_stop:
                                break
                        if self._check_reload_needed():
                            logger.warning("Обнаружено изменение кода во время ожидания - перезапуск")
                            self.checkpoint_manager.mark_server_stop(clean=True)
                            raise ServerReloadException("Перезапуск из-за изменения кода")
                        time.sleep(1)
                    
        except ServerReloadException as e:
            # Перезапуск из-за изменений в .py файлах
            logger.warning("=" * 80)
            logger.warning("ПЕРЕЗАПУСК СЕРВЕРА ИЗ-ЗА ИЗМЕНЕНИЙ В КОДЕ")
            logger.warning("=" * 80)
            logger.warning(f"Причина: {str(e)}")
            logger.warning("=" * 80)
            self._is_running = False
            self.checkpoint_manager.mark_server_stop(clean=True)
            self.server_logger.log_server_shutdown(f"Перезапуск из-за изменений в коде: {str(e)}")
            # Пробрасываем исключение дальше для обработки в main.py
            raise
            
        except KeyboardInterrupt:
            import traceback
            logger.warning("=" * 80)
            logger.warning("⚠️ ОБНАРУЖЕН KeyboardInterrupt - ОСТАНОВКА СЕРВЕРА")
            logger.warning("=" * 80)
            
            # Получаем полный traceback для диагностики
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_str = ''.join(traceback.format_tb(exc_tb)) if exc_tb else "Traceback недоступен"
            
            # Всегда логируем traceback на уровне WARNING для диагностики
            logger.warning(f"Traceback KeyboardInterrupt:\n{tb_str}")
            logger.warning(f"Exception: {exc_type.__name__}: {exc_value}")
            
            # Проверяем, был ли это реальный Ctrl+C или другой источник
            # Подозрительные паттерны, которые могут вызвать KeyboardInterrupt
            suspicious_patterns = [
                'subprocess', 
                'threading', 
                'signal',
                'docker',
                'cursor_cli',
                'execute',
                'run(',
                'time.sleep',
                'wait_for'
            ]
            
            is_suspicious = False
            suspicious_source = None
            
            if exc_tb and tb_str:
                tb_lower = tb_str.lower()
                for pattern in suspicious_patterns:
                    if pattern in tb_lower:
                        is_suspicious = True
                        suspicious_source = pattern
                        break
            
            if is_suspicious:
                reason = f"Остановка из-за KeyboardInterrupt (НЕ Ctrl+C, вероятный источник: {suspicious_source})"
                logger.error("=" * 80)
                logger.error("❌ ОБНАРУЖЕНА ПРОБЛЕМА: KeyboardInterrupt вызван НЕ пользователем!")
                logger.error(f"📋 Вероятный источник: {suspicious_source}")
                logger.error("📝 Это может быть ошибка в коде или внешнем процессе")
                logger.error("=" * 80)
            else:
                reason = "Остановка пользователем (Ctrl+C)"
                logger.info("✓ Похоже на реальный Ctrl+C от пользователя")
            
            logger.warning("=" * 80)
            
            self.server_logger.log_server_shutdown(reason)
            self._is_running = False
            
            # Отмечаем корректный останов только если это реальный Ctrl+C
            if not is_suspicious:
                self.checkpoint_manager.mark_server_stop(clean=True)
            else:
                # Если это не Ctrl+C, отмечаем как некорректный останов
                logger.warning("⚠️ Останавливаемся как некорректный останов (не Ctrl+C)")
                self.checkpoint_manager.mark_server_stop(clean=False)
            
            self.status_manager.append_status(
                f"Code Agent Server остановлен: {reason}. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            self.server_logger.log_server_shutdown(f"Критическая ошибка: {str(e)}")
            self._is_running = False
            
            # Отмечаем некорректный останов
            self.checkpoint_manager.mark_server_stop(clean=False)
            
            self.status_manager.append_status(
                f"Критическая ошибка: {str(e)}. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
            raise
        finally:
            self._is_running = False
            
            # Останавливаем file watcher
            if self.file_observer:
                try:
                    self.file_observer.stop()
                    self.file_observer.join(timeout=2)
                    logger.info("File watcher остановлен")
                except Exception as e:
                    logger.warning(f"Ошибка при остановке file watcher: {e}")
            
            # Останавливаем HTTP сервер явно
            if self.http_server:
                try:
                    self.http_server.shutdown()
                    logger.info("HTTP сервер остановлен")
                except Exception as e:
                    logger.warning(f"Ошибка при остановке HTTP сервера: {e}")
            elif self.flask_app:
                try:
                    # Flask в отдельном потоке остановится автоматически (daemon=True)
                    logger.info("HTTP сервер будет остановлен автоматически")
                except Exception as e:
                    logger.warning(f"Ошибка при остановке HTTP сервера: {e}")
            
            # Гарантируем сохранение checkpoint при любом выходе
            try:
                if not self.checkpoint_manager.was_clean_shutdown():
                    self.checkpoint_manager.mark_server_stop(clean=False)
            except Exception:
                pass


def run_server():
    """Запуск сервера (используется из main.py)"""
    # Создаем директорию для логов
    Path('logs').mkdir(exist_ok=True)

    # Создаем и запускаем сервер
    server = CodeAgentServer()
    # Для совместимости с main.py, вызываем start как обычный метод
    import asyncio
    asyncio.run(server.start())


if __name__ == "__main__":
    main()