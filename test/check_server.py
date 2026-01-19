#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для проверки доступности сервера перед запуском тестов
"""

import sys
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:3456"


def check_server():
    """Проверка доступности сервера"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Сервер доступен")
            print(f"   Статус: {data.get('status')}")
            print(f"   Время: {data.get('timestamp')}")
            return True
        else:
            print(f"[FAIL] Сервер вернул код: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Сервер недоступен на {BASE_URL}")
        print()
        print("Для запуска сервера:")
        print("  1. Откройте отдельную консоль")
        print("  2. Выполните: python main.py")
        print("  3. Дождитесь сообщения о запуске сервера")
        return False
    except Exception as e:
        print(f"[FAIL] Ошибка: {e}")
        return False


if __name__ == "__main__":
    success = check_server()
    sys.exit(0 if success else 1)
