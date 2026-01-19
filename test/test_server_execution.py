#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки выполнения инструкции через Code Agent Server
"""

import sys
import os
import logging
from pathlib import Path
import subprocess

# Добавляем путь к src
# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cursor_cli_interface import CursorCLIInterface, create_cursor_cli_interface
from src.config_loader import ConfigLoader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_cursor_cli_execution():
    """Тест выполнения инструкции через Cursor CLI (Docker)"""
    
    print("=" * 80)
    print("ТЕСТ: Выполнение инструкции через Code Agent с Docker")
    print("=" * 80)
    
    # 1. Загрузка конфигурации
    print("\n1. Загрузка конфигурации...")
    try:
        config = ConfigLoader("config/config.yaml")
        project_dir = config.get_project_dir()
        print(f"   [OK] Проект: {project_dir}")
    except Exception as e:
        print(f"   [FAIL] Ошибка загрузки конфигурации: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. Проверка Docker контейнера при старте
    print("\n2. Проверка Docker контейнера при старте...")
    try:
        compose_file = Path(__file__).parent / "docker" / "docker-compose.agent.yml"
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"   [OK] Контейнер запущен: {result.stdout.strip()}")
            container_running = True
        else:
            print(f"   [INFO] Контейнер не запущен, будет запущен автоматически")
            container_running = False
    except Exception as e:
        print(f"   [WARN] Ошибка проверки контейнера: {e}")
        container_running = False
    
    # 3. Инициализация Cursor CLI интерфейса
    print("\n3. Инициализация Cursor CLI интерфейса...")
    try:
        cursor_config = config.get('cursor', {})
        cli_config = cursor_config.get('cli', {})
        cli_path = cli_config.get('cli_path')  # None - автоматический поиск
        
        cli = create_cursor_cli_interface(
            cli_path=cli_path,
            timeout=cli_config.get('timeout', 300),
            headless=cli_config.get('headless', True)
        )
        
        if cli and cli.is_available():
            print(f"   [OK] Cursor CLI доступен")
            print(f"   [OK] Команда: {cli.cli_command}")
            
            # Проверяем, используется ли Docker
            if cli.cli_command == "docker-compose-agent":
                print(f"   [OK] Используется Docker контейнер")
                
                # Проверяем статус контейнера после инициализации
                result = subprocess.run(
                    ["docker", "compose", "-f", str(compose_file), "ps"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    print(f"   [OK] Статус контейнера:")
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            print(f"        {line}")
            else:
                print(f"   [INFO] Используется локальный CLI: {cli.cli_command}")
        else:
            print(f"   [FAIL] Cursor CLI недоступен")
            return False
    except Exception as e:
        print(f"   [FAIL] Ошибка инициализации CLI: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Выполнение инструкции через Cursor CLI
    print("\n4. Выполнение инструкции через Cursor CLI...")
    instruction = '''Ты архитектор системы, проанализируй всю документацию - создай краткую выжимку по проекту в 50 строк, сохрани результат в docs/results/mini_docs_for_user.md'''
    
    print(f"   Инструкция: {instruction[:100]}...")
    print(f"   Рабочая директория: {project_dir}")
    
    try:
        result = cli.execute_instruction(
            instruction=instruction,
            task_id="test_instruction_001",
            working_dir=str(project_dir),
            timeout=1000  # 1000 секунд для выполнения задачи
        )
        
        if result.get("success"):
            print(f"   [OK] Инструкция выполнена успешно")
            print(f"   [OK] Return code: {result.get('return_code')}")
            
            stdout = result.get('stdout', '')
            if stdout:
                print(f"   [OK] Вывод (первые 500 символов):")
                print(f"   {stdout[:500]}")
            
            stderr = result.get('stderr', '')
            if stderr:
                print(f"   [WARN] Stderr: {stderr[:300]}")
        else:
            print(f"   [FAIL] Инструкция не выполнена")
            print(f"   [FAIL] Error: {result.get('error_message')}")
            print(f"   [FAIL] Return code: {result.get('return_code')}")
            return False
    except Exception as e:
        print(f"   [FAIL] Ошибка выполнения инструкции: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Проверка результата
    print("\n5. Проверка результата...")
    result_file = Path(project_dir) / "docs" / "results" / "mini_docs_for_user.md"
    
    if result_file.exists():
        print(f"   [OK] Файл результата создан: {result_file}")
        try:
            content = result_file.read_text(encoding='utf-8')
            print(f"   [OK] Размер файла: {len(content)} символов")
            print(f"   [OK] Количество строк: {len(content.splitlines())}")
            
            print(f"\n   Содержимое файла:")
            print("   " + "-" * 70)
            for i, line in enumerate(content.splitlines()[:60], 1):
                print(f"   {i:3d} | {line}")
            print("   " + "-" * 70)
        except Exception as e:
            print(f"   [WARN] Ошибка чтения файла: {e}")
    else:
        print(f"   [WARN] Файл результата не найден: {result_file}")
        print(f"   [INFO] Возможно, требуется больше времени для выполнения")
    
    # 6. Финальная проверка контейнера
    print("\n6. Финальная проверка Docker контейнера...")
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            if "cursor-agent-life" in result.stdout and "Up" in result.stdout:
                print(f"   [OK] Контейнер работает и готов к выполнению следующих задач")
            else:
                print(f"   [WARN] Контейнер остановлен или не найден")
    except Exception as e:
        print(f"   [WARN] Ошибка проверки контейнера: {e}")
    
    print("\n" + "=" * 80)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    test_cursor_cli_execution()
