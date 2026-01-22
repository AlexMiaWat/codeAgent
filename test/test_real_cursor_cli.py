"""
Реальное тестирование Cursor CLI на целевом проекте

План:
1. Придумать простую корректную задачу для D:\Space\your-project
2. Сформировать инструкцию для Cursor
3. Выполнить через cursor.CMD -p "инструкция"
4. Проверить результат выполнения
5. Проанализировать и внести коррективы
"""

import sys
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import ConfigLoader
from src.cursor_cli_interface import CursorCLIInterface, create_cursor_cli_interface
from src.cursor_file_interface import CursorFileInterface

# Импорт вспомогательных функций для загрузки настроек
from test_utils import get_container_name

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_real_cursor_cli():
    """Реальное тестирование Cursor CLI на целевом проекте"""
    print()
    print("=" * 70)
    print("РЕАЛЬНОЕ ТЕСТИРОВАНИЕ CURSOR CLI НА ЦЕЛЕВОМ ПРОЕКТЕ")
    print("=" * 70)
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Шаг 1: Загрузка конфигурации
        print("=" * 70)
        print("ШАГ 1: Загрузка конфигурации")
        print("=" * 70)
        print()
        
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        print(f"[OK] Проект: {project_dir}")
        print()
        
        # Шаг 2: Проверка Cursor CLI
        print("=" * 70)
        print("ШАГ 2: Проверка Cursor CLI")
        print("=" * 70)
        print()
        
        cli = create_cursor_cli_interface(timeout=600, headless=True)
        
        if not cli.is_available():
            print("[FAIL] Cursor CLI недоступен!")
            return False
        
        version = cli.check_version()
        print(f"[OK] Cursor CLI доступен")
        print(f"  Версия: {version}")
        print(f"  Команда: {cli.cli_command}")
        
        # Проверяем статус Docker контейнера если используется Docker
        if cli.cli_command == "docker-compose-agent":
            print()
            print("[INFO] Проверка Docker контейнера...")
            try:
                import subprocess
                import json
                
                # Проверяем статус контейнера
                inspect_result = subprocess.run(
                    ["docker", "inspect", "--format", "{{json .State}}", get_container_name()],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if inspect_result.returncode == 0:
                    state = json.loads(inspect_result.stdout.strip())
                    status = state.get("Status", "unknown")
                    running = status == "running"
                    
                    if running:
                        print(f"  [OK] Контейнер {get_container_name()} запущен (статус: {status})")
                        if state.get("StartedAt"):
                            print(f"  [INFO] Запущен: {state.get('StartedAt', '')[:19]}")
                    else:
                        print(f"  [WARNING] Контейнер {get_container_name()} не запущен (статус: {status})")
                        if state.get("Error"):
                            print(f"  [ERROR] Ошибка: {state.get('Error')}")
                else:
                    print(f"  [INFO] Контейнер {get_container_name()} не найден (будет создан автоматически)")
            except Exception as e:
                print(f"  [WARNING] Не удалось проверить статус контейнера: {e}")
        
        print()
        
        # Шаг 3: Формирование простой задачи для целевого проекта
        print("=" * 70)
        print("ШАГ 3: Формирование задачи для тестирования")
        print("=" * 70)
        print()
        
        # Простая задача: создать тестовый файл с информацией о проекте
        task_id = f"cursor_cli_test_{int(time.time())}"
        
        instruction = f"""Выполни простую задачу в проекте:

1. Проверь наличие файла README.md в корне проекта {project_dir}
2. Если файла нет - создай базовый README.md с названием проекта
3. Если файл есть - проверь его содержимое
4. Создай файл docs/results/cursor_cli_test_{task_id}.md с отчетом о выполнении
5. В конце отчета напиши "Задача выполнена!"

Важно: работай в контексте проекта {project_dir}, все пути относительные от корня проекта.
"""
        
        print(f"[OK] Инструкция сформирована")
        print(f"  Task ID: {task_id}")
        print(f"  Длина инструкции: {len(instruction)} символов")
        print()
        print("Инструкция для Cursor:")
        print("-" * 70)
        print(instruction)
        print("-" * 70)
        print()
        
        # Шаг 4: Выполнение через Cursor CLI
        print("=" * 70)
        print("ШАГ 4: Выполнение через Cursor CLI")
        print("=" * 70)
        print()
        
        print("[INFO] Запуск команды Cursor CLI...")
        print(f"  Команда: {cli.cli_command} -p \"[инструкция]\" --new-chat --cwd {project_dir}")
        print()
        print("[WARNING] Это займет некоторое время...")
        print()
        
        # Выполняем через CLI
        result = cli.execute(
            prompt=instruction,
            working_dir=str(project_dir),
            timeout=600,  # 10 минут для выполнения
            new_chat=True
        )
        
        print(f"[INFO] Команда выполнена")
        print(f"  Success: {result.success}")
        print(f"  Return code: {result.return_code}")
        print(f"  CLI available: {result.cli_available}")
        
        if result.error_message:
            print(f"  Error: {result.error_message}")
        
        # Проверяем статус контейнера после выполнения (если используется Docker)
        if cli.cli_command == "docker-compose-agent":
            print()
            print("[INFO] Проверка Docker контейнера после выполнения...")
            try:
                import subprocess
                import json
                
                inspect_result = subprocess.run(
                    ["docker", "inspect", "--format", "{{json .State}}", get_container_name()],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if inspect_result.returncode == 0:
                    state = json.loads(inspect_result.stdout.strip())
                    status = state.get("Status", "unknown")
                    running = status == "running"
                    
                    if running:
                        print(f"  [OK] Контейнер активен (статус: {status})")
                    else:
                        print(f"  [WARNING] Контейнер не активен (статус: {status})")
                        # Показываем последние логи
                        logs_result = subprocess.run(
                            ["docker", "logs", "--tail", "10", get_container_name()],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if logs_result.returncode == 0 and logs_result.stdout.strip():
                            print(f"  [INFO] Последние логи контейнера:")
                            for line in logs_result.stdout.strip().split('\n')[-5:]:
                                if line.strip():
                                    print(f"    {line[:100]}")
            except Exception as e:
                print(f"  [WARNING] Не удалось проверить статус контейнера: {e}")
        
        print()
        
        if result.stdout:
            print("STDOUT (первые 500 символов):")
            print("-" * 70)
            print(result.stdout[:500])
            if len(result.stdout) > 500:
                print("  ... (обрезано)")
            print("-" * 70)
            print()
        
        if result.stderr:
            print("STDERR (первые 500 символов):")
            print("-" * 70)
            print(result.stderr[:500])
            if len(result.stderr) > 500:
                print("  ... (обрезано)")
            print("-" * 70)
            print()
        
        # Шаг 5: Проверка результата
        print("=" * 70)
        print("ШАГ 5: Проверка результата выполнения")
        print("=" * 70)
        print()
        
        # Проверяем ожидаемый файл результата
        result_file = project_dir / f"docs/results/cursor_cli_test_{task_id}.md"
        readme_file = project_dir / "README.md"
        
        print("Проверка файлов:")
        print()
        
        if result_file.exists():
            print(f"[OK] Файл результата найден: {result_file}")
            try:
                content = result_file.read_text(encoding='utf-8')
                print(f"  Размер: {len(content)} символов")
                print()
                print("Содержимое файла результата:")
                print("-" * 70)
                print(content[:1000])
                if len(content) > 1000:
                    print("  ... (обрезано)")
                print("-" * 70)
                
                # Проверяем контрольную фразу
                if "Задача выполнена!" in content:
                    print()
                    print("[OK] Контрольная фраза найдена: 'Задача выполнена!'")
                else:
                    print()
                    print("[WARNING] Контрольная фраза не найдена")
            except Exception as e:
                print(f"  [ERROR] Ошибка чтения файла: {e}")
        else:
            print(f"[WARNING] Файл результата не найден: {result_file}")
        
        print()
        
        if readme_file.exists():
            print(f"[OK] README.md существует")
            try:
                readme_content = readme_file.read_text(encoding='utf-8')
                print(f"  Размер: {len(readme_content)} символов")
                print()
                print("Содержимое README.md (первые 500 символов):")
                print("-" * 70)
                print(readme_content[:500])
                if len(readme_content) > 500:
                    print("  ... (обрезано)")
                print("-" * 70)
            except Exception as e:
                print(f"  [ERROR] Ошибка чтения README.md: {e}")
        else:
            print(f"[INFO] README.md не найден (возможно, был создан)")
        
        print()
        
        # Шаг 6: Анализ результата
        print("=" * 70)
        print("ШАГ 6: Анализ результата")
        print("=" * 70)
        print()
        
        if result.success:
            print("[OK] Команда Cursor CLI выполнена успешно")
        else:
            print("[WARNING] Команда Cursor CLI завершилась с ошибкой")
        
        if result_file.exists():
            print("[OK] Файл результата создан - Cursor выполнил задачу")
        else:
            print("[WARNING] Файл результата не создан - возможно, задача не выполнена")
        
        print()
        print("Выводы:")
        print("  1. Cursor CLI " + ("РАБОТАЕТ" if result.success else "НЕ РАБОТАЕТ автоматически"))
        print("  2. Задача " + ("ВЫПОЛНЕНА" if result_file.exists() else "НЕ ВЫПОЛНЕНА"))
        print()
        
        # Итоги
        print("=" * 70)
        print("ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 70)
        print()
        print(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if result.success and result_file.exists():
            print("[SUCCESS] Cursor CLI работает и выполняет задачи!")
        elif result.success and not result_file.exists():
            print("[WARNING] Cursor CLI выполнился, но файл результата не создан")
            print("  Возможно, нужно больше времени или другая инструкция")
        else:
            print("[WARNING] Cursor CLI может не поддерживать автоматическое выполнение")
            print("  Требуется дополнительное тестирование или использование файлового интерфейса")
        print()
        
        return result.success and result_file.exists()
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_real_cursor_cli()
        if success:
            print("[SUCCESS] Тестирование Cursor CLI завершено успешно!")
            sys.exit(0)
        else:
            print("[WARNING] Тестирование завершилось с предупреждениями")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
