#!/usr/bin/env python3
"""
Кросс‑платформенный скрипт очистки временных файлов и директорий Code Agent.
Запускается из Makefile target `clean`.
"""

import os
import shutil
import sys

def remove_patterns():
    """Удаляет файлы и директории по заданным шаблонам."""
    cwd = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(cwd)  # на уровень выше scripts/

    patterns_to_remove = [
        # Директории __pycache__
        ("__pycache__", True),
        # Файлы .pyc, .pyo
        (".pyc", False),
        (".pyo", False),
        # Директории с .egg-info
        (".egg-info", True),
        # Кэши тестов и покрытия
        (".pytest_cache", True),
        (".coverage", False),
        ("htmlcov", True),
        (".mypy_cache", True),
        (".ruff_cache", True),
        # Директории сборки
        ("build", True),
        ("dist", True),
    ]

    for pattern, is_dir in patterns_to_remove:
        for root, dirs, files in os.walk(project_root, topdown=False):
            if is_dir:
                for dir_name in dirs:
                    if dir_name == pattern:
                        full_path = os.path.join(root, dir_name)
                        try:
                            shutil.rmtree(full_path)
                            print(f"Удалена директория: {full_path}")
                        except Exception as e:
                            print(f"Ошибка при удалении {full_path}: {e}")
            else:
                for file_name in files:
                    if file_name.endswith(pattern):
                        full_path = os.path.join(root, file_name)
                        try:
                            os.remove(full_path)
                            print(f"Удалён файл: {full_path}")
                        except Exception as e:
                            print(f"Ошибка при удалении {full_path}: {e}")

def main():
    print("Очистка временных файлов Code Agent...")
    remove_patterns()
    print("Очистка завершена.")

if __name__ == "__main__":
    main()