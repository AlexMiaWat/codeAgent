#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления проблем с кодировкой в тестах
Заменяет эмодзи на текстовые метки для совместимости с Windows
"""

import re
from pathlib import Path

# Маппинг эмодзи на текстовые метки
EMOJI_REPLACEMENTS = {
    '[OK]': '[OK]',
    '[FAIL]': '[FAIL]',
    '[WARN]': '[WARN]',
    '[INFO]': '[INFO]',
    '[INFO]': '[INFO]',
    '[INFO]': '[INFO]',
    '[INFO]': '[INFO]',
    '[INFO]': '[INFO]',
    '[OK]': '[OK]',
    '[FAIL]': '[FAIL]',
}

def fix_file(file_path: Path):
    """Исправить один файл"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Заменяем все эмодзи
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            content = content.replace(emoji, replacement)
        
        # Если были изменения, сохраняем
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"  [OK] Исправлен: {file_path.name}")
            return True
        return False
    except Exception as e:
        print(f"  [FAIL] Ошибка в {file_path.name}: {e}")
        return False

def main():
    """Главная функция"""
    test_dir = Path(__file__).parent
    print("Исправление проблем с кодировкой в тестах...")
    print("=" * 80)
    
    fixed_count = 0
    total_count = 0
    
    # Обрабатываем все Python файлы в test/
    for py_file in test_dir.glob("*.py"):
        total_count += 1
        if fix_file(py_file):
            fixed_count += 1
    
    # Обрабатываем файлы в поддиректориях
    for py_file in test_dir.rglob("*.py"):
        if py_file.parent != test_dir:
            total_count += 1
            if fix_file(py_file):
                fixed_count += 1
    
    print("=" * 80)
    print(f"Исправлено файлов: {fixed_count}/{total_count}")

if __name__ == "__main__":
    main()
