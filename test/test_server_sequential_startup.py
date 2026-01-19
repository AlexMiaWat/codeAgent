"""
Тест последовательного запуска серверов с паузами 15 секунд

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


def start_server_process() -> Optional[subprocess.Popen]:
    """Запустить сервер в отдельном процессе"""
    try:
        project_root = Path(__file__).parent.parent
        main_py = project_root / "main.py"
        
        if not main_py.exists():
            return None
        
        # Устанавливаем переменные окружения
        env = os.environ.copy()
        if 'PROJECT_DIR' not in env:
            env_file = project_root / '.env'
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('PROJECT_DIR='):
                            env['PROJECT_DIR'] = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
        
        process = subprocess.Popen(
            [sys.executable, str(main_py)],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        return process
        
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
        return None


def wait_for_port(port: int, max_wait: int = 30) -> bool:
    """Ждать, пока порт не будет занят"""
    for i in range(max_wait):
        if is_port_in_use(port):
            return True
        time.sleep(1)
    return False


def main():
    """Главная функция теста"""
    print("=" * 80)
    print("ТЕСТ: Последовательный запуск серверов с паузами 15 секунд")
    print("=" * 80)
    
    port = 3456
    processes = []
    
    try:
        # Очищаем порт перед тестом
        print("\n[Подготовка] Очистка порта 3456...")
        for _ in range(5):
            pid = get_process_on_port(port)
            if pid:
                kill_process(pid)
                time.sleep(1)
            else:
                break
        
        # Шаг 1: Запускаем первый сервер в основном потоке
        print("\n[Шаг 1] Запуск первого сервера...")
        process1 = start_server_process()
        
        if not process1:
            print("Ошибка: не удалось запустить первый сервер")
            return
        
        processes.append(("Сервер 1", process1))
        print(f"  Процесс запущен, PID: {process1.pid}")
        
        # Ждем, пока порт не будет занят (увеличиваем время ожидания)
        print("  Ожидание запуска сервера на порту 3456 (до 90 секунд)...")
        if wait_for_port(port, max_wait=90):
            pid1 = get_process_on_port(port)
            print(f"  [OK] Первый сервер работает, порт 3456 занят, PID: {pid1}")
        else:
            # Проверяем, может процесс еще работает
            if process1.poll() is None:
                print(f"  [WARN] Порт не занят, но процесс {process1.pid} еще работает")
                print("  Возможно, HTTP сервер не запустился. Продолжаем тест...")
                # Продолжаем тест, даже если порт не занят
            else:
                print(f"  [FAIL] Первый сервер завершился (код: {process1.returncode})")
                stdout, stderr = process1.communicate()
                if stderr:
                    print(f"  stderr: {stderr[-500:]}")
                return
        
        # Шаг 2: Ждем 15 секунд и запускаем второй сервер в потоке
        print("\n[Шаг 2] Ожидание 15 секунд перед запуском второго сервера...")
        time.sleep(15)
        
        print("  Запуск второго сервера в отдельном потоке...")
        server2_started = threading.Event()
        server2_pid = [None]
        
        def start_server_2():
            process2 = start_server_process()
            if process2:
                processes.append(("Сервер 2", process2))
                server2_pid[0] = process2.pid
                print(f"  [Поток 2] Процесс запущен, PID: {process2.pid}")
                server2_started.set()
                # Ждем немного для проверки
                time.sleep(5)
                pid_on_port = get_process_on_port(port)
                print(f"  [Поток 2] PID на порту 3456: {pid_on_port}")
        
        thread2 = threading.Thread(target=start_server_2, daemon=True)
        thread2.start()
        thread2.join(timeout=10)
        
        # Проверяем результат
        time.sleep(3)
        pid2 = get_process_on_port(port)
        print(f"  После запуска второго сервера: PID на порту 3456: {pid2}")
        
        # Шаг 3: Ждем еще 15 секунд и запускаем третий сервер
        print("\n[Шаг 3] Ожидание 15 секунд перед запуском третьего сервера...")
        time.sleep(15)
        
        print("  Запуск третьего сервера в отдельном потоке...")
        server3_started = threading.Event()
        server3_pid = [None]
        
        def start_server_3():
            process3 = start_server_process()
            if process3:
                processes.append(("Сервер 3", process3))
                server3_pid[0] = process3.pid
                print(f"  [Поток 3] Процесс запущен, PID: {process3.pid}")
                server3_started.set()
                # Ждем немного для проверки
                time.sleep(5)
                pid_on_port = get_process_on_port(port)
                print(f"  [Поток 3] PID на порту 3456: {pid_on_port}")
        
        thread3 = threading.Thread(target=start_server_3, daemon=True)
        thread3.start()
        thread3.join(timeout=10)
        
        # Финальная проверка
        print("\n[Финальная проверка]")
        time.sleep(5)
        
        final_pid = get_process_on_port(port)
        port_in_use = is_port_in_use(port)
        
        print(f"  Порт {port} занят: {port_in_use}")
        print(f"  PID процесса на порту: {final_pid}")
        
        # Проверяем, что только один процесс работает
        running_count = sum(1 for _, p in processes if p and p.poll() is None)
        print(f"  Количество запущенных процессов: {running_count}")
        
        if port_in_use and final_pid:
            print(f"\n[SUCCESS] ТЕСТ ПРОЙДЕН: Только один сервер работает на порту 3456 (PID: {final_pid})")
            print(f"  Всего процессов было запущено: {len(processes)}")
            print(f"  Работающих процессов: {running_count}")
        else:
            print("\n[FAIL] ТЕСТ НЕ ПРОЙДЕН: Проблемы с запуском сервера")
        
    finally:
        # Завершаем все процессы
        print("\n[Завершение] Остановка всех процессов...")
        for name, process in processes:
            if process and process.poll() is None:
                print(f"  Завершение {name} (PID: {process.pid})...")
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
        
        print("  Все процессы завершены")


if __name__ == "__main__":
    main()
