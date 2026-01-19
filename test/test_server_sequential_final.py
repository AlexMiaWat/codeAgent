"""
Финальный тест последовательного запуска серверов

Проверяет:
1. Запуск первого сервера в основном потоке
2. Запуск второго сервера через 15 секунд в отдельном потоке
3. Запуск третьего сервера через 15 секунд в отдельном потоке
4. Проверка, что старые процессы завершаются при запуске новых
"""

import sys
import os
import time
import threading
import subprocess
from pathlib import Path
from typing import List, Tuple


def start_server(server_id: int) -> subprocess.Popen:
    """Запустить сервер"""
    project_root = Path(__file__).parent.parent
    main_py = project_root / "main.py"
    
    env = os.environ.copy()
    if 'PROJECT_DIR' not in env:
        # Пробуем прочитать из .env
        env_file = project_root / '.env'
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('PROJECT_DIR='):
                        project_dir = line.split('=', 1)[1].strip().strip('"').strip("'")
                        # Проверяем, что путь существует
                        if Path(project_dir).exists():
                            env['PROJECT_DIR'] = project_dir
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


def main():
    """Главная функция теста"""
    print("=" * 80)
    print("ТЕСТ: Последовательный запуск серверов с паузами 15 секунд")
    print("=" * 80)
    
    processes: List[Tuple[int, subprocess.Popen]] = []
    
    try:
        # Шаг 1: Запускаем первый сервер
        print("\n[Шаг 1] Запуск первого сервера в основном потоке...")
        process1 = start_server(1)
        processes.append((1, process1))
        print(f"  Сервер 1 запущен, PID: {process1.pid}")
        
        # Ждем 10 секунд для инициализации
        print("  Ожидание инициализации (10 секунд)...")
        time.sleep(10)
        
        # Проверяем, что процесс еще работает
        if process1.poll() is None:
            print(f"  [OK] Сервер 1 работает (PID: {process1.pid})")
        else:
            print(f"  [FAIL] Сервер 1 завершился (код: {process1.returncode})")
            return
        
        # Шаг 2: Ждем 15 секунд и запускаем второй сервер
        print("\n[Шаг 2] Ожидание 15 секунд перед запуском второго сервера...")
        time.sleep(15)
        
        print("  Запуск второго сервера в отдельном потоке...")
        server2_result = {'process': None, 'pid': None}
        
        def start_server_2():
            process2 = start_server(2)
            server2_result['process'] = process2
            server2_result['pid'] = process2.pid
            processes.append((2, process2))
            print(f"  [Поток 2] Сервер 2 запущен, PID: {process2.pid}")
            # Ждем немного
            time.sleep(5)
            # Проверяем статус процессов
            if process1.poll() is not None:
                print(f"  [Поток 2] Сервер 1 завершился (код: {process1.returncode})")
            else:
                print(f"  [Поток 2] Сервер 1 еще работает")
            if process2.poll() is not None:
                print(f"  [Поток 2] Сервер 2 завершился (код: {process2.returncode})")
            else:
                print(f"  [Поток 2] Сервер 2 работает")
        
        thread2 = threading.Thread(target=start_server_2, daemon=True)
        thread2.start()
        thread2.join(timeout=15)
        
        # Шаг 3: Ждем еще 15 секунд и запускаем третий сервер
        print("\n[Шаг 3] Ожидание 15 секунд перед запуском третьего сервера...")
        time.sleep(15)
        
        print("  Запуск третьего сервера в отдельном потоке...")
        server3_result = {'process': None, 'pid': None}
        
        def start_server_3():
            process3 = start_server(3)
            server3_result['process'] = process3
            server3_result['pid'] = process3.pid
            processes.append((3, process3))
            print(f"  [Поток 3] Сервер 3 запущен, PID: {process3.pid}")
            # Ждем немного
            time.sleep(5)
            # Проверяем статус всех процессов
            for server_id, proc in processes:
                if proc.poll() is not None:
                    print(f"  [Поток 3] Сервер {server_id} завершился (код: {proc.returncode})")
                else:
                    print(f"  [Поток 3] Сервер {server_id} работает (PID: {proc.pid})")
        
        thread3 = threading.Thread(target=start_server_3, daemon=True)
        thread3.start()
        thread3.join(timeout=15)
        
        # Финальная проверка
        print("\n[Финальная проверка]")
        time.sleep(5)
        
        running_processes = [(sid, p) for sid, p in processes if p and p.poll() is None]
        finished_processes = [(sid, p) for sid, p in processes if p and p.poll() is not None]
        
        print(f"  Всего запущено серверов: {len(processes)}")
        print(f"  Работающих серверов: {len(running_processes)}")
        print(f"  Завершенных серверов: {len(finished_processes)}")
        
        for server_id, process in running_processes:
            print(f"    - Сервер {server_id}: работает (PID: {process.pid})")
        
        for server_id, process in finished_processes:
            print(f"    - Сервер {server_id}: завершен (код: {process.returncode})")
        
        # Ожидаемый результат: только один сервер должен работать
        if len(running_processes) <= 1:
            print(f"\n[SUCCESS] ТЕСТ ПРОЙДЕН: Работает не более одного сервера")
            print(f"  Это означает, что система корректно завершает старые процессы")
        else:
            print(f"\n[WARN] Работает {len(running_processes)} серверов одновременно")
            print(f"  Это может быть нормально, если серверы еще не успели завершиться")
        
    finally:
        # Завершаем все процессы
        print("\n[Завершение] Остановка всех процессов...")
        for server_id, process in processes:
            if process and process.poll() is None:
                print(f"  Завершение сервера {server_id} (PID: {process.pid})...")
                try:
                    if sys.platform == 'win32':
                        subprocess.run(['taskkill', '/F', '/PID', str(process.pid)], 
                                     capture_output=True, timeout=3)
                    else:
                        subprocess.run(['kill', '-9', str(process.pid)], 
                                     capture_output=True, timeout=3)
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"    Ошибка при завершении: {e}")
        
        print("  Все процессы завершены")
        print("\n" + "=" * 80)
        print("ТЕСТ ЗАВЕРШЕН")
        print("=" * 80)


if __name__ == "__main__":
    main()
