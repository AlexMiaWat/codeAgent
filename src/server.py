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
        
        logger.info(f"Code Agent Server инициализирован")
        logger.info(f"Проект: {self.project_dir}")
        logger.info(f"Документация: {self.docs_dir}")
        logger.info(f"Статус файл: {self.status_file}")
        if self.use_cursor_cli:
            logger.info("Cursor CLI интерфейс доступен (приоритетный)")
        else:
            logger.info("Cursor CLI недоступен, будет использоваться файловый интерфейс")
    
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
            
            cli_interface = create_cursor_cli_interface(
                cli_path=cli_path,
                timeout=timeout,
                headless=headless
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
    
    def _execute_task(self, todo_item: TodoItem) -> bool:
        """
        Выполнение одной задачи через Cursor или CrewAI
        
        Args:
            todo_item: Элемент todo-листа для выполнения
        
        Returns:
            True если задача выполнена успешно
        """
        logger.info(f"Выполнение задачи: {todo_item.text}")
        
        try:
            # Определяем тип задачи
            task_type = self._determine_task_type(todo_item)
            
            # Определяем, использовать ли Cursor
            use_cursor = self._should_use_cursor(todo_item)
            
            # Обновляем статус: задача начата
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="В процессе",
                details=f"Начало выполнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (тип: {task_type}, интерфейс: {'Cursor' if use_cursor else 'CrewAI'})"
            )
            
            if use_cursor:
                # Выполнение через Cursor
                return self._execute_task_via_cursor(todo_item, task_type)
            else:
                # Выполнение через CrewAI (старый способ)
                return self._execute_task_via_crewai(todo_item)
            
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи '{todo_item.text}': {e}", exc_info=True)
            
            # Обновляем статус: ошибка
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Ошибка",
                details=f"Ошибка: {str(e)}"
            )
            return False
    
    def _execute_task_via_cursor(self, todo_item: TodoItem, task_type: str) -> bool:
        """
        Выполнение задачи через Cursor (CLI или файловый интерфейс)
        
        Args:
            todo_item: Элемент todo-листа
            task_type: Тип задачи
        
        Returns:
            True если задача выполнена успешно
        """
        # Генерируем ID задачи
        task_id = f"task_{int(time.time())}"
        
        # Получаем шаблон инструкции
        template = self._get_instruction_template(task_type, instruction_id=1)
        
        if not template:
            logger.warning(f"Шаблон инструкции для типа '{task_type}' не найден, используется базовый")
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
        
        logger.info(f"Инструкция для Cursor: {instruction_text[:200]}...")
        
        # Выполняем через CLI или файловый интерфейс
        if self.use_cursor_cli:
            # Используем Cursor CLI
            result = self.execute_cursor_instruction(
                instruction=instruction_text,
                task_id=task_id,
                timeout=timeout
            )
            
            if result.get("success"):
                logger.info(f"Задача {task_id} выполнена через Cursor CLI")
                
                # Ожидаем файл результата (если указан)
                if wait_for_file:
                    wait_result = self._wait_for_result_file(
                        task_id=task_id,
                        wait_for_file=wait_for_file,
                        control_phrase=control_phrase,
                        timeout=timeout
                    )
                    
                    if wait_result["success"]:
                        result_content = wait_result.get("content", "")
                        logger.info(f"Файл результата получен: {wait_result['file_path']}")
                    else:
                        logger.warning(f"Файл результата не получен: {wait_result.get('error')}")
                
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
                # Fallback на файловый интерфейс
                logger.info("Переключение на файловый интерфейс")
        
        # Используем файловый интерфейс (fallback или если CLI недоступен)
        logger.info(f"Использование файлового интерфейса для задачи {task_id}")
        
        # Записываем инструкцию в файл (с маркером для нового чата)
        self.cursor_file.write_instruction(
            instruction=instruction_text,
            task_id=task_id,
            metadata={
                "task_type": task_type,
                "wait_for_file": wait_for_file,
                "control_phrase": control_phrase
            },
            new_chat=True  # Всегда создаем новый чат для новой задачи
        )
        
        # Ожидаем результат
        wait_result = self.cursor_file.wait_for_result(
            task_id=task_id,
            timeout=timeout,
            control_phrase=control_phrase
        )
        
        if wait_result["success"]:
            logger.info(f"Задача {task_id} выполнена через файловый интерфейс")
            
            # Отмечаем задачу как выполненную
            self.todo_manager.mark_task_done(todo_item.text)
            
            result_content = wait_result.get("content", "")
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Выполнено",
                details=f"Выполнено через файловый интерфейс. Результат: {result_content[:300]}..."
            )
            
            return True
        else:
            logger.warning(f"Таймаут ожидания результата для задачи {task_id}: {wait_result.get('error')}")
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Ошибка",
                details=f"Таймаут ожидания результата: {wait_result.get('error')}"
            )
            return False
    
    def _execute_task_via_crewai(self, todo_item: TodoItem) -> bool:
        """
        Выполнение задачи через CrewAI (старый способ, fallback)
        
        Args:
            todo_item: Элемент todo-листа для выполнения
        
        Returns:
            True если задача выполнена успешно
        """
        logger.info(f"Выполнение задачи через CrewAI: {todo_item.text}")
        
        # Загружаем документацию
        documentation = self._load_documentation()
        
        # Создаем задачу для агента
        task = self._create_task_for_agent(todo_item, documentation)
        
        # Создаем crew и выполняем задачу
        crew = Crew(agents=[self.agent], tasks=[task])
        result = crew.kickoff()
        
        # Обновляем статус: задача выполнена
        result_summary = str(result)[:500]  # Ограничиваем размер
        self.status_manager.update_task_status(
            task_name=todo_item.text,
            status="Выполнено",
            details=f"Результат: {result_summary}"
        )
        
        # Отмечаем задачу как выполненную
        self.todo_manager.mark_task_done(todo_item.text)
        
        logger.info(f"Задача выполнена через CrewAI: {todo_item.text}")
        return True
    
    def run_iteration(self):
        """Выполнение одной итерации цикла"""
        logger.info("Начало итерации")
        
        # Получаем непройденные задачи
        pending_tasks = self.todo_manager.get_pending_tasks()
        
        if not pending_tasks:
            logger.info("Все задачи выполнены")
            self.status_manager.append_status(
                f"Все задачи выполнены. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
            return False  # Нет задач для выполнения
        
        logger.info(f"Найдено непройденных задач: {len(pending_tasks)}")
        
        # Выполняем каждую задачу в отдельной сессии
        for todo_item in pending_tasks:
            self.status_manager.add_separator()
            self._execute_task(todo_item)
            
            # Задержка между задачами
            if self.task_delay > 0:
                time.sleep(self.task_delay)
        
        return True  # Есть еще задачи
    
    def start(self):
        """Запуск сервера агента в бесконечном цикле"""
        logger.info("Запуск Code Agent Server")
        self.status_manager.append_status(
            f"Code Agent Server запущен. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            level=1
        )
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                logger.info(f"Итерация {iteration}")
                
                # Выполняем итерацию
                has_tasks = self.run_iteration()
                
                # Проверяем ограничение итераций
                if self.max_iterations and iteration >= self.max_iterations:
                    logger.info(f"Достигнуто максимальное количество итераций: {self.max_iterations}")
                    break
                
                # Если нет задач, проверяем снова через интервал
                if not has_tasks:
                    logger.info(f"Ожидание {self.check_interval} секунд перед следующей проверкой")
                    time.sleep(self.check_interval)
                else:
                    # Если задачи были, ждем интервал перед следующей итерацией
                    time.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            self.status_manager.append_status(
                f"Code Agent Server остановлен. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            self.status_manager.append_status(
                f"Критическая ошибка: {str(e)}. Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level=2
            )
            raise


def main():
    """Точка входа в программу"""
    # Создаем директорию для логов
    Path('logs').mkdir(exist_ok=True)
    
    # Создаем и запускаем сервер
    server = CodeAgentServer()
    server.start()


if __name__ == "__main__":
    main()