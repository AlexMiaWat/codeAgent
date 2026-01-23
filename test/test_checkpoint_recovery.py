"""
Тесты системы контрольных точек и восстановления после сбоев
"""

import pytest
import time
from src.checkpoint_manager import CheckpointManager, TaskState


@pytest.fixture
def temp_project_dir(tmp_path):
    """Временная директория проекта для тестов"""
    return tmp_path


@pytest.fixture
def checkpoint_manager(temp_project_dir):
    """Создание менеджера контрольных точек для тестов"""
    return CheckpointManager(temp_project_dir, checkpoint_file=".test_checkpoint.json")


def test_checkpoint_initialization(checkpoint_manager, temp_project_dir):
    """Тест инициализации checkpoint manager"""
    assert checkpoint_manager.checkpoint_file.exists()
    assert checkpoint_manager.checkpoint_data is not None
    assert "version" in checkpoint_manager.checkpoint_data
    assert "server_state" in checkpoint_manager.checkpoint_data
    assert "tasks" in checkpoint_manager.checkpoint_data


def test_server_start_stop(checkpoint_manager):
    """Тест отметки запуска и остановки сервера"""
    session_id = "test_session_001"
    
    # Запуск сервера
    checkpoint_manager.mark_server_start(session_id)
    
    assert checkpoint_manager.checkpoint_data["session_id"] == session_id
    assert checkpoint_manager.checkpoint_data["server_state"]["clean_shutdown"] is False
    assert checkpoint_manager.checkpoint_data["server_state"]["last_start_time"] is not None
    
    # Корректный останов
    checkpoint_manager.mark_server_stop(clean=True)
    
    assert checkpoint_manager.checkpoint_data["server_state"]["clean_shutdown"] is True
    assert checkpoint_manager.checkpoint_data["server_state"]["last_stop_time"] is not None


def test_task_lifecycle(checkpoint_manager):
    """Тест полного жизненного цикла задачи"""
    task_id = "task_001"
    task_text = "Тестовая задача"
    
    # Добавление задачи
    checkpoint_manager.add_task(task_id, task_text)
    
    task = checkpoint_manager._find_task(task_id)
    assert task is not None
    assert task["task_text"] == task_text
    assert task["state"] == TaskState.PENDING.value
    
    # Начало выполнения
    checkpoint_manager.mark_task_start(task_id)
    
    task = checkpoint_manager._find_task(task_id)
    assert task["state"] == TaskState.IN_PROGRESS.value
    assert task["attempts"] == 1
    assert task["start_time"] is not None
    
    # Завершение задачи
    checkpoint_manager.mark_task_completed(task_id, result={"status": "success"})
    
    task = checkpoint_manager._find_task(task_id)
    assert task["state"] == TaskState.COMPLETED.value
    assert task["end_time"] is not None
    assert "result" in task


def test_task_failure(checkpoint_manager):
    """Тест обработки ошибки выполнения задачи"""
    task_id = "task_002"
    task_text = "Задача с ошибкой"
    error_message = "Тестовая ошибка"
    
    checkpoint_manager.add_task(task_id, task_text)
    checkpoint_manager.mark_task_start(task_id)
    checkpoint_manager.mark_task_failed(task_id, error_message)
    
    task = checkpoint_manager._find_task(task_id)
    assert task["state"] == TaskState.FAILED.value
    assert task["error_message"] == error_message
    assert task["end_time"] is not None


def test_crash_recovery(checkpoint_manager):
    """Тест восстановления после сбоя"""
    session_id = "test_session_crash"
    
    # Симулируем запуск сервера
    checkpoint_manager.mark_server_start(session_id)
    
    # Добавляем несколько задач
    checkpoint_manager.add_task("task_1", "Задача 1")
    checkpoint_manager.add_task("task_2", "Задача 2")
    checkpoint_manager.add_task("task_3", "Задача 3")
    
    # Начинаем выполнение первой задачи
    checkpoint_manager.mark_task_start("task_1")
    checkpoint_manager.mark_task_completed("task_1")
    
    # Начинаем вторую задачу, но не завершаем (симуляция сбоя)
    checkpoint_manager.mark_task_start("task_2")
    
    # Проверяем информацию о восстановлении
    recovery_info = checkpoint_manager.get_recovery_info()
    
    assert recovery_info["was_clean_shutdown"] is False
    assert recovery_info["current_task"] is not None
    assert recovery_info["current_task"]["task_id"] == "task_2"
    assert recovery_info["incomplete_tasks_count"] == 2  # task_2 и task_3
    
    # Сбрасываем прерванную задачу
    checkpoint_manager.reset_interrupted_task()
    
    task_2 = checkpoint_manager._find_task("task_2")
    assert task_2["state"] == TaskState.PENDING.value


def test_duplicate_task_prevention(checkpoint_manager):
    """Тест защиты от дублирования задач"""
    task_text = "Уникальная задача"
    
    # Добавляем и завершаем задачу
    checkpoint_manager.add_task("task_unique", task_text)
    checkpoint_manager.mark_task_start("task_unique")
    checkpoint_manager.mark_task_completed("task_unique")
    
    # Проверяем, что задача отмечена как выполненная
    assert checkpoint_manager.is_task_completed(task_text) is True
    
    # Проверяем, что другая задача не отмечена
    assert checkpoint_manager.is_task_completed("Другая задача") is False


def test_incomplete_tasks_retrieval(checkpoint_manager):
    """Тест получения незавершенных задач"""
    # Добавляем задачи в разных состояниях
    checkpoint_manager.add_task("task_pending", "Ожидающая задача")
    
    checkpoint_manager.add_task("task_in_progress", "Выполняемая задача")
    checkpoint_manager.mark_task_start("task_in_progress")
    
    checkpoint_manager.add_task("task_completed", "Завершенная задача")
    checkpoint_manager.mark_task_start("task_completed")
    checkpoint_manager.mark_task_completed("task_completed")
    
    checkpoint_manager.add_task("task_failed", "Задача с ошибкой")
    checkpoint_manager.mark_task_start("task_failed")
    checkpoint_manager.mark_task_failed("task_failed", "Ошибка")
    
    # Получаем незавершенные задачи
    incomplete = checkpoint_manager.get_incomplete_tasks()
    
    assert len(incomplete) == 2  # pending и in_progress
    task_ids = [t["task_id"] for t in incomplete]
    assert "task_pending" in task_ids
    assert "task_in_progress" in task_ids


def test_failed_tasks_retrieval(checkpoint_manager):
    """Тест получения задач с ошибками"""
    checkpoint_manager.add_task("task_fail_1", "Задача 1")
    checkpoint_manager.mark_task_start("task_fail_1")
    checkpoint_manager.mark_task_failed("task_fail_1", "Ошибка 1")
    
    checkpoint_manager.add_task("task_fail_2", "Задача 2")
    checkpoint_manager.mark_task_start("task_fail_2")
    checkpoint_manager.mark_task_failed("task_fail_2", "Ошибка 2")
    
    failed_tasks = checkpoint_manager.get_failed_tasks()
    
    assert len(failed_tasks) == 2
    assert all(t["state"] == TaskState.FAILED.value for t in failed_tasks)


def test_task_retry_logic(checkpoint_manager):
    """Тест логики повторных попыток"""
    task_id = "task_retry"
    
    checkpoint_manager.add_task(task_id, "Задача для повтора")
    
    # Первая попытка
    checkpoint_manager.mark_task_start(task_id)
    assert checkpoint_manager.should_retry_task(task_id, max_attempts=3) is True
    checkpoint_manager.mark_task_failed(task_id, "Ошибка 1")
    
    # Вторая попытка
    task = checkpoint_manager._find_task(task_id)
    task["state"] = TaskState.PENDING.value  # Сбрасываем для повтора
    checkpoint_manager.mark_task_start(task_id)
    assert checkpoint_manager.should_retry_task(task_id, max_attempts=3) is True
    checkpoint_manager.mark_task_failed(task_id, "Ошибка 2")
    
    # Третья попытка
    task = checkpoint_manager._find_task(task_id)
    task["state"] = TaskState.PENDING.value
    checkpoint_manager.mark_task_start(task_id)
    assert checkpoint_manager.should_retry_task(task_id, max_attempts=3) is False  # Достигнут лимит


def test_iteration_counter(checkpoint_manager):
    """Тест счетчика итераций"""
    assert checkpoint_manager.get_iteration_count() == 0
    
    checkpoint_manager.increment_iteration()
    assert checkpoint_manager.get_iteration_count() == 1
    
    checkpoint_manager.increment_iteration()
    checkpoint_manager.increment_iteration()
    assert checkpoint_manager.get_iteration_count() == 3


def test_clear_old_tasks(checkpoint_manager):
    """Тест очистки старых задач"""
    # Добавляем много завершенных задач
    for i in range(150):
        task_id = f"task_{i}"
        checkpoint_manager.add_task(task_id, f"Задача {i}")
        checkpoint_manager.mark_task_start(task_id)
        checkpoint_manager.mark_task_completed(task_id)
        time.sleep(0.001)  # Небольшая задержка для разных timestamp
    
    # Добавляем незавершенные задачи
    checkpoint_manager.add_task("task_pending_1", "Незавершенная 1")
    checkpoint_manager.add_task("task_pending_2", "Незавершенная 2")
    
    # Очищаем старые задачи
    checkpoint_manager.clear_old_tasks(keep_last_n=50)
    
    tasks = checkpoint_manager.checkpoint_data["tasks"]
    completed_tasks = [t for t in tasks if t["state"] == TaskState.COMPLETED.value]
    
    # Должно остаться 50 завершенных + 2 незавершенных
    assert len(completed_tasks) <= 50
    assert len(checkpoint_manager.get_incomplete_tasks()) == 2


def test_statistics(checkpoint_manager):
    """Тест получения статистики"""
    # Создаем задачи в разных состояниях
    checkpoint_manager.add_task("task_c1", "Завершенная 1")
    checkpoint_manager.mark_task_start("task_c1")
    checkpoint_manager.mark_task_completed("task_c1")
    
    checkpoint_manager.add_task("task_c2", "Завершенная 2")
    checkpoint_manager.mark_task_start("task_c2")
    checkpoint_manager.mark_task_completed("task_c2")
    
    checkpoint_manager.add_task("task_f1", "С ошибкой")
    checkpoint_manager.mark_task_start("task_f1")
    checkpoint_manager.mark_task_failed("task_f1", "Ошибка")
    
    checkpoint_manager.add_task("task_p1", "Ожидающая")
    
    stats = checkpoint_manager.get_statistics()
    
    assert stats["total_tasks"] == 4
    assert stats["completed"] == 2
    assert stats["failed"] == 1
    assert stats["pending"] == 1


def test_backup_recovery(checkpoint_manager, temp_project_dir):
    """Тест восстановления из backup файла"""
    # Создаем задачу
    checkpoint_manager.add_task("task_backup", "Задача для backup")
    
    # Выполняем еще одно изменение, чтобы создать backup
    checkpoint_manager.mark_task_start("task_backup")
    
    # Симулируем повреждение основного файла
    checkpoint_file = temp_project_dir / ".test_checkpoint.json"
    backup_file = temp_project_dir / ".test_checkpoint.json.backup"
    
    # Убеждаемся, что backup создан (создается при втором сохранении)
    assert backup_file.exists()
    
    # Повреждаем основной файл
    with open(checkpoint_file, 'w') as f:
        f.write("invalid json {{{")
    
    # Создаем новый менеджер (должен восстановиться из backup)
    new_manager = CheckpointManager(temp_project_dir, checkpoint_file=".test_checkpoint.json")
    
    # Проверяем, что данные восстановлены
    task = new_manager._find_task("task_backup")
    assert task is not None
    assert task["task_text"] == "Задача для backup"


def test_concurrent_task_execution(checkpoint_manager):
    """Тест обработки текущей задачи"""
    checkpoint_manager.add_task("task_1", "Задача 1")
    checkpoint_manager.add_task("task_2", "Задача 2")
    
    # Начинаем первую задачу
    checkpoint_manager.mark_task_start("task_1")
    
    current = checkpoint_manager.get_current_task()
    assert current is not None
    assert current["task_id"] == "task_1"
    
    # Завершаем первую задачу
    checkpoint_manager.mark_task_completed("task_1")
    
    # Текущая задача должна быть очищена
    current = checkpoint_manager.get_current_task()
    assert current is None
    
    # Начинаем вторую задачу
    checkpoint_manager.mark_task_start("task_2")
    
    current = checkpoint_manager.get_current_task()
    assert current["task_id"] == "task_2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
