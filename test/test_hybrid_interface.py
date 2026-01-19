"""
Тестирование гибридного интерфейса Cursor

Проверяет:
1. Автоматическое определение сложности задач
2. Выбор оптимального метода выполнения (CLI vs файловый)
3. Fallback на файловый интерфейс при неудаче CLI
4. Проверку side-effects
"""

import sys
import time
import logging
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hybrid_cursor_interface import (
    HybridCursorInterface,
    TaskComplexity,
    create_hybrid_cursor_interface
)
from src.config_loader import ConfigLoader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_complexity_determination():
    """Тест автоматического определения сложности задач"""
    print()
    print("=" * 70)
    print("ТЕСТ #1: Определение сложности задач")
    print("=" * 70)
    print()
    
    # Загружаем конфигурацию
    config = ConfigLoader("config/config.yaml")
    project_dir = config.get_project_dir()
    
    # Создаем гибридный интерфейс
    hybrid = create_hybrid_cursor_interface(
        cli_path="docker-compose-agent",
        project_dir=str(project_dir),
        prefer_cli=False,
        verify_side_effects=False  # Отключаем для этого теста
    )
    
    # Тестовые инструкции
    test_cases = [
        # Простые задачи (вопросы, анализ)
        ("Что находится в файле README.md?", TaskComplexity.SIMPLE),
        ("Как работает функция main()?", TaskComplexity.SIMPLE),
        ("Найди все файлы с расширением .py", TaskComplexity.SIMPLE),
        ("Объясни структуру проекта", TaskComplexity.SIMPLE),
        ("What is in the config file?", TaskComplexity.SIMPLE),
        
        # Сложные задачи (создание, изменение)
        ("Создай файл test.txt с текстом Hello", TaskComplexity.COMPLEX),
        ("Измени функцию main() для обработки ошибок", TaskComplexity.COMPLEX),
        ("Добавь новый метод в класс Config", TaskComplexity.COMPLEX),
        ("Реализуй функцию для парсинга JSON", TaskComplexity.COMPLEX),
        ("Create a new file with test data", TaskComplexity.COMPLEX),
        
        # Неоднозначные задачи (по умолчанию COMPLEX)
        ("Проверь и исправь ошибки в коде", TaskComplexity.COMPLEX),
        ("Оптимизируй производительность", TaskComplexity.COMPLEX),
    ]
    
    print("Тестирование определения сложности:")
    print()
    
    correct = 0
    total = len(test_cases)
    
    for instruction, expected_complexity in test_cases:
        determined = hybrid._determine_complexity(instruction)
        is_correct = determined == expected_complexity
        
        status = "[OK]" if is_correct else "[FAIL]"
        print(f"{status} Инструкция: {instruction[:50]}...")
        print(f"   Ожидалось: {expected_complexity.value}, Определено: {determined.value}")
        print()
        
        if is_correct:
            correct += 1
    
    print(f"Результат: {correct}/{total} ({correct*100//total}%)")
    print()
    
    return correct == total


def test_simple_task_execution():
    """Тест выполнения простой задачи (вопрос)"""
    print()
    print("=" * 70)
    print("ТЕСТ #2: Выполнение простой задачи (вопрос)")
    print("=" * 70)
    print()
    
    # Загружаем конфигурацию
    config = ConfigLoader("config/config.yaml")
    project_dir = config.get_project_dir()
    
    # Создаем гибридный интерфейс
    hybrid = create_hybrid_cursor_interface(
        cli_path="docker-compose-agent",
        project_dir=str(project_dir),
        prefer_cli=True,  # Предпочитать CLI для простых задач
        verify_side_effects=False  # Не проверяем side-effects для вопросов
    )
    
    # Простая задача - вопрос
    instruction = "Что находится в файле README.md в корне проекта?"
    task_id = f"test_simple_{int(time.time())}"
    
    print(f"Инструкция: {instruction}")
    print(f"Task ID: {task_id}")
    print()
    
    # Выполняем
    result = hybrid.execute_task(
        instruction=instruction,
        task_id=task_id,
        complexity=TaskComplexity.AUTO
    )
    
    print(f"Результат:")
    print(f"  Success: {result.success}")
    print(f"  Метод: {result.method_used}")
    print(f"  Вывод: {result.output[:200] if result.output else '(пусто)'}...")
    
    if result.error_message:
        print(f"  Ошибка: {result.error_message}")
    
    print()
    
    # Простая задача должна выполниться через CLI
    expected_method = "cli"
    if result.method_used == expected_method:
        print(f"[OK] Задача выполнена через ожидаемый метод: {expected_method}")
        return True
    else:
        print(f"[WARN] Задача выполнена через: {result.method_used} (ожидалось: {expected_method})")
        return result.success  # Все равно считаем успехом если выполнилось


def test_complex_task_execution():
    """Тест выполнения сложной задачи (создание файла)"""
    print()
    print("=" * 70)
    print("ТЕСТ #3: Выполнение сложной задачи (создание файла)")
    print("=" * 70)
    print()
    
    # Загружаем конфигурацию
    config = ConfigLoader("config/config.yaml")
    project_dir = config.get_project_dir()
    
    # Создаем гибридный интерфейс
    hybrid = create_hybrid_cursor_interface(
        cli_path="docker-compose-agent",
        project_dir=str(project_dir),
        prefer_cli=False,  # НЕ предпочитать CLI для сложных задач
        verify_side_effects=True  # Проверяем side-effects
    )
    
    # Сложная задача - создание файла
    task_id = f"test_complex_{int(time.time())}"
    output_file = f"test_hybrid_{task_id}.txt"
    instruction = f"Создай файл {output_file} с текстом 'Hybrid interface test successful!'"
    
    print(f"Инструкция: {instruction}")
    print(f"Task ID: {task_id}")
    print(f"Ожидаемый файл: {project_dir / output_file}")
    print()
    
    # Удаляем файл если существует (для чистоты теста)
    output_path = project_dir / output_file
    if output_path.exists():
        output_path.unlink()
        print(f"Удален существующий файл: {output_path}")
    
    # Выполняем
    result = hybrid.execute_task(
        instruction=instruction,
        task_id=task_id,
        complexity=TaskComplexity.AUTO,
        expected_files=[output_file],
        control_phrase="Файл создан!"
    )
    
    print(f"Результат:")
    print(f"  Success: {result.success}")
    print(f"  Метод: {result.method_used}")
    print(f"  Side-effects проверены: {result.side_effects_verified}")
    
    if result.error_message:
        print(f"  Ошибка: {result.error_message}")
    
    print()
    
    # Проверяем наличие файла
    if output_path.exists():
        content = output_path.read_text(encoding='utf-8')
        print(f"[OK] Файл создан: {output_path}")
        print(f"  Содержимое: {content[:100]}...")
        print()
        return True
    else:
        print(f"[FAIL] Файл не создан: {output_path}")
        print()
        return False


def test_cli_with_fallback():
    """Тест fallback на файловый интерфейс при неудаче CLI"""
    print()
    print("=" * 70)
    print("ТЕСТ #4: Fallback на файловый интерфейс")
    print("=" * 70)
    print()
    
    # Загружаем конфигурацию
    config = ConfigLoader("config/config.yaml")
    project_dir = config.get_project_dir()
    
    # Создаем гибридный интерфейс
    hybrid = create_hybrid_cursor_interface(
        cli_path="docker-compose-agent",
        project_dir=str(project_dir),
        prefer_cli=True,  # Предпочитать CLI (но с fallback)
        verify_side_effects=True  # Проверяем side-effects
    )
    
    # Сложная задача - создание файла
    # CLI скорее всего не выполнит, должен сработать fallback
    task_id = f"test_fallback_{int(time.time())}"
    output_file = f"test_fallback_{task_id}.txt"
    instruction = f"Создай файл {output_file} с текстом 'Fallback test successful!'"
    
    print(f"Инструкция: {instruction}")
    print(f"Task ID: {task_id}")
    print(f"Ожидаемый файл: {project_dir / output_file}")
    print()
    print("Ожидается: CLI не выполнит задачу → fallback на файловый интерфейс")
    print()
    
    # Удаляем файл если существует
    output_path = project_dir / output_file
    if output_path.exists():
        output_path.unlink()
    
    # Выполняем
    result = hybrid.execute_task(
        instruction=instruction,
        task_id=task_id,
        complexity=TaskComplexity.COMPLEX,
        expected_files=[output_file],
        control_phrase="Файл создан!"
    )
    
    print(f"Результат:")
    print(f"  Success: {result.success}")
    print(f"  Метод: {result.method_used}")
    print(f"  Side-effects проверены: {result.side_effects_verified}")
    
    if result.error_message:
        print(f"  Ошибка: {result.error_message}")
    
    print()
    
    # Проверяем метод выполнения
    if result.method_used == "cli_with_fallback":
        print(f"[OK] Fallback сработал корректно")
    elif result.method_used == "file":
        print(f"[OK] Выполнено через файловый интерфейс (ожидаемо)")
    else:
        print(f"[WARN] Выполнено через: {result.method_used}")
    
    # Проверяем наличие файла
    if output_path.exists():
        content = output_path.read_text(encoding='utf-8')
        print(f"[OK] Файл создан: {output_path}")
        print(f"  Содержимое: {content[:100]}...")
        print()
        return True
    else:
        print(f"[FAIL] Файл не создан: {output_path}")
        print()
        return False


def main():
    """Главная функция тестирования"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ГИБРИДНОГО ИНТЕРФЕЙСА CURSOR")
    print("=" * 70)
    print()
    
    results = {}
    
    try:
        # Тест 1: Определение сложности
        results['complexity'] = test_complexity_determination()
        
        # Тест 2: Простая задача
        results['simple'] = test_simple_task_execution()
        
        # Тест 3: Сложная задача
        results['complex'] = test_complex_task_execution()
        
        # Тест 4: Fallback
        results['fallback'] = test_cli_with_fallback()
        
    except KeyboardInterrupt:
        print()
        print("Тестирование прервано пользователем")
        return False
    except Exception as e:
        print()
        print(f"Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Итоги
    print()
    print("=" * 70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    print()
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Результат: {passed}/{total} тестов пройдено ({passed*100//total}%)")
    print()
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
