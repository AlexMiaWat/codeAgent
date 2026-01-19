#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска всех комплексных тестов

Запускает:
1. Комплексное тестирование валидации
2. Тестирование реального сервера
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent


def run_test(test_file: str, description: str) -> bool:
    """Запуск теста"""
    print("\n" + "=" * 80)
    print(f"ЗАПУСК: {description}")
    print("=" * 80)
    
    test_path = project_root / "test" / test_file
    result = subprocess.run(
        [sys.executable, str(test_path)],
        cwd=str(project_root),
        capture_output=False
    )
    
    return result.returncode == 0


def main():
    """Главная функция"""
    print("=" * 80)
    print("ПОЛНОЕ ТЕСТИРОВАНИЕ CODE AGENT")
    print("=" * 80)
    
    results = []
    
    # Тест 1: Комплексное тестирование валидации
    results.append((
        "Комплексное тестирование валидации",
        run_test("test_comprehensive_validation.py", "Комплексное тестирование валидации")
    ))
    
    # Тест 2: Тестирование реального сервера (опционально, требует запуска сервера)
    print("\n" + "=" * 80)
    print("ПРИМЕЧАНИЕ: Тест реального сервера требует отдельного запуска")
    print("Запустите: python test/test_real_server_integration.py")
    print("=" * 80)
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\n[OK] Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        return 0
    else:
        print("\n[ERROR] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
