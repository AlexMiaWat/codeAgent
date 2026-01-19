"""
Упрощенный тест запуска сервера с паузами

Запускает:
1. Первый сервер в одном потоке
2. Затем несколько раз новый сервер в разных потоках с паузой 15 сек
"""

import sys
import os
import time
import socket
import threading
import subprocess
import requests
from pathlib import Path
from typing import Optional


def is_port_in_use(port: int) -> bool:
    """Проверка, занят ли порт"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except Exception:
        return False


def check_http_server(port: int, timeout: int = 2) -> bool:
    """Проверить доступность HTTP сервера"""
    try:
        response = requests.get(f'http://127.0.0.1:{port}/health', timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def get_process_on_port(port: int) -> Optional[int]:
    """Получить PID процесса на порту"""
    try:
        if sys.platform == 'win32':
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            try:
                                return int(parts[-1])
                            except ValueError:
                                pass
        else:
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return int(result.stdout.strip().split('\n')[0])
                except ValueError:
                    pass
    except Exception:
        pass
    return None


def kill_process(pid: int) -> bool:
    """Завершить процесс по PID"""
    try:
        if sys.platform == 'win32':
            subprocess.run(
                ['taskkill', '/F', '/PID', str(pid)],
                capture_output=True,
                timeout=3
            )
        else:
            subprocess.run(
                ['kill', '-9', str(pid)],
                capture_output=True,
                timeout=3
            )
        return True
    except Exception:
        return False


def start_server(server_id: int) -> Optional[subprocess.Popen]:
    """Запустить сервер"""
    try:
        project_root = Path(__file__).parent.parent
        main_py = project_root / "main.py"
        
        if not main_py.exists():
            print(f"[Сервер {server_id}] main.py не найден")
            return None
        
        # Устанавливаем переменные окружения
        env = os.environ.copy()
        if 'PROJECT_DIR' not in env:
            # Пробуем прочитать из .env
            env_file = project_root / '.env'
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('PROJECT_DIR='):
                            env['PROJECT_DIR'] = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
        
        print(f"[Сервер {server_id}] Запуск сервера...")
        process = subprocess.Popen(
            [sys.executable, str(main_py)],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        print(f"[Сервер {server_id}] Процесс запущен, PID: {process.pid}")
        return process
        
    except Exception as e:
        print(f"[Сервер {server_id}] Ошибка запуска: {e}")
        return None


def wait_for_server(port: int, max_wait: int = 60) -> bool:
    """Ждать запуска сервера на порту"""
    for i in range(max_wait):
        if is_port_in_use(port) and check_http_server(port, timeout=2):
            print(f"  ✓ Сервер запущен на порту {port} (через {i+1} сек)")
            return True
        time.sleep(1)
        if i % 5 == 0 and i > 0:
            print(f"  Ожидание... ({i}/{max_wait} сек)")
    return False


def main():
    """Главная функция теста"""
    print("=" * 80)
    print("ТЕСТ: Последовательный запуск серверов с паузами 15 секунд")
    print("=" * 80)
    
    port = 3456
    processes = []
    
    try:
        # Шаг 1: Запускаем первый сервер
        print("\n[Шаг 1] Запуск первого сервера в основном потоке...")
        process1 = start_server(1)
        
        if not process1:
            print("Ошибка: не удалось запустить первый сервер")
            return
        
        processes.append((1, process1))
        
        # Ждем запуска первого сервера
        print("Ожидание запуска первого сервера...")
        if not wait_for_server(port, max_wait=60):
            print("Ошибка: первый сервер не запустился")
            return
        
        pid1 = get_process_on_port(port)
        print(f"✓ Первый сервер работает, PID: {pid1}")
        
        # Шаг 2: Ждем 15 секунд и запускаем второй сервер в потоке
        print("\n[Шаг 2] Ожидание 15 секунд перед запуском второго сервера...")
        time.sleep(15)
        
        print("Запуск второго сервера в отдельном потоке...")
        
        def start_server_2():
            process2 = start_server(2)
            if process2:
                processes.append((2, process2))
                # Ждем немного
                time.sleep(5)
                pid2 = get_process_on_port(port)
                print(f"[Поток 2] PID на порту: {pid2}")
        
        thread2 = threading.Thread(target=start_server_2, daemon=True)
        thread2.start()
        thread2.join(timeout=10)
        
        # Шаг 3: Ждем еще 15 секунд и запускаем третий сервер
        print("\n[Шаг 3] Ожидание 15 секунд перед запуском третьего сервера...")
        time.sleep(15)
        
        print("Запуск третьего сервера в отдельном потоке...")
        
        def start_server_3():
            process3 = start_server(3)
            if process3:
                processes.append((3, process3))
                # Ждем немного
                time.sleep(5)
                pid3 = get_process_on_port(port)
                print(f"[Поток 3] PID на порту: {pid3}")
        
        thread3 = threading.Thread(target=start_server_3, daemon=True)
        thread3.start()
        thread3.join(timeout=10)
        
        # Финальная проверка
        print("\n[Финальная проверка]")
        time.sleep(5)
        
        final_pid = get_process_on_port(port)
        port_in_use = is_port_in_use(port)
        http_available = check_http_server(port, timeout=2)
        
        print(f"  Порт {port} занят: {port_in_use}")
        print(f"  HTTP сервер доступен: {http_available}")
        print(f"  PID процесса на порту: {final_pid}")
        
        if port_in_use and http_available:
            print("\n✓ ТЕСТ ПРОЙДЕН: Только один сервер работает на порту 3456")
        else:
            print("\n✗ ТЕСТ НЕ ПРОЙДЕН: Проблемы с запуском сервера")
        
    finally:
        # Завершаем все процессы
        print("\nЗавершение всех процессов...")
        for server_id, process in processes:
            if process and process.poll() is None:
                print(f"  Завершение сервера {server_id} (PID: {process.pid})...")
                kill_process(process.pid)
                try:
                    process.wait(timeout=5)
                except:
                    pass
        
        # Очищаем порт
        for _ in range(10):
            pid = get_process_on_port(port)
            if pid:
                kill_process(pid)
                time.sleep(1)
            else:
                break
        
        print("Все процессы завершены")


if __name__ == "__main__":
    main()
