"""
Основной сервер Code Agent
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from crewai import Task, Crew

from .config_loader import ConfigLoader
from .status_manager import StatusManager
from .todo_manager import TodoManager, TodoItem
from .agents.executor_agent import create_executor_agent


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
        
        logger.info(f"Code Agent Server инициализирован")
        logger.info(f"Проект: {self.project_dir}")
        logger.info(f"Документация: {self.docs_dir}")
        logger.info(f"Статус файл: {self.status_file}")
    
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
        Выполнение одной задачи через агента
        
        Args:
            todo_item: Элемент todo-листа для выполнения
        
        Returns:
            True если задача выполнена успешно
        """
        logger.info(f"Выполнение задачи: {todo_item.text}")
        
        try:
            # Загружаем документацию
            documentation = self._load_documentation()
            
            # Обновляем статус: задача начата
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="В процессе",
                details=f"Начало выполнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
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
            
            logger.info(f"Задача выполнена: {todo_item.text}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи '{todo_item.text}': {e}")
            
            # Обновляем статус: ошибка
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Ошибка",
                details=f"Ошибка: {str(e)}"
            )
            return False
    
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
