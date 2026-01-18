"""Скрипт проверки настройки Code Agent"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("ПРОВЕРКА НАСТРОЙКИ CODE AGENT")
print("=" * 60)
print()

# Проверка .env
print("1. Переменные окружения (.env):")
project_dir = os.getenv('PROJECT_DIR')
if project_dir:
    print(f"   [OK] PROJECT_DIR: {project_dir}")
else:
    print("   [ERROR] PROJECT_DIR не установлен")
print()

# Проверка структуры проекта
if project_dir:
    proj_path = Path(project_dir)
    print(f"2. Структура проекта ({proj_path}):")
    print(f"   Проект существует: {proj_path.exists()}")
    
    # Директории для репортов
    dirs_to_check = {
        'docs/results': 'Результаты выполнения задач',
        'docs/reviews': 'Ревью от Скептика',
        'cursor_commands': 'Команды для Cursor (файловый интерфейс)',
        'cursor_results': 'Результаты от Cursor (файловый интерфейс)',
    }
    
    for dir_path, description in dirs_to_check.items():
        full_path = proj_path / dir_path
        exists = full_path.exists()
        status = "[OK]" if exists else "[MISSING]"
        print(f"   {status} {dir_path}: {description}")
        if not exists:
            print(f"      [Создать: {full_path}]")
    print()

# Проверка API ключей
print("3. API ключи:")
openai_key = os.getenv('OPENAI_API_KEY')
if openai_key:
    print(f"   [OK] OPENAI_API_KEY: установлен (***{openai_key[-4:] if len(openai_key) > 4 else '****'})")
else:
    print("   [WARNING] OPENAI_API_KEY: не установлен (требуется для LLM агента)")
print()

# Проверка Cursor CLI
print("4. Cursor CLI:")
try:
    from src.cursor_cli_interface import create_cursor_cli_interface
    cli = create_cursor_cli_interface()
    if cli.is_available():
        version = cli.check_version()
        print(f"   [OK] Cursor CLI доступен: {version or 'версия не определена'}")
    else:
        print("   [WARNING] Cursor CLI недоступен (будет использоваться fallback)")
except Exception as e:
    print(f"   [ERROR] Ошибка проверки CLI: {e}")
print()

# Итоги
print("=" * 60)
print("ИТОГИ")
print("=" * 60)

issues = []
if not project_dir:
    issues.append("PROJECT_DIR не установлен в .env")
if project_dir:
    for dir_path in ['docs/results', 'docs/reviews']:
        if not (Path(project_dir) / dir_path).exists():
            issues.append(f"Директория {dir_path} не создана")
if not openai_key:
    issues.append("OPENAI_API_KEY не установлен (для LLM агента)")

if not issues:
    print("[OK] Вся базовая настройка выполнена!")
    print()
    print("Следующие шаги:")
    print("  - Установить OPENAI_API_KEY для полного запуска (опционально)")
    print("  - Протестировать Cursor CLI интерфейс")
    print("  - Начать работу с задачами")
else:
    print("[WARNING] Требуется дополнительная настройка:")
    for issue in issues:
        print(f"  - {issue}")

print("=" * 60)
