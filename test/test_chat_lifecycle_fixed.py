#!/usr/bin/env python3
"""
Тест правильного chat lifecycle с исправленным парсингом chat_id

Исправляет проблему с получением chat_id после создания нового чата
"""

import sys
import os
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

# Используем переменную окружения для пути к проекту
project_dir = os.environ.get("TEST_PROJECT_DIR", "/tmp/test_project")

from src.cursor_cli_interface import create_cursor_cli_interface
from src.prompt_formatter import PromptFormatter
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_chat_lifecycle_fixed():
    """Тест chat lifecycle с правильным получением chat_id"""
    print("\n" + "="*80)
    print("ТЕСТ: Chat lifecycle с исправленным chat_id")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir=project_dir,
        agent_role="Project Executor Agent",
        timeout=2000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    print(f"[OK] CLI доступен: {cli.cli_command}")
    
    # Шаг 1: Системный промпт (new_chat)
    print("\n[STEP 1] Системный промпт (new_chat)")
    system_prompt = PromptFormatter.format_system_prompt(cli.agent_role)
    
    result1 = cli.execute(
        prompt=system_prompt,
        new_chat=True,
        timeout=300
    )
    
    print(f"  Success: {result1.success}, Exit: {result1.return_code}")
    
    # Ждем немного, чтобы чат создался
    time.sleep(2)
    
    # Получаем список чатов и берем последний
    print("\n[STEP 1.1] Получение chat_id после создания чата")
    chats = cli.list_chats()
    print(f"  Всего чатов: {len(chats)}")
    
    if chats:
        # Берем последний (самый новый) чат
        last_chat_id = chats[-1]
        print(f"  Последний chat_id: {last_chat_id}")
        cli.resume_chat(last_chat_id)
        print(f"  Chat ID установлен: {cli.current_chat_id}")
    else:
        print("  [WARN] Список чатов пуст, используем новый чат")
        last_chat_id = None
    
    # Шаг 2: Задача (resume_chat с правильным chat_id)
    print("\n[STEP 2] Задача (resume_chat)")
    
    # Простая инструкция для теста
    task_instruction = PromptFormatter.format_task_instruction(
        "Create file test_chat_lifecycle.txt with text 'Chat lifecycle test successful'",
        action_type="create",
        output_path="test_chat_lifecycle.txt"
    )
    
    result2 = cli.execute(
        prompt=task_instruction,
        new_chat=False,  # Продолжаем чат
        timeout=600
    )
    
    print(f"  Success: {result2.success}, Exit: {result2.return_code}")
    if result2.stdout:
        print(f"  Stdout: {result2.stdout[:200]}")
    
    # Шаг 3: Выполнение
    print("\n[STEP 3] Выполнение")
    execution_prompt = PromptFormatter.format_execution_prompt()
    
    result3 = cli.execute(
        prompt=execution_prompt,
        new_chat=False,  # Продолжаем чат
        timeout=600
    )
    
    print(f"  Success: {result3.success}, Exit: {result3.return_code}")
    
    # Post-check
    print("\n[POST-CHECK] Проверка файла")
    output_file = Path(project_dir) / "test_chat_lifecycle.txt"
    
    if output_file.exists():
        content = output_file.read_text(encoding='utf-8', errors='ignore')
        print(f"  [OK] Файл существует: {output_file}")
        print(f"  Размер: {output_file.stat().st_size} байт")
        print(f"  Содержимое: {content[:200]}")
        success = "Chat lifecycle test successful" in content
    else:
        print(f"  [FAIL] Файл не найден: {output_file}")
        success = False
    
    print("\n" + "="*80)
    print("ИТОГ:")
    print(f"  Системный промпт: {'[OK]' if result1.success else '[FAIL]'}")
    print(f"  Задача: {'[OK]' if result2.success else '[FAIL]'}")
    print(f"  Выполнение: {'[OK]' if result3.success else '[FAIL]'}")
    print(f"  Post-check: {'[OK]' if success else '[FAIL]'}")
    print(f"  Общий результат: {'[OK] УСПЕХ' if (result1.success and result2.success and result3.success and success) else '[FAIL] ОШИБКА'}")
    
    return result1.success and result2.success and result3.success and success


if __name__ == "__main__":
    try:
        success = test_chat_lifecycle_fixed()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Исключение: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
