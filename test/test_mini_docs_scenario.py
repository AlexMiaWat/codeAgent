#!/usr/bin/env python3
"""
Детальный тест сценария создания mini_docs_for_user.md
Сложная многострочная инструкция на русском языке
"""

import sys
import logging
import time
from pathlib import Path

from src.cursor_cli_interface import create_cursor_cli_interface

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_mini_docs_creation():
    """Тест создания mini_docs_for_user.md с детальным логированием"""
    print("\n" + "="*80)
    print("ТЕСТ: Создание mini_docs_for_user.md")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        agent_role="Project Executor Agent",
        timeout=2000  # Увеличенный таймаут для сложной задачи
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    print(f"[OK] CLI доступен: {cli.cli_command}")
    print(f"[OK] Проект: {cli.project_dir}")
    print(f"[OK] Роль: {cli.agent_role}")
    
    # Сложная многострочная инструкция на русском
    instruction = """Ты архитектор системы. Проанализируй всю документацию проекта и создай краткую выжимку по проекту в 50 строк. 
Сохрани результат в файл docs/results/mini_docs_for_user.md.

В выжимке должны быть:
1. Название и назначение проекта
2. Основные технологии и инструменты
3. Структура проекта
4. Ключевые функции и возможности
5. Инструкции по запуску

Файл должен быть в формате Markdown с заголовками и структурированным содержанием."""
    
    print(f"\n[CMD] Инструкция (длина: {len(instruction)} символов):")
    print(f"  Первые 200 символов: {instruction[:200]}...")
    print("\n[MODE] Режим: Новый чат (new_chat=True)")
    print("[TIMEOUT] Таймаут: 2000 секунд")
    
    start_time = time.time()
    
    result = cli.execute(
        prompt=instruction,
        new_chat=True,
        timeout=2000
    )
    
    elapsed_time = time.time() - start_time
    
    print("\n[RESULT] Результат выполнения:")
    print(f"  Успех: {result.success}")
    print(f"  Код возврата: {result.return_code}")
    print(f"  Время выполнения: {elapsed_time:.2f} секунд")
    
    if result.stdout:
        print("\n  Вывод stdout (первые 1000 символов):")
        print(f"  {'-'*76}")
        print(f"  {result.stdout[:1000]}")
        print(f"  {'-'*76}")
        if len(result.stdout) > 1000:
            print(f"  ... (еще {len(result.stdout) - 1000} символов)")
    
    if result.stderr:
        print("\n  Ошибки stderr (первые 500 символов):")
        print(f"  {'-'*76}")
        print(f"  {result.stderr[:500]}")
        print(f"  {'-'*76}")
    
    # Проверяем, создан ли файл
    output_file = Path("d:/Space/life/docs/results/mini_docs_for_user.md")
    
    print(f"\n[CHECK] Проверка файла: {output_file}")
    
    if output_file.exists():
        file_size = output_file.stat().st_size
        content = output_file.read_text(encoding='utf-8', errors='ignore')
        lines_count = len(content.splitlines())
        
        print("  [OK] Файл существует")
        print(f"  Размер: {file_size} байт")
        print(f"  Строк: {lines_count}")
        
        if lines_count > 0:
            print("\n  Содержимое файла (первые 500 символов):")
            print(f"  {'-'*76}")
            print(f"  {content[:500]}")
            print(f"  {'-'*76}")
            
            # Проверка структуры
            has_title = "#" in content
            has_sections = content.count("#") >= 3
            has_content = len(content.strip()) > 200
            
            print("\n  Проверка структуры:")
            print(f"    Есть заголовки (#): {has_title}")
            print(f"    Много разделов (>=3): {has_sections}")
            print(f"    Есть содержание (>200 символов): {has_content}")
            
            success = has_title and has_content and lines_count >= 10
            print(f"\n  Результат проверки: {'[OK] Файл корректен' if success else '[WARN] Файл требует проверки'}")
        else:
            print("  [WARN] Файл пустой")
            success = False
    else:
        print("  [FAIL] Файл не найден")
        print(f"  Путь: {output_file.absolute()}")
        
        # Проверяем существование директории
        output_dir = output_file.parent
        if output_dir.exists():
            print(f"  [INFO] Директория существует: {output_dir}")
            files_in_dir = list(output_dir.glob("*.md"))
            print(f"  [INFO] Файлы в директории: {[f.name for f in files_in_dir]}")
        else:
            print(f"  [WARN] Директория не существует: {output_dir}")
        
        success = False
    
    print("\n[SUMMARY] Итоговый результат:")
    print(f"  Выполнение команды: {'[OK]' if result.success else '[FAIL]'}")
    print(f"  Создание файла: {'[OK]' if output_file.exists() else '[FAIL]'}")
    print(f"  Общий результат: {'[OK] УСПЕХ' if (result.success and success) else '[FAIL] ОШИБКА'}")
    
    return result.success and success


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ДЕТАЛЬНЫЙ ТЕСТ: Создание mini_docs_for_user.md")
    print("="*80)
    print("Проект: d:/Space/life")
    print("Интерфейс: Docker (cursor-agent-life)")
    print("="*80)
    
    try:
        success = test_mini_docs_creation()
        
        print("\n" + "="*80)
        print("ИТОГ ТЕСТА")
        print("="*80)
        print(f"Результат: {'[OK] УСПЕХ' if success else '[FAIL] ОШИБКА'}")
        print("="*80)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Исключение при тестировании: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
