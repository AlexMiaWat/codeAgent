#!/usr/bin/env python3
"""
Тест применения рекомендаций экспертов на целевом проекте

Тестирует:
1. Стандартизацию формата инструкций (ACTION/TASK)
2. Правильный chat lifecycle (системный промпт → задачи → выполнение)
3. Post-check для side-effects (проверка файлов)
"""

import sys
import logging
from pathlib import Path

from src.cursor_cli_interface import create_cursor_cli_interface
from src.prompt_formatter import PromptFormatter

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_expert_recommendations():
    """Тест всех рекомендаций экспертов"""
    print("\n" + "="*80)
    print("ТЕСТ: Применение рекомендаций экспертов")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        agent_role="Project Executor Agent",
        timeout=2000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    print(f"[OK] CLI доступен: {cli.cli_command}")
    print(f"[OK] Проект: {cli.project_dir}")
    print(f"[OK] Роль: {cli.agent_role}")
    
    # РЕКОМЕНДАЦИЯ #2: Стандартизация формата инструкций
    print("\n" + "-"*80)
    print("РЕКОМЕНДАЦИЯ #2: Стандартизация формата инструкций")
    print("-"*80)
    
    # Форматируем инструкцию в строгом ACTION формате
    human_instruction = "Создай файл test_expert_recommendations.txt с текстом 'Hello from expert recommendations!'"
    formatted_instruction = PromptFormatter.parse_instruction_to_action_format(
        human_instruction,
        output_path="test_expert_recommendations.txt"
    )
    
    print("[FORMAT] Исходная инструкция (человеческий язык):")
    print(f"  {human_instruction}")
    print("\n[FORMAT] Отформатированная инструкция (ACTION/TASK формат):")
    print(f"  {formatted_instruction[:200]}...")
    
    # РЕКОМЕНДАЦИЯ #3: Правильный chat lifecycle
    print("\n" + "-"*80)
    print("РЕКОМЕНДАЦИЯ #3: Правильный chat lifecycle")
    print("-"*80)
    
    # Шаг 1: Системный промпт (new_chat)
    print("[LIFECYCLE] Шаг 1: Системный промпт (new_chat)")
    system_prompt = PromptFormatter.format_system_prompt(cli.agent_role)
    
    result1 = cli.execute(
        prompt=system_prompt,
        new_chat=True,
        timeout=300
    )
    
    print(f"  Успех: {result1.success}")
    print(f"  Код возврата: {result1.return_code}")
    print(f"  Chat ID: {cli.current_chat_id or 'N/A'}")
    
    if not result1.success:
        print("[FAIL] Системный промпт не выполнен")
        return False
    
    # Шаг 2: Задача (resume_chat)
    print("\n[LIFECYCLE] Шаг 2: Задача (resume_chat)")
    result2 = cli.execute(
        prompt=formatted_instruction,
        new_chat=False,  # Продолжаем чат
        timeout=600
    )
    
    print(f"  Успех: {result2.success}")
    print(f"  Код возврата: {result2.return_code}")
    print(f"  Stdout length: {len(result2.stdout) if result2.stdout else 0}")
    
    # Шаг 3: Выполнение (resume_chat)
    print("\n[LIFECYCLE] Шаг 3: Выполнение (resume_chat)")
    execution_prompt = PromptFormatter.format_execution_prompt()
    
    result3 = cli.execute(
        prompt=execution_prompt,
        new_chat=False,  # Продолжаем чат
        timeout=600
    )
    
    print(f"  Успех: {result3.success}")
    print(f"  Код возврата: {result3.return_code}")
    
    # РЕКОМЕНДАЦИЯ #4: Post-check для side-effects
    print("\n" + "-"*80)
    print("РЕКОМЕНДАЦИЯ #4: Post-check для side-effects")
    print("-"*80)
    
    output_file = Path("d:/Space/life/test_expert_recommendations.txt")
    
    print(f"[POST-CHECK] Проверка файла: {output_file}")
    
    if output_file.exists():
        file_size = output_file.stat().st_size
        content = output_file.read_text(encoding='utf-8', errors='ignore')
        
        print("  [OK] Файл существует")
        print(f"  Размер: {file_size} байт")
        print("  Содержимое:")
        print(f"  {content[:200]}")
        
        has_expected_content = "Hello from expert recommendations" in content
        print(f"  Ожидаемый текст найден: {has_expected_content}")
        
        success = has_expected_content
    else:
        print("  [FAIL] Файл не найден")
        print(f"  Путь: {output_file.absolute()}")
        success = False
    
    # Итоговый результат
    print("\n" + "="*80)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("="*80)
    print(f"Системный промпт: {'[OK]' if result1.success else '[FAIL]'}")
    print(f"Задача: {'[OK]' if result2.success else '[FAIL]'}")
    print(f"Выполнение: {'[OK]' if result3.success else '[FAIL]'}")
    print(f"Post-check (файл): {'[OK]' if success else '[FAIL]'}")
    print(f"\nОбщий результат: {'[OK] УСПЕХ' if (result1.success and result2.success and result3.success and success) else '[FAIL] ОШИБКА'}")
    
    return result1.success and result2.success and result3.success and success


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ТЕСТ: Применение рекомендаций экспертов на целевом проекте")
    print("="*80)
    print("Проект: d:/Space/life")
    print("Интерфейс: Docker (cursor-agent-life)")
    print("="*80)
    
    try:
        success = test_expert_recommendations()
        
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
