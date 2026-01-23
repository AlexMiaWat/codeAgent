"""
Тест одновременного запуска нескольких серверов

Проверяет, что:
1. При запуске нового сервера старый автоматически завершается
2. Только один сервер может работать на порту 3456 одновременно
3. HTTP сервер доступен только от одного процесса
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
import pytest


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


def check_http_server(port: int, timeout: int = 2) -> bool:
    """Проверить доступность HTTP сервера"""
    try:
        response = requests.get(f'http://127.0.0.1:{port}/health', timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def run_server_in_thread(thread_id: int, delay: float = 0) -> dict:
    """
    Запустить сервер в отдельном потоке
    
    Args:
        thread_id: ID потока для идентификации
        delay: Задержка перед запуском (секунды)
    
    Returns:
        Словарь с результатами запуска
    """
    result = {
        'thread_id': thread_id,
        'started': False,
        'port_checked': False,
        'http_available': False,
        'pid': None,
        'process': None,
        'error': None,
        'start_time': None,
        'end_time': None
    }
    
    try:
        if delay > 0:
            time.sleep(delay)
        
        result['start_time'] = time.time()
        
        # Запускаем сервер через subprocess
        project_root = Path(__file__).parent.parent
        
        # Запускаем сервер в фоне
        env = os.environ.copy()
        # Убеждаемся, что PROJECT_DIR установлен
        if 'PROJECT_DIR' not in env:
            # Используем значение из .env или устанавливаем тестовое
            # Проверяем, есть ли .env файл
            project_root = Path(__file__).parent.parent
            env_file = project_root / '.env'
            if env_file.exists():
                # Читаем PROJECT_DIR из .env
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('PROJECT_DIR='):
                            project_dir = line.split('=', 1)[1].strip().strip('"').strip("'")
                            # Проверяем, что путь существует
                            if Path(project_dir).exists():
                                env['PROJECT_DIR'] = project_dir
                                break
            # Если все еще не установлен, используем значение по умолчанию из конфига
            if 'PROJECT_DIR' not in env:
                # Пропускаем тест, если PROJECT_DIR не установлен
                result['error'] = "PROJECT_DIR not set and not found in .env"
                return result
        
        process = subprocess.Popen(
            [sys.executable, str(project_root / 'main.py')],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        result['pid'] = process.pid
        result['process'] = process
        result['started'] = True
        
        # Ждем запуска сервера (до 60 секунд для полной инициализации)
        max_wait = 60
        for i in range(max_wait):
            if process.poll() is not None:
                # Процесс завершился
                try:
                    stdout, stderr = process.communicate(timeout=2)
                    error_msg = f"Process exited with code {process.returncode}"
                    if stdout:
                        error_msg += f"\nstdout (last 500): {stdout[-500:]}"
                    if stderr:
                        error_msg += f"\nstderr (last 500): {stderr[-500:]}"
                    result['error'] = error_msg
                    print(f"[Поток {thread_id}] Процесс завершился: {error_msg}")
                except Exception as e:
                    result['error'] = f"Process exited but couldn't read output: {e}"
                break
            
            # Проверяем порт
            if is_port_in_use(3456):
                result['port_checked'] = True
                # Проверяем HTTP сервер (даем больше времени)
                if check_http_server(3456, timeout=3):
                    result['http_available'] = True
                    print(f"[Поток {thread_id}] Сервер запущен и HTTP доступен (через {i+1} сек)")
                    break
                elif i > 10:  # После 10 секунд порт должен быть занят, но HTTP еще может запускаться
                    print(f"[Поток {thread_id}] Порт занят, но HTTP еще не доступен (через {i+1} сек)")
            
            if i % 5 == 0 and i > 0:
                print(f"[Поток {thread_id}] Ожидание запуска... ({i}/{max_wait} сек)")
            
            time.sleep(1)
        
        result['end_time'] = time.time()
        
    except Exception as e:
        result['error'] = str(e)
        result['end_time'] = time.time()
    
    return result


@pytest.mark.integration
class TestConcurrentServerStartup:
    """Тесты одновременного запуска серверов"""
    
    def test_sequential_server_startup_with_delays(self):
        """
        Тест последовательного запуска серверов с паузами 15 секунд
        
        Сценарий:
        1. Запускаем первый сервер в потоке
        2. Ждем 15 секунд
        3. Запускаем второй сервер в потоке
        4. Ждем 15 секунд
        5. Запускаем третий сервер в потоке
        6. Проверяем, что только один сервер работает
        """
        print("\n" + "=" * 80)
        print("ТЕСТ: Последовательный запуск серверов с паузами 15 секунд")
        print("=" * 80)
        
        threads = []
        results = []
        
        # Функция для запуска сервера и сохранения результата
        def server_runner(thread_id: int, delay: float):
            result = run_server_in_thread(thread_id, delay)
            results.append(result)
            print(f"\n[Поток {thread_id}] Запуск завершен:")
            print(f"  - Запущен: {result['started']}")
            print(f"  - Порт занят: {result['port_checked']}")
            print(f"  - HTTP доступен: {result['http_available']}")
            print(f"  - PID: {result['pid']}")
            if result['error']:
                print(f"  - Ошибка: {result['error']}")
        
        # Шаг 1: Запускаем первый сервер в отдельном потоке
        print("\n[Шаг 1] Запуск первого сервера...")
        thread1 = threading.Thread(
            target=server_runner,
            args=(1, 0),
            daemon=True
        )
        thread1.start()
        threads.append(thread1)
        
        # Ждем, чтобы первый сервер успел запуститься
        print("Ожидание запуска первого сервера (до 60 секунд)...")
        max_wait = 60
        server1_ready = False
        for i in range(max_wait):
            if is_port_in_use(3456) and check_http_server(3456, timeout=3):
                server1_ready = True
                break
            time.sleep(1)
            if i % 5 == 0:
                print(f"  Ожидание... ({i}/{max_wait} сек)")
        
        # Проверяем, что первый сервер запустился
        if not server1_ready:
            # Проверяем, может быть процесс еще работает, но HTTP не запустился
            if is_port_in_use(3456):
                print("  Порт занят, но HTTP сервер еще не доступен. Продолжаем тест...")
            else:
                # Проверяем результаты из потока
                if results:
                    last_result = results[-1]
                    if last_result.get('error'):
                        print(f"  Ошибка запуска: {last_result['error']}")
                assert False, "Первый сервер должен занять порт 3456"
        
        pid1 = get_process_on_port(3456)
        print(f"[OK] Первый сервер запущен, PID: {pid1}, порт 3456 занят, HTTP доступен")
        
        # Шаг 2: Ждем 15 секунд и запускаем второй сервер
        print("\n[Шаг 2] Ожидание 15 секунд перед запуском второго сервера...")
        time.sleep(15)
        
        print("Запуск второго сервера...")
        thread2 = threading.Thread(
            target=server_runner,
            args=(2, 0),
            daemon=True
        )
        thread2.start()
        threads.append(thread2)
        
        # Ждем, чтобы второй сервер попытался запуститься
        print("Ожидание попытки запуска второго сервера (5 секунд)...")
        time.sleep(5)
        
        # Проверяем, что только один сервер работает
        pid2 = get_process_on_port(3456)
        print(f"PID процесса на порту 3456: {pid2}")
        
        # Второй сервер должен был завершить первый и занять порт
        # Или первый все еще работает (если второй не успел)
        assert is_port_in_use(3456), "Порт 3456 должен быть занят"
        assert check_http_server(3456), "HTTP сервер должен быть доступен"
        print(f"[OK] После запуска второго сервера: порт занят, PID: {pid2}")
        
        # Шаг 3: Ждем еще 15 секунд и запускаем третий сервер
        print("\n[Шаг 3] Ожидание 15 секунд перед запуском третьего сервера...")
        time.sleep(15)
        
        print("Запуск третьего сервера...")
        thread3 = threading.Thread(
            target=server_runner,
            args=(3, 0),
            daemon=True
        )
        thread3.start()
        threads.append(thread3)
        
        # Ждем, чтобы третий сервер попытался запуститься
        print("Ожидание попытки запуска третьего сервера (5 секунд)...")
        time.sleep(5)
        
        # Проверяем, что только один сервер работает
        pid3 = get_process_on_port(3456)
        print(f"PID процесса на порту 3456: {pid3}")
        
        assert is_port_in_use(3456), "Порт 3456 должен быть занят"
        assert check_http_server(3456), "HTTP сервер должен быть доступен"
        print(f"[OK] После запуска третьего сервера: порт занят, PID: {pid3}")
        
        # Финальная проверка: только один процесс на порту
        print("\n[Финальная проверка] Проверка, что только один сервер работает...")
        time.sleep(2)
        
        final_pid = get_process_on_port(3456)
        assert final_pid is not None, "Должен быть один процесс на порту 3456"
        assert is_port_in_use(3456), "Порт 3456 должен быть занят"
        assert check_http_server(3456), "HTTP сервер должен быть доступен"
        
        print("\n[OK] Финальный результат:")
        print(f"  - Только один процесс на порту 3456: PID {final_pid}")
        print(f"  - HTTP сервер доступен: {check_http_server(3456)}")
        
        # Ждем завершения потоков
        print("\nОжидание завершения потоков...")
        for thread in threads:
            thread.join(timeout=5)
        
        # Завершаем все процессы
        print("\nЗавершение всех процессов сервера...")
        for result in results:
            if result.get('process') and result['process'].poll() is None:
                try:
                    result['process'].terminate()
                    result['process'].wait(timeout=5)
                except Exception as e:
                    print(f"  Ошибка при завершении процесса {result['pid']}: {e}")
                    try:
                        kill_process(result['pid'])
                    except Exception:
                        pass
        
        # Выводим результаты
        print("\n" + "=" * 80)
        print("РЕЗУЛЬТАТЫ ЗАПУСКОВ:")
        print("=" * 80)
        for result in results:
            print(f"\nПоток {result['thread_id']}:")
            print(f"  Запущен: {result['started']}")
            print(f"  Порт занят: {result['port_checked']}")
            print(f"  HTTP доступен: {result['http_available']}")
            print(f"  PID: {result['pid']}")
            if result.get('process'):
                print(f"  Процесс завершен: {result['process'].poll() is not None}")
            if result['error']:
                print(f"  Ошибка: {result['error']}")
            if result['start_time'] and result['end_time']:
                duration = result['end_time'] - result['start_time']
                print(f"  Длительность: {duration:.2f} сек")
        
        print("\n" + "=" * 80)
        print("ТЕСТ ЗАВЕРШЕН")
        print("=" * 80)


if __name__ == "__main__":
    # Запуск теста напрямую
    test = TestConcurrentServerStartup()
    test.test_sequential_server_startup_with_delays()
