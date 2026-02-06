#!/usr/bin/env python3
"""
Скрипт для классификации тестовых файлов и перемещения их в поддиректории unit/integration/e2e.
Анализирует имена файлов и маркеры pytest.
"""

import os
import re
import shutil
from pathlib import Path

# Пути
TEST_DIR = Path("test")
UNIT_DIR = TEST_DIR / "unit"
INTEGRATION_DIR = TEST_DIR / "integration"
E2E_DIR = TEST_DIR / "e2e"

# Ключевые слова для классификации
UNIT_KEYWORDS = []
INTEGRATION_KEYWORDS = [
    "integration", "llm", "docker", "cursor", "real_", "hybrid_",
    "gemini", "openrouter", "groq", "crewai", "model_discovery",
    "billing_error", "server_", "agent_", "cli_", "api_",
]
E2E_KEYWORDS = [
    "full_cycle", "real_server", "end_to_end", "e2e", "complex_scenario",
]

# Маркеры pytest (ищем в содержимом файла)
MARKER_PATTERNS = {
    "unit": r"@pytest\.mark\.unit",
    "integration": r"@pytest\.mark\.integration",
    "llm": r"@pytest\.mark\.llm",
    "docker": r"@pytest\.mark\.docker",
    "cursor": r"@pytest\.mark\.cursor",
}

def classify_file(file_path: Path) -> str:
    """Определить категорию теста: unit, integration или e2e."""
    name = file_path.stem.lower()
    # Проверить ключевые слова в имени
    for kw in E2E_KEYWORDS:
        if kw in name:
            return "e2e"
    for kw in INTEGRATION_KEYWORDS:
        if kw in name:
            return "integration"
    
    # Прочитать содержимое файла для поиска маркеров
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Если не текст, пропускаем
        return "unit"
    
    # Поиск маркеров
    if re.search(MARKER_PATTERNS["integration"], content):
        return "integration"
    if re.search(MARKER_PATTERNS["llm"], content):
        return "integration"
    if re.search(MARKER_PATTERNS["docker"], content):
        return "integration"
    if re.search(MARKER_PATTERNS["cursor"], content):
        return "integration"
    if re.search(MARKER_PATTERNS["unit"], content):
        return "unit"
    
    # Если в имени есть "test_" и нет других признаков, считаем unit
    if name.startswith("test_"):
        return "unit"
    
    # По умолчанию unit
    return "unit"

def move_file(file_path: Path, category: str):
    """Переместить файл в соответствующую поддиректорию."""
    if category == "unit":
        target_dir = UNIT_DIR
    elif category == "integration":
        target_dir = INTEGRATION_DIR
    elif category == "e2e":
        target_dir = E2E_DIR
    else:
        return
    
    # Убедиться, что целевая директория существует
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Переместить файл
    target_path = target_dir / file_path.name
    if file_path != target_path:
        print(f"Moving {file_path} -> {target_path}")
        shutil.move(str(file_path), str(target_path))

def main():
    print("Классификация тестовых файлов...")
    
    # Собрать все .py файлы в test/ (кроме поддиректорий unit/integration/e2e)
    test_files = []
    for root, dirs, files in os.walk(TEST_DIR):
        root_path = Path(root)
        # Пропустить уже созданные поддиректории, чтобы не перемещать уже перемещенные
        if root_path.name in ("unit", "integration", "e2e", "cursor_cli", "cursor_commands", "integration"):
            continue
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                test_files.append(root_path / file)
    
    print(f"Найдено {len(test_files)} тестовых файлов.")
    
    # Классифицировать и переместить
    categories = {"unit": 0, "integration": 0, "e2e": 0}
    for file_path in test_files:
        category = classify_file(file_path)
        categories[category] += 1
        move_file(file_path, category)
    
    print("Результаты классификации:")
    for cat, count in categories.items():
        print(f"  {cat}: {count} файлов")
    
    # Также переместить __init__.py в каждую поддиректорию, если нужно
    for dir_path in (UNIT_DIR, INTEGRATION_DIR, E2E_DIR):
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            print(f"Создан {init_file}")

if __name__ == "__main__":
    main()