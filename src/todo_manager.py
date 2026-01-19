"""
Модуль управления todo-листом проекта
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import yaml
import re
import logging
import os

logger = logging.getLogger(__name__)


class TodoItem:
    """Элемент todo-листа"""
    
    def __init__(self, text: str, level: int = 0, done: bool = False, parent: Optional['TodoItem'] = None):
        """
        Инициализация элемента todo
        
        Args:
            text: Текст задачи
            level: Уровень вложенности (0 - корень)
            done: Выполнена ли задача
            parent: Родительский элемент
        """
        self.text = text.strip()
        self.level = level
        self.done = done
        self.parent = parent
        self.children: List['TodoItem'] = []
    
    def __repr__(self) -> str:
        status = "✓" if self.done else "○"
        indent = "  " * self.level
        return f"{indent}{status} {self.text}"


class TodoManager:
    """Управление todo-листом проекта"""
    
    # Константы
    DEFAULT_MAX_FILE_SIZE = 1_000_000  # Максимальный размер файла todo по умолчанию (1 MB)
    
    def __init__(self, project_dir: Path, todo_format: str = "txt", max_file_size: Optional[int] = None):
        """
        Инициализация менеджера todo
        
        Args:
            project_dir: Директория проекта
            todo_format: Формат файла todo (txt, yaml, md)
        """
        self.project_dir = Path(project_dir)
        self.todo_format = todo_format
        self.max_file_size = max_file_size or self.DEFAULT_MAX_FILE_SIZE
        self.todo_file = self._find_todo_file()
        self.items: List[TodoItem] = []
        self._load_todos()
    
    def _find_todo_file(self) -> Optional[Path]:
        """
        Поиск файла todo в директории проекта
        
        Returns:
            Path к файлу todo или None
        """
        possible_names = [
            f"todo.{self.todo_format}",
            "todo.txt",
            "TODO.txt",
            "todo.yaml",
            "TODO.md",
            "todo.md",
        ]
        
        # Сначала ищем в корне проекта
        for name in possible_names:
            file_path = self.project_dir / name
            if file_path.exists():
                return file_path
        
        # Затем ищем в поддиректории todo/
        todo_dir = self.project_dir / "todo"
        if todo_dir.exists() and todo_dir.is_dir():
            # Ищем файлы в todo/ директории
            for name in possible_names:
                file_path = todo_dir / name
                if file_path.exists():
                    return file_path
            
            # Ищем CURRENT.md, DEBT.md, ROADMAP.md в todo/
            common_todo_names = ["CURRENT.md", "DEBT.md", "ROADMAP.md"]
            for name in common_todo_names:
                file_path = todo_dir / name
                if file_path.exists():
                    return file_path
        
        return None
    
    def _detect_file_format(self) -> str:
        """
        Определение формата файла TODO на основе расширения и конфигурации
        
        Returns:
            Формат файла: 'yaml', 'md', или 'txt'
        
        Raises:
            ValueError: Если формат не поддерживается или не определен
        """
        if not self.todo_file:
            # Если файл не найден, используем формат из конфигурации
            return self.todo_format
        
        # Получаем расширение файла
        file_suffix = self.todo_file.suffix.lower()
        
        # Поддерживаемые форматы
        supported_formats = {
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'md',
            '.markdown': 'md',
            '.txt': 'txt',
            '': 'txt'  # Файлы без расширения считаем текстовыми
        }
        
        # Определяем формат по расширению
        detected_format = supported_formats.get(file_suffix, None)
        
        # Если формат определен по расширению, используем его
        if detected_format:
            # Проверяем соответствие с конфигурацией
            if self.todo_format != "txt" and detected_format != self.todo_format:
                logger.warning(
                    f"Несоответствие формата: файл имеет расширение {file_suffix} "
                    f"(формат: {detected_format}), но в конфигурации указан {self.todo_format}. "
                    f"Используется формат файла: {detected_format}"
                )
            return detected_format
        
        # Если расширение не распознано, используем формат из конфигурации
        if self.todo_format in ['yaml', 'md', 'txt']:
            logger.warning(
                f"Расширение файла {file_suffix} не распознано. "
                f"Используется формат из конфигурации: {self.todo_format}"
            )
            return self.todo_format
        
        # Если формат не определен, пробуем определить по содержимому
        logger.warning(
            f"Не удалось определить формат файла {self.todo_file}. "
            f"Пробуем определить по содержимому..."
        )
        
        # Пробуем прочитать первые несколько строк для определения формата
        try:
            with open(self.todo_file, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline() for _ in range(5)]
                content_preview = '\n'.join(first_lines)
                
                # Проверка на YAML (начинается с --- или содержит типичные YAML структуры)
                if content_preview.strip().startswith('---') or 'tasks:' in content_preview or 'todo:' in content_preview:
                    return 'yaml'
                
                # Проверка на Markdown (содержит чекбоксы или markdown синтаксис)
                if '- [' in content_preview or '# ' in content_preview:
                    return 'md'
                
                # По умолчанию текстовый формат
                return 'txt'
        except Exception as e:
            logger.error(f"Ошибка при определении формата файла: {e}", exc_info=True)
            # В случае ошибки используем формат из конфигурации или txt по умолчанию
            return self.todo_format if self.todo_format in ['yaml', 'md', 'txt'] else 'txt'
    
    def _load_todos(self) -> None:
        """Загрузка todo из файла"""
        if not self.todo_file or not self.todo_file.exists():
            self.items = []
            logger.debug(f"Файл todo не найден в {self.project_dir}, используем пустой список")
            return
        
        # Проверка прав доступа на чтение
        if not os.access(self.todo_file, os.R_OK):
            logger.error(f"Нет прав на чтение файла todo: {self.todo_file}")
            self.items = []
            return
        
        # Проверка размера файла
        try:
            file_size = self.todo_file.stat().st_size
            if file_size > self.max_file_size:
                logger.error(
                    f"Файл todo слишком большой ({file_size} байт, максимум {self.max_file_size}): {self.todo_file}"
                )
                self.items = []
                return
        except OSError as e:
            logger.error(f"Ошибка проверки размера файла todo: {self.todo_file}", exc_info=True)
            self.items = []
            return
        
        try:
            # Определяем формат файла на основе расширения и конфигурации
            file_format = self._detect_file_format()
            
            if file_format == "yaml":
                self._load_from_yaml()
            elif file_format == "md":
                self._load_from_markdown()
            else:
                self._load_from_text()
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
            # В случае ошибки используем пустой список, чтобы не блокировать работу агента
            self.items = []
            logger.warning("Используется пустой список задач из-за ошибки загрузки")
    
    def _load_from_text(self) -> None:
        """Загрузка todo из текстового файла"""
        try:
            content = self.todo_file.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            logger.error(
                f"Ошибка декодирования файла todo (не UTF-8): {self.todo_file}",
                exc_info=True,
                extra={"error_type": "UnicodeDecodeError"}
            )
            # Пробуем другие кодировки
            try:
                content = self.todo_file.read_text(encoding='cp1251')
                logger.info(f"Файл успешно прочитан с кодировкой cp1251")
            except Exception:
                logger.error(f"Не удалось прочитать файл с альтернативными кодировками")
                self.items = []
                return
        except Exception as e:
            logger.error(
                f"Ошибка чтения текстового файла todo: {self.todo_file}",
                exc_info=True,
                extra={"error_type": type(e).__name__}
            )
            self.items = []
            return
        
        lines = content.split('\n')
        
        items = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Определяем уровень вложенности по отступам
            level = len(line) - len(line.lstrip())
            level = level // 2  # Предполагаем отступ в 2 пробела
            
            # Убираем номера и маркеры списка
            text = re.sub(r'^\d+[.)]\s*', '', line)
            text = re.sub(r'^[-*+]\s+', '', text)
            text = text.strip()
            
            if text:
                items.append(TodoItem(text, level=level))
        
        self.items = items
    
    def _load_from_markdown(self) -> None:
        """Загрузка todo из Markdown файла с чекбоксами"""
        try:
            content = self.todo_file.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            logger.error(
                f"Ошибка декодирования Markdown файла todo (не UTF-8): {self.todo_file}",
                exc_info=True,
                extra={"error_type": "UnicodeDecodeError"}
            )
            try:
                content = self.todo_file.read_text(encoding='cp1251')
                logger.info(f"Markdown файл успешно прочитан с кодировкой cp1251")
            except Exception:
                logger.error(f"Не удалось прочитать Markdown файл с альтернативными кодировками")
                self.items = []
                return
        except Exception as e:
            logger.error(
                f"Ошибка чтения Markdown файла todo: {self.todo_file}",
                exc_info=True,
                extra={"error_type": type(e).__name__}
            )
            self.items = []
            return
        
        lines = content.split('\n')
        
        items = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Парсинг чекбоксов: - [ ] или - [x]
            checkbox_match = re.match(r'^(\s*)- \[([ xX])\]\s*(.+)$', line)
            if checkbox_match:
                indent = len(checkbox_match.group(1))
                checked = checkbox_match.group(2).lower() == 'x'
                text = checkbox_match.group(3).strip()
                
                level = indent // 2
                items.append(TodoItem(text, level=level, done=checked))
            # Парсинг обычных списков
            elif re.match(r'^\s*[-*+]\s+', line):
                level = (len(line) - len(line.lstrip())) // 2
                text = re.sub(r'^\s*[-*+]\s+', '', line).strip()
                if text:
                    items.append(TodoItem(text, level=level))
        
        self.items = items
    
    def _load_from_yaml(self) -> None:
        """Загрузка todo из YAML файла"""
        try:
            content = self.todo_file.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            logger.error(
                f"Ошибка декодирования YAML файла todo (не UTF-8): {self.todo_file}",
                exc_info=True,
                extra={"error_type": "UnicodeDecodeError"}
            )
            try:
                content = self.todo_file.read_text(encoding='cp1251')
                logger.info(f"YAML файл успешно прочитан с кодировкой cp1251")
            except Exception:
                logger.error(f"Не удалось прочитать YAML файл с альтернативными кодировками")
                self.items = []
                return
        except Exception as e:
            logger.error(
                f"Ошибка чтения YAML файла todo: {self.todo_file}",
                exc_info=True,
                extra={"error_type": type(e).__name__}
            )
            self.items = []
            return
        
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            logger.error(
                f"Ошибка парсинга YAML файла todo: {self.todo_file}",
                exc_info=True,
                extra={
                    "error_type": "YAMLError",
                    "yaml_error": str(e)
                }
            )
            self.items = []
            return
        
        items = []
        
        def parse_items(items_data: List[Any], level: int = 0) -> None:
            for item_data in items_data:
                if isinstance(item_data, dict):
                    text = item_data.get('text', item_data.get('task', ''))
                    done = item_data.get('done', False)
                    items.append(TodoItem(text, level=level, done=done))
                    
                    if 'children' in item_data:
                        parse_items(item_data['children'], level + 1)
                elif isinstance(item_data, str):
                    items.append(TodoItem(item_data, level=level))
        
        if 'tasks' in data:
            parse_items(data['tasks'])
        elif 'todo' in data:
            parse_items(data['todo'])
        elif isinstance(data, list):
            parse_items(data)
        
        self.items = items
    
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
    
    def mark_task_done(self, task_text: str) -> bool:
        """
        Отметка задачи как выполненной
        
        Args:
            task_text: Текст задачи для отметки
        
        Returns:
            True если задача найдена и отмечена
        """
        for item in self.items:
            if item.text == task_text or item.text.startswith(task_text):
                item.done = True
                self._save_todos()
                return True
        return False
    
    def _save_todos(self) -> None:
        """
        Сохранение todo в файл
        
        Сохраняет изменения статуса задач обратно в файл todo в соответствующем формате.
        """
        if not self.todo_file or not self.todo_file.exists():
            logger.debug(f"Файл todo не найден, пропускаем сохранение")
            return
        
        # Проверка прав доступа на запись
        if not os.access(self.todo_file, os.W_OK):
            logger.warning(f"Нет прав на запись файла todo: {self.todo_file}")
            return
        
        try:
            # Определяем формат файла
            file_format = self._detect_file_format()
            
            if file_format == "yaml":
                self._save_to_yaml()
            elif file_format == "md":
                self._save_to_markdown()
            else:
                self._save_to_text()
            
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
    
    def _save_to_text(self) -> None:
        """Сохранение todo в текстовый файл"""
        if not self.todo_file:
            return
        
        lines = []
        for item in self.items:
            indent = "  " * item.level
            status = "[x]" if item.done else "[ ]"
            lines.append(f"{indent}{status} {item.text}")
        
        content = "\n".join(lines)
        if lines:
            content += "\n"
        
        self.todo_file.write_text(content, encoding='utf-8')
    
    def _save_to_markdown(self) -> None:
        """Сохранение todo в Markdown файл с чекбоксами"""
        if not self.todo_file:
            return
        
        lines = []
        for item in self.items:
            indent = "  " * item.level
            checkbox = "[x]" if item.done else "[ ]"
            lines.append(f"{indent}- {checkbox} {item.text}")
        
        content = "\n".join(lines)
        if lines:
            content += "\n"
        
        self.todo_file.write_text(content, encoding='utf-8')
    
    def _save_to_yaml(self) -> None:
        """Сохранение todo в YAML файл"""
        if not self.todo_file:
            return
        
        tasks = []
        for item in self.items:
            task_data = {
                "text": item.text,
                "done": item.done
            }
            if item.level > 0:
                task_data["level"] = item.level
            tasks.append(task_data)
        
        data = {"tasks": tasks}
        content = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        self.todo_file.write_text(content, encoding='utf-8')
    
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
