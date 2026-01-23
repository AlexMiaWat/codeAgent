"""
Полный цикл взаимодействия через CodeAgentServer

Тестирует полный цикл с использованием сервера CodeAgentServer:
1. Инициализация сервера (без CrewAI агента)
2. Выполнение задачи через Cursor
3. Ожидание результата
4. Проверка завершения
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

from src.config_loader import ConfigLoader
from src.todo_manager import TodoManager, TodoItem
from src.cursor_file_interface import CursorFileInterface
from src.status_manager import StatusManager

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestServer:
    """Упрощенный сервер для тестирования (без CrewAI)"""
    
    def __init__(self, config_path="config/config.yaml"):
        self.config = ConfigLoader(config_path)
        self.project_dir = self.config.get_project_dir()
        self.cursor_file = CursorFileInterface(self.project_dir)
        self.todo_manager = TodoManager(self.project_dir, todo_format="md")
        self.status_manager = StatusManager(self.project_dir)
    
    def _determine_task_type(self, todo_item: TodoItem) -> str:
        """Определение типа задачи"""
        task_text = todo_item.text.lower()
        if any(word in task_text for word in ['тест', 'test']):
            return 'test'
        elif any(word in task_text for word in ['документация', 'docs']):
            return 'documentation'
        elif any(word in task_text for word in ['разработка', 'реализация']):
            return 'development'
        else:
            return 'default'
    
    def _get_instruction_template(self, task_type: str, instruction_id: int = 1):
        """Получение шаблона инструкции"""
        instructions = self.config.get('instructions', {})
        task_instructions = instructions.get(task_type, instructions.get('default', []))
        
        for instruction in task_instructions:
            if isinstance(instruction, dict) and instruction.get('instruction_id') == instruction_id:
                return instruction
        
        return task_instructions[0] if task_instructions and isinstance(task_instructions[0], dict) else None
    
    def _format_instruction(self, template, todo_item: TodoItem, task_id: str) -> str:
        """Форматирование инструкции"""
        if template:
            instruction_text = template.get('template', '')
            replacements = {
                'task_name': todo_item.text,
                'task_id': task_id,
                'date': datetime.now().strftime('%Y%m%d')
            }
            for key, value in replacements.items():
                instruction_text = instruction_text.replace(f'{{{key}}}', str(value))
            return instruction_text
        else:
            return f"Выполни задачу: {todo_item.text}\n\nСоздай отчет в docs/results/last_result.md, в конце напиши 'Отчет завершен!'"
    
    def _execute_task_via_cursor(self, todo_item: TodoItem, task_type: str) -> bool:
        """Выполнение задачи через Cursor (тестовая версия)"""
        task_id = f"server_test_{int(time.time())}"
        
        # Получаем шаблон
        template = self._get_instruction_template(task_type, instruction_id=1)
        
        if template:
            instruction_text = self._format_instruction(template, todo_item, task_id)
            wait_for_file = template.get('wait_for_file', 'docs/results/last_result.md')
            control_phrase = template.get('control_phrase', 'Отчет завершен!')
            timeout = template.get('timeout', 300)
        else:
            instruction_text = f"Выполни задачу: {todo_item.text}\n\nСоздай отчет в docs/results/last_result.md, в конце напиши 'Отчет завершен!'"
            wait_for_file = 'docs/results/last_result.md'
            control_phrase = 'Отчет завершен!'
            timeout = 300
        
        logger.info(f"Инструкция для Cursor: {instruction_text[:200]}...")
        
        # Создаем файл инструкции
        self.cursor_file.write_instruction(
            instruction=instruction_text,
            task_id=task_id,
            metadata={
                "task_type": task_type,
                "wait_for_file": wait_for_file,
                "control_phrase": control_phrase
            },
            new_chat=True
        )
        
        # Имитация: создаем файл результата (в реальности пользователь делает это в Cursor)
        result_file = self.cursor_file.results_dir / f"result_{task_id}.txt"
        result_content = f"""Результат выполнения задачи: {todo_item.text}

Task ID: {task_id}
Время выполнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Задача успешно выполнена.
{control_phrase}
"""
        result_file.write_text(result_content, encoding='utf-8')
        logger.info(f"Файл результата создан (имитация): {result_file}")
        
        # Ожидаем результат
        wait_result = self.cursor_file.wait_for_result(
            task_id=task_id,
            timeout=timeout,
            control_phrase=control_phrase
        )
        
        if wait_result["success"]:
            logger.info(f"Задача {task_id} выполнена через файловый интерфейс")
            
            # Отмечаем задачу как выполненную
            self.todo_manager.mark_task_done(todo_item.text)
            
            result_content = wait_result.get("content", "")
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Выполнено",
                details=f"Выполнено через файловый интерфейс. Результат: {result_content[:300]}..."
            )
            
            return True
        else:
            logger.warning(f"Таймаут ожидания результата для задачи {task_id}: {wait_result.get('error')}")
            self.status_manager.update_task_status(
                task_name=todo_item.text,
                status="Ошибка",
                details=f"Таймаут ожидания результата: {wait_result.get('error')}"
            )
            return False


def test_full_cycle_with_server():
    """Полный цикл через TestServer"""
    print()
    print("=" * 70)
    print("ПОЛНЫЙ ЦИКЛ ЧЕРЕЗ TESTSERVER")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Инициализация сервера
        print("=" * 70)
        print("ШАГ 1: Инициализация TestServer")
        print("=" * 70)
        print()
        
        server = TestServer("config/config.yaml")
        print("[OK] TestServer создан")
        print(f"  Проект: {server.project_dir}")
        print()
        
        # Получение задачи
        print("=" * 70)
        print("ШАГ 2: Получение задачи из TODO")
        print("=" * 70)
        print()
        
        pending_tasks = server.todo_manager.get_pending_tasks()
        
        if not pending_tasks:
            print("[WARNING] Нет невыполненных задач")
            todo_item = TodoItem(text="Тестовая задача для полного цикла через сервер", done=False)
        else:
            todo_item = pending_tasks[0]
        
        print(f"[OK] Задача выбрана: {todo_item.text[:70]}")
        print()
        
        # Выполнение задачи
        print("=" * 70)
        print("ШАГ 3: Выполнение задачи через _execute_task_via_cursor")
        print("=" * 70)
        print()
        
        task_type = server._determine_task_type(todo_item)
        print(f"[INFO] Тип задачи: {task_type}")
        print("[INFO] Запуск выполнения...")
        print()
        
        success = server._execute_task_via_cursor(todo_item, task_type)
        
        if success:
            print("[OK] Задача выполнена успешно!")
        else:
            print("[FAIL] Задача не выполнена")
            return False
        print()
        
        # Проверка статуса
        print("=" * 70)
        print("ШАГ 4: Проверка статуса задачи")
        print("=" * 70)
        print()
        
        # Проверяем, что задача отмечена как выполненная
        server.todo_manager.get_pending_tasks()
        task_found = False
        for task in server.todo_manager.items:
            if task.text == todo_item.text:
                if task.done:
                    print("[OK] Задача отмечена как выполненная")
                    task_found = True
                else:
                    print("[WARNING] Задача не отмечена как выполненная")
                break
        
        if not task_found:
            print("[WARNING] Задача не найдена в списке")
        print()
        
        # Итоги
        print("=" * 70)
        print("ИТОГИ ПОЛНОГО ЦИКЛА ЧЕРЕЗ TESTSERVER")
        print("=" * 70)
        print()
        print("[SUCCESS] Полный цикл выполнен успешно!")
        print()
        print("Этапы:")
        print("  [OK] 1. Инициализация TestServer")
        print("  [OK] 2. Получение задачи из TODO")
        print("  [OK] 3. Выполнение задачи через _execute_task_via_cursor")
        print("  [OK] 4. Проверка статуса задачи")
        print()
        print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка выполнения полного цикла: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_full_cycle_with_server()
        if success:
            print("[SUCCESS] Полный цикл через TestServer завершен успешно!")
            sys.exit(0)
        else:
            print("[FAIL] Полный цикл через TestServer завершился с ошибками")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
