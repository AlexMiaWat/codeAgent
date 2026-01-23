"""
Тест создания mini_docs_for_user.md через гибридный интерфейс
"""
import sys
import time
from pathlib import Path

from src.hybrid_cursor_interface import (
    TaskComplexity,
    create_hybrid_cursor_interface
)
from src.prompt_formatter import PromptFormatter
from src.config_loader import ConfigLoader

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print()
print("=" * 70)
print("ТЕСТ: Создание mini_docs_for_user.md через гибридный интерфейс")
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
    prefer_cli=False,  # Сложная задача - через файловый интерфейс
    verify_side_effects=True
)

print(f"CLI доступен: {hybrid.cli.is_available()}")
print()

# Формируем инструкцию
task_id = f"mini_docs_{int(time.time())}"
output_file = "docs/results/mini_docs_for_user.md"

# Используем улучшенный формат с гарантией выполнения
instruction = PromptFormatter.format_task_with_execution_guarantee(
    task_name="Создание краткой документации проекта",
    task_description="""Ты архитектор системы. Проанализируй всю документацию проекта Life и создай краткую выжимку в 100 строк.

В выжимке должны быть:
1. Название и назначение проекта Life
2. Основные технологии и инструменты
3. Архитектура и структура проекта
4. Ключевые компоненты и модули
5. Основные функции и возможности
6. Инструкции по запуску и использованию

Формат: Markdown с заголовками и структурированным содержанием.
Объем: Максимум 100 строк, но информативно и полно.
Стиль: Понятно для пользователя, без лишних технических деталей.""",
    output_file=output_file,
    control_phrase="Документация создана!",
    additional_constraints=[
        "Проанализируй все файлы в docs/",
        "Изучи README.md если есть",
        "Посмотри структуру проекта",
        "Создай понятную и полезную документацию"
    ]
)

print("Инструкция сформирована:")
print(f"  Длина: {len(instruction)} символов")
print(f"  Ожидаемый файл: {project_dir / output_file}")
print()

# Проверяем, существует ли уже файл
output_path = project_dir / output_file

# Создаем директорию если нужно
output_path.parent.mkdir(parents=True, exist_ok=True)

if output_path.exists():
    print("[INFO] Файл уже существует, удаляем для чистоты теста")
    output_path.unlink()
    print()

print("=" * 70)
print("ВЫПОЛНЕНИЕ ЗАДАЧИ")
print("=" * 70)
print()

print("Метод: Файловый интерфейс (сложная задача)")
print("Таймаут: 300 секунд (5 минут)")
print()

print("ВАЖНО: Для выполнения этой задачи:")
print("1. Откройте Cursor в проекте d:/Space/life")
print("2. Следите за файлом инструкции в cursor_commands/")
print("3. Выполните инструкцию в Cursor")
print("4. Сохраните результат в cursor_results/")
print()

input("Нажмите Enter когда будете готовы начать (или Ctrl+C для отмены)...")
print()

start_time = time.time()

# Выполняем через гибридный интерфейс
result = hybrid.execute_task(
    instruction=instruction,
    task_id=task_id,
    complexity=TaskComplexity.COMPLEX,  # Явно указываем сложность
    expected_files=[output_file],
    control_phrase="Документация создана!",
    timeout=300  # 5 минут
)

elapsed_time = time.time() - start_time

print()
print("=" * 70)
print("РЕЗУЛЬТАТ")
print("=" * 70)
print()

print(f"Success: {result.success}")
print(f"Метод: {result.method_used}")
print(f"Side-effects проверены: {result.side_effects_verified}")
print(f"Время выполнения: {elapsed_time:.2f} секунд")

if result.error_message:
    print(f"Ошибка: {result.error_message}")

print()

# Проверяем файл
print("=" * 70)
print("ПРОВЕРКА ФАЙЛА")
print("=" * 70)
print()

if output_path.exists():
    file_size = output_path.stat().st_size
    content = output_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')
    
    print(f"[OK] Файл создан: {output_path}")
    print(f"  Размер: {file_size} байт")
    print(f"  Строк: {len(lines)}")
    print()
    
    print("Содержимое (первые 50 строк):")
    print("-" * 70)
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3}| {line}")
    print("-" * 70)
    
    if len(lines) > 50:
        print(f"... (еще {len(lines) - 50} строк)")
    
    print()
    
    # Проверяем ключевые элементы
    print("Проверка содержимого:")
    checks = {
        "Есть заголовки": any(line.startswith('#') for line in lines),
        "Упоминается Life": any('life' in line.lower() for line in lines),
        "Есть структура": len([line for line in lines if line.startswith('#')]) >= 3,
        "Достаточно информации": len(content) > 500,
        "Контрольная фраза": "Документация создана!" in content or "документация" in content.lower()
    }
    
    for check, passed in checks.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {check}")
    
    print()
    
    if all(checks.values()):
        print("[SUCCESS] Файл создан корректно и содержит всю необходимую информацию!")
    else:
        print("[WARNING] Файл создан, но может требовать доработки")
    
else:
    print(f"[FAIL] Файл не создан: {output_path}")
    print()
    
    # Проверяем файл инструкции
    instruction_file = hybrid.file.instruction_file(task_id)
    if instruction_file.exists():
        print(f"[INFO] Файл инструкции создан: {instruction_file}")
        print()
        print("Содержимое инструкции (первые 30 строк):")
        print("-" * 70)
        content = instruction_file.read_text(encoding='utf-8')
        for i, line in enumerate(content.split('\n')[:30], 1):
            print(f"{i:3}| {line}")
        print("-" * 70)
        print()
        print("Выполните эту инструкцию в Cursor для создания файла")
    else:
        print(f"[ERROR] Файл инструкции не создан: {instruction_file}")

print()
print("=" * 70)
print("ИТОГИ")
print("=" * 70)
print()

if result.success and output_path.exists():
    print("[SUCCESS] Задача выполнена успешно!")
    print(f"  Файл создан: {output_path}")
    print(f"  Метод: {result.method_used}")
else:
    print("[INFO] Задача требует ручного выполнения")
    print(f"  Следуйте инструкциям в файле: {hybrid.file.instruction_file(task_id)}")

print()
