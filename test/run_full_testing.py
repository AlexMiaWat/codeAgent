#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексный скрипт для полного тестирования Code Agent

Запускает:
1. Тестирование OpenRouter API
2. Тестирование LLM (генерация инструкций, выбор моделей, параллельная работа)
3. Тестирование HTTP сервера и API endpoints
4. Тестирование различных сценариев работы
"""

import sys
import subprocess
import time
import os
from pathlib import Path

# Устанавливаем UTF-8 кодировку для вывода
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent


def run_test(test_file: str, description: str, timeout: int = 300) -> tuple[bool, str]:
    """Запуск теста"""
    print("\n" + "=" * 80)
    print(f"ЗАПУСК: {description}")
    print("=" * 80)
    print()
    
    test_path = project_root / "test" / test_file
    
    if not test_path.exists():
        return False, f"Файл теста не найден: {test_path}"
    
    try:
        # Запускаем тест с правильным PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root / 'src') + os.pathsep + env.get('PYTHONPATH', '')

        result = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        # Выводим результат
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        return success, "OK" if success else f"Exit code: {result.returncode}"
        
    except subprocess.TimeoutExpired:
        return False, f"Timeout ({timeout}s)"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"


def main():
    """Главная функция"""
    print("=" * 80)
    print("ПОЛНОЕ ТЕСТИРОВАНИЕ CODE AGENT")
    print("=" * 80)
    print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # 1. Тестирование OpenRouter API
    print("\n" + "=" * 80)
    print("БЛОК 1: ТЕСТИРОВАНИЕ OpenRouter API")
    print("=" * 80)
    
    results.append((
        "OpenRouter API - базовый тест",
        run_test("test_openrouter_api.py", "Тестирование OpenRouter API - доступность и валидность API ключа", timeout=60)
    ))
    
    results.append((
        "OpenRouter API - детальное тестирование",
        run_test("test_openrouter_detailed.py", "Тестирование OpenRouter LLM - LLMManager, выбор моделей", timeout=120)
    ))
    
    # 2. Тестирование LLM (генерация инструкций, параллельная работа)
    print("\n" + "=" * 80)
    print("БЛОК 2: ТЕСТИРОВАНИЕ LLM (генерация инструкций, выбор моделей)")
    print("=" * 80)
    
    results.append((
        "LLM - реальное тестирование",
        run_test("test_llm_real.py", "Тестирование LLMManager - генерация, fallback, параллельный режим", timeout=300)
    ))
    
    # 3. Тестирование HTTP сервера
    print("\n" + "=" * 80)
    print("БЛОК 3: ТЕСТИРОВАНИЕ HTTP СЕРВЕРА И API")
    print("=" * 80)
    
    # Тест сервера с флагом --no-start (сервер уже запущен)
    print("\n" + "=" * 80)
    print("ЗАПУСК: Тестирование реального сервера - API endpoints (сервер уже запущен)")
    print("=" * 80)
    test_path = project_root / "test" / "test_real_server_integration.py"
    if test_path.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(test_path), "--no-start"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8',
                errors='replace'
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr, file=sys.stderr)
            server_success = result.returncode == 0
            results.append((
                "HTTP Server - интеграционное тестирование",
                (server_success, "OK" if server_success else f"Exit code: {result.returncode}")
            ))
        except Exception as e:
            results.append((
                "HTTP Server - интеграционное тестирование",
                (False, f"Ошибка: {str(e)}")
            ))
    else:
        results.append((
            "HTTP Server - интеграционное тестирование",
            (False, f"Файл не найден: {test_path}")
        ))
    
    # 4. Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for name, (success, message) in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status}: {name}")
        if not success:
            print(f"       {message}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print()
    print(f"[OK] Пройдено: {passed}/{len(results)}")
    print(f"[FAIL] Провалено: {failed}/{len(results)}")
    print()
    print(f"Время завершения: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    if passed == len(results):
        print("\n[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        return 0
    else:
        print("\n[WARNING] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        print("\nПримечания:")
        print("- Тесты OpenRouter могут провалиться из-за недействительного API ключа")
        print("- Тесты сервера могут требовать запущенного сервера или правильной конфигурации")
        return 1


if __name__ == "__main__":
    sys.exit(main())
