"""
Тестирование установки и настройки официального Cursor CLI (agent)

Проверяет:
1. Доступность команды agent
2. Установку через WSL (если нужно)
3. Правильную интеграцию с Code Agent
"""

import sys
import subprocess
import shutil
import os
from pathlib import Path

from src.cursor_cli_interface import create_cursor_cli_interface

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_agent_installation():
    """Тестирование установки agent"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ УСТАНОВКИ CURSOR CLI (AGENT)")
    print("=" * 70)
    print()
    print("Документация: https://cursor.com/docs/cli/overview")
    print()
    
    # Проверка 1: Поиск agent в PATH
    print("=" * 70)
    print("ПРОВЕРКА 1: Поиск agent в PATH")
    print("=" * 70)
    print()
    
    agent_path = shutil.which("agent")
    if agent_path:
        print(f"[OK] agent найден в PATH: {agent_path}")
        try:
            result = subprocess.run(
                ["agent", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"  Версия: {result.stdout.strip()}")
            else:
                print(f"  [WARNING] Не удалось получить версию: {result.stderr}")
        except Exception as e:
            print(f"  [WARNING] Ошибка проверки версии: {e}")
    else:
        print("[FAIL] agent не найден в PATH")
    
    print()
    
    # Проверка 2: Поиск через WSL
    print("=" * 70)
    print("ПРОВЕРКА 2: Поиск agent через WSL")
    print("=" * 70)
    print()
    
    if os.name == 'nt':  # Windows
        try:
            result = subprocess.run(
                ["wsl", "which", "agent"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                print(f"[OK] agent найден в WSL: {result.stdout.strip()}")
                
                # Проверка версии через WSL
                try:
                    ver_result = subprocess.run(
                        ["wsl", "agent", "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if ver_result.returncode == 0:
                        print(f"  Версия (WSL): {ver_result.stdout.strip()}")
                except Exception as e:
                    print(f"  [WARNING] Ошибка проверки версии через WSL: {e}")
            else:
                print("[INFO] agent не найден в WSL")
                print()
                print("Для установки через WSL выполните:")
                print("  1. Откройте WSL (Ubuntu)")
                print("  2. Выполните: curl https://cursor.com/install -fsS | bash")
                print("  3. Добавьте в PATH: export PATH=\"$HOME/.local/bin:$PATH\"")
        except FileNotFoundError:
            print("[INFO] WSL не установлен")
        except Exception as e:
            print(f"[WARNING] Ошибка проверки WSL: {e}")
    else:
        print("[INFO] Это не Windows - WSL недоступен")
    
    print()
    
    # Проверка 3: CursorCLIInterface
    print("=" * 70)
    print("ПРОВЕРКА 3: Интеграция с CursorCLIInterface")
    print("=" * 70)
    print()
    
    cli = create_cursor_cli_interface()
    if cli.is_available():
        print("[OK] CursorCLIInterface сообщает, что CLI доступен")
        print(f"  Команда: {cli.cli_command}")
        version = cli.check_version()
        if version:
            print(f"  Версия: {version}")
        
        # Проверяем, это ли agent или cursor.CMD
        if cli.cli_command and "agent" in cli.cli_command.lower():
            print("  [OK] Используется правильная команда 'agent'")
        elif cli.cli_command and "cursor.cmd" in cli.cli_command.lower():
            print("  [WARNING] Используется cursor.CMD вместо agent (это редактор, не CLI агент)")
            print("  Рекомендация: Установите agent через официальный скрипт")
    else:
        print("[FAIL] CursorCLIInterface сообщает, что CLI недоступен")
    
    print()
    
    # Итоги
    print("=" * 70)
    print("ИТОГИ ПРОВЕРКИ")
    print("=" * 70)
    print()
    
    if agent_path or (cli.is_available() and "agent" in (cli.cli_command or "").lower()):
        print("[OK] agent доступен для использования")
        print()
        print("Следующие шаги:")
        print("  1. Протестировать выполнение через agent -p")
        print("  2. Настроить автоматическое выполнение в Code Agent")
    else:
        print("[WARNING] agent не найден")
        print()
        print("Инструкция по установке:")
        print("  1. Откройте WSL (Ubuntu) или Linux терминал")
        print("  2. Выполните: curl https://cursor.com/install -fsS | bash")
        print("  3. Добавьте в PATH: export PATH=\"$HOME/.local/bin:$PATH\"")
        print("  4. Проверьте: agent --version")
        print()
        print("Или смотрите: INSTALL_CURSOR_AGENT.md")
    
    print()


if __name__ == "__main__":
    try:
        test_agent_installation()
    except Exception as e:
        print(f"\n[ERROR] Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
