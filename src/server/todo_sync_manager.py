import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..todo_manager import TodoItem
from ..core.interfaces import ICheckpointManager, ITodoManager, IStatusManager, ILogger # Use interfaces

logger = logging.getLogger(__name__)

class TodoCheckpointSynchronizer:
    def __init__(self, checkpoint_manager: ICheckpointManager, todo_manager: ITodoManager, status_manager: IStatusManager, server_logger: ILogger):
        self.checkpoint_manager = checkpoint_manager
        self.todo_manager = todo_manager
        self.status_manager = status_manager
        self.server_logger = server_logger
        
    def check_recovery_needed(self):
        """
        Проверка необходимости восстановления после сбоя
        """
        recovery_info = self.checkpoint_manager.get_recovery_info()
        
        if not recovery_info["was_clean_shutdown"]:
            logger.warning("=" * 80)
            logger.warning("ОБНАРУЖЕН НЕКОРРЕКТНЫЙ ОСТАНОВ СЕРВЕРА")
            logger.warning("=" * 80)
            logger.warning(f"Последний запуск: {recovery_info['last_start_time']}")
            logger.warning(f"Последний останов: {recovery_info['last_stop_time']}")
            logger.warning(f"Сессия: {recovery_info['session_id']}")
            logger.warning(f"Итераций выполнено: {recovery_info['iteration_count']}")
            
            current_task = recovery_info.get("current_task")
            if current_task:
                logger.warning(f"Прерванная задача: {current_task['task_text']}")
                logger.warning(f"  - ID: {current_task['task_id']}")
                logger.warning(f"  - Попыток: {current_task['attempts']}")
                logger.warning(f"  - Начало: {current_task['start_time']}")
                
                self.checkpoint_manager.reset_interrupted_task()
                logger.info("Прерванная задача сброшена для повторного выполнения")
            
            incomplete_count = recovery_info["incomplete_tasks_count"]
            if incomplete_count > 0:
                logger.warning(f"Незавершенных задач: {incomplete_count}")
                for task in recovery_info["incomplete_tasks"][:3]:
                    try:
                        task_text = str(task.get('task_text', 'N/A'))[:100]
                        task_state = str(task.get('state', 'unknown'))
                        logger.warning(f"  - {task_text} (состояние: {task_state})")
                    except Exception as e:
                        logger.warning(f"  - [Ошибка при выводе задачи: {e}]")
            
            failed_count = recovery_info["failed_tasks_count"]
            if failed_count > 0:
                logger.warning(f"Задач с ошибками: {failed_count}")
                for task in recovery_info["failed_tasks"][:2]:
                    try:
                        task_text = str(task.get('task_text', 'N/A'))[:100]
                        error_msg = str(task.get('error_message', 'N/A'))[:200]
                        logger.warning(f"  - {task_text}")
                        logger.warning(f"    Ошибка: {error_msg}")
                    except Exception as e:
                        logger.warning(f"  - [Ошибка при выводе задачи с ошибкой: {e}]")
            
            logger.warning("=" * 80)
            logger.info("Сервер продолжит работу с последней контрольной точки")
            logger.warning("=" * 80)
            logger.info("Восстановление завершено, продолжаем инициализацию сервера...")
            
            self.status_manager.append_status(
                f"Восстановление после сбоя. Незавершенных задач: {incomplete_count}, "
                f"с ошибками: {failed_count}",
                level=2
            )
        else:
            logger.info("Предыдущий останов был корректным. Восстановление не требуется.")
            
            stats = self.checkpoint_manager.get_statistics()
            logger.info(f"Статистика: выполнено {stats['completed']} задач, "
                       f"ошибок {stats['failed']}, итераций {stats['iteration_count']}")

    def sync_todos_with_checkpoint(self):
        """
        Синхронизация TODO задач с checkpoint - помечает задачи как выполненные в TODO файле,
        если они помечены как completed в checkpoint
        """
        try:
            all_todo_items = self.todo_manager.get_all_tasks()
            
            completed_tasks_in_checkpoint = [
                task for task in self.checkpoint_manager.checkpoint_data.get("tasks", [])
                if task.get("state") == "completed"
            ]
            
            completed_task_texts = set()
            for task in completed_tasks_in_checkpoint:
                task_text = task.get("task_text", "")
                if task_text:
                    completed_task_texts.add(task_text)
            
            synced_count = 0
            for todo_item in all_todo_items:
                if not todo_item.done and todo_item.text in completed_task_texts:
                    todo_item.done = True
                    synced_count += 1
                    logger.debug(f"Синхронизация: задача '{todo_item.text}' помечена как выполненная в TODO")
            
            if synced_count > 0:
                self.todo_manager._save_todos()
                logger.info(f"Синхронизация TODO с checkpoint: {synced_count} задач помечено как выполненные")
            else:
                logger.debug("Синхронизация TODO с checkpoint: изменений не требуется")
                
        except Exception as e:
            logger.error(f"Ошибка при синхронизации TODO с checkpoint: {e}", exc_info=True)

    def filter_completed_tasks(self, tasks: List[TodoItem]) -> List[TodoItem]:
        """
        Фильтрация задач: исключает задачи, которые уже выполнены в checkpoint
        
        Args:
            tasks: Список задач для фильтрации
            
        Returns:
            Отфильтрованный список задач (только невыполненные)
        """
        filtered_tasks = []
        for task in tasks:
            if not self.checkpoint_manager.is_task_completed(task.text):
                filtered_tasks.append(task)
            else:
                logger.debug(f"Задача '{task.text}' уже выполнена в checkpoint, пропускаем")
                self.todo_manager.mark_task_done(task.text)
        return filtered_tasks
