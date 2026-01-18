"""
Модуль управления todo-листом проекта
"""

from pathlib import Path
from typing import List, Dict, Optional
import yaml
import re


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
    
    def __repr__(self):
        status = "✓" if self.done else "○"
        indent = "  " * self.level
        return f"{indent}{status} {self.text}"


class TodoManager:
    """Управление todo-листом проекта"""
    
    def __init__(self, project_dir: Path, todo_format: str = "txt"):
        """
        Инициализация менеджера todo
        
        Args:
            project_dir: Директория проекта
            todo_format: Формат файла todo (txt, yaml, md)
        """
        self.project_dir = Path(project_dir)
        self.todo_format = todo_format
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
        
        for name in possible_names:
            file_path = self.project_dir / name
            if file_path.exists():
                return file_path
        
        return None
    
    def _load_todos(self):
        """Загрузка todo из файла"""
        if not self.todo_file or not self.todo_file.exists():
            self.items = []
            return
        
        if self.todo_format == "yaml" or self.todo_file.suffix == ".yaml":
            self._load_from_yaml()
        elif self.todo_file.suffix == ".md":
            self._load_from_markdown()
        else:
            self._load_from_text()
    
    def _load_from_text(self):
        """Загрузка todo из текстового файла"""
        content = self.todo_file.read_text(encoding='utf-8')
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
    
    def _load_from_markdown(self):
        """Загрузка todo из Markdown файла с чекбоксами"""
        content = self.todo_file.read_text(encoding='utf-8')
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
    
    def _load_from_yaml(self):
        """Загрузка todo из YAML файла"""
        content = self.todo_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content) or {}
        
        items = []
        
        def parse_items(items_data: List, level: int = 0):
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
    
    def _save_todos(self):
        """Сохранение todo в файл (базовая реализация)"""
        # В будущем можно реализовать сохранение обратно в файл
        pass
    
    def get_task_hierarchy(self) -> Dict:
        """
        Получение иерархии задач
        
        Returns:
            Словарь с иерархией задач
        """
        # Простая реализация - можно расширить для построения дерева
        return {
            'total': len(self.items),
            'pending': len(self.get_pending_tasks()),
            'completed': len([i for i in self.items if i.done]),
            'items': [{'text': item.text, 'level': item.level, 'done': item.done} 
                     for item in self.items]
        }
