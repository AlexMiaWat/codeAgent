#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнение API ключей в тестах и сервере
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("СРАВНЕНИЕ API КЛЮЧЕЙ")
print("=" * 80)
print()

# 1. Ключ в .env файле
env_file = project_root / '.env'
key_from_file = None
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('OPENROUTER_API_KEY='):
                key_from_file = line.split('=', 1)[1].strip().strip('"').strip("'")
                break

print(f"1. Ключ в .env файле:")
print(f"   {key_from_file[:30] + '...' + key_from_file[-10:] if key_from_file else 'NOT FOUND'}")
print()

# 2. Ключ после load_dotenv (как в тестах)
os.environ.pop('OPENROUTER_API_KEY', None)
load_dotenv(override=True)
key_in_tests = os.getenv('OPENROUTER_API_KEY')

print(f"2. Ключ в тестах (после load_dotenv):")
print(f"   {key_in_tests[:30] + '...' + key_in_tests[-10:] if key_in_tests else 'NOT FOUND'}")
print()

# 3. Ключ в LLMManager (как в сервере)
os.environ.pop('OPENROUTER_API_KEY', None)
load_dotenv(override=True)
try:
    from src.llm.llm_manager import LLMManager
    mgr = LLMManager('config/llm_settings.yaml')
    key_in_llm = os.getenv('OPENROUTER_API_KEY')
    print(f"3. Ключ в LLMManager (сервер):")
    print(f"   {key_in_llm[:30] + '...' + key_in_llm[-10:] if key_in_llm else 'NOT FOUND'}")
except Exception as e:
    print(f"3. Ошибка инициализации LLMManager: {e}")
    key_in_llm = None
print()

# 4. Сравнение
print("=" * 80)
print("СРАВНЕНИЕ")
print("=" * 80)

keys = {
    '.env файл': key_from_file,
    'Тесты': key_in_tests,
    'Сервер (LLMManager)': key_in_llm
}

all_same = len(set(k for k in keys.values() if k)) == 1

if all_same and key_from_file:
    print(f"[OK] Все используют один ключ: {key_from_file[:30]}...{key_from_file[-10:]}")
else:
    print("[WARN] Обнаружены различия:")
    for name, key in keys.items():
        if key:
            print(f"  {name}: {key[:30]}...{key[-10:]}")
        else:
            print(f"  {name}: NOT FOUND")

print()
