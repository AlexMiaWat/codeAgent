"""
Реальное тестирование выполнения задачи через Cursor

Создает простую задачу и готовит инструкции для выполнения в Cursor IDE
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import ConfigLoader
from src.cursor_file_interface import CursorFileInterface


def main():
    """Создание тестовой задачи для реального выполнения"""
    print()
    print("=" * 70)
    print("СОЗДАНИЕ ТЕСТОВОЙ ЗАДАЧИ ДЛЯ РЕАЛЬНОГО ВЫПОЛНЕНИЯ В CURSOR")
    print("=" * 70)
    print()
    
    config = ConfigLoader("config/config.yaml")
    project_dir = config.get_project_dir()
    
    task_id = f"real_test_{int(time.time())}"
    
    # Простая задача: создать тестовый файл с информацией о Code Agent
    instruction = f"""Выполни простую задачу в проекте:

1. Создай файл: docs/results/cursor_execution_test_{task_id}.md

2. Запиши в него следующий отчет:

# Тест выполнения задачи через Cursor

**Task ID:** {task_id}
**Дата выполнения:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Проект:** your-project 

## Описание теста

Этот файл создан автоматически через Cursor IDE по инструкции от Code Agent.

## Результат выполнения

Задача выполнена успешно через Cursor IDE.

## Детали

- Инструкция получена через файловый интерфейс
- Выполнение произведено в контексте проекта your-project 
- Результат сохранен в docs/results/

Задача выполнена!

3. Убедись, что файл создан и содержит текст выше.
4. В конце файла должна быть строка: "Задача выполнена!"

Важно: работай в контексте проекта {project_dir}, используй относительные пути от корня проекта.
"""
    
    # Создаем файл инструкции
    cursor_file = CursorFileInterface(project_dir)
    instruction_file = cursor_file.write_instruction(
        instruction=instruction,
        task_id=task_id,
        metadata={
            "test_type": "real_execution",
            "expected_file": f"docs/results/cursor_execution_test_{task_id}.md"
        },
        new_chat=True
    )
    
    print(f"[OK] Файл инструкции создан")
    print(f"  Путь: {instruction_file}")
    print()
    
    # Инструкции пользователю
    print("=" * 70)
    print("ИНСТРУКЦИИ ДЛЯ ВЫПОЛНЕНИЯ В CURSOR")
    print("=" * 70)
    print()
    print("Для завершения теста выполни следующие шаги:")
    print()
    print(f"1. Открой Cursor IDE в проекте: {project_dir}")
    print(f"2. Открой файл инструкции:")
    print(f"   {instruction_file}")
    print(f"3. Создай новый чат в Cursor (Ctrl+L или кнопка 'New Chat')")
    print(f"4. Скопируй инструкцию из файла в новый чат Cursor")
    print(f"5. Выполни инструкцию в Cursor")
    print(f"6. Проверь, что файл создан:")
    print(f"   docs/results/cursor_execution_test_{task_id}.md")
    print()
    print("После выполнения задачи продолжай с проверкой результата.")
    print()
    print("=" * 70)
    print()
    
    # Информация о проверке
    expected_file = project_dir / f"docs/results/cursor_execution_test_{task_id}.md"
    print(f"Ожидаемый файл результата: {expected_file}")
    print()
    
    return task_id, expected_file, instruction_file


if __name__ == "__main__":
    try:
        task_id, expected_file, instruction_file = main()
        print(f"[INFO] Задача создана. Task ID: {task_id}")
        print(f"[INFO] Файл инструкции: {instruction_file.name}")
        print(f"[INFO] Ожидаемый файл: {expected_file.name}")
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
