"""
Простое тестирование Cursor через файловый интерфейс с реальным выполнением

План:
1. Создать простую задачу (создать тестовый файл)
2. Создать файл инструкции
3. Инструкции пользователю для ручного выполнения в Cursor
4. Ожидать результат
5. Проанализировать результат
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import ConfigLoader
from src.cursor_file_interface import CursorFileInterface

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_simple_cursor_task():
    """Простое тестирование с реальным выполнением задачи"""
    print()
    print("=" * 70)
    print("ПРОСТОЕ ТЕСТИРОВАНИЕ CURSOR С РЕАЛЬНЫМ ВЫПОЛНЕНИЕМ")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Шаг 1: Загрузка конфигурации
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        print(f"[OK] Проект: {project_dir}")
        print()
        
        # Шаг 2: Создание простой задачи
        print("=" * 70)
        print("ШАГ 1: Формирование простой задачи")
        print("=" * 70)
        print()
        
        task_id = f"simple_test_{int(time.time())}"
        
        # Очень простая задача: создать тестовый файл
        instruction = f"""Выполни простую задачу в проекте:

1. Создай файл: docs/results/cursor_test_{task_id}.md
2. Запиши в него следующий текст:

# Тест выполнения задачи через Cursor

**Task ID:** {task_id}
**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Задача выполнена

Этот файл создан автоматически через Cursor по инструкции от Code Agent.

Задача выполнена успешно!

3. В конце файла добавь строку: "Задача выполнена!"

Важно: работай в контексте проекта {project_dir}, используй относительные пути от корня проекта.
"""
        
        print(f"[OK] Инструкция сформирована")
        print(f"  Task ID: {task_id}")
        print(f"  Ожидаемый файл: docs/results/cursor_test_{task_id}.md")
        print()
        
        # Шаг 3: Создание файла инструкции
        print("=" * 70)
        print("ШАГ 2: Создание файла инструкции")
        print("=" * 70)
        print()
        
        cursor_file = CursorFileInterface(project_dir)
        instruction_file = cursor_file.write_instruction(
            instruction=instruction,
            task_id=task_id,
            metadata={
                "test": True,
                "expected_file": f"docs/results/cursor_test_{task_id}.md"
            },
            new_chat=True
        )
        
        print(f"[OK] Файл инструкции создан")
        print(f"  Путь: {instruction_file}")
        print()
        
        # Шаг 4: Инструкции пользователю
        print("=" * 70)
        print("ШАГ 3: ИНСТРУКЦИИ ДЛЯ ВЫПОЛНЕНИЯ В CURSOR")
        print("=" * 70)
        print()
        print("Для завершения теста нужно:")
        print()
        print(f"1. Открой Cursor IDE в проекте: {project_dir}")
        print(f"2. Открой файл инструкции: {instruction_file.name}")
        print(f"   (путь: {instruction_file})")
        print(f"3. Создай новый чат в Cursor (Ctrl+L или кнопка 'New Chat')")
        print(f"4. Скопируй инструкцию из файла в новый чат")
        print(f"5. Выполни инструкцию в Cursor")
        print(f"6. Проверь, что файл создан: docs/results/cursor_test_{task_id}.md")
        print()
        print("После выполнения продолжи тест нажатием Enter...")
        print()
        input("Нажмите Enter после выполнения задачи в Cursor...")
        
        # Шаг 5: Проверка результата
        print()
        print("=" * 70)
        print("ШАГ 4: Проверка результата")
        print("=" * 70)
        print()
        
        expected_file = project_dir / f"docs/results/cursor_test_{task_id}.md"
        
        if expected_file.exists():
            print(f"[OK] Файл результата найден: {expected_file}")
            print()
            
            try:
                content = expected_file.read_text(encoding='utf-8')
                print(f"[OK] Содержимое файла прочитано ({len(content)} символов)")
                print()
                print("Содержимое файла:")
                print("-" * 70)
                print(content)
                print("-" * 70)
                print()
                
                # Проверка контрольной фразы
                if "Задача выполнена!" in content:
                    print("[OK] Контрольная фраза найдена: 'Задача выполнена!'")
                else:
                    print("[WARNING] Контрольная фраза не найдена")
                
                # Проверка Task ID
                if task_id in content:
                    print(f"[OK] Task ID найден в файле: {task_id}")
                else:
                    print(f"[WARNING] Task ID не найден в файле")
                
                print()
                
                # Итоги
                print("=" * 70)
                print("ИТОГИ ТЕСТИРОВАНИЯ")
                print("=" * 70)
                print()
                print("[SUCCESS] Задача выполнена успешно через Cursor!")
                print()
                print("Результаты:")
                print(f"  - Файл создан: {expected_file.exists()}")
                print(f"  - Размер: {len(content)} символов")
                print(f"  - Контрольная фраза: {'найдена' if 'Задача выполнена!' in content else 'не найдена'}")
                print(f"  - Task ID: {'найден' if task_id in content else 'не найден'}")
                print()
                
                return True
                
            except Exception as e:
                print(f"[ERROR] Ошибка чтения файла: {e}")
                return False
        else:
            print(f"[WARNING] Файл результата не найден: {expected_file}")
            print()
            print("Возможные причины:")
            print("  1. Задача еще не выполнена в Cursor")
            print("  2. Файл создан в другом месте")
            print("  3. Ошибка при выполнении задачи")
            print()
            
            # Проверяем директорию results
            results_dir = project_dir / "docs" / "results"
            if results_dir.exists():
                print(f"Файлы в docs/results/:")
                for f in sorted(results_dir.glob("*.md")):
                    print(f"  - {f.name}")
            else:
                print(f"Директория docs/results/ не существует")
            
            print()
            return False
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_simple_cursor_task()
        if success:
            print("[SUCCESS] Тестирование завершено успешно!")
            sys.exit(0)
        else:
            print("[WARNING] Тестирование завершилось с предупреждениями")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
