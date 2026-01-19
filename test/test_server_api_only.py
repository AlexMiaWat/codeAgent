#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование API сервера (сервер должен быть уже запущен)
"""

import sys
import time
import requests
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://127.0.0.1:3456"


def test_health():
    """Тест health endpoint"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Health Endpoint")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("[OK] Health check успешен")
            print(f"   Статус: {data.get('status')}")
            print(f"   Время: {data.get('timestamp')}")
            return True
        else:
            print(f"[FAIL] Health check вернул код: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Ошибка health check: {e}")
        return False


def test_root():
    """Тест root endpoint"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Root Endpoint")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("[OK] Root endpoint успешен")
            print(f"   Статус: {data.get('status')}")
            print(f"   Порт: {data.get('port')}")
            print(f"   Сессия: {data.get('session_id')}")
            return True
        else:
            print(f"[FAIL] Root endpoint вернул код: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Ошибка root endpoint: {e}")
        return False


def test_status():
    """Тест status endpoint"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Status Endpoint")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("[OK] Status получен успешно")
            
            server_info = data.get('server', {})
            print(f"   Статус сервера: {server_info.get('status')}")
            print(f"   Проект: {server_info.get('project_dir')}")
            print(f"   Cursor CLI доступен: {server_info.get('cursor_cli_available')}")
            
            tasks_info = data.get('tasks', {})
            print(f"   Задач всего: {tasks_info.get('total', 0)}")
            print(f"   В процессе: {tasks_info.get('in_progress', 0)}")
            print(f"   Выполнено: {tasks_info.get('completed', 0)}")
            print(f"   Ожидает: {tasks_info.get('pending', 0)}")
            
            return True
        else:
            print(f"[FAIL] Status вернул код: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Ошибка получения status: {e}")
        return False


def main():
    """Главная функция"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ API СЕРВЕРА")
    print("=" * 80)
    print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 80)
    
    # Проверяем доступность сервера
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("[FAIL] Сервер не отвечает на /health")
            return 1
    except requests.exceptions.ConnectionError as e:
        print(f"[FAIL] Сервер недоступен: {e}")
        print("[INFO] Убедитесь, что сервер запущен:")
        print("[INFO]   1. Откройте отдельную консоль")
        print("[INFO]   2. Выполните: python main.py")
        print("[INFO]   3. Дождитесь сообщения о запуске сервера")
        print("[INFO]   4. Затем запустите тесты снова")
        return 1
    except Exception as e:
        print(f"[FAIL] Неожиданная ошибка: {e}")
        print("[INFO] Убедитесь, что сервер запущен: python main.py")
        return 1
    
    results = []
    
    # Тесты API
    results.append(("Health Endpoint", test_health()))
    time.sleep(1)
    
    results.append(("Root Endpoint", test_root()))
    time.sleep(1)
    
    results.append(("Status Endpoint", test_status()))
    time.sleep(1)
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")
    
    print(f"\n[OK] Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] ВСЕ ТЕСТЫ API ПРОЙДЕНЫ УСПЕШНО")
        return 0
    else:
        print("\n[WARNING] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
