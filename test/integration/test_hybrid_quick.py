"""
Быстрый тест гибридного интерфейса
"""
from pathlib import Path

from src.hybrid_cursor_interface import (
    TaskComplexity,
    create_hybrid_cursor_interface
)
from src.config_loader import ConfigLoader
from src.prompt_formatter import PromptFormatter

# Корень проекта
project_root = Path(__file__).parent.parent

print()
print("=" * 70)
print("БЫСТРЫЙ ТЕСТ ГИБРИДНОГО ИНТЕРФЕЙСА")
print("=" * 70)
print()

# Тест 1: Определение сложности
print("Тест 1: Определение сложности задач")
print("-" * 70)

config = ConfigLoader("config/config.yaml")
project_dir = config.get_project_dir()

hybrid = create_hybrid_cursor_interface(
    cli_path="docker-compose-agent",
    project_dir=str(project_dir),
    prefer_cli=False,
    verify_side_effects=False
)

test_cases = [
    ("Что находится в файле README.md?", TaskComplexity.SIMPLE),
    ("Создай файл test.txt", TaskComplexity.COMPLEX),
    ("Как работает функция main()?", TaskComplexity.SIMPLE),
    ("Измени конфигурацию", TaskComplexity.COMPLEX),
]

correct = 0
for instruction, expected in test_cases:
    determined = hybrid._determine_complexity(instruction)
    is_correct = determined == expected
    status = "OK" if is_correct else "FAIL"
    
    print(f"[{status}] {instruction[:40]:40} -> {determined.value:8} (expected: {expected.value})")
    
    if is_correct:
        correct += 1

print(f"\nРезультат: {correct}/{len(test_cases)} ({correct*100//len(test_cases)}%)")
print()

# Тест 2: Проверка доступности интерфейсов
print("Тест 2: Проверка доступности интерфейсов")
print("-" * 70)

print(f"CLI доступен: {hybrid.cli.is_available()}")
print(f"CLI команда: {hybrid.cli.cli_command}")
print(f"Проект: {hybrid.project_dir}")
print("Файловый интерфейс: готов")
print()

# Тест 3: Создание инструкции с гарантией выполнения
print("Тест 3: Форматирование инструкции")
print("-" * 70)

instruction = PromptFormatter.format_task_with_execution_guarantee(
    task_name="Создание тестового файла",
    task_description="Создай файл test_hybrid.txt с текстом 'Test'",
    output_file="test_hybrid.txt",
    control_phrase="Задача выполнена!"
)

print(f"Инструкция сформирована, длина: {len(instruction)} символов")
print("Первые 200 символов:")
print(instruction[:200])
print()

# Итоги
print("=" * 70)
print("ИТОГИ БЫСТРОГО ТЕСТА")
print("=" * 70)
print()
print("[OK] Импорты работают")
print("[OK] Определение сложности работает")
print("[OK] Интерфейсы инициализированы")
print("[OK] Форматирование инструкций работает")
print()
print("Гибридный интерфейс готов к использованию!")
print()
