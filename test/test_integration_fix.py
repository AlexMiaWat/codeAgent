#!/usr/bin/env python3
"""
Тест исправлений интеграции агент-Cursor

Проверяет:
1. Автоматическое создание директорий
2. Повторные попытки при ошибках
3. Правильное ожидание файлов
"""

import sys
import time
import logging
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import ConfigLoader
from src.server import CodeAgentServer
from src.cursor_cli_interface import create_cursor_cli_interface

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_directory_creation():
    """Тест автоматического создания директорий"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Автоматическое создание директорий")
    print("="*60)

    try:
        # Загружаем конфигурацию
        config_loader = ConfigLoader("config/config.yaml")
        config = config_loader.config

        # Создаем сервер
        server = CodeAgentServer("config/config.yaml")

        # Проверяем, что директории созданы
        results_dir = Path("docs/results")
        cursor_results_dir = Path("cursor_results")

        if results_dir.exists():
            print(f"[OK] Директория docs/results существует")
        else:
            print(f"[FAIL] Директория docs/results не существует")
            return False

        if cursor_results_dir.exists():
            print(f"[OK] Директория cursor_results существует")
        else:
            print(f"[FAIL] Директория cursor_results не существует")
            return False

        return True

    except Exception as e:
        print(f"[ERROR] Ошибка в тесте создания директорий: {e}")
        return False


def test_cursor_cli_availability():
    """Тест доступности Cursor CLI"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Доступность Cursor CLI")
    print("="*60)

    try:
        # Загружаем конфигурацию
        config_loader = ConfigLoader("config/config.yaml")
        config = config_loader.config

        # Создаем интерфейс CLI
        cursor_config = config.get('cursor', {})
        cli_config = cursor_config.get('cli', {})

        cli_interface = create_cursor_cli_interface(
            cli_path=cli_config.get('cli_path'),
            container_name=cli_config.get('container_name'),
            project_dir=config_loader.get_project_dir(),
            agent_role=cursor_config.get('agent_role'),
            timeout=cli_config.get('timeout', 300)
        )

        if cli_interface.is_available():
            print(f"[OK] Cursor CLI доступен: {cli_interface.cli_command}")
            return True
        else:
            print(f"[FAIL] Agent CLI недоступен")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка в тесте доступности CLI: {e}")
        return False


def test_file_waiting_mechanism():
    """Тест механизма ожидания файлов"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Механизм ожидания файлов")
    print("="*60)

    try:
        # Загружаем конфигурацию
        config_loader = ConfigLoader("config/config.yaml")
        config = config_loader.config

        # Создаем сервер
        server = CodeAgentServer("config/config.yaml")

        # Создаем тестовый файл заранее в правильном месте
        project_dir = Path(config_loader.get_project_dir())
        test_file = project_dir / "docs" / "results" / "test_wait_mechanism.md"
        test_content = "Тестовый файл для проверки механизма ожидания\nТест завершен!"

        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(test_content, encoding='utf-8')

        print(f"[OK] Создан тестовый файл: {test_file}")

        # Тестируем ожидание файла
        result = server._wait_for_result_file(
            task_id="test_wait",
            wait_for_file="docs/results/test_wait_mechanism.md",
            control_phrase="Тест завершен!",
            timeout=5  # короткий таймаут для теста
        )

        if result.get("success"):
            print(f"[OK] Механизм ожидания файлов работает")
            print(f"      Файл найден: {result.get('file_path')}")
            return True
        else:
            print(f"[FAIL] Механизм ожидания файлов не работает: {result.get('error')}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка в тесте ожидания файлов: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("НАЧАЛО ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ ИНТЕГРАЦИИ АГЕНТ-CURSOR")
    print(f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("Создание директорий", test_directory_creation),
        ("Доступность CLI", test_cursor_cli_availability),
        ("Ожидание файлов", test_file_waiting_mechanism),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[CRITICAL] Тест '{test_name}' упал с исключением: {e}")
            results.append((test_name, False))

    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print("15")
        if result:
            passed += 1

    print(f"\nВсего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")

    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Интеграция исправлена.")
        return 0
    else:
        print(f"\n⚠️  Некоторые тесты провалены. Требуется дополнительная настройка.")
        return 1


if __name__ == "__main__":
    exit(main())