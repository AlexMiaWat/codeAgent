#!/usr/bin/env python3
"""
Тест всех сценариев работы Cursor CLI с реальным целевым проектом
- Создание нового чата
- Продолжение диалога
- Сложные инструкции на русском языке
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cursor_cli_interface import create_cursor_cli_interface
import logging
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_scenario_1_new_chat():
    """Сценарий 1: Создание нового чата с простой инструкцией"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 1: Создание нового чата с простой инструкцией")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        agent_role="Project Executor Agent",
        timeout=1000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    print(f"[OK] CLI доступен: {cli.cli_command}")
    print(f"[OK] Проект: {cli.project_dir}")
    print(f"[OK] Роль: {cli.agent_role}")
    
    instruction = "Создай файл test_scenario_1.txt с текстом 'Тест сценария 1'"
    
    print(f"\n[CMD] Инструкция: {instruction}")
    print(f"[MODE] Режим: Новый чат (new_chat=True)")
    
    result = cli.execute(
        prompt=instruction,
        new_chat=True
    )
    
    print(f"\n[RESULT] Результат:")
    print(f"  Успех: {result.success}")
    print(f"  Код возврата: {result.return_code}")
    if result.stdout:
        print(f"  Вывод (первые 500 символов):\n{result.stdout[:500]}")
    if result.stderr:
        print(f"  Ошибки:\n{result.stderr[:500]}")
    
    return result.success


def test_scenario_2_continue_dialog():
    """Сценарий 2: Продолжение диалога - несколько команд в одном чате"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 2: Продолжение диалога - несколько команд в одном чате")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        agent_role="Project Executor Agent",
        timeout=1000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    # Первая команда - создаем новый чат
    instruction1 = "Создай файл test_scenario_2_part1.txt с текстом 'Часть 1 сценария 2'"
    
    print(f"\n[CMD] Команда 1 (новый чат): {instruction1}")
    result1 = cli.execute(
        prompt=instruction1,
        new_chat=True
    )
    
    print(f"  Результат 1: {result1.success} (код: {result1.return_code})")
    
    if not result1.success:
        print("[FAIL] Первая команда не выполнена, пропускаем продолжение")
        return False
    
    time.sleep(2)  # Небольшая задержка между командами
    
    # Вторая команда - продолжаем диалог
    instruction2 = "Теперь создай файл test_scenario_2_part2.txt с текстом 'Часть 2 сценария 2'"
    
    print(f"\n[CMD] Команда 2 (продолжение диалога): {instruction2}")
    result2 = cli.execute(
        prompt=instruction2,
        new_chat=False  # Продолжаем тот же чат
    )
    
    print(f"  Результат 2: {result2.success} (код: {result2.return_code})")
    if result2.stdout:
        print(f"  Вывод 2 (первые 300 символов):\n{result2.stdout[:300]}")
    
    time.sleep(2)
    
    # Третья команда - снова продолжаем
    instruction3 = "Выведи список всех файлов test_scenario_2*"
    
    print(f"\n[CMD] Команда 3 (продолжение диалога): {instruction3}")
    result3 = cli.execute(
        prompt=instruction3,
        new_chat=False  # Продолжаем тот же чат
    )
    
    print(f"  Результат 3: {result3.success} (код: {result3.return_code})")
    if result3.stdout:
        print(f"  Вывод 3 (первые 300 символов):\n{result3.stdout[:300]}")
    
    return result1.success and result2.success and result3.success


def test_scenario_3_complex_russian():
    """Сценарий 3: Сложная инструкция на русском языке"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 3: Сложная инструкция на русском языке")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        agent_role="Project Executor Agent",
        timeout=1000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    # Сложная инструкция на русском
    instruction = """Ты архитектор системы. Проанализируй всю документацию проекта и создай краткую выжимку по проекту в 50 строк. 
Сохрани результат в файл docs/results/mini_docs_for_user.md.

В выжимке должны быть:
1. Название и назначение проекта
2. Основные технологии и инструменты
3. Структура проекта
4. Ключевые функции и возможности
5. Инструкции по запуску

Файл должен быть в формате Markdown с заголовками и структурированным содержанием."""
    
    print(f"\n[CMD] Сложная инструкция (длина: {len(instruction)} символов):")
    print(f"  {instruction[:200]}...")
    print(f"\n[MODE] Режим: Новый чат (new_chat=True)")
    
    result = cli.execute(
        prompt=instruction,
        new_chat=True
    )
    
    print(f"\n[RESULT] Результат:")
    print(f"  Успех: {result.success}")
    print(f"  Код возврата: {result.return_code}")
    if result.stdout:
        print(f"  Вывод (первые 800 символов):\n{result.stdout[:800]}")
    if result.stderr:
        print(f"  Ошибки:\n{result.stderr[:500]}")
    
    # Проверяем, создан ли файл
    output_file = Path("d:/Space/life/docs/results/mini_docs_for_user.md")
    if output_file.exists():
        print(f"\n[OK] Файл создан: {output_file}")
        print(f"   Размер: {output_file.stat().st_size} байт")
        content = output_file.read_text(encoding='utf-8', errors='ignore')
        print(f"   Строк: {len(content.splitlines())}")
        print(f"\n   Первые 300 символов:\n{content[:300]}")
    else:
        print(f"\n[WARN] Файл не найден: {output_file}")
    
    return result.success


def test_scenario_4_list_chats():
    """Сценарий 4: Получение списка чатов"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 4: Получение списка доступных чатов")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        agent_role="Project Executor Agent",
        timeout=1000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    print("[INFO] Получаем список чатов...")
    chats = cli.list_chats()
    
    print(f"\n[RESULT] Результат:")
    print(f"  Найдено чатов: {len(chats)}")
    if chats:
        print("  Chat IDs:")
        for chat_id in chats:
            print(f"    - {chat_id}")
    else:
        print("  (Список пуст или команда не поддерживается)")
    
    return True


def test_scenario_5_resume_chat():
    """Сценарий 5: Явное возобновление чата по chat_id"""
    print("\n" + "="*80)
    print("СЦЕНАРИЙ 5: Явное возобновление чата по chat_id")
    print("="*80)
    
    cli = create_cursor_cli_interface(
        cli_path="docker-compose-agent",
        project_dir="d:/Space/life",
        agent_role="Project Executor Agent",
        timeout=1000
    )
    
    if not cli.is_available():
        print("[FAIL] Cursor CLI недоступен")
        return False
    
    # Получаем список чатов
    chats = cli.list_chats()
    
    if not chats:
        print("[WARN] Нет доступных чатов для возобновления")
        return True  # Не критичная ошибка
    
    # Используем первый доступный чат
    chat_id = chats[0]
    print(f"[INFO] Используем chat_id: {chat_id}")
    
    # Возобновляем чат
    success = cli.resume_chat(chat_id)
    print(f"  Возобновление: {'[OK] Успешно' if success else '[FAIL] Ошибка'}")
    
    # Выполняем команду в возобновленном чате
    instruction = "Продолжи работу. Выведи краткую информацию о текущем состоянии проекта."
    
    print(f"\n[CMD] Инструкция: {instruction}")
    result = cli.execute(
        prompt=instruction,
        chat_id=chat_id  # Явно указываем chat_id
    )
    
    print(f"\n[RESULT] Результат:")
    print(f"  Успех: {result.success}")
    print(f"  Код возврата: {result.return_code}")
    if result.stdout:
        print(f"  Вывод (первые 500 символов):\n{result.stdout[:500]}")
    
    return result.success


def main():
    """Запуск всех тестовых сценариев"""
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ ВСЕХ СЦЕНАРИЕВ CURSOR CLI")
    print("="*80)
    print(f"Целевой проект: d:/Space/life")
    print(f"Интерфейс: Docker (cursor-agent-life)")
    print("="*80)
    
    results = {}
    
    # Сценарий 1: Новый чат
    try:
        results['scenario_1'] = test_scenario_1_new_chat()
    except Exception as e:
        print(f"[FAIL] Ошибка в сценарии 1: {e}")
        results['scenario_1'] = False
    
    time.sleep(3)
    
    # Сценарий 2: Продолжение диалога
    try:
        results['scenario_2'] = test_scenario_2_continue_dialog()
    except Exception as e:
        print(f"[FAIL] Ошибка в сценарии 2: {e}")
        results['scenario_2'] = False
    
    time.sleep(3)
    
    # Сценарий 3: Сложная инструкция на русском
    try:
        results['scenario_3'] = test_scenario_3_complex_russian()
    except Exception as e:
        print(f"[FAIL] Ошибка в сценарии 3: {e}")
        results['scenario_3'] = False
    
    time.sleep(2)
    
    # Сценарий 4: Список чатов
    try:
        results['scenario_4'] = test_scenario_4_list_chats()
    except Exception as e:
        print(f"[FAIL] Ошибка в сценарии 4: {e}")
        results['scenario_4'] = False
    
    time.sleep(2)
    
    # Сценарий 5: Возобновление чата
    try:
        results['scenario_5'] = test_scenario_5_resume_chat()
    except Exception as e:
        print(f"[FAIL] Ошибка в сценарии 5: {e}")
        results['scenario_5'] = False
    
    # Итоги
    print("\n" + "="*80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)
    
    for scenario, success in results.items():
        status = "[OK] УСПЕХ" if success else "[FAIL] ОШИБКА"
        print(f"  {scenario.upper()}: {status}")
    
    total = len(results)
    passed = sum(1 for s in results.values() if s)
    
    print(f"\nВсего сценариев: {total}")
    print(f"Успешно: {passed}")
    print(f"Ошибок: {total - passed}")
    print("="*80)
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
