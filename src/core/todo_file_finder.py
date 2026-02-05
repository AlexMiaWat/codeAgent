from typing import Optional, Dict, Any
from pathlib import Path
import os

from src.utils.logging_utils import logger

class TodoFileFinder:
    """Responsible for finding the todo file and detecting its format."""

    def __init__(self, project_dir: Path, config: Optional[Dict[str, Any]] = None):
        self.project_dir = Path(project_dir)
        self.config = config or {}
        self.todo_format = self.config.get('todo_format', 'txt')
    
    def find_todo_file(self) -> Optional[Path]:
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
    
    def detect_file_format(self, todo_file: Optional[Path]) -> str:
        """
        Определение формата файла TODO на основе расширения и конфигурации
        
        Returns:
            Формат файла: 'yaml', 'md', или 'txt'
        
        Raises:
            ValueError: Если формат не поддерживается или не определен
        """
        if not todo_file:
            return self.todo_format
        
        file_suffix = todo_file.suffix.lower()
        
        supported_formats = {
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'md',
            '.markdown': 'md',
            '.txt': 'txt',
            '': 'txt'
        }
        
        detected_format = supported_formats.get(file_suffix, None)
        
        if detected_format:
            if self.todo_format != "txt" and detected_format != self.todo_format:
                logger.warning(
                    f"Несоответствие формата: файл имеет расширение {file_suffix} "
                    f"(формат: {detected_format}), но в конфигурации указан {self.todo_format}. "
                    f"Используется формат файла: {detected_format}"
                )
            return detected_format
        
        if self.todo_format in ['yaml', 'md', 'txt']:
            logger.warning(
                f"Расширение файла {file_suffix} не распознано. "
                f"Используется формат из конфигурации: {self.todo_format}"
            )
            return self.todo_format
        
        logger.warning(
            f"Не удалось определить формат файла {todo_file}. "
            f"Пробуем определить по содержимому..."
        )
        
        try:
            with open(todo_file, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline() for _ in range(5)]
                content_preview = '\n'.join(first_lines)
                
                if content_preview.strip().startswith('---') or 'tasks:' in content_preview or 'todo:' in content_preview:
                    return 'yaml'
                
                if '- [' in content_preview or '# ' in content_preview:
                    return 'md'
                
                return 'txt'
        except Exception as e:
            logger.error(f"Ошибка при определении формата файла: {e}", exc_info=True)
            return self.todo_format if self.todo_format in ['yaml', 'md', 'txt'] else 'txt'