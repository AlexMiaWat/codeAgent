#!/usr/bin/env python3
"""
Скрипт для запуска всех проверок качества кода:
- Форматирование black
- Линтинг ruff
- Проверка типов mypy
- Запуск тестов pytest
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    """Запустить команду и вернуть код возврата, stdout, stderr."""
    print(f"🚀 Запуск: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode, result.stdout, result.stderr


def check_black() -> bool:
    """Проверить форматирование black."""
    print("\n" + "="*60)
    print("🔧 Проверка форматирования black")
    print("="*60)
    code, out, err = run_command(
        ["python", "-m", "black", "--check", "--diff", "."],
        PROJECT_ROOT,
    )
    if code == 0:
        print("✅ Форматирование black в порядке.")
        return True
    else:
        print("❌ Найдены проблемы форматирования black.")
        print("   Запустите 'python -m black .' для автоматического исправления.")
        return False


def check_ruff() -> bool:
    """Проверить линтинг ruff."""
    print("\n" + "="*60)
    print("🧹 Проверка линтинга ruff")
    print("="*60)
    code, out, err = run_command(
        ["python", "-m", "ruff", "check", "--fix", "."],
        PROJECT_ROOT,
    )
    if code == 0:
        print("✅ Линтинг ruff в порядке.")
        return True
    else:
        print("❌ Найдены проблемы линтинга ruff.")
        return False


def check_mypy() -> bool:
    """Проверить типы mypy."""
    print("\n" + "="*60)
    print("📘 Проверка типов mypy")
    print("="*60)
    code, out, err = run_command(
        [
            "python",
            "-m",
            "mypy",
            "--ignore-missing-imports",
            "--show-error-codes",
            "src",
            "test",
        ],
        PROJECT_ROOT,
    )
    if code == 0:
        print("✅ Проверка типов mypy в порядке.")
        return True
    else:
        print("❌ Найдены проблемы типов mypy.")
        return False


def run_tests() -> bool:
    """Запустить тесты pytest."""
    print("\n" + "="*60)
    print("🧪 Запуск тестов pytest")
    print("="*60)
    code, out, err = run_command(
        ["python", "-m", "pytest", "test/", "-x", "--tb=short", "--strict-markers"],
        PROJECT_ROOT,
    )
    if code == 0:
        print("✅ Все тесты пройдены.")
        return True
    else:
        print("❌ Некоторые тесты не прошли.")
        return False


def main() -> int:
    """Основная функция."""
    print("🚀 Запуск проверок качества кода проекта Code Agent")
    print(f"📂 Рабочая директория: {PROJECT_ROOT}")
    
    # Проверка наличия необходимых инструментов
    tools = ["black", "ruff", "mypy", "pytest"]
    missing = []
    for tool in tools:
        try:
            subprocess.run(
                [sys.executable, "-m", tool, "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(tool)
    
    if missing:
        print(f"❌ Отсутствуют инструменты: {', '.join(missing)}")
        print("   Установите их: pip install " + " ".join(missing))
        return 1
    
    success = True
    success = check_black() and success
    success = check_ruff() and success
    success = check_mypy() and success
    success = run_tests() and success
    
    print("\n" + "="*60)
    if success:
        print("🎉 Все проверки пройдены успешно!")
        return 0
    else:
        print("❌ Некоторые проверки не прошли.")
        print("\nРекомендации:")
        print("1. Запустите 'python -m black .' для форматирования")
        print("2. Запустите 'python -m ruff check --fix .' для исправления линтинга")
        print("3. Исправьте ошибки типов mypy")
        print("4. Исправьте упавшие тесты")
        return 1


if __name__ == "__main__":
    sys.exit(main())