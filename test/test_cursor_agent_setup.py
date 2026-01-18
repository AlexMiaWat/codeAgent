"""
Проверка установки и настройки cursor-agent

Проверяет:
1. Доступность cursor-agent в системе
2. Альтернативные способы установки
3. Возможность автоматического выполнения
"""

import sys
import subprocess
import shutil
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.cursor_cli_interface import create_cursor_cli_interface


def check_cursor_agent_availability():
    """Проверка доступности cursor-agent"""
    print()
    print("=" * 70)
    print("ПРОВЕРКА ДОСТУПНОСТИ CURSOR-AGENT")
    print("=" * 70)
    print()
    
    # Проверка 1: Поиск в PATH
    print("Проверка 1: Поиск cursor-agent в PATH")
    print("-" * 70)
    
    cursor_agent_path = shutil.which("cursor-agent")
    if cursor_agent_path:
        print(f"[OK] cursor-agent найден в PATH: {cursor_agent_path}")
    else:
        print("[FAIL] cursor-agent не найден в PATH")
    
    print()
    
    # Проверка 2: Через CursorCLIInterface
    print("Проверка 2: Через CursorCLIInterface")
    print("-" * 70)
    
    cli = create_cursor_cli_interface()
    if cli.is_available():
        print(f"[OK] Cursor CLI доступен: {cli.cli_command}")
        version = cli.check_version()
        if version:
            print(f"  Версия: {version}")
    else:
        print("[FAIL] Cursor CLI не доступен")
    
    print()
    
    # Проверка 3: Проверка возможных путей установки
    print("Проверка 3: Возможные пути установки")
    print("-" * 70)
    
    possible_paths = [
        Path.home() / ".local" / "bin" / "cursor-agent",
        Path.home() / ".cargo" / "bin" / "cursor-agent",
        Path("/usr/local/bin/cursor-agent"),
        Path("/opt/cursor-agent/cursor-agent"),
        Path(os.environ.get("APPDATA", "")) / "npm" / "cursor-agent.cmd",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cursor-agent",
    ]
    
    found_paths = []
    for path in possible_paths:
        if path.exists():
            found_paths.append(path)
            print(f"[OK] Найден: {path}")
    
    if not found_paths:
        print("[FAIL] cursor-agent не найден ни в одном из стандартных путей")
    
    print()
    
    # Проверка 4: WSL доступность
    print("Проверка 4: WSL доступность (для установки)")
    print("-" * 70)
    
    try:
        wsl_result = subprocess.run(
            ["wsl", "--status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if wsl_result.returncode == 0:
            print("[OK] WSL доступен - можно установить cursor-agent через WSL")
            print(f"  Output: {wsl_result.stdout[:100]}...")
        else:
            print("[INFO] WSL может быть не настроен корректно")
    except FileNotFoundError:
        print("[INFO] WSL не установлен")
    except subprocess.TimeoutExpired:
        print("[WARNING] WSL проверка превысила таймаут")
    except Exception as e:
        print(f"[INFO] Ошибка проверки WSL: {e}")
    
    print()
    
    # Итоги
    print("=" * 70)
    print("ИТОГИ ПРОВЕРКИ")
    print("=" * 70)
    print()
    
    if cursor_agent_path or cli.is_available():
        print("[OK] cursor-agent доступен для использования")
        print()
        print("Следующие шаги:")
        print("  1. Протестировать выполнение через cursor-agent")
        print("  2. Настроить автоматическое выполнение")
    else:
        print("[WARNING] cursor-agent не найден")
        print()
        print("Рекомендации:")
        print("  1. Установить cursor-agent через WSL (если доступен)")
        print("  2. Использовать файловый интерфейс с автоматизацией")
        print("  3. Рассмотреть Background Agents API (для GitHub репозиториев)")
    
    print()


if __name__ == "__main__":
    try:
        check_cursor_agent_availability()
    except Exception as e:
        print(f"\n[ERROR] Ошибка проверки: {e}")
        import traceback
        traceback.print_exc()
