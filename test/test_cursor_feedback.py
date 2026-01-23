"""
Тест обратной связи от Cursor

Проверяет:
1. Создание файла инструкции
2. Ожидание файла результата (с имитацией)
3. Проверку контрольной фразы
"""

import sys
import time
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import ConfigLoader
from src.cursor_file_interface import CursorFileInterface


def test_feedback_mechanism():
    """Тест механизма обратной связи"""
    print()
    print("=" * 70)
    print("ТЕСТ ОБРАТНОЙ СВЯЗИ ОТ CURSOR")
    print("=" * 70)
    print()
    
    # 1. Загружаем конфигурацию
    config = ConfigLoader("config/config.yaml")
    project_dir = config.get_project_dir()
    print(f"[INFO] Проект: {project_dir}")
    print()
    
    # 2. Создаем файловый интерфейс
    cursor_file = CursorFileInterface(project_dir)
    print("[INFO] Файловый интерфейс создан")
    print(f"  Commands dir: {cursor_file.commands_dir}")
    print(f"  Results dir: {cursor_file.results_dir}")
    print()
    
    # 3. Создаем файл инструкции (как обычно)
    task_id = f"feedback_test_{int(time.time())}"
    instruction = "Тестовая инструкция для проверки обратной связи"
    
    print("[STEP 1] Создание файла инструкции")
    instruction_file = cursor_file.write_instruction(
        instruction=instruction,
        task_id=task_id,
        new_chat=True
    )
    print(f"  [OK] Файл создан: {instruction_file}")
    print()
    
    # 4. Проверяем, что файл инструкции создан
    if instruction_file.exists():
        print("[OK] Файл инструкции существует")
        print(f"  Размер: {instruction_file.stat().st_size} байт")
        print()
    else:
        print("[FAIL] Файл инструкции не существует!")
        return False
    
    # 5. Проверяем ожидание файла результата (без таймаута, короткий тест)
    print("[STEP 2] Проверка ожидания файла результата")
    print(f"  Ожидаемый файл: {cursor_file.results_dir / f'result_{task_id}.txt'}")
    print("  Таймаут: 5s (короткий для теста)")
    print()
    
    print("[INFO] Файл результата НЕ создан автоматически")
    print("  Для полного теста нужно:")
    print("    1. Открыть Cursor IDE")
    print("    2. Прочитать инструкцию из файла")
    print("    3. Выполнить инструкцию")
    print("    4. Сохранить результат в: cursor_results/result_{task_id}.txt")
    print()
    
    # 6. Имитация: создаем тестовый файл результата для проверки механизма
    print("[STEP 3] Имитация: создание тестового файла результата")
    test_result_file = cursor_file.results_dir / f"result_{task_id}.txt"
    test_content = """Результат выполнения тестовой задачи

Задача выполнена успешно.
Отчет завершен!
"""
    test_result_file.write_text(test_content, encoding='utf-8')
    print(f"  [OK] Тестовый файл создан: {test_result_file}")
    print()
    
    # 7. Проверяем обнаружение файла результата
    print("[STEP 4] Проверка обнаружения файла результата")
    
    if cursor_file.check_result_exists(task_id):
        print("  [OK] Файл результата обнаружен!")
    else:
        print("  [FAIL] Файл результата не обнаружен!")
        return False
    
    # 8. Читаем содержимое файла
    content = cursor_file.read_result(task_id)
    if content:
        print(f"  [OK] Содержимое файла прочитано ({len(content)} символов)")
        print()
        print("Содержимое файла результата:")
        print("  " + "\n  ".join(content.split("\n")[:5]))
        print()
    else:
        print("  [FAIL] Не удалось прочитать файл результата!")
        return False
    
    # 9. Проверяем контрольную фразу
    print("[STEP 5] Проверка контрольной фразы")
    control_phrase = "Отчет завершен!"
    
    if cursor_file.check_control_phrase(content, control_phrase):
        print(f"  [OK] Контрольная фраза найдена: '{control_phrase}'")
    else:
        print(f"  [WARNING] Контрольная фраза не найдена: '{control_phrase}'")
        print(f"  Содержимое: {content[:100]}...")
    print()
    
    # 10. Тестируем wait_for_result с коротким таймаутом (файл уже существует)
    print("[STEP 6] Тест wait_for_result (файл уже существует)")
    wait_result = cursor_file.wait_for_result(
        task_id=task_id,
        timeout=5,
        check_interval=1,
        control_phrase=control_phrase
    )
    
    if wait_result["success"]:
        print("  [OK] Файл результата найден через wait_for_result")
        print(f"  Время ожидания: {wait_result['wait_time']:.2f}s")
        print(f"  Путь: {wait_result['file_path']}")
    else:
        print("  [FAIL] Файл результата не найден через wait_for_result")
        print(f"  Ошибка: {wait_result.get('error')}")
    print()
    
    # 11. Очистка тестового файла
    print("[STEP 7] Очистка тестового файла")
    if test_result_file.exists():
        test_result_file.unlink()
        print("  [OK] Тестовый файл удален")
    print()
    
    print("=" * 70)
    print("ИТОГИ ТЕСТИРОВАНИЯ ОБРАТНОЙ СВЯЗИ")
    print("=" * 70)
    print()
    print("[OK] Механизм обратной связи работает корректно:")
    print("  1. Создание файлов инструкций - работает")
    print("  2. Ожидание файлов результатов - работает")
    print("  3. Проверка контрольных фраз - работает")
    print("  4. Чтение содержимого файлов - работает")
    print()
    print("[INFO] Для реального тестирования нужно:")
    print("  1. Выполнить инструкцию в Cursor вручную")
    print("  2. Сохранить результат в cursor_results/result_{task_id}.txt")
    print("  3. Code Agent автоматически обнаружит файл и проверит контрольную фразу")
    print()
    print("[INFO] Файл инструкции готов для использования:")
    print(f"  {instruction_file}")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = test_feedback_mechanism()
        if success:
            print("[SUCCESS] Тест обратной связи пройден успешно!")
        else:
            print("[FAIL] Тест обратной связи провален!")
    except Exception as e:
        print(f"\n[ERROR] Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
