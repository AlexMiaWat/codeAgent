#!/usr/bin/env python3
"""
Комплексное тестирование сложных сценариев

Тестирует различные типы задач:
1. Создание файла с содержимым
2. Модификация существующего файла
3. Анализ документации
4. Многошаговые задачи
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cursor_cli_interface import create_cursor_cli_interface
from src.prompt_formatter import PromptFormatter
import logging

# Импорт вспомогательных функций для загрузки настроек
from test_utils import get_cli_path, get_project_dir, get_agent_role

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_scenario_1_create_file():
    """Сценарий 1: Создание файла с содержимым"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 1: Создание файла с содержимым")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path=get_cli_path(),
        project_dir=get_project_dir(),
        agent_role=get_agent_role(),
        timeout=2000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    # Используем строгий ACTION формат
    instruction = PromptFormatter.format_task_instruction(
        "Create file test_scenario_1_create.txt with content:\nLine 1: Test scenario 1\nLine 2: File creation test\nLine 3: Success indicator",
        action_type="create",
        output_path="test_scenario_1_create.txt"
    )
    
    result = cli.execute(
        prompt=instruction,
        new_chat=True,
        timeout=600
    )
    
    print(f"  Success: {result.success}, Exit: {result.return_code}")
    
    # Post-check
    output_file = Path(get_project_dir()) / "test_scenario_1_create.txt"
    if output_file.exists():
        content = output_file.read_text(encoding='utf-8', errors='ignore')
        print(f"  [OK] Файл создан: {len(content)} байт")
        has_expected = "Test scenario 1" in content or "Success indicator" in content
        return result.success and has_expected
    else:
        print(f"  [FAIL] Файл не найден: {output_file}")
        return False


def test_scenario_2_analyze_docs():
    """Сценарий 2: Анализ документации"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 2: Анализ документации")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path=get_cli_path(),
        project_dir=get_project_dir(),
        agent_role=get_agent_role(),
        timeout=2000
    )
    
    instruction = PromptFormatter.format_task_instruction(
        "Analyze all .md files in docs/ directory. Create summary file test_scenario_2_analysis.txt with list of found documentation files and their main topics.",
        action_type="analyze",
        output_path="test_scenario_2_analysis.txt",
        constraints=["List all .md files", "Extract main topics from each file", "Save to output file"]
    )
    
    result = cli.execute(
        prompt=instruction,
        new_chat=True,
        timeout=900
    )
    
    print(f"  Success: {result.success}, Exit: {result.return_code}")
    
    # Post-check
    output_file = Path(get_project_dir()) / "test_scenario_2_analysis.txt"
    if output_file.exists():
        content = output_file.read_text(encoding='utf-8', errors='ignore')
        print(f"  [OK] Файл создан: {len(content)} байт, {len(content.splitlines())} строк")
        return result.success
    else:
        print(f"  [FAIL] Файл не найден")
        return False


def test_scenario_3_multi_step():
    """Сценарий 3: Многошаговая задача"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 3: Многошаговая задача")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path=get_cli_path(),
        project_dir=get_project_dir(),
        agent_role=get_agent_role(),
        timeout=2000
    )
    
    instruction = PromptFormatter.format_task_instruction(
        """Perform multi-step task:
1. Create directory test_scenario_3/ if not exists
2. Create file test_scenario_3/step1.txt with content "Step 1 completed"
3. Create file test_scenario_3/step2.txt with content "Step 2 completed"
4. Create file test_scenario_3/summary.txt with content "Multi-step task completed successfully"
5. Verify all files exist""",
        action_type="execute",
        output_path="test_scenario_3/summary.txt",
        constraints=["Execute all steps", "Verify results", "Report completion"]
    )
    
    result = cli.execute(
        prompt=instruction,
        new_chat=True,
        timeout=1200
    )
    
    print(f"  Success: {result.success}, Exit: {result.return_code}")
    
    # Post-check
    base_dir = Path(get_project_dir()) / "test_scenario_3"
    files_to_check = [
        base_dir / "step1.txt",
        base_dir / "step2.txt",
        base_dir / "summary.txt"
    ]
    
    files_created = 0
    for file_path in files_to_check:
        if file_path.exists():
            files_created += 1
            print(f"  [OK] Файл создан: {file_path.name}")
    
    print(f"  Создано файлов: {files_created}/{len(files_to_check)}")
    return result.success and files_created >= 2


def test_scenario_4_russian_instruction():
    """Сценарий 4: Сложная русскоязычная инструкция"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 4: Сложная русскоязычная инструкция")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path=get_cli_path(),
        project_dir=get_project_dir(),
        agent_role=get_agent_role(),
        timeout=2000
    )
    
    # Исходная инструкция на русском
    human_instruction = "Ты архитектор системы. Проанализируй структуру проекта, создай файл test_scenario_4_analysis.txt с кратким описанием основных компонентов и технологий проекта."
    
    # Преобразуем в строгий формат
    formatted_instruction = PromptFormatter.parse_instruction_to_action_format(
        human_instruction,
        output_path="test_scenario_4_analysis.txt"
    )
    
    result = cli.execute(
        prompt=formatted_instruction,
        new_chat=True,
        timeout=1200
    )
    
    print(f"  Success: {result.success}, Exit: {result.return_code}")
    
    # Post-check
    output_file = Path(get_project_dir()) / "test_scenario_4_analysis.txt"
    if output_file.exists():
        content = output_file.read_text(encoding='utf-8', errors='ignore')
        print(f"  [OK] Файл создан: {len(content)} байт")
        return result.success
    else:
        print(f"  [FAIL] Файл не найден")
        return False


def test_scenario_5_lifecycle_full():
    """Сценарий 5: Полный lifecycle с системным промптом"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 5: Полный lifecycle с системным промптом")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path=get_cli_path(),
        project_dir=get_project_dir(),
        agent_role=get_agent_role(),
        timeout=2000
    )
    
    # Шаг 1: Системный промпт
    print("[STEP 1] Системный промпт")
    system_prompt = PromptFormatter.format_system_prompt(cli.agent_role)
    result1 = cli.execute(system_prompt, new_chat=True, timeout=300)
    print(f"  Success: {result1.success}")
    
    if not result1.success:
        return False
    
    time.sleep(2)
    
    # Получаем chat_id
    chats = cli.list_chats()
    if chats:
        cli.resume_chat(chats[-1])
        print(f"  Chat ID: {cli.current_chat_id}")
    
    # Шаг 2: Задача
    print("\n[STEP 2] Задача")
    task_instruction = PromptFormatter.format_task_instruction(
        "Create file test_scenario_5_lifecycle.txt with content 'Lifecycle test successful'",
        action_type="create",
        output_path="test_scenario_5_lifecycle.txt"
    )
    result2 = cli.execute(task_instruction, new_chat=False, timeout=600)
    print(f"  Success: {result2.success}")
    
    # Шаг 3: Выполнение
    print("\n[STEP 3] Выполнение")
    exec_prompt = PromptFormatter.format_execution_prompt()
    result3 = cli.execute(exec_prompt, new_chat=False, timeout=600)
    print(f"  Success: {result3.success}")
    
    # Post-check
    output_file = Path(get_project_dir()) / "test_scenario_5_lifecycle.txt"
    success = output_file.exists() and result1.success and result2.success and result3.success
    
    if output_file.exists():
        print(f"  [OK] Файл создан")
    else:
        print(f"  [FAIL] Файл не найден")
    
    return success


def run_all_scenarios():
    """Запуск всех сценариев"""
    print("\n" + "="*80)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СЛОЖНЫХ СЦЕНАРИЕВ")
    print("="*80)
    print(f"Проект: {get_project_dir()}")
    print(f"Интерфейс: Docker (cursor-agent)")
    print("="*80)
    
    scenarios = [
        ("Создание файла", test_scenario_1_create_file),
        ("Анализ документации", test_scenario_2_analyze_docs),
        ("Многошаговая задача", test_scenario_3_multi_step),
        ("Русскоязычная инструкция", test_scenario_4_russian_instruction),
        ("Полный lifecycle", test_scenario_5_lifecycle_full),
    ]
    
    results = {}
    
    for name, test_func in scenarios:
        try:
            print(f"\n{'='*80}")
            print(f"Запуск: {name}")
            print(f"{'='*80}")
            results[name] = test_func()
            print(f"\n[RESULT] {name}: {'[OK] УСПЕХ' if results[name] else '[FAIL] ОШИБКА'}")
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Итоги
    print("\n" + "="*80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for name, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"  {name}: {status}")
    
    print(f"\nУспешно: {success_count}/{total_count} ({success_count*100//total_count if total_count > 0 else 0}%)")
    print(f"Общий результат: {'[OK] ЧАСТИЧНО УСПЕШНО' if success_count > 0 else '[FAIL] ОШИБКА'}")
    
    return success_count, total_count


if __name__ == "__main__":
    try:
        success_count, total_count = run_all_scenarios()
        sys.exit(0 if success_count == total_count else 1)
    except Exception as e:
        print(f"\n[ERROR] Исключение: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
