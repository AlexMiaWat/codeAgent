"""
Демонстрация системы логирования Code Agent

Этот скрипт показывает, как работает система логирования
для задач и сервера.
"""

import sys
import time
import io
from pathlib import Path

# Настройка UTF-8 для Windows консоли
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=True
    )

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.task_logger import TaskLogger, ServerLogger, TaskPhase


def demo_task_logger():
    """Демонстрация TaskLogger"""
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ TASK LOGGER")
    print("="*80 + "\n")
    
    # Создаем логгер для задачи
    task_logger = TaskLogger(
        task_id="demo_task_001",
        task_name="Демонстрационная задача - добавить функцию валидации"
    )
    
    # Фаза 1: Анализ задачи
    task_logger.set_phase(TaskPhase.TASK_ANALYSIS)
    time.sleep(0.5)
    task_logger.log_debug("Определяем тип задачи: development")
    task_logger.log_debug("Выбираем интерфейс: Cursor CLI")
    
    # Фаза 2: Генерация инструкции
    task_logger.set_phase(TaskPhase.INSTRUCTION_GENERATION, stage=1, instruction_num=1)
    time.sleep(0.5)
    
    instruction = """
Выполни следующую задачу:

1. Создай файл src/validators.py
2. Добавь функцию validate_email(email: str) -> bool
3. Реализуй проверку формата email через регулярное выражение
4. Добавь тесты в test/test_validators.py
5. Создай отчет в docs/results/result_demo_task_001.md
6. В конце отчета напиши "Отчет завершен!"
"""
    
    task_logger.log_instruction(1, instruction, "development")
    
    # Фаза 3: Выполнение через Cursor
    task_logger.set_phase(TaskPhase.CURSOR_EXECUTION, stage=1, instruction_num=1)
    time.sleep(0.5)
    
    task_logger.log_new_chat(chat_id="chat_demo_12345")
    
    # Имитируем выполнение
    time.sleep(1.0)
    
    # Имитируем успешный ответ от Cursor
    cursor_response = {
        'success': True,
        'stdout': '''
Successfully created file src/validators.py
Modified file src/__init__.py to export validate_email
Created test file test/test_validators.py
All tests passed (3/3)
Created report docs/results/result_demo_task_001.md
        ''',
        'stderr': '',
        'return_code': 0
    }
    
    task_logger.log_cursor_response(cursor_response, brief=True)
    
    # Фаза 4: Ожидание результата
    task_logger.set_phase(TaskPhase.WAITING_RESULT)
    time.sleep(0.5)
    
    task_logger.log_waiting_result(
        "docs/results/result_demo_task_001.md",
        timeout=300
    )
    
    # Имитируем ожидание
    time.sleep(1.0)
    
    # Фаза 5: Получение результата
    result_content = """
# Отчет о выполнении задачи

## Выполненные действия

1. ✅ Создан файл src/validators.py с функцией validate_email
2. ✅ Добавлена проверка формата email через regex
3. ✅ Созданы тесты в test/test_validators.py
4. ✅ Все тесты пройдены успешно (3/3)

## Созданные файлы

- src/validators.py
- test/test_validators.py

## Измененные файлы

- src/__init__.py

Отчет завершен!
"""
    
    task_logger.log_result_received(
        "docs/results/result_demo_task_001.md",
        wait_time=1.2,
        content_preview=result_content
    )
    
    # Фаза 6: Завершение
    task_logger.set_phase(TaskPhase.COMPLETION)
    time.sleep(0.5)
    
    task_logger.log_completion(
        success=True,
        summary="Функция валидации email успешно добавлена и протестирована"
    )
    
    # Закрываем логгер
    task_logger.close()
    
    print(f"\n✅ Лог-файл задачи создан: {task_logger.log_file}")


def demo_task_logger_with_error():
    """Демонстрация TaskLogger с ошибкой"""
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ TASK LOGGER С ОШИБКОЙ")
    print("="*80 + "\n")
    
    # Создаем логгер для задачи
    task_logger = TaskLogger(
        task_id="demo_task_002",
        task_name="Демонстрационная задача с ошибкой"
    )
    
    # Фаза 1: Анализ задачи
    task_logger.set_phase(TaskPhase.TASK_ANALYSIS)
    time.sleep(0.3)
    
    # Фаза 2: Генерация инструкции
    task_logger.set_phase(TaskPhase.INSTRUCTION_GENERATION, stage=1, instruction_num=1)
    time.sleep(0.3)
    
    task_logger.log_instruction(
        1,
        "Выполни задачу с ошибкой для демонстрации",
        "test"
    )
    
    # Фаза 3: Выполнение через Cursor
    task_logger.set_phase(TaskPhase.CURSOR_EXECUTION, stage=1, instruction_num=1)
    time.sleep(0.3)
    
    task_logger.log_new_chat()
    
    # Имитируем ошибку
    time.sleep(0.5)
    
    # Имитируем ошибочный ответ от Cursor
    cursor_response = {
        'success': False,
        'stdout': '',
        'stderr': 'Error: File not found: missing_file.py',
        'return_code': 1,
        'error_message': 'Cursor CLI вернул код 1'
    }
    
    task_logger.log_cursor_response(cursor_response, brief=True)
    
    # Логируем ошибку
    try:
        raise FileNotFoundError("missing_file.py not found")
    except FileNotFoundError as e:
        task_logger.log_error("Файл не найден при выполнении задачи", e)
    
    # Завершение с ошибкой
    task_logger.set_phase(TaskPhase.ERROR)
    time.sleep(0.3)
    
    task_logger.log_completion(
        success=False,
        summary="Ошибка: файл не найден"
    )
    
    # Закрываем логгер
    task_logger.close()
    
    print(f"\n✅ Лог-файл задачи создан: {task_logger.log_file}")


def demo_server_logger():
    """Демонстрация ServerLogger"""
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ SERVER LOGGER")
    print("="*80 + "\n")
    
    # Создаем логгер сервера
    server_logger = ServerLogger()
    
    # Инициализация
    server_logger.log_initialization({
        'project_dir': 'd:\\Space\\codeAgent',
        'docs_dir': 'd:\\Space\\codeAgent\\docs',
        'cursor_cli_available': True
    })
    
    time.sleep(0.5)
    
    # Итерация 1
    server_logger.log_iteration_start(iteration=1, pending_tasks=3)
    time.sleep(0.3)
    
    # Задача 1
    server_logger.log_task_start(
        task_number=1,
        total_tasks=3,
        task_name="Добавить функцию валидации email"
    )
    time.sleep(0.5)
    
    # Задача 2
    server_logger.log_task_start(
        task_number=2,
        total_tasks=3,
        task_name="Обновить документацию"
    )
    time.sleep(0.5)
    
    # Задача 3
    server_logger.log_task_start(
        task_number=3,
        total_tasks=3,
        task_name="Добавить тесты"
    )
    time.sleep(0.5)
    
    # Остановка сервера
    server_logger.log_server_shutdown(reason="Демонстрация завершена")


def main():
    """Главная функция"""
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ СИСТЕМЫ ЛОГИРОВАНИЯ CODE AGENT")
    print("="*80)
    
    # Создаем директорию для логов если её нет
    Path("logs").mkdir(exist_ok=True)
    
    # Демонстрация TaskLogger
    demo_task_logger()
    
    time.sleep(1)
    
    # Демонстрация TaskLogger с ошибкой
    demo_task_logger_with_error()
    
    time.sleep(1)
    
    # Демонстрация ServerLogger
    demo_server_logger()
    
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("="*80)
    print("\nПроверьте созданные лог-файлы в директории logs/")
    print("Файлы:")
    
    # Показываем созданные файлы
    log_files = sorted(Path("logs").glob("task_demo_*.log"))
    for log_file in log_files:
        print(f"  - {log_file}")
    
    print("\nДля просмотра лог-файла используйте:")
    if log_files:
        print(f"  type {log_files[0]}  (Windows)")
        print(f"  cat {log_files[0]}   (Linux/Mac)")


if __name__ == "__main__":
    main()
