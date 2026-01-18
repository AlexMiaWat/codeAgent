"""
Модуль управления статусами проекта
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime


class StatusManager:
    """Управление файлом статусов проекта"""
    
    def __init__(self, status_file: Path):
        """
        Инициализация менеджера статусов
        
        Args:
            status_file: Путь к файлу статусов
        """
        self.status_file = Path(status_file)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Создание файла статусов, если он не существует"""
        if not self.status_file.exists():
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            initial_content = f"""# Статус выполнения проекта Code Agent

> Файл автоматически создается и обновляется Code Agent
> Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## История выполнения

"""
            self.status_file.write_text(initial_content, encoding='utf-8')
    
    def read_status(self) -> str:
        """
        Чтение текущего статуса
        
        Returns:
            Содержимое файла статусов
        """
        if not self.status_file.exists():
            return ""
        return self.status_file.read_text(encoding='utf-8')
    
    def write_status(self, content: str):
        """
        Перезапись всего файла статусов
        
        Args:
            content: Новое содержимое файла
        """
        self.status_file.write_text(content, encoding='utf-8')
    
    def append_status(self, message: str, level: int = 1):
        """
        Добавление статуса в конец файла
        
        Args:
            message: Сообщение для добавления
            level: Уровень заголовка (1-6) для markdown, 0 для обычного текста
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.status_file, 'a', encoding='utf-8') as f:
            if level > 0:
                prefix = '#' * level + ' '
                f.write(f"\n{prefix}{message}\n")
            else:
                f.write(f"\n**[{timestamp}]** {message}\n")
    
    def update_task_status(self, task_name: str, status: str, details: Optional[str] = None):
        """
        Обновление статуса конкретной задачи
        
        Args:
            task_name: Название задачи
            status: Статус (например, "В процессе", "Выполнено", "Ошибка")
            details: Дополнительные детали выполнения
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"**Задача:** {task_name}\n**Статус:** {status}"
        
        if details:
            message += f"\n**Детали:** {details}"
        
        self.append_status(message, level=3)
    
    def add_separator(self):
        """Добавление разделителя в файл статусов"""
        with open(self.status_file, 'a', encoding='utf-8') as f:
            f.write("\n---\n")
