#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование API сервера (сервер должен быть уже запущен)
"""

import sys
import time
import requests
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://127.0.0.1:3456"


def test_health():
    """Тест health endpoint"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Health Endpoint")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("[OK] Health check успешен")
            print(f"   Статус: {data.get('status')}")
            print(f"   Время: {data.get('timestamp')}")
            return True
        else:
            print(f"[FAIL] Health check вернул код: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Ошибка health check: {e}")
        return False


def test_root():
    """Тест root endpoint"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Root Endpoint")
    print("=" * 80)
    
    # Пробуем несколько раз с увеличивающимся таймаутом
    for attempt in range(3):
        try:
            timeout = 10 + (attempt * 5)  # 10, 15, 20 секунд
            response = requests.get(f"{BASE_URL}/", timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                print("[OK] Root endpoint успешен")
                print(f"   Статус: {data.get('status')}")
                print(f"   Порт: {data.get('port')}")
                print(f"   Сессия: {data.get('session_id')}")
                return True
            else:
                print(f"[FAIL] Root endpoint вернул код: {response.status_code}")
                return False
        except requests.exceptions.Timeout:
            if attempt < 2:
                print(f"[WARN] Таймаут при попытке {attempt + 1}, повторяем с таймаутом {10 + ((attempt + 1) * 5)} сек...")
                time.sleep(2)
                continue
            else:
                print(f"[FAIL] Таймаут root endpoint после 3 попыток")
                return False
        except Exception as e:
            print(f"[FAIL] Ошибка root endpoint: {e}")
            return False
    return False


def test_status():
    """Тест status endpoint"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Status Endpoint")
    print("=" * 80)
    
    # Пробуем несколько раз с увеличивающимся таймаутом
    # Сервер может перезагружаться во время теста из-за file watcher
    for attempt in range(5):
        try:
            timeout = 10 + (attempt * 5)  # 10, 15, 20, 25, 30 секунд
            response = requests.get(f"{BASE_URL}/status", timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                print("[OK] Status получен успешно")
                
                server_info = data.get('server', {})
                print(f"   Статус сервера: {server_info.get('status')}")
                print(f"   Проект: {server_info.get('project_dir')}")
                print(f"   Cursor CLI доступен: {server_info.get('cursor_cli_available')}")
                
                tasks_info = data.get('tasks', {})
                print(f"   Задач всего: {tasks_info.get('total', 0)}")
                print(f"   В процессе: {tasks_info.get('in_progress', 0)}")
                print(f"   Выполнено: {tasks_info.get('completed', 0)}")
                print(f"   Ошибок: {tasks_info.get('failed', 0)}")
                print(f"   Ожидает: {tasks_info.get('pending', 0)}")
                
                return True
            else:
                print(f"[WARN] Status endpoint вернул код: {response.status_code}, повторяем...")
                if attempt < 4:
                    time.sleep(3)
                    continue
                else:
                    return False
        except requests.exceptions.ConnectionError:
            # Сервер может перезагружаться - ждем и повторяем
            if attempt < 4:
                wait_time = 5 + (attempt * 2)
                print(f"[WARN] Сервер недоступен (возможно перезагрузка), ждем {wait_time} сек и повторяем (попытка {attempt + 1}/5)...")
                time.sleep(wait_time)
                continue
            else:
                print(f"[FAIL] Сервер недоступен после 5 попыток")
                return False
        except requests.exceptions.Timeout:
            if attempt < 4:
                print(f"[WARN] Таймаут при попытке {attempt + 1}, повторяем с таймаутом {10 + ((attempt + 1) * 5)} сек...")
                time.sleep(2)
                continue
            else:
                print(f"[FAIL] Таймаут status endpoint после 5 попыток")
                return False
        except Exception as e:
            if attempt < 4:
                print(f"[WARN] Ошибка при получении status: {e}, повторяем...")
                time.sleep(3)
                continue
            else:
                print(f"[FAIL] Ошибка получения status: {e}")
                return False
    return False


def wait_for_server(max_wait: int = 300, server_process=None) -> bool:
    """Ожидание запуска сервера с проверкой /health
    
    Args:
        max_wait: Максимальное время ожидания в секундах
        server_process: Опциональный процесс сервера для проверки завершения
    """
    print(f"[INFO] Ожидание запуска сервера (макс. {max_wait} сек)...")
    print(f"[INFO] Примечание: инициализация сервера может занять до 3 минут из-за восстановления checkpoint")
    for i in range(max_wait):
        # Проверяем, не завершился ли процесс сервера с ошибкой
        if server_process is not None:
            if server_process.poll() is not None:
                print(f"[FAIL] Процесс сервера завершился с кодом: {server_process.returncode}")
                return False
        
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print(f"[OK] Сервер доступен (время ожидания: {i+1} сек)")
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # Сервер еще не готов
            if i % 15 == 0 and i > 0:
                print(f"   Ожидание... ({i}/{max_wait}) - сервер инициализируется...")
        except Exception as e:
            if i % 15 == 0:
                print(f"[DEBUG] Ошибка при проверке: {e}")
        time.sleep(1)
    
    print(f"[FAIL] Сервер не запустился за {max_wait} секунд")
    print(f"[INFO] Возможные причины:")
    print(f"  1. Медленная инициализация из-за большого checkpoint")
    print(f"  2. Проблемы с Docker или Cursor CLI")
    print(f"  3. Отсутствует переменная окружения PROJECT_DIR")
    print(f"  4. Проверьте логи в logs/code_agent.log")
    return False


def main():
    """Главная функция"""
    import sys
    import subprocess
    from pathlib import Path
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ API СЕРВЕРА")
    print("=" * 80)
    print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 80)
    
    # Проверяем доступность сервера
    server_process = None
    server_started_by_test = False
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("[INFO] Сервер уже запущен")
        else:
            print(f"[WARN] Сервер вернул код {response.status_code}")
            if not wait_for_server():
                return 1
    except requests.exceptions.ConnectionError:
        # Сервер не запущен - пытаемся запустить автоматически
        print("[INFO] Сервер не запущен, пытаемся запустить автоматически...")
        
        # Проверяем, не запущен ли уже другой процесс
        import socket
        port_in_use = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', 3456))
                if result == 0:
                    port_in_use = True
                    print("[INFO] Порт 3456 занят, возможно сервер запускается...")
                    if wait_for_server(max_wait=300):
                        server_started_by_test = False  # Используем существующий
                    else:
                        return 1
        except Exception:
            pass
        
        # Если порт свободен, запускаем сервер
        if not port_in_use:
            project_root = Path(__file__).parent.parent
            main_py = project_root / "main.py"
            
            if not main_py.exists():
                print(f"[FAIL] Файл main.py не найден: {main_py}")
                return 1
            
            print(f"[INFO] Запуск сервера: {main_py}")
            try:
                # Запускаем сервер в фоне
                # Используем PIPE, но читаем в фоновом потоке, чтобы избежать блокировки
                import threading
                server_process = subprocess.Popen(
                    [sys.executable, str(main_py)],
                    cwd=str(project_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1  # Небуферизованный режим
                )
                print(f"[INFO] Процесс сервера запущен (PID: {server_process.pid})")
                server_started_by_test = True
                
                # Читаем stdout/stderr в фоне, чтобы избежать блокировки
                stdout_lines = []
                stderr_lines = []
                
                def read_stdout():
                    try:
                        for line in iter(server_process.stdout.readline, ''):
                            if line:
                                stdout_lines.append(line.strip())
                                # Выводим важные сообщения
                                if any(kw in line.lower() for kw in ['http сервер', 'запущен', 'порт 3456', 'доступен', 'error', 'fail']):
                                    if 'error' in line.lower() or 'fail' in line.lower():
                                        print(f"[STDOUT] {line.strip()}")
                    except:
                        pass
                
                def read_stderr():
                    try:
                        for line in iter(server_process.stderr.readline, ''):
                            if line:
                                stderr_lines.append(line.strip())
                                # Выводим ошибки
                                if any(kw in line.lower() for kw in ['error', 'fail', 'exception', 'traceback']):
                                    print(f"[STDERR] {line.strip()}")
                    except:
                        pass
                
                stdout_thread = threading.Thread(target=read_stdout, daemon=True)
                stdout_thread.start()
                
                stderr_thread = threading.Thread(target=read_stderr, daemon=True)
                stderr_thread.start()
                
                # Небольшая задержка перед проверкой
                time.sleep(2)
                
                # Проверяем, не завершился ли процесс сразу
                if server_process.poll() is not None:
                    print(f"[FAIL] Процесс завершился сразу с кодом: {server_process.returncode}")
                    if stderr_lines:
                        print("[ERROR] Последние ошибки:")
                        for line in stderr_lines[-10:]:
                            print(f"  {line}")
                    return 1
                
                # Ждем запуска сервера (увеличиваем таймаут для медленной инициализации)
                # Инициализация может занимать до 3 минут из-за восстановления checkpoint
                if not wait_for_server(max_wait=300, server_process=server_process):
                    print("[FAIL] Не удалось запустить сервер")
                    # Проверяем, не завершился ли процесс
                    if server_process.poll() is not None:
                        print(f"[ERROR] Процесс завершился с кодом: {server_process.returncode}")
                        if stderr_lines:
                            print("[ERROR] Последние ошибки:")
                            for line in stderr_lines[-20:]:
                                print(f"  {line}")
                    try:
                        server_process.terminate()
                        server_process.wait(timeout=5)
                    except:
                        try:
                            server_process.kill()
                        except:
                            pass
                    return 1
            except Exception as e:
                print(f"[FAIL] Ошибка при запуске сервера: {e}")
                return 1
    except Exception as e:
        print(f"[FAIL] Неожиданная ошибка: {e}")
        print("[INFO] Убедитесь, что сервер запущен: python main.py")
        return 1
    
    results = []
    
    # Тесты API
    results.append(("Health Endpoint", test_health()))
    time.sleep(1)
    
    results.append(("Root Endpoint", test_root()))
    time.sleep(1)
    
    results.append(("Status Endpoint", test_status()))
    time.sleep(1)
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")
    
    print(f"\n[OK] Пройдено: {passed}/{total}")
    
    # Останавливаем сервер, если мы его запустили
    if server_started_by_test and server_process:
        try:
            print("\n[INFO] Остановка сервера...")
            # Отправляем запрос на остановку
            try:
                requests.post(f"{BASE_URL}/stop", timeout=2)
                time.sleep(1)
            except:
                pass
            # Завершаем процесс
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
            except:
                try:
                    server_process.kill()
                except:
                    pass
            print("[INFO] Сервер остановлен")
        except Exception as e:
            print(f"[WARN] Ошибка при остановке сервера: {e}")
    
    if passed == total:
        print("\n[SUCCESS] ВСЕ ТЕСТЫ API ПРОЙДЕНЫ УСПЕШНО")
        return 0
    else:
        print("\n[WARNING] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
