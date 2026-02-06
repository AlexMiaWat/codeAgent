#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрая проверка какого API ключа используется
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Читаем ключ из .env напрямую
env_file = project_root / '.env'
key_from_file = None
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('OPENROUTER_API_KEY='):
                key_from_file = line.split('=', 1)[1].strip().strip('"').strip("'")
                break

# Загружаем через load_dotenv
load_dotenv(override=True)
key_from_env = os.getenv('OPENROUTER_API_KEY')

print("=" * 80)
print("ПРОВЕРКА API КЛЮЧА")
print("=" * 80)
print()
print(f"Ключ в .env файле:     {key_from_file[:30] + '...' + key_from_file[-10:] if key_from_file else 'NOT FOUND'}")
print(f"Ключ после load_dotenv: {key_from_env[:30] + '...' + key_from_env[-10:] if key_from_env else 'NOT FOUND'}")
print()

if key_from_file and key_from_env:
    if key_from_file == key_from_env:
        print("[OK] Ключи совпадают")
    else:
        print("[WARN] Ключи НЕ совпадают!")
        print(f"  .env:     {key_from_file}")
        print(f"  getenv(): {key_from_env}")
        
# Проверяем в LLMManager
try:
    from src.llm.llm_manager import LLMManager
    mgr = LLMManager('config/llm_settings.yaml')
    key_used = os.getenv('OPENROUTER_API_KEY')
    print(f"Ключ в LLMManager:     {key_used[:30] + '...' + key_used[-10:] if key_used else 'NOT FOUND'}")
    
    if key_used == key_from_file:
        print("[OK] LLMManager использует ключ из .env")
    else:
        print("[WARN] LLMManager использует другой ключ!")
except Exception as e:
    print(f"[ERROR] Ошибка проверки LLMManager: {e}")

print()
