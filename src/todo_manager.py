"""
Модуль управления todo-листом проекта
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import yaml
import re
import logging
import os

from core.interfaces import ITodoManager
from src.core.types import TaskType

from src.core.todo_item import TodoItem
from core.todo_file_io import ITodoFileParser, ITodoFileSerializer, TextTodoParser, MarkdownTodoParser, YamlTodoParser, TextTodoSerializer, MarkdownTodoSerializer, YamlTodoSerializer
from src.core.todo_file_finder import TodoFileFinder
from src.core.time_provider import IDateTimeProvider, SystemDateTimeProvider
logger = logging.getLogger(__name__)





class TodoManager(ITodoManager):
    """Управление todo-листом проекта"""
    
    # Константы
    DEFAULT_MAX_FILE_SIZE = 1_000_000  # Максимальный размер файла todo по умолчанию (1 MB)
    
    def __init__(self,
                 project_dir: Path,
                 config: Optional[Dict[str, Any]] = None,
                 todo_file_finder: Optional[TodoFileFinder] = None,
                 parsers: Optional[Dict[str, ITodoFileParser]] = None,
                 serializers: Optional[Dict[str, ITodoFileSerializer]] = None,
                 datetime_provider: Optional[IDateTimeProvider] = None):
        """
        Инициализация менеджера todo

        Args:
            project_dir: Директория проекта
            config: Конфигурация менеджера
            todo_file_finder: Инжектируемый поисковик todo-файлов
            parsers: Словарь парсеров по форматам
            serializers: Словарь сериализаторов по форматам
            datetime_provider: Провайдер даты/времени для тестирования
        """
        self.project_dir = Path(project_dir)
        self.config = config or {}

        self.todo_format = self.config.get('todo_format', 'txt')
        self.max_file_size = self.config.get('max_file_size', self.DEFAULT_MAX_FILE_SIZE)

        self.todo_file_finder = todo_file_finder or TodoFileFinder(project_dir, config)
        self.todo_file = self.todo_file_finder.find_todo_file()

        self.parsers = parsers or {
            "txt": TextTodoParser(),
            "md": MarkdownTodoParser(),
            "yaml": YamlTodoParser(),
        }
        self.serializers = serializers or {
            "txt": TextTodoSerializer(),
            "md": MarkdownTodoSerializer(),
            "yaml": YamlTodoSerializer(),
        }
        self.datetime_provider = datetime_provider or SystemDateTimeProvider()

        self.items: List[TodoItem] = []
        self._load_todos()
    

    

    
    def _load_todos(self) -> None:
        """Загрузка todo из файла"""
        if not self.todo_file or not self.todo_file.exists():
            self.items = []
            logger.debug(f"Файл todo не найден в {self.project_dir}, используем пустой список")
            return
        
        if not os.access(self.todo_file, os.R_OK):
            logger.error(f"Нет прав на чтение файла todo: {self.todo_file}")
            self.items = []
            return
        
        try:
            file_size = self.todo_file.stat().st_size
            if file_size > self.max_file_size:
                logger.error(
                    f"Файл todo слишком большой ({file_size} байт, максимум {self.max_file_size}): {self.todo_file}"
                )
                self.items = []
                return
        except OSError:
            logger.error(f"Ошибка проверки размера файла todo: {self.todo_file}", exc_info=True)
            self.items = []
            return
        
        try:
            file_format = self.todo_file_finder.detect_file_format(self.todo_file)
            parser = self.parsers.get(file_format)
            if not parser:
                raise ValueError(f"No parser available for format: {file_format}")
            
            content = self.todo_file.read_text(encoding='utf-8', errors='ignore')
            self.items = parser.parse(content)
        except UnicodeDecodeError:
            logger.error(
                f"Ошибка декодирования файла todo (не UTF-8): {self.todo_file}",
                exc_info=True,
                extra={"error_type": "UnicodeDecodeError"}
            )
            try:
                content = self.todo_file.read_text(encoding='cp1251', errors='ignore')
                self.items = parser.parse(content)
                logger.info("Файл успешно прочитан с кодировкой cp1251")
            except Exception:
                logger.error("Не удалось прочитать файл с альтернативными кодировками")
                self.items = []
                return
        except Exception as e:
            logger.error(
                f"Ошибка при загрузке todo из файла {self.todo_file}",
                exc_info=True,
                extra={
                    "todo_file": str(self.todo_file),
                    "todo_format": self.todo_format,
                    "error_type": type(e).__name__
                }
            )
            self.items = []
            logger.warning("Используется пустой список задач из-за ошибки загрузки")
    

    

    

    
    def get_pending_tasks(self) -> List[TodoItem]:
        """
        Получение непройденных задач
        
        Returns:
            Список невыполненных задач
        """
        return [item for item in self.items if not item.done]
    
    def get_all_tasks(self) -> List[TodoItem]:
        """
        Получение всех задач
        
        Returns:
            Список всех задач
        """
        return self.items
    
    def mark_task_done(self, task_text: str, comment: Optional[str] = None) -> bool:
        """
        Отметка задачи как выполненной
        
        Args:
            task_text: Текст задачи для отметки
            comment: Комментарий к выполнению (опционально, дата/время добавляется автоматически)
        
        Returns:
            True если задача найдена и отмечена
        """
        for item in self.items:
            if item.text == task_text or item.text.startswith(task_text):
                item.done = True
                if comment:
                    timestamp = self.datetime_provider.now().strftime('%Y-%m-%d %H:%M:%S')
                    item.comment = f"{comment} - {timestamp}"
                elif not item.comment:
                    timestamp = self.datetime_provider.now().strftime('%Y-%m-%d %H:%M:%S')
                    item.comment = f"Выполнено - {timestamp}"
                self._save_todos()
                return True
        return False
    
    def _save_todos(self) -> None:
        """
        Сохранение todo в файл
        
        Сохраняет изменения статуса задач обратно в файл todo в соответствующем формате.
        """
        if not self.todo_file or not self.todo_file.exists():
            logger.debug("Файл todo не найден, пропускаем сохранение")
            return
        
        if not os.access(self.todo_file, os.W_OK):
            logger.warning(f"Нет прав на запись файла todo: {self.todo_file}")
            return
        
        try:
            file_format = self.todo_file_finder.detect_file_format(self.todo_file)
            serializer = self.serializers.get(file_format)
            if not serializer:
                raise ValueError(f"No serializer available for format: {file_format}")
            
            content = serializer.serialize(self.items)
            self.todo_file.write_text(content, encoding='utf-8')
            
            logger.debug(f"Todo файл обновлен: {self.todo_file}")
        except Exception as e:
            logger.error(
                f"Ошибка при сохранении todo в файл {self.todo_file}",
                exc_info=True,
                extra={
                    "todo_file": str(self.todo_file),
                    "error_type": type(e).__name__
                }
            )
    

    

    

    
    def get_task_hierarchy(self) -> Dict[str, Any]:
        """
        Получение иерархии задач
        
        Returns:
            Словарь с иерархией задач, содержащий:
            - 'total': общее количество задач
            - 'pending': количество невыполненных задач
            - 'completed': количество выполненных задач
            - 'items': список словарей с информацией о каждой задаче
        """
        # Простая реализация - можно расширить для построения дерева
        return {
            'total': len(self.items),
            'pending': len(self.get_pending_tasks()),
            'completed': len([i for i in self.items if i.done]),
            'items': [{'text': item.text, 'level': item.level, 'done': item.done}
                     for item in self.items]
        }

    def load_todos(self) -> bool:
        """
        Load todo items from the project directory.

        Returns:
            True if loading was successful, False otherwise
        """
        try:
            self._load_todos()
            return True
        except Exception as e:
            logger.error(f"Failed to load todos: {e}")
            return False

    def save_todos(self) -> bool:
        """
        Save the current todo state to file.

        Returns:
            True if saving was successful, False otherwise
        """
        try:
            self._save_todos()
            return True
        except Exception as e:
            logger.error(f"Failed to save todos: {e}")
            return False

    def is_healthy(self) -> bool:
        """
        Проверить здоровье менеджера задач.

        Returns:
            True если менеджер в рабочем состоянии
        """
        try:
            # Менеджер считается здоровым, если инициализирован корректно
            # Наличие файла не обязательно для работоспособности
            return hasattr(self, 'project_dir') and self.project_dir.exists()
        except Exception as e:
            logger.error(f"Health check failed for TodoManager: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Получить статус менеджера задач.

        Returns:
            Словарь со статусной информацией
        """
        return {
            'healthy': self.is_healthy(),
            'project_dir': str(self.project_dir),
            'todo_format': self.todo_format,
            'items_count': len(getattr(self, 'items', [])),
            'pending_count': len(self.get_pending_tasks()),
        }

    def get_tasks_by_type(self, task_type: TaskType) -> List[TodoItem]:
        """
        Get all tasks of a specific type.

        Args:
            task_type: TaskType to filter by

        Returns:
            List of TodoItem instances of the specified type
        """
        all_tasks = self.get_all_tasks()
        return [task for task in all_tasks if task.effective_task_type == task_type]

    def get_task_type_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about task types distribution.

        Returns:
            Dictionary containing statistics about task types (counts, percentages, etc.)
        """
        all_tasks = self.get_all_tasks()
        total_tasks = len(all_tasks)

        if total_tasks == 0:
            return {
                'total_tasks': 0,
                'types': {},
                'untyped_tasks': 0,
                'untyped_percentage': 0.0
            }

        type_counts = {}
        untyped_count = 0

        for task in all_tasks:
            task_type = task.effective_task_type
            if task_type:
                type_key = task_type.value
                type_counts[type_key] = type_counts.get(type_key, 0) + 1
            else:
                untyped_count += 1

        # Calculate percentages
        type_stats = {}
        for type_name, count in type_counts.items():
            type_stats[type_name] = {
                'count': count,
                'percentage': round((count / total_tasks) * 100, 2)
            }

        return {
            'total_tasks': total_tasks,
            'types': type_stats,
            'untyped_tasks': untyped_count,
            'untyped_percentage': round((untyped_count / total_tasks) * 100, 2)
        }

    def update_task_type(self, task_id: str, task_type: Optional[TaskType]) -> bool:
        """
        Update the task type for a specific task.

        Args:
            task_id: Unique task identifier
            task_type: New TaskType to assign, or None for auto-detection

        Returns:
            True if update was successful, False otherwise
        """
        try:
            all_tasks = self.get_all_tasks()
            for task in all_tasks:
                if task.id == task_id:
                    task.set_task_type(task_type)
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to update task type for task {task_id}: {e}")
            return False

    def validate_task_types(self) -> Dict[str, Any]:
        """
        Validate that all tasks have appropriate types assigned.

        Returns:
            Dictionary containing validation results, including any tasks
            that may need type assignment or correction
        """
        all_tasks = self.get_all_tasks()
        total_tasks = len(all_tasks)

        if total_tasks == 0:
            return {
                'valid': True,
                'total_tasks': 0,
                'typed_tasks': 0,
                'untyped_tasks': 0,
                'issues': []
            }

        typed_tasks = 0
        untyped_tasks = []
        type_distribution = {}

        for task in all_tasks:
            effective_type = task.effective_task_type
            if effective_type:
                typed_tasks += 1
                type_key = effective_type.value
                type_distribution[type_key] = type_distribution.get(type_key, 0) + 1
            else:
                untyped_tasks.append({
                    'id': task.id,
                    'text': task.text,
                    'level': task.level
                })

        # Check for potential issues
        issues = []

        # Tasks without types
        if untyped_tasks:
            issues.append({
                'type': 'untyped_tasks',
                'severity': 'warning',
                'message': f'{len(untyped_tasks)} tasks have no type assigned',
                'tasks': untyped_tasks[:10]  # Limit to first 10 for brevity
            })

        # Check type distribution balance
        if typed_tasks > 0:
            expected_types = {t.value for t in TaskType.get_all_types()}
            missing_types = expected_types - set(type_distribution.keys())
            if missing_types:
                issues.append({
                    'type': 'missing_types',
                    'severity': 'info',
                    'message': f'No tasks found for types: {", ".join(missing_types)}',
                    'missing_types': list(missing_types)
                })

        return {
            'valid': len(issues) == 0,
            'total_tasks': total_tasks,
            'typed_tasks': typed_tasks,
            'untyped_tasks': len(untyped_tasks),
            'type_distribution': type_distribution,
            'issues': issues
        }

    def dispose(self) -> None:
        """
        Очистить ресурсы менеджера задач.
        """
        # Очищаем загруженные элементы
        if hasattr(self, 'items'):
            self.items.clear()
        logger.debug("TodoManager disposed")
