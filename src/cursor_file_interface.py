"""
Файловый интерфейс взаимодействия с Cursor (fallback)

Используется когда Cursor CLI недоступен. Работает через файловую систему:
- Code Agent создает файл с инструкцией
- Пользователь/расширение Cursor читает файл и выполняет в Cursor
- Результат записывается в файл результата
- Code Agent читает результат и продолжает работу
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CursorFileInterface:
    """
    Файловый интерфейс взаимодействия с Cursor через файловую систему
    
    Это fallback механизм, когда Cursor CLI недоступен.
    """
    
    def __init__(self, project_dir: Path, commands_dir: str = "cursor_commands", results_dir: str = "cursor_results"):
        """
        Инициализация файлового интерфейса
        
        Args:
            project_dir: Директория проекта
            commands_dir: Директория для файлов с инструкциями
            results_dir: Директория для файлов с результатами
        """
        self.project_dir = Path(project_dir)
        self.commands_dir = self.project_dir / commands_dir
        self.results_dir = self.project_dir / results_dir
        
        # Создаем директории если их нет
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Cursor File Interface initialized")
        logger.info(f"Commands dir: {self.commands_dir}")
        logger.info(f"Results dir: {self.results_dir}")
    
    def write_instruction(
        self,
        instruction: str,
        task_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        new_chat: bool = True
    ) -> Path:
        """
        Записать инструкцию в файл
        
        Args:
            instruction: Текст инструкции
            task_id: Идентификатор задачи
            metadata: Дополнительные метаданные (необязательно)
            new_chat: Если True, добавлять маркер для создания нового чата
        
        Returns:
            Path к созданному файлу
        """
        # Имя файла с маркером NEW_CHAT если требуется
        if new_chat:
            filename = f"instruction_{task_id}_NEW_CHAT.txt"
        else:
            filename = f"instruction_{task_id}.txt"
        file_path = self.commands_dir / filename
        
        # Формируем содержимое файла
        content_parts = []
        
        # Маркер для нового чата (если требуется)
        if new_chat:
            content_parts.extend([
                "# ========================================",
                "# НОВЫЙ ЧАТ - Создай новый чат в Cursor",
                "# ========================================",
                ""
            ])
        
        content_parts.extend([
            f"# Инструкция для задачи {task_id}",
            f"# Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ])
        
        if metadata:
            content_parts.append("# Метаданные:")
            for key, value in metadata.items():
                content_parts.append(f"# {key}: {value}")
            content_parts.append("")
        
        if new_chat:
            content_parts.extend([
                "# ДЕЙСТВИЕ:",
                "# 1. Открой Cursor IDE",
                "# 2. Создай НОВЫЙ чат (Ctrl+L или кнопка 'New Chat')",
                "# 3. Скопируй инструкцию ниже в новый чат",
                "# 4. Выполни инструкцию",
                "# 5. Сохрани результат в файл результата (указан ниже)",
                ""
            ])
        
        content_parts.extend([
            "# Инструкция:",
            "",
            instruction,
            "",
            "# Ожидаемый файл результата:",
            f"# {self.results_dir / f'result_{task_id}.txt'}"
        ])
        
        if new_chat:
            content_parts.extend([
                "",
                "# После выполнения добавь контрольную фразу в конец файла результата:",
                "# 'Задача выполнена!' или 'Отчет завершен!'"
            ])
        
        # Записываем файл
        content = "\n".join(content_parts)
        file_path.write_text(content, encoding='utf-8')
        
        logger.info(f"Инструкция записана в файл: {file_path}")
        return file_path
    
    def instruction_file(self, task_id: str) -> Path:
        """
        Получить путь к файлу инструкции для задачи
        
        Args:
            task_id: Идентификатор задачи
        
        Returns:
            Path к файлу инструкции
        """
        return self.commands_dir / f"instruction_{task_id}.txt"
    
    def result_file(self, task_id: str) -> Path:
        """
        Получить путь к файлу результата для задачи
        
        Args:
            task_id: Идентификатор задачи
        
        Returns:
            Path к файлу результата
        """
        return self.results_dir / f"result_{task_id}.txt"
    
    def read_result(self, task_id: str) -> Optional[str]:
        """
        Прочитать результат выполнения из файла
        
        Args:
            task_id: Идентификатор задачи
        
        Returns:
            Содержимое файла результата или None если файл не существует
        """
        filename = f"result_{task_id}.txt"
        file_path = self.results_dir / filename
        
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            logger.info(f"Результат прочитан из файла: {file_path}")
            return content
        except Exception as e:
            logger.error(f"Ошибка чтения файла результата {file_path}: {e}")
            return None
    
    def check_result_exists(self, task_id: str) -> bool:
        """
        Проверить существование файла результата
        
        Args:
            task_id: Идентификатор задачи
        
        Returns:
            True если файл существует
        """
        filename = f"result_{task_id}.txt"
        file_path = self.results_dir / filename
        return file_path.exists()
    
    def wait_for_result(
        self,
        task_id: str,
        timeout: int = 300,
        check_interval: int = 2,
        control_phrase: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ожидать появления файла результата
        
        Args:
            task_id: Идентификатор задачи
            timeout: Таймаут ожидания (секунды)
            check_interval: Интервал проверки файла (секунды)
            control_phrase: Контрольная фраза, которая должна быть в файле
        
        Returns:
            Словарь с результатом ожидания
        """
        filename = f"result_{task_id}.txt"
        file_path = self.results_dir / filename
        
        start_time = time.time()
        logger.info(f"Ожидание файла результата: {file_path} (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            if file_path.exists():
                # Файл появился, проверяем контрольную фразу если указана
                if control_phrase:
                    content = file_path.read_text(encoding='utf-8')
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
                    content = file_path.read_text(encoding='utf-8')
                    logger.info(f"Файл результата найден")
                    return {
                        "success": True,
                        "file_path": str(file_path),
                        "content": content,
                        "wait_time": time.time() - start_time
                    }
            
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
    
    def check_control_phrase(self, content: str, control_phrase: str) -> bool:
        """
        Проверить наличие контрольной фразы в содержимом
        
        Args:
            content: Содержимое файла
            control_phrase: Контрольная фраза для поиска
        
        Returns:
            True если фраза найдена
        """
        return control_phrase in content if content else False
    
    def cleanup_old_files(self, older_than_days: int = 7):
        """
        Удалить старые файлы команд и результатов
        
        Args:
            older_than_days: Удалить файлы старше указанного количества дней
        """
        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        
        removed_commands = 0
        removed_results = 0
        
        # Удаляем старые файлы инструкций
        for file_path in self.commands_dir.glob("instruction_*.txt"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                removed_commands += 1
        
        # Удаляем старые файлы результатов
        for file_path in self.results_dir.glob("result_*.txt"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                removed_results += 1
        
        if removed_commands > 0 or removed_results > 0:
            logger.info(f"Удалено старых файлов: {removed_commands} инструкций, {removed_results} результатов")
