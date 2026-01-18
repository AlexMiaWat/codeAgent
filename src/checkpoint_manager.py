"""
Модуль управления контрольными точками (checkpoints) для восстановления после сбоев
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Состояние выполнения задачи"""
    PENDING = "pending"           # Ожидает выполнения
    IN_PROGRESS = "in_progress"   # В процессе выполнения
    COMPLETED = "completed"       # Успешно завершена
    FAILED = "failed"             # Завершена с ошибкой
    ROLLED_BACK = "rolled_back"   # Откачена


class CheckpointManager:
    """
    Управление контрольными точками для безопасного восстановления после сбоев
    
    Функции:
    - Сохранение состояния выполнения задач
    - Восстановление с последней точки
    - Защита от дублирования задач
    - Откат при критических ошибках
    """
    
    def __init__(self, project_dir: Path, checkpoint_file: str = ".codeagent_checkpoint.json"):
        """
        Инициализация менеджера контрольных точек
        
        Args:
            project_dir: Директория проекта
            checkpoint_file: Имя файла для хранения контрольных точек
        """
        self.project_dir = Path(project_dir)
        self.checkpoint_file = self.project_dir / checkpoint_file
        self.backup_file = self.project_dir / f"{checkpoint_file}.backup"
        
        # Загружаем или создаем checkpoint
        self.checkpoint_data = self._load_checkpoint()
        
        # Сохраняем checkpoint если он был только что создан
        if not self.checkpoint_file.exists():
            self._save_checkpoint(create_backup=False)
        
        logger.info(f"Checkpoint Manager инициализирован: {self.checkpoint_file}")
    
    def _load_checkpoint(self) -> Dict[str, Any]:
        """
        Загрузка контрольной точки из файла
        
        Returns:
            Словарь с данными контрольной точки
        """
        default_data: Dict[str, Any] = {
            "version": "1.0",
            "server_state": {
                "last_start_time": None,
                "last_stop_time": None,
                "iteration_count": 0,
                "clean_shutdown": True
            },
            "tasks": [],
            "current_task": None,
            "session_id": None,
            "last_update": None
        }
        
        # Пробуем загрузить основной файл
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Проверяем, был ли чистый останов
                    if not data.get("server_state", {}).get("clean_shutdown", True):
                        logger.warning(
                            "Обнаружен некорректный останов сервера. "
                            "Будет выполнено восстановление с последней контрольной точки."
                        )
                    
                    return data if isinstance(data, dict) else default_data
            except Exception as e:
                logger.error(f"Ошибка загрузки checkpoint: {e}")
                
                # Пробуем загрузить backup
                if self.backup_file.exists():
                    logger.info("Попытка восстановления из backup файла")
                    try:
                        with open(self.backup_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            logger.info("Успешно восстановлено из backup")
                            return data if isinstance(data, dict) else default_data
                    except Exception as backup_error:
                        logger.error(f"Ошибка загрузки backup: {backup_error}")
        
        return default_data
    
    def _save_checkpoint(self, create_backup: bool = True):
        """
        Сохранение контрольной точки в файл
        
        Args:
            create_backup: Создать резервную копию перед сохранением
        """
        try:
            # Создаем директорию если нужно
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Создаем backup существующего файла
            if create_backup and self.checkpoint_file.exists():
                try:
                    import shutil
                    shutil.copy2(self.checkpoint_file, self.backup_file)
                except Exception as e:
                    logger.warning(f"Не удалось создать backup: {e}")
            
            # Обновляем время последнего обновления
            self.checkpoint_data["last_update"] = datetime.now().isoformat()
            
            # Сохраняем checkpoint
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Checkpoint сохранен: {self.checkpoint_file}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения checkpoint: {e}")
    
    def mark_server_start(self, session_id: str):
        """
        Отметить запуск сервера
        
        Args:
            session_id: ID текущей сессии
        """
        self.checkpoint_data["server_state"]["last_start_time"] = datetime.now().isoformat()
        self.checkpoint_data["server_state"]["clean_shutdown"] = False
        self.checkpoint_data["session_id"] = session_id
        
        self._save_checkpoint()
        
        logger.info(f"Сервер запущен. Сессия: {session_id}")
    
    def mark_server_stop(self, clean: bool = True):
        """
        Отметить остановку сервера
        
        Args:
            clean: True если останов был корректным
        """
        self.checkpoint_data["server_state"]["last_stop_time"] = datetime.now().isoformat()
        self.checkpoint_data["server_state"]["clean_shutdown"] = clean
        self.checkpoint_data["current_task"] = None
        
        self._save_checkpoint()
        
        logger.info(f"Сервер остановлен. Чистый останов: {clean}")
    
    def increment_iteration(self):
        """Увеличить счетчик итераций"""
        self.checkpoint_data["server_state"]["iteration_count"] += 1
        self._save_checkpoint(create_backup=False)
    
    def get_iteration_count(self) -> int:
        """
        Получить текущий счетчик итераций
        
        Returns:
            Количество выполненных итераций
        """
        return self.checkpoint_data["server_state"].get("iteration_count", 0)
    
    def was_clean_shutdown(self) -> bool:
        """
        Проверка, был ли последний останов корректным
        
        Returns:
            True если останов был корректным
        """
        return self.checkpoint_data["server_state"].get("clean_shutdown", True)
    
    def add_task(self, task_id: str, task_text: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Добавить задачу в checkpoint
        
        Args:
            task_id: Уникальный ID задачи
            task_text: Текст задачи
            metadata: Дополнительные метаданные
        """
        task_entry = {
            "task_id": task_id,
            "task_text": task_text,
            "state": TaskState.PENDING.value,
            "start_time": None,
            "end_time": None,
            "attempts": 0,
            "error_message": None,
            "metadata": metadata or {}
        }
        
        # Проверяем, не существует ли уже такая задача
        existing_task = self._find_task(task_id)
        if existing_task:
            logger.warning(f"Задача {task_id} уже существует в checkpoint")
            return
        
        self.checkpoint_data["tasks"].append(task_entry)
        self._save_checkpoint(create_backup=False)
        
        logger.debug(f"Задача добавлена в checkpoint: {task_id}")
    
    def mark_task_start(self, task_id: str):
        """
        Отметить начало выполнения задачи
        
        Args:
            task_id: ID задачи
        """
        task = self._find_task(task_id)
        if not task:
            logger.warning(f"Задача {task_id} не найдена в checkpoint")
            return
        
        task["state"] = TaskState.IN_PROGRESS.value
        task["start_time"] = datetime.now().isoformat()
        task["attempts"] += 1
        
        self.checkpoint_data["current_task"] = task_id
        self._save_checkpoint()
        
        logger.info(f"Задача начата: {task_id} (попытка {task['attempts']})")
    
    def mark_task_completed(self, task_id: str, result: Optional[Dict[str, Any]] = None):
        """
        Отметить успешное завершение задачи
        
        Args:
            task_id: ID задачи
            result: Результат выполнения
        """
        task = self._find_task(task_id)
        if not task:
            logger.warning(f"Задача {task_id} не найдена в checkpoint")
            return
        
        task["state"] = TaskState.COMPLETED.value
        task["end_time"] = datetime.now().isoformat()
        if result:
            task["result"] = result
        
        # Очищаем current_task если это была текущая задача
        if self.checkpoint_data.get("current_task") == task_id:
            self.checkpoint_data["current_task"] = None
        
        self._save_checkpoint()
        
        logger.info(f"Задача завершена: {task_id}")
    
    def mark_task_failed(self, task_id: str, error_message: str):
        """
        Отметить неудачное выполнение задачи
        
        Args:
            task_id: ID задачи
            error_message: Сообщение об ошибке
        """
        task = self._find_task(task_id)
        if not task:
            logger.warning(f"Задача {task_id} не найдена в checkpoint")
            return
        
        task["state"] = TaskState.FAILED.value
        task["end_time"] = datetime.now().isoformat()
        task["error_message"] = error_message
        
        # Очищаем current_task если это была текущая задача
        if self.checkpoint_data.get("current_task") == task_id:
            self.checkpoint_data["current_task"] = None
        
        self._save_checkpoint()
        
        logger.warning(f"Задача завершена с ошибкой: {task_id} - {error_message}")
    
    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """
        Получить текущую выполняемую задачу
        
        Returns:
            Данные текущей задачи или None
        """
        current_task_id = self.checkpoint_data.get("current_task")
        if not current_task_id:
            return None
        
        return self._find_task(current_task_id)
    
    def get_incomplete_tasks(self) -> List[Dict[str, Any]]:
        """
        Получить список незавершенных задач
        
        Returns:
            Список задач в состоянии PENDING или IN_PROGRESS
        """
        incomplete_states = [TaskState.PENDING.value, TaskState.IN_PROGRESS.value]
        return [
            task for task in self.checkpoint_data.get("tasks", [])
            if task.get("state") in incomplete_states
        ]
    
    def get_failed_tasks(self) -> List[Dict[str, Any]]:
        """
        Получить список задач, завершенных с ошибкой
        
        Returns:
            Список задач в состоянии FAILED
        """
        return [
            task for task in self.checkpoint_data.get("tasks", [])
            if task.get("state") == TaskState.FAILED.value
        ]
    
    def should_retry_task(self, task_id: str, max_attempts: int = 3) -> bool:
        """
        Проверить, нужно ли повторить задачу
        
        Args:
            task_id: ID задачи
            max_attempts: Максимальное количество попыток
        
        Returns:
            True если нужно повторить
        """
        task = self._find_task(task_id)
        if not task:
            return False
        
        return task.get("attempts", 0) < max_attempts
    
    def _find_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Найти задачу по ID
        
        Args:
            task_id: ID задачи
        
        Returns:
            Данные задачи или None
        """
        for task in self.checkpoint_data.get("tasks", []):
            if task.get("task_id") == task_id:
                return task
        return None
    
    def is_task_completed(self, task_text: str) -> bool:
        """
        Проверить, была ли задача уже выполнена
        
        Args:
            task_text: Текст задачи
        
        Returns:
            True если задача уже выполнена
        """
        for task in self.checkpoint_data.get("tasks", []):
            if task.get("task_text") == task_text and task.get("state") == TaskState.COMPLETED.value:
                return True
        return False
    
    def get_recovery_info(self) -> Dict[str, Any]:
        """
        Получить информацию для восстановления после сбоя
        
        Returns:
            Словарь с информацией о состоянии
        """
        incomplete_tasks = self.get_incomplete_tasks()
        failed_tasks = self.get_failed_tasks()
        current_task = self.get_current_task()
        
        return {
            "was_clean_shutdown": self.was_clean_shutdown(),
            "last_start_time": self.checkpoint_data["server_state"].get("last_start_time"),
            "last_stop_time": self.checkpoint_data["server_state"].get("last_stop_time"),
            "iteration_count": self.get_iteration_count(),
            "session_id": self.checkpoint_data.get("session_id"),
            "current_task": current_task,
            "incomplete_tasks_count": len(incomplete_tasks),
            "failed_tasks_count": len(failed_tasks),
            "incomplete_tasks": incomplete_tasks,
            "failed_tasks": failed_tasks
        }
    
    def reset_interrupted_task(self):
        """
        Сбросить состояние прерванной задачи для повторного выполнения
        """
        current_task = self.get_current_task()
        if current_task:
            task_id = current_task["task_id"]
            logger.info(f"Сброс прерванной задачи: {task_id}")
            
            # Возвращаем задачу в состояние PENDING
            current_task["state"] = TaskState.PENDING.value
            current_task["end_time"] = None
            
            self.checkpoint_data["current_task"] = None
            self._save_checkpoint()
    
    def clear_old_tasks(self, keep_last_n: int = 100):
        """
        Очистить старые завершенные задачи для экономии места
        
        Args:
            keep_last_n: Количество последних задач для сохранения
        """
        tasks = self.checkpoint_data.get("tasks", [])
        
        # Разделяем на завершенные и незавершенные
        completed_tasks = [t for t in tasks if t.get("state") == TaskState.COMPLETED.value]
        other_tasks = [t for t in tasks if t.get("state") != TaskState.COMPLETED.value]
        
        # Оставляем только последние N завершенных задач
        if len(completed_tasks) > keep_last_n:
            # Сортируем по времени завершения
            completed_tasks.sort(key=lambda t: t.get("end_time", ""), reverse=True)
            completed_tasks = completed_tasks[:keep_last_n]
            
            logger.info(f"Очищено старых задач: {len(tasks) - len(completed_tasks) - len(other_tasks)}")
        
        # Объединяем обратно
        self.checkpoint_data["tasks"] = other_tasks + completed_tasks
        self._save_checkpoint()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получить статистику выполнения задач
        
        Returns:
            Словарь со статистикой
        """
        tasks = self.checkpoint_data.get("tasks", [])
        
        stats = {
            "total_tasks": len(tasks),
            "completed": len([t for t in tasks if t.get("state") == TaskState.COMPLETED.value]),
            "failed": len([t for t in tasks if t.get("state") == TaskState.FAILED.value]),
            "in_progress": len([t for t in tasks if t.get("state") == TaskState.IN_PROGRESS.value]),
            "pending": len([t for t in tasks if t.get("state") == TaskState.PENDING.value]),
            "iteration_count": self.get_iteration_count(),
            "session_id": self.checkpoint_data.get("session_id")
        }
        
        return stats
