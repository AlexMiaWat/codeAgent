#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для проверки API ключа OpenRouter

Проверяет откуда берется ключ и какой используется
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_api_key():
    """Проверка API ключа из разных источников"""
    print("=" * 80)
    print("ПРОВЕРКА API КЛЮЧА OpenRouter")
    print("=" * 80)
    print()
    
    # 1. Системная переменная окружения (до load_dotenv)
    system_key = os.environ.get('OPENROUTER_API_KEY')
    print("1. Системная переменная окружения (os.environ):")
    if system_key:
        print(f"   [OK] Найдена: {system_key[:30]}...{system_key[-10:]}")
    else:
        print("   [FAIL] Не установлена")
    print()
    
    # 2. Переменная окружения через os.getenv (до load_dotenv)
    getenv_key_before = os.getenv('OPENROUTER_API_KEY')
    print("2. os.getenv (до load_dotenv):")
    if getenv_key_before:
        print(f"   [OK] Найдена: {getenv_key_before[:30]}...{getenv_key_before[-10:]}")
    else:
        print("   [FAIL] Не найдена")
    print()
    
    # 3. Загружаем .env файл
    env_file = project_root / '.env'
    print(f"3. Файл .env: {env_file}")
    if env_file.exists():
        print("   [OK] Файл существует")
        # Читаем напрямую
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
            if 'OPENROUTER_API_KEY' in env_content:
                for line in env_content.split('\n'):
                    if line.strip().startswith('OPENROUTER_API_KEY='):
                        key_from_file = line.split('=', 1)[1].strip().strip('"').strip("'")
                        print(f"   [OK] Ключ в файле: {key_from_file[:30]}...{key_from_file[-10:]}")
                        break
            else:
                print("   [FAIL] Ключ не найден в файле")
    else:
        print("   [FAIL] Файл не существует")
    print()
    
    # 4. После load_dotenv
    load_dotenv()
    getenv_key_after = os.getenv('OPENROUTER_API_KEY')
    print("4. os.getenv (после load_dotenv):")
    if getenv_key_after:
        print(f"   [OK] Найдена: {getenv_key_after[:30]}...{getenv_key_after[-10:]}")
    else:
        print("   [FAIL] Не найдена")
    print()
    
    # 5. Проверка в LLMManager
    try:
        from src.llm.llm_manager import LLMManager
        print("5. Проверка через LLMManager:")
        try:
            mgr = LLMManager('config/llm_settings.yaml')
            # Получаем ключ из клиента
            if 'openrouter' in mgr.clients:
                client = mgr.clients['openrouter']
                # Ключ хранится в client.api_key, но это приватное поле
                # Проверяем через тестовый запрос
                print("   [OK] LLMManager инициализирован")
                print("   [INFO] Ключ используется из переменной окружения или конфига")
        except ValueError as e:
            print(f"   [FAIL] Ошибка инициализации: {e}")
        except Exception as e:
            print(f"   [ERROR] Ошибка: {e}")
    except Exception as e:
        print(f"   [ERROR] Не удалось импортировать LLMManager: {e}")
    print()
    
    # 6. Проверка в конфиге (не должно быть!)
    try:
        import yaml
        config_file = project_root / 'config' / 'llm_settings.yaml'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                provider_config = config.get('providers', {}).get('openrouter', {})
                config_key = provider_config.get('api_key')
                print("6. Проверка config/llm_settings.yaml:")
                if config_key:
                    print(f"   [WARN] Ключ найден в конфиге: {config_key[:30]}...{config_key[-10:]}")
                    print("   [WARN] Это небезопасно! Ключ должен быть только в переменных окружения")
                else:
                    print("   [OK] Ключ не найден в конфиге (правильно)")
    except Exception as e:
        print(f"   [ERROR] Ошибка проверки конфига: {e}")
    print()
    
    # Итоги
    print("=" * 80)
    print("ИТОГИ")
    print("=" * 80)
    
    final_key = os.getenv('OPENROUTER_API_KEY')
    if final_key:
        print(f"[OK] Используемый ключ: {final_key[:30]}...{final_key[-10:]}")
        print()
        print("Источники (в порядке приоритета):")
        if system_key:
            print("  1. Системная переменная окружения")
        if env_file.exists():
            print("  2. Файл .env")
        if config_key:
            print("  3. config/llm_settings.yaml (не рекомендуется!)")
    else:
        print("[FAIL] API ключ не найден!")
        print()
        print("Установите ключ одним из способов:")
        print("  1. Переменная окружения: export OPENROUTER_API_KEY=...")
        print("  2. Файл .env: OPENROUTER_API_KEY=...")
    
    print()

if __name__ == "__main__":
    check_api_key()
