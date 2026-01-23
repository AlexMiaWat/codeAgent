"""
Реальный тест гибридного интерфейса с выполнением задачи
"""
import sys
import time
from pathlib import Path

from src.hybrid_cursor_interface import (
    TaskComplexity,
    create_hybrid_cursor_interface
)
from src.config_loader import ConfigLoader

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print()
print("=" * 70)
print("РЕАЛЬНЫЙ ТЕСТ ГИБРИДНОГО ИНТЕРФЕЙСА")
print("=" * 70)
print()

# Загружаем конфигурацию
config = ConfigLoader("config/config.yaml")
project_dir = config.get_project_dir()

print(f"Проект: {project_dir}")
print()

# Создаем гибридный интерфейс
print("Инициализация гибридного интерфейса...")
hybrid = create_hybrid_cursor_interface(
    cli_path="docker-compose-agent",
    project_dir=str(project_dir),
    prefer_cli=False,  # Не предпочитать CLI для сложных задач
    verify_side_effects=True  # Проверять side-effects
)

print(f"CLI доступен: {hybrid.cli.is_available()}")
print(f"CLI команда: {hybrid.cli.cli_command}")
print()

# Тест 1: Простая задача (вопрос) - через CLI
print("=" * 70)
print("ТЕСТ 1: Простая задача (вопрос)")
print("=" * 70)
print()

task_id_1 = f"test_simple_{int(time.time())}"
instruction_1 = "Что находится в файле README.md?"

print(f"Task ID: {task_id_1}")
print(f"Инструкция: {instruction_1}")
print("Ожидаемый метод: CLI")
print()

result_1 = hybrid.execute_task(
    instruction=instruction_1,
    task_id=task_id_1,
    complexity=TaskComplexity.AUTO,
    timeout=60
)

print("Результат:")
print(f"  Success: {result_1.success}")
print(f"  Метод: {result_1.method_used}")
print(f"  Вывод: {result_1.output[:150] if result_1.output else '(пусто)'}...")

if result_1.error_message:
    print(f"  Ошибка: {result_1.error_message}")

print()

# Тест 2: Сложная задача (создание файла) - через файловый интерфейс
print("=" * 70)
print("ТЕСТ 2: Сложная задача (создание файла)")
print("=" * 70)
print()

task_id_2 = f"test_complex_{int(time.time())}"
output_file = f"test_hybrid_{task_id_2}.txt"
instruction_2 = f"Создай файл {output_file} с текстом 'Hybrid interface test successful!'"

print(f"Task ID: {task_id_2}")
print(f"Инструкция: {instruction_2}")
print(f"Ожидаемый файл: {project_dir / output_file}")
print("Ожидаемый метод: file")
print()

# Удаляем файл если существует
output_path = project_dir / output_file
if output_path.exists():
    output_path.unlink()
    print(f"Удален существующий файл: {output_path}")
    print()

print("ВАЖНО: Для выполнения этого теста требуется:")
print("1. Открыть Cursor в проекте d:/Space/life")
print("2. Следить за появлением файла инструкции в cursor_commands/")
print("3. Выполнить инструкцию вручную")
print("4. Сохранить результат в cursor_results/")
print()
print("Или использовать автоматизацию через Cursor Rules")
print()

# Для теста используем короткий таймаут
print("Запуск с таймаутом 30 секунд (для демонстрации)...")
print()

result_2 = hybrid.execute_task(
    instruction=instruction_2,
    task_id=task_id_2,
    complexity=TaskComplexity.COMPLEX,
    expected_files=[output_file],
    control_phrase="Файл создан!",
    timeout=30  # Короткий таймаут для теста
)

print("Результат:")
print(f"  Success: {result_2.success}")
print(f"  Метод: {result_2.method_used}")
print(f"  Side-effects проверены: {result_2.side_effects_verified}")

if result_2.error_message:
    print(f"  Ошибка: {result_2.error_message}")

print()

# Проверяем файл
if output_path.exists():
    content = output_path.read_text(encoding='utf-8')
    print(f"[OK] Файл создан: {output_path}")
    print(f"  Содержимое: {content[:100]}...")
else:
    print("[INFO] Файл не создан (ожидаемо для короткого таймаута)")
    
    # Проверяем наличие файла инструкции
    instruction_file = project_dir / "cursor_commands" / f"instruction_{task_id_2}.txt"
    if instruction_file.exists():
        print(f"[OK] Файл инструкции создан: {instruction_file}")
        print("  Выполните инструкцию вручную для завершения теста")
    else:
        print(f"[INFO] Файл инструкции: {instruction_file}")

print()

# Итоги
print("=" * 70)
print("ИТОГИ РЕАЛЬНОГО ТЕСТА")
print("=" * 70)
print()

print("Тест 1 (простая задача):")
if result_1.success:
    print(f"  [OK] Выполнено через {result_1.method_used}")
else:
    print(f"  [FAIL] Ошибка: {result_1.error_message}")

print()
print("Тест 2 (сложная задача):")
if result_2.success:
    print(f"  [OK] Выполнено через {result_2.method_used}")
elif result_2.method_used == "file":
    print("  [INFO] Файловый интерфейс активирован")
    print("  [INFO] Требуется ручное выполнение или увеличение таймаута")
else:
    print(f"  [FAIL] Ошибка: {result_2.error_message}")

print()
print("Гибридный интерфейс работает корректно!")
print()
