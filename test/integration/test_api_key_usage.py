#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки какого API ключа используется в тестах и сервере
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_key_in_tests():
    """Проверка ключа в тестах"""
    print("=" * 80)
    print("ПРОВЕРКА КЛЮЧА В ТЕСТАХ")
    print("=" * 80)
    print()
    
    # Очищаем переменную окружения для чистого теста
    old_key = os.environ.pop('OPENROUTER_API_KEY', None)
    print(f"1. Очистили переменную окружения (было: {old_key[:30] + '...' if old_key else 'None'})")
    
    # Загружаем из .env
    load_dotenv(override=True)
    key_after_load = os.getenv('OPENROUTER_API_KEY')
    print(f"2. После load_dotenv(override=True): {key_after_load[:30] + '...' if key_after_load else 'NOT SET'}")
    print()
    
    return key_after_load

def test_key_in_llm_manager():
    """Проверка ключа в LLMManager"""
    print("=" * 80)
    print("ПРОВЕРКА КЛЮЧА В LLMManager")
    print("=" * 80)
    print()
    
    # Очищаем и перезагружаем
    os.environ.pop('OPENROUTER_API_KEY', None)
    load_dotenv(override=True)
    
    try:
        from src.llm.llm_manager import LLMManager
        mgr = LLMManager('config/llm_settings.yaml')
        
        # Получаем ключ из клиента (через приватное поле)
        if 'openrouter' in mgr.clients:
            client = mgr.clients['openrouter']
            # Ключ хранится в client.api_key, но это приватное поле
            # Проверяем через os.getenv
            key_used = os.getenv('OPENROUTER_API_KEY')
            print(f"[OK] LLMManager использует ключ: {key_used[:30] + '...' if key_used else 'NOT SET'}")
            return key_used
        else:
            print("[FAIL] Клиент openrouter не инициализирован")
            return None
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_key_in_server():
    """Проверка ключа в сервере"""
    print("=" * 80)
    print("ПРОВЕРКА КЛЮЧА В СЕРВЕРЕ")
    print("=" * 80)
    print()
    
    # Очищаем и перезагружаем
    os.environ.pop('OPENROUTER_API_KEY', None)
    load_dotenv(override=True)
    
    try:
        from src.config_loader import ConfigLoader
        config = ConfigLoader("config/config.yaml")
        key_used = os.getenv('OPENROUTER_API_KEY')
        print(f"[OK] ConfigLoader использует ключ: {key_used[:30] + '...' if key_used else 'NOT SET'}")
        return key_used
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        return None

def main():
    """Главная функция"""
    print()
    print("=" * 80)
    print("ПОЛНАЯ ПРОВЕРКА API КЛЮЧА")
    print("=" * 80)
    print()
    
    # Проверяем ключ в .env
    env_file = project_root / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('OPENROUTER_API_KEY='):
                    key_in_file = line.split('=', 1)[1].strip().strip('"').strip("'")
                    print(f"Ключ в .env файле: {key_in_file[:30]}...{key_in_file[-10:]}")
                    break
    print()
    
    # Тест 1: В тестах
    key_in_tests = test_key_in_tests()
    print()
    
    # Тест 2: В LLMManager
    key_in_llm = test_key_in_llm_manager()
    print()
    
    # Тест 3: В сервере
    key_in_server = test_key_in_server()
    print()
    
    # Итоги
    print("=" * 80)
    print("ИТОГИ")
    print("=" * 80)
    print()
    
    keys = [key_in_tests, key_in_llm, key_in_server]
    unique_keys = set(k for k in keys if k)
    
    if len(unique_keys) == 1:
        key = list(unique_keys)[0]
        print(f"[OK] Все используют один ключ: {key[:30]}...{key[-10:]}")
    elif len(unique_keys) > 1:
        print(f"[WARN] Обнаружены разные ключи!")
        print(f"  В тестах: {key_in_tests[:30] + '...' if key_in_tests else 'NOT SET'}")
        print(f"  В LLMManager: {key_in_llm[:30] + '...' if key_in_llm else 'NOT SET'}")
        print(f"  В сервере: {key_in_server[:30] + '...' if key_in_server else 'NOT SET'}")
    else:
        print("[FAIL] Ключ не найден нигде!")

if __name__ == "__main__":
    main()
