"""
Тестирование интеграции Code Agent с Cursor (без CrewAI)

Тестирует только взаимодействие с Cursor:
1. Инициализация компонентов
2. Загрузка todo файла
3. Определение типа задачи
4. Получение шаблона инструкции
5. Форматирование инструкции
6. Файловый интерфейс
7. Проверка CLI
8. Ожидание файлов результатов
"""

import sys
import time
from pathlib import Path
from datetime import datetime

from src.config_loader import ConfigLoader
from src.todo_manager import TodoManager
from src.cursor_file_interface import CursorFileInterface
from src.cursor_cli_interface import create_cursor_cli_interface

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_loading():
    """Тест 1: Загрузка конфигурации"""
    print("=" * 70)
    print("ТЕСТ 1: Загрузка конфигурации")
    print("=" * 70)
    print()
    
    try:
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        
        print("[OK] Конфигурация загружена")
        print(f"  Проект: {project_dir}")
        print(f"  Todo формат: {config.get('project.todo_format')}")
        print(f"  Cursor interface_type: {config.get('cursor.interface_type')}")
        print()
        
        return True, config, project_dir
    except Exception as e:
        print(f"[FAIL] Ошибка загрузки конфигурации: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_todo_loading(project_dir):
    """Тест 2: Загрузка todo файла"""
    print()
    print("=" * 70)
    print("ТЕСТ 2: Загрузка TODO файла")
    print("=" * 70)
    print()
    
    try:
        todo_format = "md"
        todo_manager = TodoManager(project_dir, todo_format=todo_format)
        
        print("[OK] Todo менеджер создан")
        print(f"  Файл: {todo_manager.todo_file}")
        print(f"  Найдено задач: {len(todo_manager.items)}")
        
        pending = todo_manager.get_pending_tasks()
        print(f"  Невыполненных задач: {len(pending)}")
        print()
        
        if pending:
            print("Первые 5 невыполненных задач:")
            for i, task in enumerate(pending[:5], 1):
                status = "[DONE]" if task.done else "[TODO]"
                print(f"  {i}. {status} {task.text[:70]}")
            print()
            return True, todo_manager, pending[0]
        else:
            print("[WARNING] Не найдено невыполненных задач")
            return False, todo_manager, None
            
    except Exception as e:
        print(f"[FAIL] Ошибка загрузки todo: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_task_type_determination(config, todo_item):
    """Тест 3: Определение типа задачи (симуляция метода)"""
    print()
    print("=" * 70)
    print("ТЕСТ 3: Определение типа задачи")
    print("=" * 70)
    print()
    
    try:
        # Симулируем логику определения типа задачи
        task_text = todo_item.text.lower()
        
        if any(word in task_text for word in ['тест', 'test', 'тестирование']):
            task_type = 'test'
        elif any(word in task_text for word in ['документация', 'docs', 'readme']):
            task_type = 'documentation'
        elif any(word in task_text for word in ['рефакторинг', 'refactor']):
            task_type = 'refactoring'
        elif any(word in task_text for word in ['разработка', 'реализация', 'implement']):
            task_type = 'development'
        else:
            task_type = 'default'
        
        print(f"[OK] Тип задачи определен: {task_type}")
        print(f"  Задача: {todo_item.text[:60]}")
        print(f"  Тип: {task_type}")
        print()
        
        return True, task_type
    except Exception as e:
        print(f"[FAIL] Ошибка определения типа: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_instruction_template(config, task_type):
    """Тест 4: Получение шаблона инструкции"""
    print()
    print("=" * 70)
    print("ТЕСТ 4: Получение шаблона инструкции")
    print("=" * 70)
    print()
    
    try:
        instructions = config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))
        
        template = None
        for instruction in task_instructions:
            if isinstance(instruction, dict) and instruction.get('instruction_id') == 1:
                template = instruction
                break
        
        if not template and task_instructions and isinstance(task_instructions[0], dict):
            template = task_instructions[0]
        
        if template:
            print("[OK] Шаблон найден")
            print(f"  ID: {template.get('instruction_id')}")
            print(f"  Имя: {template.get('name')}")
            print(f"  Для Cursor: {template.get('for_cursor')}")
            print(f"  Wait for file: {template.get('wait_for_file')}")
            print(f"  Control phrase: {template.get('control_phrase')}")
            print(f"  Timeout: {template.get('timeout')}")
            print()
            return True, template
        else:
            print("[WARNING] Шаблон не найден")
            return False, None
            
    except Exception as e:
        print(f"[FAIL] Ошибка получения шаблона: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_instruction_formatting(template, todo_item, task_id):
    """Тест 5: Форматирование инструкции"""
    print()
    print("=" * 70)
    print("ТЕСТ 5: Форматирование инструкции")
    print("=" * 70)
    print()
    
    try:
        if template:
            instruction_text = template.get('template', '')
            
            # Подстановка значений
            replacements = {
                'task_name': todo_item.text,
                'task_id': task_id,
                'task_description': todo_item.text,
                'date': datetime.now().strftime('%Y%m%d'),
            }
            
            for key, value in replacements.items():
                instruction_text = instruction_text.replace(f'{{{key}}}', str(value))
        else:
            instruction_text = f"Выполни задачу: {todo_item.text}\n\nСоздай отчет в docs/results/last_result.md, в конце напиши 'Отчет завершен!'"
        
        print("[OK] Инструкция отформатирована")
        print(f"  Task ID: {task_id}")
        print(f"  Длина: {len(instruction_text)} символов")
        print()
        print("Отформатированная инструкция (первые 400 символов):")
        print("  " + "\n  ".join(instruction_text[:400].split("\n")))
        print("  ...")
        print()
        
        return True, instruction_text
    except Exception as e:
        print(f"[FAIL] Ошибка форматирования: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_cursor_cli(project_dir):
    """Тест 6: Проверка Cursor CLI"""
    print()
    print("=" * 70)
    print("ТЕСТ 6: Проверка Cursor CLI")
    print("=" * 70)
    print()
    
    try:
        cli = create_cursor_cli_interface(timeout=300, headless=True)
        
        is_available = cli.is_available()
        print(f"[INFO] Cursor CLI доступен: {is_available}")
        
        if is_available:
            version = cli.check_version()
            if version:
                print(f"  Версия CLI: {version}")
            print(f"  CLI команда: {cli.cli_command}")
        else:
            print("  CLI не найден в системе (будет использоваться файловый интерфейс)")
        print()
        
        return True, cli, is_available
    except Exception as e:
        print(f"[WARNING] Ошибка проверки CLI: {e}")
        return False, None, False


def test_file_interface(project_dir, instruction, task_id):
    """Тест 7: Файловый интерфейс - создание файла инструкции"""
    print()
    print("=" * 70)
    print("ТЕСТ 7: Файловый интерфейс - создание файла инструкции")
    print("=" * 70)
    print()
    
    try:
        cursor_file = CursorFileInterface(project_dir)
        
        # Записываем инструкцию с маркером NEW_CHAT
        file_path = cursor_file.write_instruction(
            instruction=instruction,
            task_id=task_id,
            metadata={
                "test": True,
                "timestamp": datetime.now().isoformat()
            },
            new_chat=True
        )
        
        print("[OK] Файл инструкции создан")
        print(f"  Путь: {file_path}")
        print(f"  Существует: {file_path.exists()}")
        
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8')
                print(f"  Размер: {len(content)} символов")
                print(f"  Содержит NEW_CHAT: {'NEW_CHAT' in content}")
                print(f"  Содержит инструкцию: {instruction[:50] in content}")
            except Exception as e:
                print(f"  [WARNING] Ошибка чтения файла: {e}")
        
        print()
        print("Структура директорий:")
        print(f"  cursor_commands: {cursor_file.commands_dir.exists()}")
        print(f"    Файлов инструкций: {len(list(cursor_file.commands_dir.glob('instruction_*.txt')))}")
        print(f"  cursor_results: {cursor_file.results_dir.exists()}")
        print()
        
        return True, file_path, cursor_file
    except Exception as e:
        print(f"[FAIL] Ошибка файлового интерфейса: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_wait_for_result_logic(cursor_file, project_dir, task_id, wait_for_file, control_phrase):
    """Тест 8: Логика ожидания файла результата"""
    print()
    print("=" * 70)
    print("ТЕСТ 8: Логика ожидания файла результата")
    print("=" * 70)
    print()
    
    try:
        # Тестируем метод ожидания с коротким таймаутом
        timeout = 5
        check_interval = 1
        
        print("Тестирование ожидания файла:")
        print(f"  Файл: {wait_for_file}")
        print(f"  Контрольная фраза: {control_phrase}")
        print(f"  Таймаут: {timeout}s (короткий для теста)")
        print()
        print("[INFO] Запускается проверка (таймаут ожидается, так как файла нет)")
        
        wait_result = cursor_file.wait_for_result(
            task_id=task_id,
            timeout=timeout,
            check_interval=check_interval,
            control_phrase=control_phrase
        )
        
        if wait_result["success"]:
            print("[OK] Файл найден (неожиданно)")
            print(f"  Путь: {wait_result['file_path']}")
            print(f"  Время ожидания: {wait_result['wait_time']:.2f}s")
        else:
            print("[INFO] Файл не найден (ожидаемо для теста)")
            print(f"  Ошибка: {wait_result.get('error')}")
            print(f"  Ожидаемый путь: {wait_result['file_path']}")
        print()
        
        return True
    except Exception as e:
        print(f"[WARNING] Ошибка тестирования ожидания: {e}")
        return False


def test_full_flow(config, todo_manager, todo_item, project_dir):
    """Тест 9: Полный поток выполнения задачи (симуляция)"""
    print()
    print("=" * 70)
    print("ТЕСТ 9: Полный поток выполнения задачи (симуляция)")
    print("=" * 70)
    print()
    
    try:
        task_id = f"test_{int(time.time())}"
        
        print("Шаг 1: Определение типа задачи")
        task_text = todo_item.text.lower()
        if any(word in task_text for word in ['тест', 'test']):
            task_type = 'test'
        elif any(word in task_text for word in ['документация', 'docs']):
            task_type = 'documentation'
        elif any(word in task_text for word in ['разработка', 'реализация']):
            task_type = 'development'
        else:
            task_type = 'default'
        print(f"  [OK] Тип: {task_type}")
        print()
        
        print("Шаг 2: Получение шаблона инструкции")
        instructions = config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))
        template = task_instructions[0] if task_instructions and isinstance(task_instructions[0], dict) else None
        if template:
            print(f"  [OK] Шаблон найден: {template.get('name')}")
        else:
            print("  [INFO] Шаблон не найден, используется базовый")
        print()
        
        print("Шаг 3: Форматирование инструкции")
        if template:
            instruction = template.get('template', '').replace('{task_name}', todo_item.text).replace('{task_id}', task_id)
        else:
            instruction = f"Выполни задачу: {todo_item.text}"
        print(f"  [OK] Инструкция отформатирована ({len(instruction)} символов)")
        print()
        
        print("Шаг 4: Создание файла инструкции (файловый интерфейс)")
        cursor_file = CursorFileInterface(project_dir)
        file_path = cursor_file.write_instruction(instruction, task_id, new_chat=True)
        print(f"  [OK] Файл создан: {file_path.name}")
        print()
        
        print("Шаг 5: Информация для пользователя")
        print("  [INFO] Следующие шаги:")
        print("    1. Открой Cursor IDE")
        print(f"    2. Открой проект: {project_dir}")
        print("    3. Создай новый чат (Ctrl+L)")
        print(f"    4. Прочитай инструкцию из файла: {file_path}")
        print("    5. Выполни инструкцию в Cursor")
        print(f"    6. Сохрани результат в: cursor_results/result_{task_id}.txt")
        print()
        
        print("[OK] Полный поток смоделирован успешно")
        print()
        return True
        
    except Exception as e:
        print(f"[FAIL] Ошибка моделирования потока: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция тестирования"""
    print()
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ CODE AGENT С CURSOR")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Целевой проект: D:\\Space\\life")
    print()
    
    results = {}
    
    # Тест 1: Конфигурация
    success, config, project_dir = test_config_loading()
    results['config'] = success
    if not success or not config:
        print("[ERROR] Не удалось загрузить конфигурацию")
        return
    
    # Тест 2: Todo
    success, todo_manager, todo_item = test_todo_loading(project_dir)
    results['todo'] = success
    if not todo_item:
        print("[WARNING] Нет задач для дальнейшего тестирования")
    
    # Тест 3: Тип задачи
    if todo_item:
        success, task_type = test_task_type_determination(config, todo_item)
        results['task_type'] = success
    else:
        task_type = 'default'
        results['task_type'] = False
    
    # Тест 4: Шаблон
    success, template = test_instruction_template(config, task_type)
    results['template'] = success
    
    # Тест 5: Форматирование
    if todo_item:
        task_id = f"test_{int(time.time())}"
        success, instruction = test_instruction_formatting(template, todo_item, task_id)
        results['formatting'] = success
    else:
        instruction = "Test instruction"
        task_id = "test_001"
        results['formatting'] = False
    
    # Тест 6: CLI
    success, cli, cli_available = test_cursor_cli(project_dir)
    results['cli'] = success
    
    # Тест 7: Файловый интерфейс
    success, file_path, cursor_file = test_file_interface(project_dir, instruction, task_id)
    results['file_interface'] = success
    
    # Тест 8: Ожидание файла
    if template:
        wait_for_file = template.get('wait_for_file', "docs/results/last_result.md")
        control_phrase = template.get('control_phrase', "Отчет завершен!")
    else:
        wait_for_file = "docs/results/last_result.md"
        control_phrase = "Отчет завершен!"
    
    if cursor_file:
        success = test_wait_for_result_logic(cursor_file, project_dir, task_id, wait_for_file, control_phrase)
        results['wait_logic'] = success
    else:
        results['wait_logic'] = False
    
    # Тест 9: Полный поток
    if todo_item:
        success = test_full_flow(config, todo_manager, todo_item, project_dir)
        results['full_flow'] = success
    else:
        results['full_flow'] = False
    
    # Итоги
    print()
    print("=" * 70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    print()
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"Всего тестов: {total}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {total - passed}")
    print()
    
    for test_name, result in results.items():
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"  {test_name}: {status}")
    
    print()
    print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    if file_path and file_path.exists():
        print("[INFO] Файл инструкции создан и готов для использования:")
        print(f"  {file_path}")
        print()
        print("Для тестирования реального выполнения:")
        print(f"  1. Открой Cursor IDE в проекте {project_dir}")
        print(f"  2. Прочитай инструкцию из файла: {file_path.name}")
        print("  3. Создай новый чат и выполни инструкцию")
        print(f"  4. Сохрани результат в: cursor_results/result_{task_id}.txt")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
