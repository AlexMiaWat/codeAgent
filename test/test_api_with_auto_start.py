#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование API с автоматическим запуском сервера

Этот тест автоматически запускает сервер, если он не запущен.
"""

import sys
import time
from pathlib import Path

from test.test_real_server_integration import ServerTester

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://127.0.0.1:3456"


def main():
    """Главная функция"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ API С АВТОМАТИЧЕСКИМ ЗАПУСКОМ СЕРВЕРА")
    print("=" * 80)
    print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Создаем тестер, который автоматически запустит сервер если нужно
    tester = ServerTester()
    
    # Запускаем тесты с автоматическим запуском сервера (start_server_flag=True)
    print("[INFO] Запуск тестов с автоматическим запуском сервера...")
    print("[INFO] Если сервер не запущен, он будет запущен автоматически")
    print()
    
    success = tester.run_all_tests(start_server_flag=True)
    
    if success:
        print("\n[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        return 0
    else:
        print("\n[FAIL] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
