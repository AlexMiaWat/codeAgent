#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления импортов в тестах
Заменяет неправильные пути sys.path.insert на правильные
"""

import re
from pathlib import Path

def fix_file(file_path: Path):
    """Исправить один файл"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Паттерн для поиска неправильного пути
        pattern1 = r'sys\.path\.insert\(0,\s*str\(Path\(__file__\)\.parent\)\)'
        replacement1 = '''# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))'''
        
        # Паттерн для поиска без импорта Path
        pattern2 = r'sys\.path\.insert\(0,\s*str\(Path\(__file__\)\.parent\.parent\)\)'
        
        # Проверяем, есть ли неправильный путь
        if re.search(pattern1, content) and not re.search(pattern2, content):
            # Заменяем неправильный путь
            content = re.sub(pattern1, replacement1, content)
            
            # Если был изменен, сохраняем
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
    print("Исправление импортов в тестах...")
    print("=" * 80)
    
    fixed_count = 0
    total_count = 0
    
    # Обрабатываем все Python файлы в test/
    for py_file in test_dir.rglob("*.py"):
        # Пропускаем сам скрипт
        if py_file.name == "fix_imports.py":
            continue
        total_count += 1
        if fix_file(py_file):
            fixed_count += 1
    
    print("=" * 80)
    print(f"Исправлено файлов: {fixed_count}/{total_count}")

if __name__ == "__main__":
    main()
