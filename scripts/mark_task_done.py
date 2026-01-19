"""
Скрипт для отметки задачи как выполненной в TODO файле
"""
import sys
import os
from pathlib import Path

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

# Добавляем путь к src для импорта
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from todo_manager import TodoManager
from config_loader import ConfigLoader

def mark_task_done(task_text: str):
    """
    Отметить задачу как выполненную
    
    Args:
        task_text: Текст задачи для отметки
    """
    # Загружаем конфигурацию
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    config_loader = ConfigLoader(str(config_path))
    config = config_loader.config
    
    # Получаем директорию проекта
    project_dir = os.getenv('PROJECT_DIR')
    if not project_dir:
        # Пытаемся загрузить из .env файла
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('PROJECT_DIR='):
                        project_dir = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
    
    if not project_dir:
        print("ОШИБКА: PROJECT_DIR не установлен. Установите переменную окружения PROJECT_DIR или добавьте её в .env файл")
        return False
    
    project_dir = Path(project_dir)
    if not project_dir.exists():
        print(f"ОШИБКА: Директория проекта не найдена: {project_dir}")
        return False
    
    # Получаем формат TODO из конфигурации
    todo_format = config.get('project', {}).get('todo_format', 'md')
    
    # Создаем TodoManager
    todo_manager = TodoManager(project_dir, todo_format=todo_format)
    
    if not todo_manager.todo_file:
        print(f"ОШИБКА: TODO файл не найден в проекте: {project_dir}")
        print("Искались файлы: todo.md, TODO.md, todo.txt, TODO.txt, todo.yaml, CURRENT.md в todo/")
        return False
    
    print(f"Найден TODO файл: {todo_manager.todo_file}")
    
    # Ищем задачу
    found = False
    for item in todo_manager.items:
        if task_text.lower() in item.text.lower() or item.text.lower() in task_text.lower():
            if item.done:
                print(f"Задача уже отмечена как выполненная: {item.text}")
            else:
                item.done = True
                found = True
                print(f"✓ Задача отмечена как выполненная: {item.text}")
    
    if not found:
        print(f"ВНИМАНИЕ: Задача не найдена точно. Искали: '{task_text}'")
        print("\nДоступные задачи в TODO файле:")
        for item in todo_manager.items:
            status = "[x]" if item.done else "[ ]"
            print(f"  {status} {item.text}")
        
        # Попробуем найти частичное совпадение
        print("\nПопытка найти частичное совпадение...")
        task_lower = task_text.lower()
        for item in todo_manager.items:
            if "selfstate" in task_lower and "selfstate" in item.text.lower():
                if "цель 4" in task_lower or "goal 4" in task_lower:
                    if "цель 4" in item.text.lower() or "goal 4" in item.text.lower() or "4" in item.text:
                        if not item.done:
                            item.done = True
                            found = True
                            print(f"✓ Задача найдена по частичному совпадению и отмечена: {item.text}")
                            todo_manager._save_todos()
                            return True
        
        return False
    
    # Сохраняем изменения
    todo_manager._save_todos()
    print(f"\n✓ Изменения сохранены в файл: {todo_manager.todo_file}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python mark_task_done.py \"Текст задачи\"")
        print("\nПример:")
        print('  python mark_task_done.py "Улучшение SelfState согласно ROADMAP_2026.md, раздел \\"Цель 4\\""')
        sys.exit(1)
    
    task_text = sys.argv[1]
    success = mark_task_done(task_text)
    sys.exit(0 if success else 1)
