import os
import sys
import time
import logging
import socket
import subprocess
import threading
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime

from crewai import Task, Crew  # type: ignore[import-untyped]

try:
    from flask import Flask, jsonify, request  # type: ignore[import-untyped]
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    from watchdog.observers import Observer  # type: ignore[import-untyped]
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent  # type: ignore[import-untyped]
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

from .config_loader import ConfigLoader
from .status_manager import StatusManager
from .todo_manager import TodoManager, TodoItem
from .llm.llm_manager import LLMManager # Added import

from .agents.executor_agent import create_executor_agent
from .cursor_cli_interface import CursorCLIInterface, create_cursor_cli_interface
from .cursor_file_interface import CursorFileInterface
from .task_logger import TaskLogger, ServerLogger, TaskPhase, Colors

from .session_tracker import SessionTracker
from .checkpoint_manager import CheckpointManager
from .git_utils import auto_push_after_commit

# Импорт Gemini интерфейса
try:
    from .agents.gemini_agent.gemini_cli_interface import GeminiCLIInterface, create_gemini_cli_interface
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Gemini CLI интерфейс недоступен")


class SecurityError(Exception):
    """Исключение для нарушений безопасности"""
    pass


def setup_asyncio_exception_handling():
    """Настройка обработки необработанных исключений в asyncio задачах"""
    def handle_exception(loop, context):
        """Обработчик необработанных исключений в asyncio"""
        exception = context.get('exception')
        if exception:
            error_msg = str(exception)
            # Полностью подавляем httpx cleanup ошибки при завершении
            if ("Event loop is closed" in error_msg and
                any(lib in error_msg.lower() for lib in ['httpx', 'anyio', 'httpcore', 'asyncclient'])):
                # Полностью игнорируем эти ошибки - они безвредны
                return
            # Также подавляем любые httpx cleanup ошибки
            if any(lib in error_msg.lower() for lib in ['httpx', 'anyio', 'httpcore', 'asyncclient']):
                # Игнорируем все httpx связанные ошибки cleanup
                return

        # Для остальных ошибок используем стандартную обработку
        logging.getLogger(__name__).error(f"Необработанное исключение в asyncio задаче: {context}")

    # Устанавливаем обработчик исключений
    asyncio.get_event_loop().set_exception_handler(handle_exception)


def patch_asyncio_for_cleanup():
    """Монkey patch asyncio методов для безопасного закрытия при завершения работы"""
    import asyncio.base_events

    # Сохраняем оригинальные методы
    original_call_soon = asyncio.base_events.BaseEventLoop.call_soon
    original_call_at = asyncio.base_events.BaseEventLoop.call_at
    original_call_later = asyncio.base_events.BaseEventLoop.call_later

    def safe_call_soon(self, callback, *args, context=None):
        """Безопасная версия call_soon которая не падает если loop закрыт"""
        try:
            if self._closed:
                # Loop закрыт - игнорируем вызов
                logger = logging.getLogger(__name__)
                logger.debug("Ignoring call_soon on closed event loop")
                return None
            return original_call_soon(self, callback, *args, context=context)
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger = logging.getLogger(__name__)
                logger.debug("Suppressed call_soon on closed event loop")
                return None
            raise

    def safe_call_at(self, when, callback, *args, context=None):
        """Безопасная версия call_at которая не падает если loop закрыт"""
        try:
            if self._closed:
                logger = logging.getLogger(__name__)
                logger.debug("Ignoring call_at on closed event loop")
                return None
            return original_call_at(self, when, callback, *args, context=context)
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger = logging.getLogger(__name__)
                logger.debug("Suppressed call_at on closed event loop")
                return None
            raise

    def safe_call_later(self, delay, callback, *args, context=None):
        """Безопасная версия call_later которая не падает если loop закрыт"""
        try:
            if self._closed:
                logger = logging.getLogger(__name__)
                logger.debug("Ignoring call_later on closed event loop")
                return None
            return original_call_later(self, delay, callback, *args, context=context)
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger = logging.getLogger(__name__)
                logger.debug("Suppressed call_later on closed event loop")
                return None
            raise

    # Применяем патчи
    asyncio.base_events.BaseEventLoop.call_soon = safe_call_soon  # type: ignore[assignment]
    asyncio.base_events.BaseEventLoop.call_at = safe_call_at  # type: ignore[assignment]
    asyncio.base_events.BaseEventLoop.call_later = safe_call_later  # type: ignore[assignment]

    logging.getLogger(__name__).debug("Applied asyncio cleanup patches")


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
    
    # Константы для обработки ошибок CLI
    MAX_CLI_ERRORS = 3  # Максимальное количество последовательных ошибок перед перезапуском
    CLI_ERROR_DELAY_INITIAL = 30  # Начальная задержка при ошибке (секунды)
    CLI_ERROR_DELAY_INCREMENT = 30  # Увеличение задержки при каждой новой ошибке (секунды)
    
    # Константы таймаутов
    DEFAULT_CLI_TIMEOUT = 300  # Таймаут по умолчанию для CLI (секунды)
    
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
        
        # Инициализация менеджеров
        self.status_manager = StatusManager(self.status_file)
        todo_format = self.config.get('project.todo_format', 'txt')
        self.todo_manager = TodoManager(self.project_dir, todo_format=todo_format)

        # Отложенные задачи (задачи, которые LLM Manager решил отложить до конца списка TODO)
        self.postponed_tasks: List[TodoItem] = []
        
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
        self._waiting_change_detected = False   # Флаг для изменения в моменте ожидания
        self._reload_lock = threading.Lock()
        
        # Счетчик перезапусков
        self._restart_count = 0
        self._restart_count_lock = threading.Lock()

        # Счетчик изменений кода в ожидании (для остановки после 15 изменений подряд)
        self._waiting_change_count = 0
        self._waiting_change_count_lock = threading.Lock()
        
        # Флаг для остановки сервера через API
        self._should_stop = False
        self._stop_lock = threading.Lock()
        
        # Текущее состояние сервера
        self._current_iteration = 0
        self._is_running = False
        
        # Флаг отслеживания активной задачи (для отложенного перезапуска)
        self._task_in_progress = False
        self._task_in_progress_lock = threading.Lock()
        
        # Отслеживание повторяющихся ошибок CLI
        self._cli_error_count = 0  # Счетчик последовательных ошибок
        self._cli_error_lock = threading.Lock()
        self._last_cli_error = None  # Последняя ошибка CLI
        self._cli_error_delay = 0  # Дополнительная задержка при ошибках (секунды)
        self._max_cli_errors = self.MAX_CLI_ERRORS  # Максимальное количество ошибок перед перезапуском
        
        # Отслеживание выполнения ревизии
        self._revision_done = False  # Флаг выполнения ревизии в текущей сессии
        self._revision_lock = threading.Lock()
        
        # Чтение опции CLI интерфейса из конфига
        llm_config = self.config.get('llm', {})
        cli_interface_type = llm_config.get('cli_interface', 'cursor').lower()

        # Валидация значения (дополнительная проверка)
        valid_interfaces = ['cursor', 'gemini']
        if cli_interface_type not in valid_interfaces:
            logger.warning(f"Недопустимое значение cli_interface: {cli_interface_type}, используем cursor по умолчанию")
            cli_interface_type = 'cursor'

        logger.info(f"🔧 Выбран CLI интерфейс: {cli_interface_type}")

        # Инициализация интерфейсов
        self.cli_interface_type = cli_interface_type
        
        # Инициализация Cursor CLI интерфейса
        cursor_config = self.config.get('cursor', {})
        interface_type = cursor_config.get('interface_type', 'cli')
        self.cursor_cli = self._init_cursor_cli()
        self.use_cursor_cli = (
            interface_type == 'cli' and
            self.cursor_cli and
            self.cursor_cli.is_available()
        )

        # Инициализация Gemini CLI интерфейса
        if GEMINI_AVAILABLE:
            gemini_config = self.config.get('gemini', {})
            cli_config = gemini_config.get('cli', {})
            self.gemini_cli = create_gemini_cli_interface(
                project_dir=str(self.project_dir),
                timeout=cli_config.get('timeout', self.DEFAULT_CLI_TIMEOUT), # Use generic timeout
                container_name=cli_config.get('container_name')
            )
            self.use_gemini_cli = (
                self.gemini_cli and
                self.gemini_cli.is_available()
            )
        else:
            self.gemini_cli = None
            self.use_gemini_cli = False
            if cli_interface_type == 'gemini':
                logger.error("Gemini CLI интерфейс недоступен, но выбран в конфиге")

        # Инициализация файлового интерфейса (fallback)
        self.cursor_file = CursorFileInterface(self.project_dir)
        
        # Инициализация логгера сервера
        self.server_logger = ServerLogger()
        
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
        checkpoint_file = server_config.get('checkpoint_file', '.codeagent_checkpoint.json')
        codeagent_dir = Path(__file__).parent.parent  # Директория codeAgent
        self.checkpoint_manager = CheckpointManager(codeagent_dir, checkpoint_file)
        
        # Проверяем, нужно ли восстановление после сбоя
        self._check_recovery_needed()
        
        # Синхронизируем TODO задачи с checkpoint (помечаем выполненные задачи)
        self._sync_todos_with_checkpoint()

    def _validate_path_within_project(self, path: Union[str, Path], operation: str = "access") -> Path:
        """
        Валидация пути - проверка, что путь находится внутри директории проекта

        Args:
            path: Путь для валидации
            operation: Описание операции для логирования

        Returns:
            Path: Нормализованный путь

        Raises:
            SecurityError: Если путь находится вне директории проекта
        """
        if isinstance(path, str):
            path = Path(path)

        # Нормализуем путь (разрешаем .. и .)
        resolved_path = path.resolve()

        # Проверяем, что путь находится внутри project_dir
        try:
            resolved_path.relative_to(self.project_dir.resolve())
        except ValueError:
            logger.error(f"🚨 БЕЗОПАСНОСТЬ: Попытка {operation} файла вне директории проекта!")
            logger.error(f"   Директория проекта: {self.project_dir}")
            logger.error(f"   Запрашиваемый путь: {resolved_path}")
            raise SecurityError(f"Доступ к файлу вне директории проекта запрещен: {resolved_path}")

        return resolved_path

    def _validate_instruction_security(self, instruction: str) -> bool:
        """
        Проверяет инструкцию на наличие потенциально опасных путей

        Args:
            instruction: Текст инструкции для проверки

        Returns:
            True если найдены подозрительные пути, False если безопасно
        """
        import re

        # Паттерны подозрительных путей - только самые опасные
        suspicious_patterns = [
            # Абсолютные пути Windows с буквой диска, начинающиеся с другой буквы
            r'(?<![\w/])[B-Zb-z]:[\\/]',
            # Пути к другим потенциальным проектам (hardcoded примеры)
            r'D:/Space/[a-zA-Z]',
            r'/home/[^/\s]+/',
            r'/Users/[^/\s]+/',
            # Пути к системным директориям
            r'/etc/',
            r'/var/',
            r'/usr/',
            r'C:/Windows/',
            r'C:/Program Files/',
        ]

        for pattern in suspicious_patterns:
            matches = re.findall(pattern, instruction)
            if matches:
                logger.warning(f"🚨 Найден подозрительный путь в инструкции: {pattern}")
                logger.warning(f"   Найденные совпадения: {matches}")
                logger.warning(f"   Инструкция: {instruction[:300]}{'...' if len(instruction) > 300 else ''}")
                return True

        # Проверяем на наличие слишком длинных абсолютных путей
        # Ищем пути длиннее 150 символов, которые могут быть абсолютными
        long_path_pattern = r'[^\s]{150,}'
        long_paths = re.findall(long_path_pattern, instruction)
        for path in long_paths:
            if ('/' in path or '\\' in path) and len(path) > 150:
                logger.warning(f"🚨 Найден слишком длинный путь в инструкции: {path[:100]}...")
                return True

        return False

        # Логируем инициализацию
        cli_status = "недоступен"
        if self.cli_interface_type == 'cursor' and self.cursor_cli and self.cursor_cli.is_available():
            cli_status = "cursor (доступен)"
        elif self.cli_interface_type == 'gemini' and self.gemini_cli and self.gemini_cli.is_available():
            cli_status = "gemini (доступен)"
        elif self.cli_interface_type == 'cursor' and self.cursor_cli:
            cli_status = "cursor (инициализирован, но недоступен)"
        elif self.cli_interface_type == 'gemini' and self.gemini_cli:
            cli_status = "gemini (инициализирован, но недоступен)"
        else:
            cli_status = f"{self.cli_interface_type} (не инициализирован)"

        self.server_logger.log_initialization({
            'project_dir': str(self.project_dir),
            'docs_dir': str(self.docs_dir),
            'cli_interface': cli_status,
            'auto_todo_enabled': self.auto_todo_enabled,
            'max_todo_generations': self.max_todo_generations,
            'checkpoint_enabled': True
        })

        logger.info(f"Code Agent Server инициализирован")
        logger.info(f"Проект: {self.project_dir}")
        logger.info(f"Документация: {self.docs_dir}")
        logger.info(f"Статус файл: {self.status_file}")
        logger.info(f"CLI интерфейс: {cli_status}")
        if self.auto_todo_enabled:
            logger.info(f"Автоматическая генерация TODO включена (макс. {self.max_todo_generations} раз за сессию)")
        logger.info(f"Checkpoint система активирована для защиты от сбоев")
    
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
            logger.warning("Обнаружен некорректный останов сервера")
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
            
            logger.info("Сервер продолжит работу с последней контрольной точки")
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

    def _analyze_task_completion_comment(self, todo_item: TodoItem) -> Dict[str, Any]:
        """
        Анализирует комментарий задачи на предмет незавершенного выполнения

        Args:
            todo_item: Элемент задачи для анализа

        Returns:
            Словарь с результатами анализа:
            {
                "has_partial_completion": bool,  # Есть ли частичное выполнение
                "completed_instructions": int,   # Выполнено инструкций
                "total_instructions": int,       # Всего инструкций
                "completion_ratio": float        # Процент выполнения (0.0-1.0)
            }
        """
        if not todo_item.comment:
            return {
                "has_partial_completion": False,
                "completed_instructions": 0,
                "total_instructions": 0,
                "completion_ratio": 0.0
            }

        import re

        # Ищем паттерн "Выполнено успешно (X/Y инструкций)"
        pattern = r'Выполнено успешно \((\d+)/(\d+) инструкций?\)'
        match = re.search(pattern, todo_item.comment)

        if match:
            completed = int(match.group(1))
            total = int(match.group(2))

            return {
                "has_partial_completion": completed < total,
                "completed_instructions": completed,
                "total_instructions": total,
                "completion_ratio": completed / total if total > 0 else 0.0
            }

        return {
            "has_partial_completion": False,
            "completed_instructions": 0,
            "total_instructions": 0,
            "completion_ratio": 0.0
        }

    async def _check_completed_tasks_for_incomplete_execution(self) -> List[TodoItem]:
        """
        Проверяет выполненные задачи на предмет незавершенного выполнения

        Returns:
            Список выполненных задач, которые нужно доработать
        """
        # Получаем все задачи
        all_tasks = self.todo_manager.get_all_tasks()

        # Фильтруем только выполненные задачи
        completed_tasks = [task for task in all_tasks if task.done and not task.skipped]

        tasks_to_redo = []

        for task in completed_tasks:
            # Анализируем комментарий на предмет незавершенного выполнения
            completion_info = self._analyze_task_completion_comment(task)

            if completion_info["has_partial_completion"]:
                logger.info(f"⚠️ Выполненная задача имеет незавершенное выполнение: '{task.text[:50]}...'" )
                logger.info(f"   Выполнено: {completion_info['completed_instructions']}/{completion_info['total_instructions']} инструкций")

                # Создаем копию задачи для доработки (убираем статус done)
                task_for_redo = TodoItem(
                    text=task.text,
                    level=task.level,
                    done=False,  # Важно: помечаем как невыполненную для повторного выполнения
                    skipped=False,
                    comment=f"Доработка незавершенной задачи: {task.comment}" if task.comment else "Доработка незавершенной задачи"
                )

                # Принимаем решение о доработке через LLM Manager
                decision = await self._decide_incomplete_task_redo(task_for_redo, completion_info)

                if decision == "redo_task":
                    tasks_to_redo.append(task_for_redo)
                    logger.info(f"✅ Задача добавлена для доработки: '{task.text[:50]}...'" )
                else:
                    logger.info(Colors.colorize(f"📋 LLM Manager решил не дорабатывать задачу: '{task.text[:50]}...'", Colors.BRIGHT_MAGENTA))

        return tasks_to_redo

    async def _decide_incomplete_task_redo(self, todo_item: TodoItem, completion_info: Dict[str, Any]) -> str:
        """
        Принимает решение о доработке выполненной, но незавершенной задачи

        Args:
            todo_item: Задача для доработки
            completion_info: Информация о выполнении

        Returns:
            "redo_task" - доработать задачу
            "skip_redo" - пропустить доработку
        """
        completed = completion_info["completed_instructions"]
        total = completion_info["total_instructions"]
        ratio = completion_info["completion_ratio"]

        logger.info(f"🔄 Запрашиваю решение о доработке задачи...")

        # Формируем промпт для LLM Manager
        prompt = f"""
Ты - стратегический планировщик задач разработки. Проанализируй выполненную, но незавершенную задачу и реши, стоит ли её дорабатывать.

ЗАДАЧА: "{todo_item.text}"

СТАТУС: Выполнена, но не полностью ({completed}/{total} инструкций = {ratio:.1%})

КОНТЕКСТ:
- Задача помечена как выполненная в TODO списке
- Но выполнена только часть инструкций
- Осталось выполнить {total - completed} инструкций

АНАЛИЗ СИТУАЦИИ:
- Если задача почти завершена (>90%), имеет смысл её доработать
- Если задача требует значительной доработки (>50% осталось), возможно лучше оставить как есть
- Учитывай: задача уже помечена как выполненная - возможно, оставшаяся часть не критична

ПРИМИ РЕШЕНИЕ:

1. **REDO_TASK** - Доработать задачу, выполнить оставшиеся инструкции
2. **SKIP_REDO** - Оставить как есть, задача считается достаточно выполненной

ОБОСНУЙ решение на основе:
- Степени завершенности задачи
- Важности оставшихся инструкций
- Возможного влияния на проект

ФОРМАТ ОТВЕТА (ТОЛЬКО JSON):
{{
    "decision": "redo_task" | "skip_redo",
    "reason": "Подробное обоснование решения"
}}"""

        try:
            # Используем LLM Manager для принятия решения
            from src.llm.llm_manager import LLMManager

            # Проверяем, есть ли уже инициализированный LLM Manager
            llm_manager = getattr(self, 'llm_manager', None)
            if not llm_manager:
                llm_manager = LLMManager(config_path="config/llm_settings.yaml")

            response = await llm_manager.generate_response(
                prompt=prompt,
                response_format={"type": "json_object"}
            )

            import json
            decision_data = json.loads(response.content)

            decision = decision_data.get('decision', 'skip_redo').lower()
            reason = decision_data.get('reason', 'Решение принято автоматически')

            # Валидируем решение
            if decision not in ['redo_task', 'skip_redo']:
                logger.warning(f"Недопустимое решение о доработке: {decision}, используем skip_redo")
                decision = 'skip_redo'

            logger.info(f"🤖 Решение о доработке: {decision.upper()}")
            logger.info(f"   Причина: {reason}")

            return decision

        except Exception as e:
            logger.warning(f"Не удалось получить решение о доработке от LLM Manager: {e}")
            logger.warning("Пропускаю доработку задачи по умолчанию")
            return "skip_redo"

    async def _decide_task_continuation(self, todo_item: TodoItem, completion_info: Dict[str, Any]) -> str:
        """
        Принимает решение о продолжении незавершенной задачи через LLM Manager

        Args:
            todo_item: Задача с частичным выполнением
            completion_info: Информация о выполнении из _analyze_task_completion_comment

        Returns:
            "continue_task" - продолжить выполнение текущей задачи
            "postpone_task" - отложить задачу до конца списка TODO
        """
        if not completion_info["has_partial_completion"]:
            return "continue_task"

        completed = completion_info["completed_instructions"]
        total = completion_info["total_instructions"]
        ratio = completion_info["completion_ratio"]

        logger.info(f"🔍 Обнаружена незавершенная задача: '{todo_item.text[:50]}...'" )
        logger.info(f"   Выполнено: {completed}/{total} инструкций ({ratio:.1%})")
        logger.info(f"   Запрашиваю решение LLM Manager...")

        # Формируем промпт для LLM Manager
        prompt = f"""
Ты - стратегический планировщик задач разработки. Проанализируй ситуацию и прими решение о продолжении незавершенной задачи.

НЕЗАВЕРШЕННАЯ ЗАДАЧА: "{todo_item.text}"

СТАТУС ВЫПОЛНЕНИЯ: {completed}/{total} инструкций выполнено ({ratio:.1%})

КОНТЕКСТ:
- Задача была начата ранее, но не завершена полностью
- Осталось выполнить {total - completed} инструкций
- Текущий прогресс: {ratio:.1%}

АНАЛИЗ СИТУАЦИИ:
- Если задача близка к завершению (>80%), имеет смысл продолжить немедленно
- Если задача на ранней стадии (<50%), возможно лучше отложить до конца списка TODO
- Учитывай логическую последовательность: некоторые задачи могут требовать завершения перед началом других

ПРИМИ РЕШЕНИЕ:

1. **CONTINUE_TASK** - Продолжить выполнение этой задачи немедленно (следующая инструкция)
2. **POSTPONE_TASK** - Отложить задачу до конца всего списка TODO

ОБОСНУЙ решение на основе:
- Текущего прогресса выполнения
- Логической последовательности задач
- Потенциальной сложности оставшихся инструкций

ФОРМАТ ОТВЕТА (ТОЛЬКО JSON):
{{
    "decision": "continue_task" | "postpone_task",
    "reason": "Подробное обоснование решения"
}}"""

        try:
            # Используем LLM Manager для принятия решения
            from src.llm.llm_manager import LLMManager

            # Проверяем, есть ли уже инициализированный LLM Manager
            llm_manager = getattr(self, 'llm_manager', None)
            if not llm_manager:
                llm_manager = LLMManager(config_path="config/llm_settings.yaml")

            response = await llm_manager.generate_response(
                prompt=prompt,
                response_format={"type": "json_object"}
            )

            import json
            decision_data = json.loads(response.content)

            decision = decision_data.get('decision', 'continue_task').lower()
            reason = decision_data.get('reason', 'Решение принято автоматически')

            # Валидируем решение
            if decision not in ['continue_task', 'postpone_task']:
                logger.warning(f"Недопустимое решение о продолжении задачи: {decision}, используем continue_task")
                decision = 'continue_task'

            logger.info(Colors.colorize(f"🤖 LLM Manager решил: {decision.upper()}", Colors.BRIGHT_MAGENTA))
            logger.info(Colors.colorize(f"   Причина: {reason}", Colors.BRIGHT_MAGENTA))

            return decision

        except Exception as e:
            logger.warning(f"Не удалось получить решение от LLM Manager: {e}")
            logger.warning("Продолжаю выполнение задачи по умолчанию")
            return "continue_task"
    
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
            timeout = cli_config.get('timeout', self.DEFAULT_CLI_TIMEOUT)
            headless = cli_config.get('headless', True)
            container_name = cli_config.get('container_name')

            if not container_name:
                raise ValueError("container_name должен быть указан в конфигурации config/config.yaml в разделе cursor.cli.container_name")

            logger.debug(f"Инициализация Cursor CLI: timeout={timeout} секунд (из конфига: {cli_config.get('timeout', 'не указан')}, дефолт: {self.DEFAULT_CLI_TIMEOUT})")

            # Передаем директорию проекта и роль агента для настройки контекста
            agent_config = self.config.get('agent', {})
            cli_interface = create_cursor_cli_interface(
                cli_path=cli_path,
                timeout=timeout,
                headless=headless,
                container_name=container_name,
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
    
    def execute_cli_instruction(
        self,
        instruction: str,
        task_id: str,
        interface_type: str,
        timeout: Optional[int] = None
    ) -> dict:
        """
        Выполнить инструкцию через указанный CLI интерфейс с graceful fallback

        Args:
            instruction: Текст инструкции для выполнения
            task_id: Идентификатор задачи
            interface_type: Тип интерфейса ('cursor', 'gemini')
            timeout: Таймаут выполнения (если None - используется из конфига)

        Returns:
            Словарь с результатом выполнения
        """
        logger.info(f"🔧 Начинаем выполнение инструкции для задачи {task_id} через {interface_type} CLI")
        logger.debug(f"📝 Текст инструкции: {instruction[:200]}{'...' if len(instruction) > 200 else ''}")
        logger.debug(f"⏱️ Таймаут: {timeout} сек, рабочая директория: {self.project_dir}")

        # ВАЛИДАЦИЯ БЕЗОПАСНОСТИ: проверяем инструкцию на наличие подозрительных путей
        if self._validate_instruction_security(instruction):
            logger.warning("🚨 Инструкция содержит подозрительные пути, отклонена из соображений безопасности")
            return {
                "task_id": task_id,
                "success": False,
                "error": "Инструкция отклонена из соображений безопасности",
                "cli_available": True
            }

        # Попытка выполнить через основной интерфейс
        primary_result = None
        if interface_type == 'cursor' and self.cursor_cli and self.cursor_cli.is_available():
            logger.debug("Попытка выполнения через основной интерфейс: cursor")
            primary_result = self._execute_cursor_instruction(instruction, task_id, timeout)
            if primary_result.get("success"):
                return primary_result
        elif interface_type == 'gemini' and self.gemini_cli and self.gemini_cli.is_available():
            logger.debug("Попытка выполнения через основной интерфейс: gemini")
            primary_result = self._execute_gemini_instruction(instruction, task_id, timeout)
            if primary_result.get("success"):
                return primary_result

        # Основной интерфейс недоступен или неудачен - пробуем fallback
        logger.warning(f"⚠️ Основной интерфейс {interface_type} недоступен или неудачен, пробуем fallback")

        fallback_result = None
        if interface_type == 'cursor' and self.gemini_cli and self.gemini_cli.is_available():
            logger.info("🔄 Fallback: cursor -> gemini")
            fallback_result = self._execute_gemini_instruction(instruction, task_id, timeout)
            if fallback_result.get("success"):
                logger.info("✅ Fallback успешен: gemini")
                return fallback_result
        elif interface_type == 'gemini' and self.cursor_cli and self.cursor_cli.is_available():
            logger.info("🔄 Fallback: gemini -> cursor")
            fallback_result = self._execute_cursor_instruction(instruction, task_id, timeout)
            if fallback_result.get("success"):
                logger.info("✅ Fallback успешен: cursor")
                return fallback_result

        # Все интерфейсы недоступны или неудачны
        error_msg = f"Все CLI интерфейсы недоступны или неудачны"
        if primary_result:
            error_msg += f" (основной: {primary_result.get('error_message', 'неизвестная ошибка')})"
        if fallback_result:
            error_msg += f" (fallback: {fallback_result.get('error_message', 'неизвестная ошибка')})"

        logger.error(f"❌ {error_msg}")
        return {
            "task_id": task_id,
            "success": False,
            "error": error_msg,
            "cli_available": False
        }

    def _execute_cursor_instruction(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int] = None
    ) -> dict:
        """
        Выполнить инструкцию через Cursor CLI
        """
        if not self.cursor_cli:
            logger.error("❌ Cursor CLI объект не инициализирован")
            return {
                "task_id": task_id,
                "success": False,
                "error": "Cursor CLI объект не инициализирован",
                "cli_available": False
            }

        if not self.cursor_cli.is_available():
            logger.warning("⚠️ Cursor CLI недоступен")
            return {
                "task_id": task_id,
                "success": False,
                "error": "Cursor CLI недоступен",
                "cli_available": False
            }

        logger.info(f"✅ Cursor CLI доступен, выполняем инструкцию для задачи {task_id}")

        start_time = time.time()
        logger.info(f"🚀 Запускаем выполнение инструкции в Cursor CLI...")

        result = self.cursor_cli.execute_instruction(
            instruction=instruction,
            task_id=task_id,
            working_dir=str(self.project_dir),
            timeout=timeout
        )

        execution_time = time.time() - start_time
        logger.info(f"⏱️ Выполнение инструкции завершено за {execution_time:.2f} сек")

        if result["success"]:
            logger.info(f"✅ Инструкция для задачи {task_id} выполнена успешно")
            logger.debug(f"📄 Результат: stdout={len(result.get('stdout', ''))} символов, return_code={result.get('return_code')}")
        else:
            logger.error(f"❌ Инструкция для задачи {task_id} завершилась с ошибкой")
            logger.error(f"🔍 Детали ошибки: {result.get('error_message', 'неизвестная ошибка')}")
            logger.error(f"🔍 Stdout: {result.get('stdout', '')[:500]}{'...' if len(result.get('stdout', '')) > 500 else ''}")
            logger.error(f"🔍 Stderr: {result.get('stderr', '')[:500]}{'...' if len(result.get('stderr', '')) > 500 else ''}")
            logger.error(f"🔍 Return code: {result.get('return_code')}")

        return result

    def _execute_gemini_instruction(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int] = None
    ) -> dict:
        """
        Выполнить инструкцию через Gemini CLI
        """
        if not self.gemini_cli:
            logger.error("❌ Gemini CLI объект не инициализирован")
            return {
                "task_id": task_id,
                "success": False,
                "error": "Gemini CLI объект не инициализирован",
                "cli_available": False
            }

        if not self.gemini_cli.is_available():
            logger.warning("⚠️ Gemini CLI недоступен")
            return {
                "task_id": task_id,
                "success": False,
                "error": "Gemini CLI недоступен",
                "cli_available": False
            }

        logger.info(f"✅ Gemini CLI доступен, выполняем инструкцию для задачи {task_id}")

        start_time = time.time()
        logger.info(f"🚀 Запускаем выполнение инструкции в Gemini CLI...")

        result = self.gemini_cli.execute_instruction(
            instruction=instruction,
            task_id=task_id,
            working_dir=str(self.project_dir),
            timeout=timeout
        )

        execution_time = time.time() - start_time
        logger.info(f"⏱️ Выполнение инструкции завершено за {execution_time:.2f} сек")

        if result["success"]:
            logger.info(f"✅ Инструкция для задачи {task_id} выполнена успешно")
            logger.debug(f"📄 Результат: stdout={len(result.get('stdout', ''))} символов, return_code={result.get('return_code')}")
        else:
            logger.error(f"❌ Инструкция для задачи {task_id} завершилась с ошибкой")
            logger.error(f"🔍 Детали ошибки: {result.get('error_message', 'неизвестная ошибка')}")
            logger.error(f"🔍 Stdout: {result.get('stdout', '')[:500]}{'...' if len(result.get('stdout', '')) > 500 else ''}")
            logger.error(f"🔍 Stderr: {result.get('stderr', '')[:500]}{'...' if len(result.get('stderr', '')) > 500 else ''}")
            logger.error(f"🔍 Return code: {result.get('return_code')}")

        return result
    
    def _execute_cli_instruction_with_retry(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int],
        task_logger: TaskLogger,
        instruction_num: int,
        interface_type: str
    ) -> dict:
        """
        Выполнить инструкцию через указанный CLI с обработкой повторяющихся ошибок

        Args:
            instruction: Текст инструкции
            task_id: ID задачи
            timeout: Таймаут выполнения
            task_logger: Логгер задачи
            instruction_num: Номер инструкции
            interface_type: Тип интерфейса ('cursor' или 'gemini')

        Returns:
            Словарь с результатом выполнения
        """
        max_retries = 2
        retry_delay = 5  # секунды

        for attempt in range(max_retries + 1):
            try:
                logger.info(f"🔄 Попытка {attempt + 1}/{max_retries + 1} выполнения инструкции {instruction_num} для задачи {task_id} через {interface_type} CLI")

                # Choose the appropriate executor based on interface_type
                if interface_type == 'cursor':
                    executor_function = self._execute_cursor_instruction
                elif interface_type == 'gemini':
                    executor_function = self._execute_gemini_instruction
                else:
                    return {
                        "task_id": task_id,
                        "success": False,
                        "error": f"Неизвестный тип интерфейса: {interface_type}",
                        "cli_available": False
                    }

                result = executor_function(
                    instruction=instruction,
                    task_id=task_id,
                    timeout=timeout,
                )

                if result.get("success"):
                    logger.info(f"✅ Инструкция {instruction_num} выполнена успешно на попытке {attempt + 1}")
                    return result

                # Анализируем ошибку для принятия решения о повторной попытке
                error_message = result.get('error_message', '')
                stderr = result.get('stderr', '')

                # Проверяем типы ошибок, при которых стоит повторить
                should_retry = False
                if "timeout" in error_message.lower() or "timeout" in stderr.lower():
                    logger.warning(f"⏰ Таймаут при выполнении инструкции {instruction_num}, повторяем...")
                    should_retry = True
                elif "connection" in error_message.lower() or "network" in error_message.lower():
                    logger.warning(f"🌐 Сетевая ошибка при выполнении инструкции {instruction_num}, повторяем...")
                    should_retry = True
                elif "cli not available" in error_message.lower():
                    logger.warning(f"🔌 {interface_type.capitalize()} CLI недоступен при выполнении инструкции {instruction_num}, повторяем...")
                    should_retry = True

                if should_retry and attempt < max_retries:
                    logger.info(f"⏳ Ждем {retry_delay} сек перед повторной попыткой...")
                    time.sleep(retry_delay)
                    continue

                # Если не стоит повторять или исчерпаны попытки
                logger.error(f"❌ Инструкция {instruction_num} завершилась с ошибкой после {attempt + 1} попыток")
                return result

            except Exception as e:
                logger.error(f"💥 Неожиданная ошибка при выполнении инструкции {instruction_num} на попытке {attempt + 1}: {e}")
                if attempt < max_retries:
                    logger.info(f"⏳ Ждем {retry_delay} сек перед повторной попыткой...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        "task_id": task_id,
                        "success": False,
                        "error": f"Неожиданная ошибка: {str(e)}",
                        "cli_available": False
                    }

        # Это не должно достигаться, но на всякий случай
        return {
            "task_id": task_id,
            "success": False,
            "error": "Исчерпаны все попытки выполнения инструкции",
            "cli_available": False
        }

    async def _safe_close_llm_manager(self, llm_manager):
        """
        Безопасно закрывает LLM manager, обрабатывая все исключения
        """
        if not llm_manager:
            return

        try:
            logger.debug("Безопасное закрытие LLM manager...")
            await asyncio.wait_for(llm_manager.close(), timeout=3.0)
            logger.debug("LLM manager закрыт успешно")
        except asyncio.TimeoutError:
            logger.warning("Таймаут при закрытии LLM manager")
        except asyncio.CancelledError:
            logger.warning("Закрытие LLM manager было отменено")
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.warning("Event loop закрыт при закрытии LLM manager - пропускаем")
            elif "no running event loop" in str(e).lower():
                logger.warning("Нет запущенного event loop при закрытии LLM manager - пропускаем")
            else:
                logger.warning(f"Runtime error при закрытии LLM manager: {e}")
        except ConnectionError as e:
            logger.warning(f"Сетевая ошибка при закрытии LLM manager: {e}")
        except Exception as e:
            logger.warning(f"Неожиданная ошибка при закрытии LLM manager: {e}")

    def _execute_special_instruction_handling(
        self,
        instruction: str,
        task_id: str,
        timeout: Optional[int],
        task_logger: TaskLogger,
        instruction_num: int,
        active_cli: Union[CursorCLIInterface, GeminiCLIInterface],
        interface_type: str
    ) -> dict:
        """
        Выполнить инструкцию через CLI с особой обработкой для свободных инструкций (например, billing error).

        Для свободных инструкций billing error не активирует fallback,
        а считается успешным выполнением (проблема аккаунта, не инструкции).
        """
        logger.info(f"🔧 Начинаем выполнение свободной инструкции для задачи {task_id} через {interface_type.capitalize()} CLI")
        logger.debug(f"📝 Текст инструкции: {instruction[:200]}{'...' if len(instruction) > 200 else ''}")
        logger.debug(f"⏱️ Таймаут: {timeout} сек, рабочая директория: {self.project_dir}")

        if not active_cli:
            logger.error(f"❌ {interface_type.capitalize()} CLI объект не инициализирован")
            return {
                "task_id": task_id,
                "success": False,
                "error": f"{interface_type.capitalize()} CLI объект не инициализирован",
                "cli_available": False
            }

        if not active_cli.is_available():
            logger.warning(f"⚠️ {interface_type.capitalize()} CLI недоступен")
            return {
                "task_id": task_id,
                "success": False,
                "error": f"{interface_type.capitalize()} CLI недоступен",
                "cli_available": False
            }

        logger.info(f"✅ {interface_type.capitalize()} CLI доступен, выполняем свободную инструкцию для задачи {task_id}")

        start_time = time.time()
        logger.info(f"🚀 Запускаем выполнение свободной инструкции в {interface_type.capitalize()} CLI...")

        result = active_cli.execute_instruction(
            instruction=instruction,
            task_id=task_id,
            working_dir=str(self.project_dir),
            timeout=timeout
        )

        execution_time = time.time() - start_time
        logger.info(f"⏱️ Выполнение инструкции завершено за {execution_time:.2f} сек")

        # Особая обработка для свободных инструкций: billing error считаем успешным
        if not result["success"]:
            error_message = result.get('error_message', '')
            stderr = result.get('stderr', '')

            # Проверяем, является ли это billing error
            stderr_lower = stderr.lower()
            is_billing_error = (
                "unpaid invoice" in stderr_lower or
                "pay your invoice" in stderr_lower or
                "usage limit" in stderr_lower or
                "spend limit" in stderr_lower
            )

            if is_billing_error:
                logger.warning(f"⚠️ Billing error в свободной инструкции - считаем успешным (проблема аккаунта)")
                logger.warning(f"📄 Свободная инструкция выполнена с billing error - результат будет сгенерирован fallback системой")

                # Возвращаем "успешный" результат для свободной инструкции
                # Fallback система должна была активироваться и выполнить инструкцию
                return {
                    "task_id": task_id,
                    "success": True,  # Считаем успешным несмотря на billing error
                    "stdout": result.get('stdout', ''),
                    "stderr": stderr,
                    "return_code": result.get('return_code', 1),
                    "billing_error_ignored": True,  # Флаг что billing error был проигнорирован
                    "cli_available": True
                }

        # Для остальных ошибок возвращаем как есть
        if result["success"]:
            logger.info(f"✅ Свободная инструкция для задачи {task_id} выполнена успешно")
            logger.debug(f"📄 Результат: stdout={len(result.get('stdout', ''))} символов, return_code={result.get('return_code')}")
        else:
            logger.error(f"❌ Свободная инструкция для задачи {task_id} завершилась с ошибкой")
            logger.error(f"🔍 Детали ошибки: {result.get('error_message', 'неизвестная ошибка')}")
            logger.error(f"🔍 Stdout: {result.get('stdout', '')[:500]}{'...' if len(result.get('stdout', '')) > 500 else ''}")
            logger.error(f"🔍 Stderr: {result.get('stderr', '')[:500]}{'...' if len(result.get('stderr', '')) > 500 else ''}")
            logger.error(f"🔍 Return code: {result.get('return_code')}")

        return result

    def _is_critical_cli_error(self, error_message: str) -> bool:
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
            "api key expired",
            "user location is not supported" # Gemini-специфичная ошибка
        ]
        return any(keyword in error_lower for keyword in critical_keywords)
    
    def _is_unexpected_cli_error(self, error_message: str) -> bool:
        """
        Проверка, является ли ошибка непредвиденной (требует перезапуска Docker)
        
        Непредвиденные ошибки - это ошибки, которые могут быть исправлены перезапуском Docker,
        например, когда CLI недоступен или возвращает неизвестную ошибку.
        
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
    
    def _handle_cli_error(self, error_message: str, task_logger: TaskLogger) -> bool:
        """
        Обработка ошибки CLI с учетом повторяющихся ошибок
        
        Args:
            error_message: Сообщение об ошибке
            task_logger: Логгер задачи
            
        Returns:
            True если можно продолжать работу, False если нужно остановить сервер
        """
        # Проверяем, является ли ошибка критической
        is_critical = self._is_critical_cli_error(error_message)
        
        # Проверяем, является ли ошибка непредвиденной (требует немедленного перезапуска Docker)
        is_unexpected = self._is_unexpected_cli_error(error_message)
        logger.info(f"Обработка ошибки CLI: error_message='{error_message}', is_critical={is_critical}, is_unexpected={is_unexpected}")
        
        with self._cli_error_lock:
            # Проверяем, та же ли ошибка (сравниваем по первым 100 символам для группировки похожих ошибок)
            error_key = error_message[:100] if error_message else ""
            if self._last_cli_error == error_key:
                self._cli_error_count += 1
            else:
                # Новая ошибка - сбрасываем счетчик и задержку
                self._cli_error_count = 1
                self._last_cli_error = error_key
                self._cli_error_delay = self.CLI_ERROR_DELAY_INITIAL  # Начинаем с начальной задержки для новой ошибки
            
            # Для критических ошибок - останавливаем сервер сразу (не ждем повторений)
            if is_critical:
                logger.error("--- ")
                logger.error(f"Критическая ошибка CLI: {error_message}")
                logger.error("Критическая ошибка не исправится перезапуском - останавливаем сервер немедленно")
                logger.error("--- ")
                task_logger.log_error(f"Критическая ошибка CLI (не исправится): {error_message}", Exception(error_message))
                # Останавливаем сервер немедленно для критических ошибок
                self._stop_server_due_to_cli_errors(error_message)
                return False
            
            # Для непредвиденных ошибок - перезапускаем Docker при первой или второй ошибке (если используется Docker)
            # Это позволяет перезапустить Docker даже если первая ошибка была другой
            logger.info(f"Проверка непредвиденной ошибки: is_unexpected={is_unexpected}, счетчик={self._cli_error_count}")
            if is_unexpected and self._cli_error_count <= 2:
                logger.info(f"Обнаружена непредвиденная ошибка (счетчик: {self._cli_error_count}), проверяем использование Docker...")
                
                # Dynamically get the active CLI interface
                active_cli_interface = None
                if self.cli_interface_type == 'cursor':
                    active_cli_interface = self.cursor_cli
                elif self.cli_interface_type == 'gemini':
                    active_cli_interface = self.gemini_cli

                if active_cli_interface and hasattr(active_cli_interface, 'use_docker') and active_cli_interface.use_docker:
                    logger.warning(f"Непредвиденная ошибка CLI (#{self._cli_error_count}): {error_message}")
                    logger.warning("Перезапускаем Docker контейнер из-за непредвиденной ошибки...")
                    task_logger.log_warning(f"Непредвиденная ошибка CLI - перезапуск Docker: {error_message}")
                        
                    # Перезапускаем Docker контейнер и очищаем диалоги
                    self._safe_print("Попытка перезапуска Docker контейнера из-за непредвиденной ошибки...")
                    if self._restart_cli_environment():
                        success_msg = "Docker контейнер перезапущен после непредвиденной ошибки. Сбрасываем счетчик ошибок."
                        self._safe_print(success_msg)
                        logger.info(success_msg)
                        task_logger.log_info("Docker контейнер перезапущен после непредвиденной ошибки")
                        # Сбрасываем счетчик после перезапуска
                        self._cli_error_count = 0
                        self._cli_error_delay = 0
                        self._last_cli_error = None
                        return True
                    else:
                        logger.warning("Перезапуск Docker не удался, продолжаем с обычной обработкой ошибки")
                else:
                    logger.warning(f"Docker не используется для {self.cli_interface_type}, пропускаем перезапуск для непредвиденной ошибки")
            elif is_unexpected:
                logger.debug(f"Непредвиденная ошибка обнаружена, но счетчик ошибок ({self._cli_error_count}) > 2, пропускаем перезапуск")
            else:
                logger.debug(f"Ошибка не является непредвиденной (is_unexpected=False), обычная обработка")
            
            # Увеличиваем задержку на +30 секунд при каждой повторяющейся ошибке
            # При первой ошибке задержка уже установлена в 30 секунд выше
            # При каждой следующей повторяющейся ошибке добавляем еще 30 секунд
            if self._cli_error_count > 1:
                self._cli_error_delay += self.CLI_ERROR_DELAY_INCREMENT
            
            # The delay needs to be applied here, after the decision to retry or stop
            if self._cli_error_delay > 0:
                logger.info(f"Ожидание {self._cli_error_delay} секунд перед следующим запросом (из-за предыдущих ошибок CLI)")
                task_logger.log_info(f"Задержка {self._cli_error_delay} сек перед следующим запросом из-за ошибок CLI")
                
                for i in range(self._cli_error_delay):
                    time.sleep(1)
                    if self._should_stop:
                        logger.warning(f"Получен запрос на остановку во время задержки из-за ошибок CLI (через {i+1} секунд)")
                        return False
                
                if self._should_stop:
                    logger.warning("Получен запрос на остановку после задержки из-за ошибок CLI")
                    return False
            
            logger.warning(f"Ошибка CLI #{self._cli_error_count}: {error_message}")
            logger.warning(f"Дополнительная задержка перед следующим запросом: {self._cli_error_delay} секунд")
            task_logger.log_warning(f"Ошибка CLI #{self._cli_error_count}, задержка перед следующим запросом: {self._cli_error_delay}с")
            
            # Если ошибка повторилась 3 раза - перезапускаем Docker и очищаем диалоги
            if self._cli_error_count >= self._max_cli_errors:
                # Выводим в консоль и в лог
                critical_msg = "=" * 80 + "\n"
                critical_msg += f"КРИТИЧЕСКАЯ СИТУАЦИЯ: Ошибка CLI повторилась {self._cli_error_count} раз\n"
                critical_msg += f"Последняя ошибка: {error_message}\n"
                critical_msg += "=" * 80 + "\n"
                critical_msg += "РЕКОМЕНДАЦИИ:\n"
                critical_msg += f"1. Проверьте состояние аккаунта для {self.cli_interface_type.capitalize()}\n"
                critical_msg += "2. Проверьте доступность Docker контейнера (если используется)\n"
                critical_msg += f"3. Проверьте логи {self.cli_interface_type.capitalize()} для деталей ошибки\n"
                critical_msg += "4. Перезапустите сервер вручную после устранения проблемы\n"
                critical_msg += "=" * 80
                
                # Выводим в консоль (с защитой от ошибок потока)
                self._safe_print("\n" + critical_msg + "\n")
                
                # Логируем
                logger.error(critical_msg)
                
                task_logger.log_error(f"Критическая ошибка: повтор {self._cli_error_count} раз", Exception(error_message))
                
                # Перезапускаем Docker контейнер и очищаем диалоги
                self._safe_print("Попытка перезапуска Docker контейнера и очистки диалогов...")
                if self._restart_cli_environment():
                    success_msg = "✅ Docker контейнер и диалоги перезапущены. Сбрасываем счетчик ошибок."
                    self._safe_print(success_msg)
                    logger.info(success_msg)
                    task_logger.log_info("Docker контейнер перезапущен после критической ошибки")
                    # Сбрасываем счетчик после перезапуска
                    self._cli_error_count = 0
                    self._cli_error_delay = 0
                    self._last_cli_error = None
                    return True
                else:
                    # Перезапуск не помог - останавливаем сервер
                    self._safe_print("Перезапуск не помог. Останавливаем сервер...")
                    task_logger.log_error("Критическая ошибка: перезапуск не помог, сервер остановлен", Exception(error_message))
                    
                    # Останавливаем сервер
                    self._stop_server_due_to_cli_errors(error_message)
                    return False
            
            return True
    
    def _restart_cli_environment(self) -> bool:
        """
        Перезапустить окружение для текущего CLI (например, Docker контейнер)
        
        Returns:
            True если Перезапуск успешен, False иначе
        """
        logger.info("--- ")
        logger.info(f"Перезапуск окружения для CLI: {self.cli_interface_type}")
        logger.info("--- ")

        if self.cli_interface_type == 'cursor':
            cli_interface = self.cursor_cli
            config_name = 'cursor'
        elif self.cli_interface_type == 'gemini':
            cli_interface = self.gemini_cli
            config_name = 'gemini'
        else:
            logger.warning(f"Неизвестный тип CLI: {self.cli_interface_type}, перезапуск невозможен")
            return False

        if not cli_interface:
            logger.warning(f"Интерфейс для {self.cli_interface_type} не инициализирован, перезапуск невозможен")
            return False

        try:
            # 1. Очищаем открытые диалоги (если метод есть)
            if hasattr(cli_interface, 'prepare_for_new_task'):
                logger.info("Шаг 1: Очистка открытых диалогов...")
                cleanup_result = cli_interface.prepare_for_new_task()
                if cleanup_result:
                    logger.info("  ✓ Диалоги очищены")
                else:
                    logger.warning("  ⚠ Не удалось полностью очистить диалоги")
            
            # 2. Перезапускаем Docker контейнер (если используется)
            logger.info("Шаг 2: Перезапуск Docker контейнера (если применимо)...")
            if hasattr(cli_interface, 'use_docker') and cli_interface.use_docker:
                # Получаем конфигурацию CLI
                cli_main_config = self.config.get(config_name, {})
                cli_config = cli_main_config.get('cli', {})
                container_name = cli_config.get('container_name')

                if not container_name:
                    logger.error(f"  ✗ Имя контейнера не найдено в конфигурации для {config_name}")
                    return False
                
                compose_file = Path(__file__).parent.parent / "docker" / f"docker-compose.{config_name}.yml"
                # Пробуем старое имя файла для обратной совместимости
                if not compose_file.exists():
                    compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
                    if not compose_file.exists():
                        logger.error(f"  ✗ Docker compose файл не найден: docker-compose.{config_name}.yml")
                        return False
                
                try:
                    import subprocess
                    
                    # Останавливаем контейнер
                    logger.info(f"  Остановка контейнера {container_name}...")
                    stop_result = subprocess.run(["docker", "stop", container_name], capture_output=True, text=True, timeout=15)
                    if stop_result.returncode == 0:
                        logger.info(f"  ✓ Контейнер {container_name} остановлен")
                    else:
                        logger.warning(f"  ⚠ Не удалось остановить контейнер (возможно, уже был остановлен): {stop_result.stderr[:200]}")
                    
                    time.sleep(2)
                    
                    # Запускаем контейнер заново
                    logger.info(f"  Запуск контейнера {container_name}...")
                    up_result = subprocess.run(["docker", "compose", "-f", str(compose_file), "up", "-d"], capture_output=True, text=True, timeout=30)
                    
                    if up_result.returncode == 0:
                        logger.info(f"  ✓ Контейнер {container_name} запущен")
                        time.sleep(5)
                        
                        # Проверяем, что контейнер отвечает
                        check_result = subprocess.run(["docker", "exec", container_name, "echo", "ok"], capture_output=True, timeout=5)
                        if check_result.returncode == 0:
                            logger.info("  ✓ Контейнер работает корректно")
                            # Дополнительные проверки, специфичные для CLI (например, установка agent)
                            if self.cli_interface_type == 'cursor':
                                logger.info("  Проверка установки Cursor Agent...")
                                agent_check = subprocess.run(["docker", "exec", container_name, "/root/.local/bin/agent", "--version"], capture_output=True, text=True, timeout=10)
                                if agent_check.returncode != 0:
                                    logger.warning("  ⚠ Cursor Agent не найден, пытаемся переустановить...")
                                    reinstall_cmd = "curl https://cursor.com/install -fsS | bash"
                                    subprocess.run(["docker", "exec", container_name, "bash", "-c", reinstall_cmd], capture_output=True, text=True, timeout=60)
                            return True
                        else:
                            logger.warning(f"  ⚠ Контейнер запущен, но не отвечает: {check_result.stderr[:200]}")
                    else:
                        logger.error(f"  ✗ Не удалось запустить контейнер: {up_result.stderr[:200]}")
                except Exception as e:
                    logger.error(f"  ✗ Ошибка при перезапуске Docker: {e}", exc_info=True)
                
                return False
            else:
                logger.info("  Docker не используется для этого CLI, пропускаем перезапуск контейнера")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при перезапуске окружения CLI: {e}", exc_info=True)
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
        except (OSError, IOError, ValueError) as e:
            # Если stdout недоступен (закрыт или обернут), используем stderr
            try:
                sys.stderr.write(message + (end if end else ""))
                sys.stderr.flush()
            except (OSError, IOError, ValueError):
                # Если и stderr недоступен, просто пропускаем вывод в консоль
                # Логирование все равно произойдет через logger
                pass
    
    def _stop_server_due_to_cli_errors(self, error_message: str):
        """
        Остановить сервер из-за критических ошибок CLI
        
        Args:
            error_message: Сообщение об ошибке
        """
        # Выводим в консоль и в лог
        error_msg = "=" * 80 + "\n"
        error_msg += f"Остановка сервера из-за критических ошибок CLI ({self.cli_interface_type})\n"
        error_msg += "=" * 80 + "\n"
        error_msg += f"Ошибка повторяется: {error_message}\n"
        error_msg += f"Количество повторений: {self._cli_error_count}\n"
        error_msg += "Перезапуск окружения CLI не помог\n"
        error_msg += "=" * 80 + "\n"
        error_msg += "РЕКОМЕНДАЦИИ:\n"
        error_msg += f"1. Проверьте состояние аккаунта для {self.cli_interface_type.capitalize()}\n"
        error_msg += "2. Проверьте доступность Docker контейнера (если используется)\n"
        error_msg += f"3. Проверьте логи {self.cli_interface_type.capitalize()} для деталей ошибки\n"
        error_msg += "4. Перезапустите сервер вручную после устранения проблемы\n"
        error_msg += "=" * 80
        
        # Выводим в консоль (с защитой от ошибок потока)
        self._safe_print("\n" + error_msg + "\n")
        
        # Логируем
        logger.error(error_msg)
        
        # Обновляем статус
        self.status_manager.append_status(
            f"КРИТИЧЕСКАЯ ОШИБКА: Ошибка CLI повторяется ({self._cli_error_count} раз). "
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
            f"Остановка из-за критических ошибок CLI: {error_message} (повтор {self._cli_error_count} раз)"
        )
    
    def is_active_cli_available(self) -> bool:
        """
        Проверка доступности активного CLI
        
        Returns:
            True если активный CLI доступен, False иначе
        """
        if self.cli_interface_type == 'cursor':
            return self.cursor_cli is not None and self.cursor_cli.is_available()
        elif self.cli_interface_type == 'gemini':
            return self.gemini_cli is not None and self.gemini_cli.is_available()
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
    
    def _get_instruction_template(self, task_type: str, instruction_id: Union[int, str]) -> Optional[Dict[str, Any]]:
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
        # Исключаем системные инструкции со строковыми ID (report-check, free)
        valid_instructions = [
            instr for instr in task_instructions
            if isinstance(instr, dict) and 'instruction_id' in instr and isinstance(instr.get('instruction_id'), int)
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
        Ожидание файла результата от CLI
        
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

        # ВАЛИДАЦИЯ БЕЗОПАСНОСТИ: проверяем, что путь находится внутри project_dir
        try:
            file_path = self._validate_path_within_project(file_path, f"ожидание файла результата для задачи {task_id}")
        except SecurityError as e:
            logger.error(str(e))
            return {
                "success": False,
                "file_path": str(file_path),
                "content": None,
                "wait_time": 0,
                "error": "Нарушение безопасности: попытка доступа к файлу вне директории проекта"
            }

        # Автоматически создаем директорию для файла результата
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Создана директория для файла результата: {file_path.parent}")

        # ДОПОЛНИТЕЛЬНО: Проверяем также `results_dir` (или аналогичную) на случай, если файл создан через файловый интерфейс
        # Для обобщения - будем проверять либо `docs/results` либо `project_dir/results`
        results_dir_candidates = [self.project_dir / "docs" / "results", self.project_dir / "results"]
        
        result_patterns = [
            f"result_{task_id}.txt",
            f"result_{task_id}.md",
            f"{task_id}.txt",
            f"{task_id}.md",
            f"result_full_cycle_{task_id}.txt",
            f"result_full_cycle_{task_id}.md"
        ]
        
        logger.info(f"Ожидание файла результата: {file_path} (timeout: {timeout}s)")
        logger.debug(f"Контрольная фраза: '{control_phrase}'")
        logger.debug(f"Также проверяем дополнительные директории: {results_dir_candidates} на наличие файлов: {result_patterns}")

        # Во время ожидания результата считаем, что "инструкция выполняется",
        # чтобы автоперезапуск не обрывал ожидание (перезапуск будет отложен).
        with self._task_in_progress_lock:
            prev_task_in_progress = self._task_in_progress
            self._task_in_progress = True

        start_time = time.time()
        check_interval = 2
        last_log_time = 0
        log_interval = 100  # Логируем каждые 100 секунд

        try:
            logger.info(Colors.colorize(f"⏳ Начало ожидания файла: {file_path.name} (макс: {timeout}s)", Colors.YELLOW))

            while time.time() - start_time < timeout:
                elapsed = time.time() - start_time
                remaining = timeout - elapsed

                # Периодическое логирование для диагностики
                if elapsed - last_log_time >= log_interval:
                    progress_percent = (elapsed / timeout) * 100
                    logger.info(Colors.colorize(
                        f"⏱️  Ожидание {file_path.name}: {elapsed:.0f}s/{timeout}s ({progress_percent:.1f}%) - осталось {remaining:.0f}s",
                        Colors.BRIGHT_YELLOW
                    ))
                    last_log_time = elapsed
                
                # Проверяем основной путь
                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        if control_phrase and control_phrase not in content:
                            logger.debug("Файл найден, но контрольная фраза еще не появилась")
                        else:
                            logger.info(f"Файл {file_path} содержит контрольную фразу" if control_phrase else f"Файл {file_path} найден")
                            return {
                                "success": True,
                                "file_path": str(file_path),
                                "content": content,
                                "wait_time": time.time() - start_time,
                                "error": None
                            }
                    except Exception as e:
                        logger.warning(f"Ошибка чтения файла {file_path}: {e}")
                
                # Проверяем дополнительные директории
                for candidate_dir in results_dir_candidates:
                    if candidate_dir.exists():
                        for pattern in result_patterns:
                            candidate_file_path = candidate_dir / pattern
                            if candidate_file_path.exists():
                                try:
                                    content = candidate_file_path.read_text(encoding='utf-8')
                                    if control_phrase and control_phrase not in content:
                                        logger.debug(f"Файл найден в {candidate_dir}, но контрольная фраза еще не появилась")
                                    else:
                                        logger.info(f"Файл {candidate_file_path} содержит контрольную фразу" if control_phrase else f"Файл {candidate_file_path} найден")
                                        return {
                                            "success": True,
                                            "file_path": str(candidate_file_path),
                                            "content": content,
                                            "wait_time": time.time() - start_time,
                                            "error": None
                                        }
                                except Exception as e:
                                    logger.warning(f"Ошибка чтения файла из {candidate_dir} {candidate_file_path}: {e}")

                time.sleep(check_interval)
            
            logger.warning(f"Таймаут ожидания файла {file_path.name} (лимит: {timeout}с)")
            return {
                "success": False,
                "file_path": str(file_path),
                "content": None,
                "wait_time": time.time() - start_time,
                "error": "Таймаут ожидания файла"
            }
        finally:
            with self._task_in_progress_lock:
                self._task_in_progress = prev_task_in_progress

    async def _execute_task_via_crewai(self, todo_item: TodoItem, task_logger: TaskLogger) -> bool:
        """
        Выполнение задачи через CrewAI
        """
        if not FLASK_AVAILABLE:
            logger.error("Flask не установлен, CrewAI недоступен")
            task_logger.log_error("Flask не установлен, CrewAI недоступен")
            return False

        if not self.config.get('crewai.enabled', False):
            logger.warning("CrewAI не включен в конфигурации")
            task_logger.log_warning("CrewAI не включен в конфигурации")
            return False

        task_id = task_logger.task_id
        logger.info(f"🚀 Запускаем выполнение задачи через CrewAI: {todo_item.text}")
        task_logger.log_info(f"Запускаем выполнение задачи через CrewAI: {todo_item.text}")

        # Создаем задачу CrewAI
        task = Task(
            description=f"Выполни задачу: {todo_item.text}",
            agent=self.agent,  # Используем предварительно созданный агент
            expected_output="Полное и корректное выполнение задачи. Убедись, что все файлы созданы/изменены согласно инструкции. Включи только код и короткое описание изменений.",
        )

        # Создаем Crew
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=2
        )

        try:
            result = await asyncio.to_thread(crew.kickoff) # Запускаем в отдельном потоке, чтобы не блокировать asyncio loop
            logger.info(f"✅ Задача CrewAI выполнена успешно. Результат: {result[:500]}...")
            task_logger.log_info("Задача CrewAI выполнена успешно")
            self.status_manager.update_task_status(task_id, 'done', details="Выполнено через CrewAI")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении задачи через CrewAI: {e}", exc_info=True)
            task_logger.log_error(f"Ошибка при выполнении задачи через CrewAI: {e}", e)
            self.status_manager.update_task_status(task_id, 'error', details=f"Ошибка CrewAI: {str(e)}")
            return False
    
        return tasks_to_redo

    async def _generate_initial_todo(self) -> bool:
        """
        Генерирует начальный TODO лист при отсутствии активных задач.
        """
        logger.info("🤖 Генерирую начальный TODO лист...")
        try:
            from src.llm.llm_manager import LLMManager
            from src.todo_manager import TodoItem
            import json # Add this import

            llm_manager = getattr(self, 'llm_manager', None)
            if not llm_manager:
                llm_manager = LLMManager(config_path="config/llm_settings.yaml")

            # Промпт для генерации начального TODO
            prompt = """Ты - Code Agent, твоя задача - создать начальный TODO лист для себя на основе текущего проекта.
Проанализируй структуру проекта, файлы и потенциальные улучшения/задачи.
Создай 3-5 высокоуровневых TODO задач, которые помогут улучшить или развить проект.
Каждая задача должна быть краткой, но достаточно ясной.
Возвращай ТОЛЬКО JSON массив строк с задачами. Пример: ["Задача 1", "Задача 2"]
"""
            response = await llm_manager.generate_response(prompt=prompt, response_format={"type": "json_object"})
            
            generated_todos_raw = json.loads(response.content)

            if not isinstance(generated_todos_raw, list):
                logger.debug(f"LLM fallback response is not a list, returning empty TODO list. Raw response: {generated_todos_raw}")
                return []
            
            if isinstance(generated_todos_raw, list) and generated_todos_raw:
                generated_todos = [TodoItem(text=task_text, level=1) for task_text in generated_todos_raw]
                self.todo_manager.add_tasks_to_start(generated_todos)
                self.session_tracker.record_generation(
                    todo_file="generated_todo.md", # Placeholder file name
                    task_count=len(generated_todos),
                    metadata={"source": "auto_generated_initial"}
                )
                logger.info(f"✅ Начальный TODO лист сгенерирован с {len(generated_todos)} задачами.")
                return True
            else:
                logger.warning("Не удалось сгенерировать начальный TODO лист (пустой или некорректный формат).")
                return False
        except Exception as e:
            logger.error(f"Ошибка при генерации начального TODO листа: {e}", exc_info=True)
            return False

    async def process_todo_item(self, todo_item: TodoItem) -> bool:
        """
        Обработать один элемент из списка TODO
        """
        task_id = f"task_{hash(todo_item.text + datetime.now().strftime('%Y%m%d%H%M%S')) % (10**10)}"
        task_logger = TaskLogger(task_id, todo_item.text)
        
        logger.info(f"--- Начинаем обрабатывать задачу {task_id}: {todo_item.text[:100]}...")
        self.status_manager.add_task(task_id, todo_item.text)
        
        try:
            # Отмечаем задачу в checkpoint
            self.checkpoint_manager.start_task(todo_item, task_id)

            # Определяем тип задачи
            task_type = self._determine_task_type(todo_item)
            logger.debug(f"Определен тип задачи: {task_type}")

            # Проверяем, какой интерфейс LLM выбран
            llm_config = self.config.get('llm', {})
            interface_type = llm_config.get('cli_interface', 'cursor').lower()
            logger.debug(f"Выбран интерфейс LLM: {interface_type}")

            # Определяем, как выполнять задачу - через CLI или CrewAI
            if interface_type in ['cursor', 'gemini']:
                # Выполнение через CLI (Cursor или Gemini)
                result = await self._execute_task_via_cli(todo_item, task_type, task_logger, interface_type)
            else:
                # Выполнение через CrewAI
                result = await self._execute_task_via_crewai(todo_item, task_logger)

            # Обновляем статус задачи в checkpoint
            self.checkpoint_manager.end_task(task_id, success=result)

            if result:
                self.todo_manager.mark_task_done(todo_item.text)
                task_logger.log_completion(True)
                logger.info(f"+++ Задача {task_id} '{todo_item.text[:100]}...' успешно завершена.")
                return True
            else:
                task_logger.log_completion(False, summary="Задача не выполнена")
                logger.error(f"--- Задача {task_id} '{todo_item.text[:100]}...' завершена с ошибкой.")
                # Ошибочные задачи не отмечаем как выполненные
                return False
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при обработке задачи {task_id}: {e}", exc_info=True)
            task_logger.log_error(f"Критическая ошибка: {e}", e)
            self.status_manager.update_task_status(task_id, 'error', details=f"Критическая ошибка: {str(e)}")
            self.checkpoint_manager.end_task(task_id, success=False, error_message=str(e))
            return False
        finally:
            task_logger.close()
    
    async def start(self):
        """
        Запустить основной цикл обработки задач
        """
        logger.info(f"Запуск сервера Code Agent. Интервал проверки: {self.check_interval}с")
        self.status_manager.update_server_status('running', 'Ожидание задач')
        self.server_logger.log_info("Сервер запущен")
        
        # Обновляем запись о старте сервера в checkpoint
        self.checkpoint_manager.mark_server_start(self.session_tracker.current_session_id)

        try:
            self._is_running = True
            
            # Запускаем HTTP сервер Flask в отдельном потоке, если включен
            if self.http_enabled and FLASK_AVAILABLE:
                self._start_http_server()
            elif self.http_enabled and not FLASK_AVAILABLE:
                logger.warning("Flask не установлен, HTTP сервер не может быть запущен.")
            
            # Запускаем мониторинг изменений файлов, если включен
            if self.auto_reload and self.reload_on_py_changes:
                self._start_file_observer()

            while self._is_running:
                with self._stop_lock:
                    if self._should_stop:
                        logger.info("Получен запрос на остановку, завершаем работу.")
                        break
                
                # Проверяем флаг перезагрузки
                with self._reload_lock:
                    if self._should_reload and not self._task_in_progress:
                        logger.info("Обнаружены изменения, перезапускаем сервер...")
                        self._should_reload = False # Сбрасываем флаг
                        raise ServerReloadException("Перезапуск из-за изменений в файлах")
                    elif self._should_reload and self._task_in_progress:
                        logger.info("Обнаружены изменения, но задача в процессе. Перезапуск будет после завершения.")
                        self._reload_after_instruction = True # Отмечаем, что нужно перезапустить после текущей инструкции

                # Проверяем, есть ли незавершенные задачи, которые нужно доработать
                tasks_to_redo = await self._check_completed_tasks_for_incomplete_execution()
                if tasks_to_redo:
                    logger.info(f"Найдены {len(tasks_to_redo)} выполненные задачи, требующие доработки. Добавляем их в начало списка.")
                    # Добавляем их в начало списка TODO
                    self.todo_manager.add_tasks_to_start(tasks_to_redo)

                all_todos = self.todo_manager.get_all_tasks()
                active_todos = [t for t in all_todos if not t.done and not t.skipped]
                
                # Фильтруем задачи, которые уже выполнены в checkpoint
                active_todos = self._filter_completed_tasks(active_todos)

                num_active_todos = len(active_todos)
                self.server_logger.log_iteration_start(self._current_iteration, num_active_todos)
                
                if num_active_todos == 0:
                    logger.info("Список TODO пуст. Ожидаем новые задачи.")
                    # Пытаемся автоматически сгенерировать TODO
                    if self.auto_todo_enabled and self.session_tracker.can_generate_todo():
                        logger.info("Попытка автоматической генерации нового TODO листа...")
                        new_todo_generated = await self._generate_initial_todo()
                        if new_todo_generated:
                            logger.info("Автоматически сгенерирован новый TODO лист. Продолжаем.")
                            # Перезапускаем итерацию для обработки нового TODO
                            self._current_iteration += 1
                            continue
                        else:
                            logger.info("Не удалось автоматически сгенерировать новый TODO лист. Ожидаем.")
                            self.session_tracker.record_todo_generation_attempt(success=False)
                    else:
                        logger.debug("Автоматическая генерация TODO не включена или превышен лимит.")
                        self.status_manager.update_server_status('idle', 'Ожидание новых задач в списке TODO')
                        # Если нет задач и нет автогенерации, ждем
                        time.sleep(self.check_interval)
                        self._current_iteration += 1
                        continue
                
                self.status_manager.update_server_status('processing', f"Обработка {num_active_todos} задач")
                
                # Обрабатываем задачи последовательно
                self._task_in_progress = True
                try:
                    current_task_index = 0
                    while current_task_index < len(active_todos):
                        todo_item = active_todos[current_task_index]
                        
                        # Проверяем флаг перезагрузки перед каждой задачей
                        with self._reload_lock:
                            if self._should_reload and not self._task_in_progress:
                                logger.info("Обнаружены изменения, перезапускаем сервер...")
                                self._should_reload = False # Сбрасываем флаг
                                raise ServerReloadException("Перезапуск из-за изменений в файлах")
                            elif self._should_reload and self._task_in_progress:
                                logger.info("Обнаружены изменения, но задача в процессе. Перезапуск будет после завершения.")
                                self._reload_after_instruction = True # Отмечаем, что нужно перезапустить после текущей инструкции

                        self.server_logger.log_task_start(current_task_index + 1, num_active_todos, todo_item.text)
                        
                        # Перед началом выполнения задачи, проверяем не является ли она частично выполненной
                        completion_info = self._analyze_task_completion_comment(todo_item)
                        if completion_info["has_partial_completion"]:
                            decision = await self._decide_task_continuation(todo_item, completion_info)
                            if decision == "postpone_task":
                                logger.info(Colors.colorize(f"📋 LLM Manager решил отложить задачу: '{todo_item.text[:50]}...'", Colors.BRIGHT_MAGENTA))
                                self.postponed_tasks.append(todo_item)
                                active_todos.pop(current_task_index) # Удаляем из текущего списка, чтобы не обрабатывать
                                continue # Переходим к следующей задаче
                            else:
                                logger.info(Colors.colorize(f"📋 LLM Manager решил продолжить задачу: '{todo_item.text[:50]}...'", Colors.BRIGHT_MAGENTA))

                        success = await self.process_todo_item(todo_item)
                        
                        # Проверяем флаг остановки после обработки задачи
                        with self._stop_lock:
                            if self._should_stop:
                                logger.info("Получен запрос на остановку, завершаем работу.")
                                break
                        
                        # Если нужно перезапустить после текущей инструкции
                        with self._reload_lock:
                            if self._reload_after_instruction:
                                logger.info("Перезапуск после текущей инструкции...")
                                self._reload_after_instruction = False
                                raise ServerReloadException("Перезапуск после инструкции")
                        
                        # Если задача не была выполнена, но не критична, переходим к следующей
                        # Если задача была успешно выполнена, но оставались недоработки, LLM Manager мог ее переотложить
                        # Поэтому просто перечитываем активные задачи
                        all_todos = self.todo_manager.get_all_tasks()
                        active_todos = [t for t in all_todos if not t.done and not t.skipped]
                        active_todos = self._filter_completed_tasks(active_todos)
                        num_active_todos = len(active_todos) # Обновляем количество
                        
                        # Если количество задач уменьшилось, текущая задача могла быть выполнена/удалена
                        # Просто двигаем index вперед
                        current_task_index += 1
                        if current_task_index >= num_active_todos:
                            break # Все задачи в текущем списке обработаны
                finally:
                    self._task_in_progress = False

                # Добавляем отложенные задачи в конец списка
                if self.postponed_tasks:
                    logger.info(f"Добавляем {len(self.postponed_tasks)} отложенных задач в конец списка TODO.")
                    self.todo_manager.add_tasks_to_end(self.postponed_tasks)
                    self.postponed_tasks.clear() # Очищаем список отложенных

                self._current_iteration += 1
                if self.max_iterations and self._current_iteration >= self.max_iterations:
                    logger.info(f"Достигнуто максимальное количество итераций: {self.max_iterations}")
                    self.server_logger.log_server_shutdown(f"Достигнуто максимальное количество итераций: {self.max_iterations}")
                    break # Завершаем работу после достижения лимита итераций

                self.status_manager.update_server_status('idle', 'Ожидание новых задач или следующей итерации')
                
                # Проверяем запрос на остановку после итерации
                with self._stop_lock:
                    if self._should_stop:
                        logger.info("Получен запрос на остановку, завершаем работу.")
                        break
                
                # Проверяем, это остановка через API или из-за ошибок CLI
                with self._cli_error_lock:
                    cli_error_stop = self._cli_error_count >= self._max_cli_errors
                
                if cli_error_stop:
                    logger.error("Остановка сервера из-за критических ошибок CLI")
                    break

                logger.info(f"Ожидание {self.check_interval} секунд перед следующей итерацией...")
                time.sleep(self.check_interval)

        except ServerReloadException:
            # Сервер будет перезапущен вызывающим кодом (main.py)
            logger.info("Сервер завершил работу для перезапуска.")
        except Exception as e:
            logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА СЕРВЕРА: {e}", exc_info=True)
            self.server_logger.log_error(f"Критическая ошибка сервера: {e}", e)
            self.status_manager.update_server_status('error', f"Критическая ошибка: {str(e)}")
        finally:
            self._is_running = False
            self.status_manager.update_server_status('stopped', 'Сервер остановлен')
            self.server_logger.log_server_shutdown("Обычное завершение" if not self._should_stop else "Остановка по запросу")
            self._stop_http_server()
            self._stop_file_observer()
            self.checkpoint_manager.mark_server_stop(clean=not self._should_stop)
            logger.info("Сервер Code Agent остановлен.")

    async def close(self):
        """
        Корректное закрытие ресурсов сервера
        """
        logger.info("Закрытие ресурсов сервера Code Agent...")
        self._stop_http_server()
        self._stop_file_observer()
        # Дополнительная очистка, если требуется
        logger.info("Все ресурсы сервера Code Agent закрыты.")

    def _start_http_server(self):
        """Запуск HTTP сервера Flask в отдельном потоке"""
        if not FLASK_AVAILABLE:
            logger.warning("Flask не установлен, HTTP сервер не может быть запущен.")
            return

        self.flask_app = Flask(__name__)
        self._setup_routes()

        def run_flask():
            # Отключаем вывод запуска Flask
            cli = sys.modules['flask.cli']
            cli.show_server_banner = lambda *x: None
            self.flask_app.run(port=self.http_port, use_reloader=False, debug=False)

        self.http_thread = threading.Thread(target=run_flask)
        self.http_thread.daemon = True
        self.http_thread.start()
        logger.info(f"HTTP сервер запущен на порту {self.http_port}")
        self.status_manager.update_server_status('running', 'HTTP сервер активен')

    def _stop_http_server(self):
        """Остановка HTTP сервера Flask"""
        if self.http_thread and self.http_thread.is_alive():
            logger.info("Остановка HTTP сервера...")
            # Это не самый изящный способ, но для тестового/локального сервера Flask
            # достаточно "убить" процесс, связанный с сервером
            if self.http_server:
                self.http_server.shutdown()
            
            # Если нет werkzeug сервера, пытаемся убить процесс по порту
            try:
                # Найти PID процесса, слушающего self.http_port
                if sys.platform == 'win32':
                    find_pid_cmd = f"netstat -ano | findstr :{self.http_port}"
                    result = subprocess.run(find_pid_cmd, capture_output=True, text=True, shell=True)
                    if result.returncode == 0 and result.stdout:
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if "LISTENING" in line:
                                parts = line.split()
                                pid = parts[-1]
                                logger.debug(f"Найдена Flask-сессия на PID: {pid}. Попытка завершения.")
                                subprocess.run(f"taskkill /PID {pid} /F", capture_output=True, text=True, shell=True)
                                logger.info(f"Flask процесс на PID {pid} завершен.")
                                break
                else:
                    find_pid_cmd = f"lsof -t -i :{self.http_port}"
                    result = subprocess.run(find_pid_cmd, capture_output=True, text=True, shell=True)
                    if result.returncode == 0 and result.stdout:
                        pid = result.stdout.strip()
                        logger.debug(f"Найдена Flask-сессия на PID: {pid}. Попытка завершения.")
                        subprocess.run(f"kill -9 {pid}", capture_output=True, text=True, shell=True)
                        logger.info(f"Flask процесс на PID {pid} завершен.")
            except Exception as e:
                logger.warning(f"Не удалось остановить HTTP сервер по PID: {e}")

            self.http_thread.join(timeout=1) # Даем потоку время на завершение
            logger.info("HTTP сервер остановлен.")

    def _setup_routes(self):
        """Настройка HTTP маршрутов"""
        @self.flask_app.route('/status', methods=['GET'])
        def get_status():
            return jsonify(self.status_manager.get_full_status())

        @self.flask_app.route('/stop', methods=['POST'])
        def stop_server_route():
            logger.info("Получен HTTP запрос на остановку сервера.")
            with self._stop_lock:
                self._should_stop = True
            return jsonify({"message": "Серверу отправлен сигнал остановки."}), 200
        
        @self.flask_app.route('/reload', methods=['POST'])
        def reload_server_route():
            logger.info("Получен HTTP запрос на перезагрузку сервера.")
            with self._reload_lock:
                self._should_reload = True
            return jsonify({"message": "Серверу отправлен сигнал перезагрузки."}), 200

        @self.flask_app.route('/add_todo', methods=['POST'])
        def add_todo_route():
            data = request.json # type: ignore
            if not data or 'task' not in data:
                return jsonify({"error": "Требуется поле 'task'."}), 400
            
            task_text = data['task']
            self.todo_manager.add_task(task_text)
            logger.info(f"Задача добавлена через API: {task_text}")
            return jsonify({"message": "Задача успешно добавлена."} ), 200

        @self.flask_app.route('/clear_todos', methods=['POST'])
        def clear_todos_route():
            self.todo_manager.clear_all_tasks()
            logger.info("Все задачи TODO очищены через API.")
            return jsonify({"message": "Все задачи TODO очищены."} ), 200
        
        @self.flask_app.route('/skip_current_task', methods=['POST'])
        def skip_current_task_route():
            current_task = self.status_manager.get_current_task()
            if current_task and current_task.get('status') == 'processing':
                task_id = current_task.get('task_id')
                task_text = current_task.get('description')
                self.todo_manager.mark_task_skipped(task_text)
                self.status_manager.update_task_status(task_id, 'skipped', details="Пропущено по запросу API")
                logger.info(f"Текущая задача '{task_text}' (ID: {task_id}) пропущена по запросу API.")
                return jsonify({"message": f"Задача '{task_text}' пропущена."} ), 200
            else:
                return jsonify({"message": "Нет активной задачи для пропуска."} ), 404

    def _start_file_observer(self):
        """Запуск мониторинга изменений файлов"""
        event_handler = FileChangeHandler(self)
        self.file_observer = Observer()
        self.file_observer.schedule(event_handler, str(Path(__file__).parent.parent), recursive=True)
        self.file_observer.start()
        logger.info("Мониторинг изменений файлов запущен.")

    def _stop_file_observer(self):
        """Остановка мониторинга изменений файлов"""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            logger.info("Мониторинг изменений файлов остановлен.")

class FileChangeHandler(FileSystemEventHandler):
    """Обработчик изменений файлов для перезагрузки сервера"""
    def __init__(self, server_instance):
        super().__init__()
        self.server_instance = server_instance
        self.last_modified_time = time.time()
        self.debounce_interval = 1 # Интервал для подавления частых событий (секунды)

    def on_modified(self, event):
        if event.is_directory:
            return

        # Игнорируем изменения в определенных директориях и файлах
        ignored_paths = [
            ".git", ".mypy_cache", ".pytest_cache", ".venv", "__pycache__", "logs", "temp", "htmlcov",
            "results", ".env", ".cursor", "test_output.md", "todo_gemini-cli.md",
            "gemini_env", "code_agent.egg-info", "docker", "docs" # Игнорируем папку docs
        ]
        if any(ignored_path in event.src_path for ignored_path in ignored_paths):
            return
        
        # Дополнительно игнорируем файлы конфигурации, которые могут часто меняться
        if any(event.src_path.endswith(f) for f in [
            "config/llm_settings.yaml", "config/config.yaml", "config/agents.yaml"
        ]):
            return

        current_time = time.time()
        if current_time - self.last_modified_time < self.debounce_interval:
            return # Подавляем частые события

        self.last_modified_time = current_time
        logger.info(f"Обнаружено изменение файла: {event.src_path}. Сигнал для перезагрузки.")
        with self.server_instance._reload_lock:
            self.server_instance._should_reload = True
            # Увеличиваем счетчик изменений, если сервер в ожидании
            if not self.server_instance._task_in_progress:
                with self.server_instance._waiting_change_count_lock:
                    self.server_instance._waiting_change_count += 1
                    if self.server_instance._waiting_change_count > 15:
                        logger.warning("Слишком много изменений файлов подряд в ожидании, принудительная остановка.")
                        with self.server_instance._stop_lock:
                            self.server_instance._should_stop = True

