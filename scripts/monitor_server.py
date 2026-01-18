#!/usr/bin/env python3
"""
Скрипт для мониторинга работы Code Agent Server
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime

# Настройка UTF-8 для Windows консоли
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')

def load_checkpoint(checkpoint_file):
    """Загрузить checkpoint файл"""
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None

def print_status(checkpoint_data):
    """Вывести статус сервера"""
    if not checkpoint_data:
        print("[X] Checkpoint файл недоступен")
        return
    
    server_state = checkpoint_data.get('server_state', {})
    tasks = checkpoint_data.get('tasks', [])
    
    # Статистика
    in_progress = len([t for t in tasks if t['state'] == 'in_progress'])
    completed = len([t for t in tasks if t['state'] == 'completed'])
    failed = len([t for t in tasks if t['state'] == 'failed'])
    
    print("\n" + "="*80)
    print("CODE AGENT SERVER - MONITORING")
    print("="*80)
    print(f"Session: {checkpoint_data.get('session_id', 'N/A')}")
    print(f"Iteration: {server_state.get('iteration_count', 0)}")
    print(f"Started: {server_state.get('last_start_time', 'N/A')}")
    print(f"Status: {'[RUNNING]' if not server_state.get('clean_shutdown', True) else '[STOPPED]'}")
    print()
    print(f"TASK STATISTICS:")
    print(f"   In Progress: {in_progress}")
    print(f"   Completed: {completed}")
    print(f"   Failed: {failed}")
    print(f"   Total: {len(tasks)}")
    print()
    
    # Текущая задача
    current_task_id = checkpoint_data.get('current_task')
    if current_task_id:
        current_task = next((t for t in tasks if t['task_id'] == current_task_id), None)
        if current_task:
            print(f"CURRENT TASK:")
            print(f"   ID: {current_task['task_id']}")
            print(f"   Text: {current_task['task_text'][:80]}...")
            print(f"   State: {current_task['state']}")
            print(f"   Attempts: {current_task['attempts']}")
            print(f"   Started: {current_task.get('start_time', 'N/A')}")
            print()
    
    # Последние завершенные задачи
    completed_tasks = [t for t in tasks if t['state'] == 'completed']
    if completed_tasks:
        print(f"RECENTLY COMPLETED TASKS:")
        for task in completed_tasks[-3:]:
            print(f"   - {task['task_text'][:60]}... ({task.get('end_time', 'N/A')})")
        print()
    
    # Задачи с ошибками
    failed_tasks = [t for t in tasks if t['state'] == 'failed']
    if failed_tasks:
        print(f"FAILED TASKS:")
        for task in failed_tasks[-3:]:
            print(f"   - {task['task_text'][:60]}...")
            print(f"     Error: {task.get('error_message', 'N/A')[:80]}")
        print()
    
    print("="*80)

def tail_log(log_file, lines=10):
    """Показать последние строки лога"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            print("\nRECENT LOGS:")
            print("-"*80)
            for line in last_lines:
                # Убираем ANSI escape коды для чистого вывода
                clean_line = line.rstrip()
                # Пытаемся вывести, игнорируя проблемы с кодировкой
                try:
                    print(clean_line)
                except UnicodeEncodeError:
                    print(clean_line.encode('ascii', errors='ignore').decode('ascii'))
            print("-"*80)
    except Exception as e:
        print(f"[X] Error reading log: {e}")

def main():
    """Основная функция"""
    # Определяем пути
    # Checkpoint файлы теперь хранятся в каталоге codeAgent
    codeagent_dir = Path(__file__).parent.parent  # d:\Space\codeAgent
    checkpoint_file = codeagent_dir / ".codeagent_checkpoint.json"
    log_file = codeagent_dir / "logs" / "code_agent.log"
    
    # Проверяем наличие файлов
    if not checkpoint_file.exists():
        print(f"[X] Checkpoint file not found: {checkpoint_file}")
        return
    
    # Загружаем и выводим статус
    checkpoint_data = load_checkpoint(checkpoint_file)
    print_status(checkpoint_data)
    
    # Показываем последние логи
    if log_file.exists():
        tail_log(log_file, lines=15)
    
    print("\n[TIP] For continuous monitoring run:")
    print("   watch -n 5 python scripts/monitor_server.py")
    print("   or: while true; do python scripts/monitor_server.py; sleep 5; done")

if __name__ == "__main__":
    main()
