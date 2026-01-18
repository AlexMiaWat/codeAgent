"""
Основной сервер Code Agent
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from crewai import Task, Crew

from .config_loader import ConfigLoader
from .status_manager import StatusManager
from .todo_manager import TodoManager, TodoItem
from .agents.executor_agent import create_executor_agent
from .cursor_cli_interface import CursorCLIInterface, create_cursor_cli_interface
from .cursor_file_interface import CursorFileInterface
from .task_logger import TaskLogger, ServerLogger, TaskPhase
from .session_tracker import SessionTracker
from .checkpoint_manager import CheckpointManager


# Настройка кодировки для Windows консоли
if sys.platform == 'win32':
    # Устанавливаем UTF-8 для stdout
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    else:
        # Для старых версий Python
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/code_agent.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CodeAgentServer:
    """Основной сервер Code Agent"""
    
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
        
        # Инициализация менеджеров
        self.status_manager = StatusManager(self.status_file)
        todo_format = self.config.get('project.todo_format', 'txt')
        self.todo_manager = TodoManager(self.project_dir, todo_format=todo_format)
        
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
        self.check_interval = server_config.get('check_interval', 60)
        self.task_delay = server_config.get('task_delay', 5)
        self.max_iterations = server_config.get('max_iterations')
        
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
        
        # Логируем инициализацию
        self.server_logger.log_initialization({
            'project_dir': str(self.project_dir),
            'docs_dir': str(self.docs_dir),
            'cursor_cli_available': self.use_cursor_cli,
            'auto_todo_enabled': self.auto_todo_enabled,
            'max_todo_generations': self.max_todo_generations,
            'checkpoint_enabled': True
        })
        
        logger.info(f"Code Agent Server инициализирован")
        logger.info(f"Проект: {self.project_dir}")
        logger.info(f"Документация: {self.docs_dir}")
        logger.info(f"Статус файл: {self.status_file}")
        if self.use_cursor_cli:
            logger.info("Cursor CLI интерфейс доступен (приоритетный)")
        else:
            logger.info("Cursor CLI недоступен, будет использоваться файловый интерфейс")
        if self.auto_todo_enabled:
            logger.info(f"Автоматическая генерация TODO включена (макс. {self.max_todo_generations} раз за сессию)")
        logger.info(f"Checkpoint система активирована для защиты от сбоев")
    
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
            
            # Показываем незавершенные задачи
            incomplete_count = recovery_info["incomplete_tasks_count"]
            if incomplete_count > 0:
                logger.warning(f"Незавершенных задач: {incomplete_count}")
                for task in recovery_info["incomplete_tasks"][:5]:  # Показываем первые 5
                    logger.warning(f"  - {task['task_text']} (состояние: {task['state']})")
            
            # Показываем задачи с ошибками
            failed_count = recovery_info["failed_tasks_count"]
            if failed_count > 0:
                logger.warning(f"Задач с ошибками: {failed_count}")
                for task in recovery_info["failed_tasks"][:3]:  # Показываем первые 3
                    logger.warning(f"  - {task['task_text']}")
                    logger.warning(f"    Ошибка: {task.get('error_message', 'N/A')}")
            
            logger.warning("=" * 80)
            logger.info("Сервер продолжит работу с последней контрольной точки")
            logger.warning("=" * 80)
            
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
            timeout = cli_config.get('timeout', 300)
            headless = cli_config.get('headless', True)
            
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
            instruction_id: ID инструкции (обычно 1 для базовой)
        
        Returns:
            Словарь с шаблоном инструкции или None
        """
        instructions = self.config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))
        
        # Ищем инструкцию с нужным ID
        for instruction in task_instructions:
            if isinstance(instruction, dict) and instruction.get('instruction_id') == instruction_id:
                return instruction
        
        # Если не найдена, берем первую доступную
        if task_instructions and isinstance(task_instructions[0], dict):
            return task_instructions[0]
        
        return None
    
    def _format_instruction(self, template: Dict[str, Any], todo_item: TodoItem, task_id: str) -> str:
        """
        Форматирование инструкции из шаблона
        
        Args:
            template: Шаблон инструкции
            todo_item: Элемент todo-листа
            task_id: Идентификатор задачи
        
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
            'plan_item_number': '1',  # По умолчанию
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
        
        logger.info(f"Ожидание файла результата: {file_path} (timeout: {timeout}s)")
        
        start_time = time.time()
        check_interval = 2
        
        while time.time() - start_time < timeout:
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Проверяем контрольную фразу если указана
                    if control_phrase:
                        if control_phrase in content:
                            logger.info(f"Файл результата найден и содержит контрольную фразу")
                            return {
                                "success": True,
                                "file_path": str(file_path),
                                "content": content,
                                "wait_time": time.time() - start_time
                            }
                        else:
                            logger.debug(f"Файл найден, но контрольная фраза еще не появилась")
                    else:
                        # Контрольная фраза не требуется
                        logger.info(f"Файл результата найден")
                        return {
                            "success": True,
                            "file_path": str(file_path),
                            "content": content,
                            "wait_time": time.time() - start_time
                        }
                except Exception as e:
                    logger.warning(f"Ошибка чтения файла {file_path}: {e}")
            
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
        max_file_size = self.config.get('docs.max_file_size', 1000000)
        
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
        # Проверяем, не была ли задача уже выполнена
        if self.checkpoint_manager.is_task_completed(todo_item.text):
            logger.info(f"Задача уже выполнена (пропуск): {todo_item.text}")
            return True
        
        # Логируем начало задачи
        self.server_logger.log_task_start(task_number, total_tasks, todo_item.text)
        logger.info(f"Выполнение задачи: {todo_item.text}")
        
        # Генерируем ID задачи
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
                
                # Отмечаем в checkpoint
                if result:
                    self.checkpoint_manager.mark_task_completed(task_id)
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
                else:
                    self.checkpoint_manager.mark_task_failed(task_id, "Задача не выполнена через CrewAI")
                
                return result
            
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи '{todo_item.text}': {e}", exc_info=True)
            
            # Логируем ошибку
            task_logger.log_error(f"Критическая ошибка при выполнении задачи", e)
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
            return False
    
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
        
        # Получаем шаблон инструкции
        template = self._get_instruction_template(task_type, instruction_id=1)
        
        if not template:
            logger.warning(f"Шаблон инструкции для типа '{task_type}' не найден, используется базовый")
            task_logger.log_debug("Шаблон не найден, используется базовый")
            # Используем базовый шаблон
            instruction_text = f"Выполни задачу: {todo_item.text}\n\nСоздай отчет в docs/results/last_result.md, в конце напиши 'Отчет завершен!'"
            wait_for_file = "docs/results/last_result.md"
            control_phrase = "Отчет завершен!"
            timeout = 600
        else:
            # Форматируем инструкцию из шаблона
            instruction_text = self._format_instruction(template, todo_item, task_id)
            wait_for_file = template.get('wait_for_file')
            control_phrase = template.get('control_phrase')
            timeout = template.get('timeout', 600)
        
        # Логируем инструкцию
        task_logger.log_instruction(1, instruction_text, task_type)
        logger.info(f"Инструкция для Cursor: {instruction_text[:200]}...")
        
        # Фаза: Выполнение через Cursor
        task_logger.set_phase(TaskPhase.CURSOR_EXECUTION, stage=1, instruction_num=1)
        
        # Выполняем через CLI или файловый интерфейс
        if self.use_cursor_cli:
            # Логируем создание нового диалога
            task_logger.log_new_chat()
            
            # Используем Cursor CLI
            result = self.execute_cursor_instruction(
                instruction=instruction_text,
                task_id=task_id,
                timeout=timeout
            )
            
            # Логируем ответ от Cursor
            task_logger.log_cursor_response(result, brief=True)
            
            if result.get("success"):
                logger.info(f"Задача {task_id} выполнена через Cursor CLI")
                
                # Фаза: Ожидание результата
                if wait_for_file:
                    task_logger.set_phase(TaskPhase.WAITING_RESULT)
                    task_logger.log_waiting_result(wait_for_file, timeout)
                    
                    wait_result = self._wait_for_result_file(
                        task_id=task_id,
                        wait_for_file=wait_for_file,
                        control_phrase=control_phrase,
                        timeout=timeout
                    )
                    
                    if wait_result["success"]:
                        result_content = wait_result.get("content", "")
                        task_logger.log_result_received(
                            wait_result['file_path'],
                            wait_result['wait_time'],
                            result_content[:500]
                        )
                        logger.info(f"Файл результата получен: {wait_result['file_path']}")
                    else:
                        task_logger.log_error(f"Файл результата не получен: {wait_result.get('error')}")
                        logger.warning(f"Файл результата не получен: {wait_result.get('error')}")
                
                # Фаза: Завершение
                task_logger.set_phase(TaskPhase.COMPLETION)
                
                # Отмечаем задачу как выполненную
                self.todo_manager.mark_task_done(todo_item.text)
                
                self.status_manager.update_task_status(
                    task_name=todo_item.text,
                    status="Выполнено",
                    details=f"Выполнено через Cursor CLI (task_id: {task_id})"
                )
                
                return True
            else:
                logger.warning(f"Cursor CLI вернул ошибку: {result.get('error_message')}")
                task_logger.log_error(f"Cursor CLI вернул ошибку: {result.get('error_message')}")
                
                # НЕ используем fallback на файловый интерфейс - только автоматическое выполнение!
                # Помечаем задачу как неуспешную и возвращаем False
                self.status_manager.update_task_status(
                    task_name=todo_item.text,
                    status="Ошибка",
                    details=f"Ошибка выполнения через Cursor CLI: {result.get('error_message')}"
                )
                return False
        
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
        self.todo_manager = TodoManager(
            self.project_dir,
            todo_format=self.config.get('project.todo_format', 'txt')
        )
        
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
    
    def run_iteration(self, iteration: int = 1):
        """
        Выполнение одной итерации цикла
        
        Args:
            iteration: Номер итерации
        """
        logger.info(f"Начало итерации {iteration}")
        
        # Увеличиваем счетчик итераций в checkpoint
        self.checkpoint_manager.increment_iteration()
        
        # Получаем непройденные задачи
        pending_tasks = self.todo_manager.get_pending_tasks()
        
        if not pending_tasks:
            logger.info("Все задачи выполнены")
            self.status_manager.append_status(
                f"Все задачи выполнены. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
            
            # Пытаемся сгенерировать новый TODO лист
            if self.auto_todo_enabled:
                logger.info("Попытка генерации нового TODO листа...")
                generation_success = self._generate_new_todo_list()
                
                if generation_success:
                    logger.info("Новый TODO лист успешно сгенерирован, перезагрузка задач")
                    # Перезагружаем задачи
                    pending_tasks = self.todo_manager.get_pending_tasks()
                    
                    if pending_tasks:
                        logger.info(f"Загружено {len(pending_tasks)} новых задач")
                        # Продолжаем выполнение с новыми задачами
                    else:
                        logger.warning("После генерации TODO задачи не найдены")
                        return False
                else:
                    logger.info("Генерация TODO не выполнена (лимит или отключена)")
                    return False
            else:
                return False  # Нет задач для выполнения
        
        # Логируем начало итерации
        self.server_logger.log_iteration_start(iteration, len(pending_tasks))
        logger.info(f"Найдено непройденных задач: {len(pending_tasks)}")
        
        # Выполняем каждую задачу в отдельной сессии
        total_tasks = len(pending_tasks)
        for idx, todo_item in enumerate(pending_tasks, start=1):
            self.status_manager.add_separator()
            self._execute_task(todo_item, task_number=idx, total_tasks=total_tasks)
            
            # Задержка между задачами
            if self.task_delay > 0:
                time.sleep(self.task_delay)
        
        return True  # Есть еще задачи
    
    def start(self):
        """Запуск сервера агента в бесконечном цикле"""
        logger.info("Запуск Code Agent Server")
        
        # Отмечаем запуск в checkpoint
        session_id = self.session_tracker.current_session_id
        self.checkpoint_manager.mark_server_start(session_id)
        
        self.status_manager.append_status(
            f"Code Agent Server запущен. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            level=1
        )
        
        # Получаем начальную итерацию из checkpoint (для восстановления)
        iteration = self.checkpoint_manager.get_iteration_count()
        
        try:
            while True:
                iteration += 1
                logger.info(f"Итерация {iteration}")
                
                # Выполняем итерацию
                has_tasks = self.run_iteration(iteration)
                
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
                    time.sleep(self.check_interval)
                else:
                    # Если задачи были, ждем интервал перед следующей итерацией
                    time.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            self.server_logger.log_server_shutdown("Остановка пользователем (Ctrl+C)")
            
            # Отмечаем корректный останов
            self.checkpoint_manager.mark_server_stop(clean=True)
            
            self.status_manager.append_status(
                f"Code Agent Server остановлен. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            self.server_logger.log_server_shutdown(f"Критическая ошибка: {str(e)}")
            
            # Отмечаем некорректный останов
            self.checkpoint_manager.mark_server_stop(clean=False)
            
            self.status_manager.append_status(
                f"Критическая ошибка: {str(e)}. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
            raise
        finally:
            # Гарантируем сохранение checkpoint при любом выходе
            try:
                if not self.checkpoint_manager.was_clean_shutdown():
                    self.checkpoint_manager.mark_server_stop(clean=False)
            except:
                pass


def main():
    """Точка входа в программу"""
    # Создаем директорию для логов
    Path('logs').mkdir(exist_ok=True)
    
    # Создаем и запускаем сервер
    server = CodeAgentServer()
    server.start()


if __name__ == "__main__":
    main()