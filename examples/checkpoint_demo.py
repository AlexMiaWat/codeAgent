"""
Демонстрация работы системы контрольных точек
"""

import time
import sys
import io
from pathlib import Path

# Настройка кодировки для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.checkpoint_manager import CheckpointManager, TaskState


def demo_normal_flow():
    """Демонстрация нормального потока выполнения"""
    print("=" * 80)
    print("ДЕМОНСТРАЦИЯ: Нормальный поток выполнения")
    print("=" * 80)
    
    # Создаем checkpoint manager
    checkpoint = CheckpointManager(Path.cwd(), checkpoint_file=".demo_checkpoint.json")
    
    # Запуск сервера
    session_id = "demo_session_001"
    checkpoint.mark_server_start(session_id)
    print(f"✓ Сервер запущен. Сессия: {session_id}")
    
    # Добавляем задачи
    tasks = [
        ("task_001", "Реализовать функцию логирования"),
        ("task_002", "Написать тесты для логирования"),
        ("task_003", "Обновить документацию")
    ]
    
    for task_id, task_text in tasks:
        checkpoint.add_task(task_id, task_text)
        print(f"✓ Добавлена задача: {task_text}")
    
    # Выполняем задачи
    for task_id, task_text in tasks:
        print(f"\n→ Начало выполнения: {task_text}")
        checkpoint.mark_task_start(task_id)
        
        # Симуляция работы
        time.sleep(0.5)
        
        checkpoint.mark_task_completed(task_id, result={"status": "success"})
        print(f"✓ Завершено: {task_text}")
    
    # Корректный останов
    checkpoint.mark_server_stop(clean=True)
    print(f"\n✓ Сервер остановлен корректно")
    
    # Статистика
    stats = checkpoint.get_statistics()
    print(f"\nСтатистика:")
    print(f"  - Всего задач: {stats['total_tasks']}")
    print(f"  - Завершено: {stats['completed']}")
    print(f"  - С ошибками: {stats['failed']}")
    print(f"  - Итераций: {stats['iteration_count']}")


def demo_crash_recovery():
    """Демонстрация восстановления после сбоя"""
    print("\n" + "=" * 80)
    print("ДЕМОНСТРАЦИЯ: Восстановление после сбоя")
    print("=" * 80)
    
    # Создаем checkpoint manager
    checkpoint = CheckpointManager(Path.cwd(), checkpoint_file=".demo_crash_checkpoint.json")
    
    # Запуск сервера
    session_id = "demo_crash_session"
    checkpoint.mark_server_start(session_id)
    print(f"✓ Сервер запущен. Сессия: {session_id}")
    
    # Добавляем задачи
    tasks = [
        ("crash_task_001", "Задача 1 - будет завершена"),
        ("crash_task_002", "Задача 2 - будет прервана"),
        ("crash_task_003", "Задача 3 - не начнется")
    ]
    
    for task_id, task_text in tasks:
        checkpoint.add_task(task_id, task_text)
        print(f"✓ Добавлена задача: {task_text}")
    
    # Выполняем первую задачу
    print(f"\n→ Начало выполнения: {tasks[0][1]}")
    checkpoint.mark_task_start(tasks[0][0])
    time.sleep(0.3)
    checkpoint.mark_task_completed(tasks[0][0])
    print(f"✓ Завершено: {tasks[0][1]}")
    
    # Начинаем вторую задачу, но НЕ завершаем (симуляция сбоя)
    print(f"\n→ Начало выполнения: {tasks[1][1]}")
    checkpoint.mark_task_start(tasks[1][0])
    time.sleep(0.2)
    print("💥 СИМУЛЯЦИЯ СБОЯ - сервер падает без корректного останова!")
    
    # НЕ вызываем mark_server_stop - симулируем сбой
    
    print("\n" + "-" * 80)
    print("Перезапуск сервера...")
    print("-" * 80)
    
    # Создаем новый checkpoint manager (симуляция перезапуска)
    checkpoint_new = CheckpointManager(Path.cwd(), checkpoint_file=".demo_crash_checkpoint.json")
    
    # Проверяем информацию о восстановлении
    recovery_info = checkpoint_new.get_recovery_info()
    
    if not recovery_info["was_clean_shutdown"]:
        print("\n⚠ ОБНАРУЖЕН НЕКОРРЕКТНЫЙ ОСТАНОВ СЕРВЕРА")
        print(f"⚠ Сессия: {recovery_info['session_id']}")
        
        current_task = recovery_info.get("current_task")
        if current_task:
            print(f"⚠ Прерванная задача: {current_task['task_text']}")
            print(f"  - ID: {current_task['task_id']}")
            print(f"  - Попыток: {current_task['attempts']}")
            
            # Сбрасываем прерванную задачу
            checkpoint_new.reset_interrupted_task()
            print("✓ Прерванная задача сброшена для повторного выполнения")
        
        print(f"⚠ Незавершенных задач: {recovery_info['incomplete_tasks_count']}")
        for task in recovery_info["incomplete_tasks"]:
            print(f"  - {task['task_text']} (состояние: {task['state']})")
        
        print("\n✓ Сервер продолжит работу с последней контрольной точки")
    
    # Продолжаем выполнение незавершенных задач
    incomplete = checkpoint_new.get_incomplete_tasks()
    print(f"\n→ Продолжение выполнения {len(incomplete)} незавершенных задач...")
    
    for task in incomplete:
        print(f"\n→ Выполнение: {task['task_text']}")
        checkpoint_new.mark_task_start(task['task_id'])
        time.sleep(0.3)
        checkpoint_new.mark_task_completed(task['task_id'])
        print(f"✓ Завершено: {task['task_text']}")
    
    # Корректный останов
    checkpoint_new.mark_server_stop(clean=True)
    print(f"\n✓ Сервер остановлен корректно")
    
    # Финальная статистика
    stats = checkpoint_new.get_statistics()
    print(f"\nФинальная статистика:")
    print(f"  - Всего задач: {stats['total_tasks']}")
    print(f"  - Завершено: {stats['completed']}")
    print(f"  - С ошибками: {stats['failed']}")


def demo_task_retry():
    """Демонстрация повторных попыток при ошибках"""
    print("\n" + "=" * 80)
    print("ДЕМОНСТРАЦИЯ: Повторные попытки при ошибках")
    print("=" * 80)
    
    checkpoint = CheckpointManager(Path.cwd(), checkpoint_file=".demo_retry_checkpoint.json")
    
    session_id = "demo_retry_session"
    checkpoint.mark_server_start(session_id)
    print(f"✓ Сервер запущен. Сессия: {session_id}")
    
    task_id = "retry_task_001"
    task_text = "Задача с ошибками"
    
    checkpoint.add_task(task_id, task_text)
    print(f"✓ Добавлена задача: {task_text}")
    
    max_attempts = 3
    
    # Симулируем несколько неудачных попыток
    for attempt in range(1, max_attempts + 1):
        print(f"\n→ Попытка {attempt}/{max_attempts}: {task_text}")
        checkpoint.mark_task_start(task_id)
        time.sleep(0.2)
        
        if attempt < max_attempts:
            # Симулируем ошибку
            error_msg = f"Ошибка при попытке {attempt}"
            checkpoint.mark_task_failed(task_id, error_msg)
            print(f"✗ Ошибка: {error_msg}")
            
            # Проверяем, можно ли повторить
            if checkpoint.should_retry_task(task_id, max_attempts):
                print(f"  → Будет выполнена повторная попытка")
                # Сбрасываем состояние для повтора
                task = checkpoint._find_task(task_id)
                task["state"] = TaskState.PENDING.value
            else:
                print(f"  ✗ Достигнут лимит попыток")
                break
        else:
            # Последняя попытка успешна
            checkpoint.mark_task_completed(task_id)
            print(f"✓ Успешно завершено на попытке {attempt}")
    
    checkpoint.mark_server_stop(clean=True)
    print(f"\n✓ Сервер остановлен")


def demo_duplicate_prevention():
    """Демонстрация защиты от дублирования"""
    print("\n" + "=" * 80)
    print("ДЕМОНСТРАЦИЯ: Защита от дублирования задач")
    print("=" * 80)
    
    checkpoint = CheckpointManager(Path.cwd(), checkpoint_file=".demo_duplicate_checkpoint.json")
    
    session_id = "demo_duplicate_session"
    checkpoint.mark_server_start(session_id)
    print(f"✓ Сервер запущен. Сессия: {session_id}")
    
    task_id = "duplicate_task_001"
    task_text = "Уникальная задача"
    
    # Добавляем и выполняем задачу
    checkpoint.add_task(task_id, task_text)
    print(f"✓ Добавлена задача: {task_text}")
    
    checkpoint.mark_task_start(task_id)
    time.sleep(0.2)
    checkpoint.mark_task_completed(task_id)
    print(f"✓ Задача выполнена: {task_text}")
    
    # Проверяем, выполнена ли задача
    if checkpoint.is_task_completed(task_text):
        print(f"\n✓ Задача отмечена как выполненная")
        print(f"  → При следующем запуске она будет пропущена")
    
    # Симулируем попытку добавить ту же задачу снова
    print(f"\n→ Попытка добавить ту же задачу снова...")
    checkpoint.add_task(task_id + "_duplicate", task_text)
    
    if checkpoint.is_task_completed(task_text):
        print(f"✓ Защита от дублирования: задача уже выполнена, пропускаем")
    
    checkpoint.mark_server_stop(clean=True)


def cleanup_demo_files():
    """Очистка демонстрационных файлов"""
    demo_files = [
        ".demo_checkpoint.json",
        ".demo_checkpoint.json.backup",
        ".demo_crash_checkpoint.json",
        ".demo_crash_checkpoint.json.backup",
        ".demo_retry_checkpoint.json",
        ".demo_retry_checkpoint.json.backup",
        ".demo_duplicate_checkpoint.json",
        ".demo_duplicate_checkpoint.json.backup"
    ]
    
    for filename in demo_files:
        filepath = Path(filename)
        if filepath.exists():
            filepath.unlink()


if __name__ == "__main__":
    try:
        # Очищаем старые демо-файлы
        cleanup_demo_files()
        
        # Запускаем демонстрации
        demo_normal_flow()
        time.sleep(1)
        
        demo_crash_recovery()
        time.sleep(1)
        
        demo_task_retry()
        time.sleep(1)
        
        demo_duplicate_prevention()
        
        print("\n" + "=" * 80)
        print("ВСЕ ДЕМОНСТРАЦИИ ЗАВЕРШЕНЫ")
        print("=" * 80)
        print("\nСистема контрольных точек готова к использованию!")
        print("Запустите сервер обычным способом - восстановление будет автоматическим.")
        
    finally:
        # Очищаем демо-файлы после завершения
        print("\n→ Очистка демонстрационных файлов...")
        cleanup_demo_files()
        print("✓ Готово!")
