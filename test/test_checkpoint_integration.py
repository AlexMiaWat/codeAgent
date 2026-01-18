"""
Интеграционный тест checkpoint с сервером
"""

import pytest
from pathlib import Path
from src.checkpoint_manager import CheckpointManager


def test_checkpoint_basic_integration():
    """Базовый интеграционный тест checkpoint"""
    project_dir = Path.cwd()
    
    # Создаем checkpoint manager
    checkpoint = CheckpointManager(project_dir, checkpoint_file=".test_integration_checkpoint.json")
    
    # Проверяем инициализацию
    assert checkpoint.checkpoint_file.exists()
    assert checkpoint.checkpoint_data is not None
    
    # Симулируем работу сервера
    session_id = "integration_test_session"
    checkpoint.mark_server_start(session_id)
    
    # Добавляем задачи
    tasks = [
        ("task_int_001", "Интеграционная задача 1"),
        ("task_int_002", "Интеграционная задача 2"),
    ]
    
    for task_id, task_text in tasks:
        checkpoint.add_task(task_id, task_text)
    
    # Выполняем первую задачу
    checkpoint.mark_task_start(tasks[0][0])
    checkpoint.mark_task_completed(tasks[0][0])
    
    # Проверяем состояние
    stats = checkpoint.get_statistics()
    assert stats["total_tasks"] == 2
    assert stats["completed"] == 1
    assert stats["pending"] == 1
    
    # Корректный останов
    checkpoint.mark_server_stop(clean=True)
    
    # Проверяем, что останов был чистым
    assert checkpoint.was_clean_shutdown() is True
    
    # Очистка
    checkpoint.checkpoint_file.unlink()
    if checkpoint.backup_file.exists():
        checkpoint.backup_file.unlink()
    
    print("✓ Интеграционный тест checkpoint прошел успешно")


def test_checkpoint_recovery_simulation():
    """Симуляция восстановления после сбоя"""
    project_dir = Path.cwd()
    
    # Первый запуск - симуляция сбоя
    checkpoint1 = CheckpointManager(project_dir, checkpoint_file=".test_recovery_checkpoint.json")
    
    session_id = "recovery_test_session"
    checkpoint1.mark_server_start(session_id)
    
    # Добавляем задачи
    checkpoint1.add_task("rec_task_001", "Задача для восстановления 1")
    checkpoint1.add_task("rec_task_002", "Задача для восстановления 2")
    
    # Выполняем первую задачу
    checkpoint1.mark_task_start("rec_task_001")
    checkpoint1.mark_task_completed("rec_task_001")
    
    # Начинаем вторую, но не завершаем (симуляция сбоя)
    checkpoint1.mark_task_start("rec_task_002")
    # НЕ вызываем mark_server_stop - симулируем сбой
    
    # Второй запуск - восстановление
    checkpoint2 = CheckpointManager(project_dir, checkpoint_file=".test_recovery_checkpoint.json")
    
    # Проверяем, что обнаружен сбой
    assert checkpoint2.was_clean_shutdown() is False
    
    # Получаем информацию о восстановлении
    recovery_info = checkpoint2.get_recovery_info()
    assert recovery_info["was_clean_shutdown"] is False
    assert recovery_info["current_task"] is not None
    assert recovery_info["current_task"]["task_id"] == "rec_task_002"
    assert recovery_info["incomplete_tasks_count"] == 1
    
    # Сбрасываем прерванную задачу
    checkpoint2.reset_interrupted_task()
    
    # Проверяем, что задача сброшена
    current_task = checkpoint2.get_current_task()
    assert current_task is None
    
    # Получаем незавершенные задачи
    incomplete = checkpoint2.get_incomplete_tasks()
    assert len(incomplete) == 1
    assert incomplete[0]["task_id"] == "rec_task_002"
    
    # Завершаем восстановление
    checkpoint2.mark_task_start("rec_task_002")
    checkpoint2.mark_task_completed("rec_task_002")
    checkpoint2.mark_server_stop(clean=True)
    
    # Проверяем финальное состояние
    stats = checkpoint2.get_statistics()
    assert stats["total_tasks"] == 2
    assert stats["completed"] == 2
    
    # Очистка
    checkpoint2.checkpoint_file.unlink()
    if checkpoint2.backup_file.exists():
        checkpoint2.backup_file.unlink()
    
    print("✓ Тест восстановления после сбоя прошел успешно")


if __name__ == "__main__":
    test_checkpoint_basic_integration()
    test_checkpoint_recovery_simulation()
    print("\n✓ Все интеграционные тесты прошли успешно!")
