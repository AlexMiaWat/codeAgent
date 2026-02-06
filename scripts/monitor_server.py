#!/usr/bin/env python3
"""
Скрипт для мониторинга работы Code Agent Server
"""

import json
import subprocess
import sys
from pathlib import Path

# Настройка UTF-8 для Windows консоли
if sys.platform == "win32":
    import codecs

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")


def load_checkpoint(checkpoint_file):
    """Загрузить checkpoint файл"""
    try:
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def is_server_process_running():
    """Проверить, запущен ли процесс сервера"""
    try:
        if sys.platform == "win32":
            # Windows: используем wmic для получения командных строк
            try:
                result = subprocess.run(
                    [
                        "wmic",
                        "process",
                        "where",
                        'name="python.exe"',
                        "get",
                        "CommandLine",
                        "/format:list",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    output = result.stdout
                    # Проверяем наличие src.server или server.py в командной строке
                    if "src.server" in output or (
                        "server.py" in output and "monitor_server.py" not in output
                    ):
                        return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback: проверяем через tasklist (менее надежно)
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # tasklist не показывает командные строки, поэтому всегда возвращаем None
                # чтобы использовать только checkpoint для определения статуса
                pass
        else:
            # Linux/Mac: используем ps
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Проверяем наличие процессов с src.server или server.py
                for line in result.stdout.split("\n"):
                    if "src.server" in line or "server.py" in line:
                        # Исключаем сам скрипт мониторинга
                        if "monitor_server.py" not in line:
                            return True
    except Exception:
        # Если не удалось проверить, возвращаем None (неизвестно)
        return None
    return False


def print_status(checkpoint_data):
    """Вывести статус сервера"""
    if not checkpoint_data:
        print("[X] Checkpoint файл недоступен")
        return

    server_state = checkpoint_data.get("server_state", {})
    tasks = checkpoint_data.get("tasks", [])

    # Проверяем реальное состояние процесса
    process_running = is_server_process_running()

    # Определяем статус на основе checkpoint и проверки процесса
    checkpoint_clean_shutdown = server_state.get("clean_shutdown", True)

    if process_running is True:
        status = "[RUNNING]"
        status_detail = "✅ Процесс запущен"
    elif process_running is False:
        if not checkpoint_clean_shutdown:
            status = "[STOPPED (unclean)]"
            status_detail = "⚠️ Процесс не запущен (некорректное завершение)"
        else:
            status = "[STOPPED]"
            status_detail = "✅ Процесс остановлен корректно"
    else:
        # Не удалось проверить процесс, используем только checkpoint
        if not checkpoint_clean_shutdown:
            status = "[UNKNOWN - checkpoint: running]"
            status_detail = "❓ Не удалось проверить процесс (checkpoint показывает running)"
        else:
            status = "[STOPPED]"
            status_detail = "✅ Checkpoint показывает остановку"

    # Статистика
    in_progress = len([t for t in tasks if t["state"] == "in_progress"])
    completed = len([t for t in tasks if t["state"] == "completed"])
    failed = len([t for t in tasks if t["state"] == "failed"])

    print("\n" + "=" * 80)
    print("CODE AGENT SERVER - MONITORING")
    print("=" * 80)
    print(f"Session: {checkpoint_data.get('session_id', 'N/A')}")
    print(f"Iteration: {server_state.get('iteration_count', 0)}")
    print(f"Started: {server_state.get('last_start_time', 'N/A')}")
    print(f"Status: {status}")
    print(f"         {status_detail}")
    print()
    print("TASK STATISTICS:")
    print(f"   In Progress: {in_progress}")
    print(f"   Completed: {completed}")
    print(f"   Failed: {failed}")
    print(f"   Total: {len(tasks)}")
    print()

    # Текущая задача
    current_task_id = checkpoint_data.get("current_task")
    if current_task_id:
        current_task = next((t for t in tasks if t["task_id"] == current_task_id), None)
        if current_task:
            print("CURRENT TASK:")
            print(f"   ID: {current_task['task_id']}")
            print(f"   Text: {current_task['task_text'][:80]}...")
            print(f"   State: {current_task['state']}")
            print(f"   Attempts: {current_task['attempts']}")
            print(f"   Started: {current_task.get('start_time', 'N/A')}")
            print()

    # Последние завершенные задачи
    completed_tasks = [t for t in tasks if t["state"] == "completed"]
    if completed_tasks:
        print("RECENTLY COMPLETED TASKS:")
        for task in completed_tasks[-3:]:
            print(f"   - {task['task_text'][:60]}... ({task.get('end_time', 'N/A')})")
        print()

    # Задачи с ошибками
    failed_tasks = [t for t in tasks if t["state"] == "failed"]
    if failed_tasks:
        print("FAILED TASKS:")
        for task in failed_tasks[-3:]:
            print(f"   - {task['task_text'][:60]}...")
            print(f"     Error: {task.get('error_message', 'N/A')[:80]}")
        print()

    print("=" * 80)


def tail_log(log_file, lines=10):
    """Показать последние строки лога"""
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            print("\nRECENT LOGS:")
            print("-" * 80)
            for line in last_lines:
                # Убираем ANSI escape коды для чистого вывода
                clean_line = line.rstrip()
                # Пытаемся вывести, игнорируя проблемы с кодировкой
                try:
                    print(clean_line)
                except UnicodeEncodeError:
                    print(clean_line.encode("ascii", errors="ignore").decode("ascii"))
            print("-" * 80)
    except Exception as e:
        print(f"[X] Error reading log: {e}")


def main():
    """Основная функция"""
    # Определяем пути
    # Checkpoint файлы теперь хранятся в каталоге codeAgent
    codeagent_dir = Path(__file__).parent.parent  # d:\Space\codeAgent
    checkpoint_file = codeagent_dir / "data" / ".codeagent_checkpoint.json"
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
