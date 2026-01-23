"""
Модуль управления статусами проекта
"""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import os
import logging

from .core.interfaces import IStatusManager

logger = logging.getLogger(__name__)


class StatusManager(IStatusManager):
    """Управление файлом статусов проекта"""
    
    def __init__(self, status_file: Path, config: Optional[dict] = None):
        """
        Инициализация менеджера статусов

        Args:
            status_file: Путь к файлу статусов
            config: Конфигурация менеджера
        """
        self.status_file = Path(status_file)
        self.config = config or {}
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Создание файла статусов, если он не существует"""
        if not self.status_file.exists():
            # Проверка прав на запись в директорию
            parent_dir = self.status_file.parent
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    logger.error(f"Нет прав на создание директории: {parent_dir}")
                    raise
                except OSError as e:
                    logger.error(f"Ошибка создания директории {parent_dir}: {e}", exc_info=True)
                    raise
            
            # Проверка прав на запись
            if not os.access(parent_dir, os.W_OK):
                logger.error(f"Нет прав на запись в директорию: {parent_dir}")
                raise PermissionError(f"Нет прав на запись в директорию: {parent_dir}")
            
            initial_content = f"""# Статус выполнения проекта Code Agent

> Файл автоматически создается и обновляется Code Agent
> Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## История выполнения

"""
            try:
                self.status_file.write_text(initial_content, encoding='utf-8')
            except PermissionError:
                logger.error(f"Нет прав на запись в файл: {self.status_file}")
                raise
            except OSError as e:
                logger.error(f"Ошибка записи в файл {self.status_file}: {e}", exc_info=True)
                raise
    
    def read_status(self) -> str:
        """
        Чтение текущего статуса
        
        Returns:
            Содержимое файла статусов
        
        Raises:
            PermissionError: Если нет прав на чтение файла
            OSError: При других ошибках чтения
        """
        if not self.status_file.exists():
            return ""
        
        # Проверка прав на чтение
        if not os.access(self.status_file, os.R_OK):
            logger.error(f"Нет прав на чтение файла статусов: {self.status_file}")
            raise PermissionError(f"Нет прав на чтение файла: {self.status_file}")
        
        try:
            return self.status_file.read_text(encoding='utf-8')
        except PermissionError:
            logger.error(f"Ошибка доступа при чтении файла: {self.status_file}")
            raise
        except OSError as e:
            logger.error(f"Ошибка чтения файла {self.status_file}: {e}", exc_info=True)
            raise
    
    def write_status(self, content: str) -> None:
        """
        Перезапись всего файла статусов
        
        Args:
            content: Новое содержимое файла
        
        Raises:
            PermissionError: Если нет прав на запись файла
            OSError: При других ошибках записи
        """
        # Проверка прав на запись
        parent_dir = self.status_file.parent
        if not os.access(parent_dir, os.W_OK):
            logger.error(f"Нет прав на запись в директорию: {parent_dir}")
            raise PermissionError(f"Нет прав на запись в директорию: {parent_dir}")
        
        try:
            self.status_file.write_text(content, encoding='utf-8')
        except PermissionError:
            logger.error(f"Нет прав на запись в файл: {self.status_file}")
            raise
        except OSError as e:
            logger.error(f"Ошибка записи в файл {self.status_file}: {e}", exc_info=True)
            raise
    
    def append_status(self, message: str, level: int = 1) -> None:
        """
        Добавление статуса в конец файла
        
        Args:
            message: Сообщение для добавления
            level: Уровень заголовка (1-6) для markdown, 0 для обычного текста
        
        Raises:
            PermissionError: Если нет прав на запись файла
            OSError: При других ошибках записи
        """
        # Проверка прав на запись
        parent_dir = self.status_file.parent
        if not os.access(parent_dir, os.W_OK):
            logger.error(f"Нет прав на запись в директорию: {parent_dir}")
            raise PermissionError(f"Нет прав на запись в директорию: {parent_dir}")
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            with open(self.status_file, 'a', encoding='utf-8') as f:
                if level > 0:
                    prefix = '#' * level + ' '
                    f.write(f"\n{prefix}{message}\n")
                else:
                    f.write(f"\n**[{timestamp}]** {message}\n")
        except PermissionError:
            logger.error(f"Нет прав на запись в файл: {self.status_file}")
            raise
        except OSError as e:
            logger.error(f"Ошибка записи в файл {self.status_file}: {e}", exc_info=True)
            raise
    
    def update_task_status(self, task_name: str, status: str, details: Optional[str] = None) -> None:
        """
        Обновление статуса конкретной задачи
        
        Args:
            task_name: Название задачи
            status: Статус (например, "В процессе", "Выполнено", "Ошибка")
            details: Дополнительные детали выполнения
        
        Raises:
            PermissionError: Если нет прав на запись файла
            OSError: При других ошибках записи
        """
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"**Задача:** {task_name}\n**Статус:** {status}"
        
        if details:
            message += f"\n**Детали:** {details}"
        
        self.append_status(message, level=3)
    
    def add_separator(self) -> None:
        """
        Добавление разделителя в файл статусов
        
        Raises:
            PermissionError: Если нет прав на запись файла
            OSError: При других ошибках записи
        """
        # Проверка прав на запись
        parent_dir = self.status_file.parent
        if not os.access(parent_dir, os.W_OK):
            logger.error(f"Нет прав на запись в директорию: {parent_dir}")
            raise PermissionError(f"Нет прав на запись в директорию: {parent_dir}")
        
        try:
            with open(self.status_file, 'a', encoding='utf-8') as f:
                f.write("\n---\n")
        except PermissionError:
            logger.error(f"Нет прав на запись в файл: {self.status_file}")
            raise
        except OSError as e:
            logger.error(f"Ошибка записи в файл {self.status_file}: {e}", exc_info=True)
            raise

    def is_healthy(self) -> bool:
        """
        Проверить здоровье менеджера статусов.

        Returns:
            True если менеджер в рабочем состоянии
        """
        try:
            # Проверяем что можем прочитать файл
            parent_dir = self.status_file.parent
            return (parent_dir.exists() and
                   os.access(parent_dir, os.W_OK) and
                   (not self.status_file.exists() or self.status_file.stat().st_size >= 0))
        except Exception as e:
            logger.error(f"Health check failed for StatusManager: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Получить статус менеджера статусов.

        Returns:
            Словарь со статусной информацией
        """
        try:
            file_exists = self.status_file.exists()
            file_size = self.status_file.stat().st_size if file_exists else 0
            return {
                'healthy': self.is_healthy(),
                'status_file': str(self.status_file),
                'file_exists': file_exists,
                'file_size': file_size,
                'readable': file_exists and os.access(self.status_file, os.R_OK),
                'writable': os.access(self.status_file.parent, os.W_OK),
            }
        except Exception as e:
            logger.error(f"Failed to get status for StatusManager: {e}")
            return {
                'healthy': False,
                'error': str(e),
            }

    def dispose(self) -> None:
        """
        Очистить ресурсы менеджера статусов.
        """
        # StatusManager не требует специальной очистки ресурсов
        logger.debug("StatusManager disposed")
