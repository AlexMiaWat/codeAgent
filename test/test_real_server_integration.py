#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование реального сервера с реальными целевыми проектами

Проверяет:
1. Запуск реального сервера
2. Работу HTTP API
3. Обработку задач из реального проекта
4. Интеграцию со всеми компонентами
"""

import sys
import os
import time
import logging
import subprocess
import requests
import signal
from pathlib import Path
from typing import Optional
import threading

from src.config_loader import ConfigLoader

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServerTester:
    """Класс для тестирования реального сервера"""
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.base_url = "http://127.0.0.1:3456"
        self.config = ConfigLoader("config/config.yaml")
        self.project_dir = self.config.get_project_dir()
    
    def start_server(self, timeout: int = 45) -> bool:
        """Запуск сервера"""
        print(f"\n{'='*80}")
        print("ЗАПУСК РЕАЛЬНОГО СЕРВЕРА")
        print(f"{'='*80}")
        
        stderr_lines = []
        stderr_thread = None
        
        try:
            main_py = project_root / "main.py"
            if not main_py.exists():
                print(f"[FAIL] Файл main.py не найден: {main_py}")
                return False
            
            # Подготовка окружения
            env = os.environ.copy()
            if 'PROJECT_DIR' not in env:
                env_file = project_root / '.env'
                if env_file.exists():
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('PROJECT_DIR='):
                                project_dir = line.split('=', 1)[1].strip().strip('"').strip("'")
                                if Path(project_dir).exists():
                                    env['PROJECT_DIR'] = project_dir
                                    break
            
            print(f"[INFO] Проект: {self.project_dir}")
            
            # Проверяем, не занят ли порт другим процессом
            import socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('127.0.0.1', 3456))
                    if result == 0:
                        print("[WARN] Порт 3456 уже занят другим процессом")
                        # Проверяем, отвечает ли сервер на health check
                        try:
                            response = requests.get(f"{self.base_url}/health", timeout=2)
                            if response.status_code == 200:
                                print("[INFO] Сервер уже запущен и отвечает на запросы")
                                print("[INFO] Используем существующий сервер")
                                return True
                        except Exception:
                            print("[WARN] Порт занят, но сервер не отвечает. Попытка запустить новый процесс...")
            except Exception as e:
                print(f"[DEBUG] Ошибка при проверке порта: {e}")
            
            print("[INFO] Запуск сервера...")
            
            # Запуск сервера
            self.server_process = subprocess.Popen(
                [sys.executable, str(main_py)],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1  # Небуферизованный режим
            )
            
            stdout_lines = []
            stderr_lines = []
            
            # Читаем stdout в фоне для диагностики (сервер выводит через logger в stdout)
            def read_stdout():
                try:
                    for line in iter(self.server_process.stdout.readline, ''):
                        if line:
                            line_stripped = line.strip()
                            stdout_lines.append(line_stripped)
                            # Выводим важные сообщения о запуске
                            if any(keyword in line_stripped.lower() for keyword in 
                                   ['http сервер', 'запущен', 'порт 3456', 'доступен', 'ready', 'started']):
                                print(f"[STDOUT] {line_stripped}")
                except Exception:
                    pass
            
            # Читаем stderr в фоне для диагностики
            def read_stderr():
                try:
                    for line in iter(self.server_process.stderr.readline, ''):
                        if line:
                            line_stripped = line.strip()
                            stderr_lines.append(line_stripped)
                            # Выводим важные ошибки сразу
                            if any(keyword in line_stripped.lower() for keyword in ['error', 'fail', 'exception', 'traceback']):
                                print(f"[STDERR] {line_stripped}")
                except Exception:
                    pass
            
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stdout_thread.start()
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # Ожидание запуска сервера
            print(f"[INFO] Ожидание запуска сервера (макс. {timeout} сек)...")
            print(f"[INFO] PID процесса: {self.server_process.pid}")
            
            # Сначала проверяем, что процесс не завершился сразу
            time.sleep(2)
            if self.server_process.poll() is not None:
                print(f"[FAIL] Процесс завершился сразу с кодом: {self.server_process.returncode}")
                if stderr_lines:
                    print("[ERROR] Последние ошибки из stderr:")
                    for line in stderr_lines[-10:]:
                        print(f"  {line}")
                # Пытаемся прочитать оставшийся stderr
                try:
                    remaining_stderr = self.server_process.stderr.read()
                    if remaining_stderr:
                        print("[ERROR] Остаток stderr:")
                        print(remaining_stderr[:500])
                except Exception:
                    pass
                return False
            
            # Проверяем доступность сервера
            for i in range(timeout):
                # Проверяем, что процесс еще работает
                if self.server_process.poll() is not None:
                    print(f"[FAIL] Процесс завершился с кодом: {self.server_process.returncode}")
                    if stderr_lines:
                        print("[ERROR] Ошибки из stderr:")
                        for line in stderr_lines[-20:]:
                            print(f"  {line}")
                    # Пытаемся прочитать оставшийся stderr
                    try:
                        remaining_stderr = self.server_process.stderr.read()
                        if remaining_stderr:
                            print("[ERROR] Остаток stderr:")
                            print(remaining_stderr[:500])
                    except Exception:
                        pass
                    return False
                
                # Проверяем доступность через /health
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"[OK] Сервер запущен успешно (PID: {self.server_process.pid})")
                        print(f"[INFO] Время запуска: {i+1} секунд")
                        # Показываем последние сообщения из stdout для диагностики
                        if stdout_lines:
                            recent_messages = [line for line in stdout_lines[-5:] 
                                             if any(kw in line.lower() for kw in ['http', 'сервер', 'порт', 'запущен'])]
                            if recent_messages:
                                print("[DEBUG] Последние сообщения сервера:")
                                for msg in recent_messages:
                                    print(f"  {msg}")
                        # Дополнительное ожидание для полной готовности сервера
                        print("[INFO] Ожидание полной готовности сервера (2 сек)...")
                        time.sleep(2)
                        return True
                except requests.exceptions.ConnectionError as e:
                    # Сервер еще не готов - это нормально
                    if i > 10 and i % 5 == 0:  # Показываем диагностику после 10 секунд
                        print(f"[DEBUG] ConnectionError при проверке /health (попытка {i+1}): {e}")
                except requests.exceptions.Timeout:
                    # Таймаут - сервер может быть перегружен
                    if i > 10 and i % 5 == 0:
                        print(f"[DEBUG] Timeout при проверке /health (попытка {i+1})")
                except requests.exceptions.RequestException as e:
                    # Другие ошибки - возможно сервер запускается
                    if i > 10 and i % 5 == 0:
                        print(f"[DEBUG] RequestException при проверке /health (попытка {i+1}): {e}")
                
                time.sleep(1)
                if i % 5 == 0 and i > 0:
                    print(f"   Ожидание... ({i}/{timeout})")
                    # Показываем последние ошибки если есть
                    if stderr_lines and i % 10 == 0:
                        recent_errors = [line for line in stderr_lines[-5:] if any(kw in line.lower() for kw in ['error', 'fail', 'exception'])]
                        if recent_errors:
                            print(f"   Последние ошибки: {recent_errors[-1]}")
            
            print(f"[FAIL] Сервер не запустился за {timeout} секунд")
            print(f"[INFO] Процесс все еще работает: {self.server_process.poll() is None}")
            
            # Показываем последние сообщения из stdout
            if stdout_lines:
                print(f"[DEBUG] Последние сообщения из stdout ({len(stdout_lines)} строк):")
                for line in stdout_lines[-20:]:
                    print(f"  {line}")
            
            if stderr_lines:
                print(f"[ERROR] Последние ошибки из stderr ({len(stderr_lines)} строк):")
                for line in stderr_lines[-20:]:
                    print(f"  {line}")
            
            # Пытаемся прочитать оставшийся stderr
            try:
                remaining_stderr = self.server_process.stderr.read()
                if remaining_stderr:
                    print("[ERROR] Остаток stderr:")
                    print(remaining_stderr[:1000])
            except Exception:
                pass
            
            # Пытаемся прочитать оставшийся stdout
            try:
                remaining_stdout = self.server_process.stdout.read()
                if remaining_stdout:
                    print("[DEBUG] Остаток stdout:")
                    print(remaining_stdout[:1000])
            except Exception:
                pass
            return False
            
        except Exception as e:
            print(f"[FAIL] Ошибка запуска сервера: {e}")
            import traceback
            traceback.print_exc()
            if stderr_lines:
                print("[ERROR] Ошибки из stderr:")
                for line in stderr_lines[-10:]:
                    print(f"  {line}")
            return False
    
    def stop_server(self):
        """Остановка сервера"""
        if self.server_process:
            print(f"\n{'='*80}")
            print("ОСТАНОВКА СЕРВЕРА")
            print(f"{'='*80}")
            
            try:
                # Пробуем остановить через API (graceful shutdown)
                try:
                    print("[INFO] Отправка запроса на остановку через API...")
                    response = requests.post(f"{self.base_url}/stop", timeout=5)
                    print(f"[INFO] Запрос на остановку отправлен: {response.status_code}")
                    if response.status_code == 200:
                        print("[INFO] Сервер получил запрос на остановку")
                    
                    # Даем время на graceful shutdown
                    print("[INFO] Ожидание graceful shutdown (10 сек)...")
                    for i in range(10):
                        if self.server_process.poll() is not None:
                            print(f"[OK] Процесс завершился gracefully (PID: {self.server_process.pid})")
                            return
                        time.sleep(1)
                        if i % 3 == 0:
                            print(f"   Ожидание завершения... ({i}/10)")
                except requests.exceptions.RequestException as e:
                    print(f"[WARN] Не удалось отправить запрос на остановку: {e}")
                    print("[INFO] Продолжаем с принудительной остановкой...")
                
                # Принудительная остановка процесса
                if self.server_process.poll() is None:
                    print(f"[INFO] Принудительная остановка процесса (PID: {self.server_process.pid})")
                    if sys.platform == 'win32':
                        self.server_process.terminate()
                    else:
                        self.server_process.send_signal(signal.SIGTERM)
                    
                    # Ждем завершения с таймаутом
                    try:
                        self.server_process.wait(timeout=10)
                        print("[OK] Процесс остановлен")
                    except subprocess.TimeoutExpired:
                        print("[WARN] Процесс не остановился за 10 секунд, принудительное завершение...")
                        self.server_process.kill()
                        try:
                            self.server_process.wait(timeout=5)
                            print("[OK] Процесс завершен принудительно")
                        except subprocess.TimeoutExpired:
                            print("[ERROR] Не удалось завершить процесс даже после kill()")
                else:
                    print(f"[OK] Процесс уже завершен (код: {self.server_process.returncode})")
            except Exception as e:
                print(f"[WARN] Ошибка при остановке сервера: {e}")
                # Последняя попытка - kill
                if self.server_process.poll() is None:
                    try:
                        self.server_process.kill()
                        self.server_process.wait(timeout=3)
                        print("[OK] Процесс завершен через kill()")
                    except Exception:
                        print("[ERROR] Критическая ошибка при завершении процесса")
    
    def test_health_endpoint(self) -> bool:
        """Тест health endpoint"""
        print(f"\n{'='*80}")
        print("ТЕСТ: Health Endpoint")
        print(f"{'='*80}")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
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
    
    def test_status_endpoint(self) -> bool:
        """Тест status endpoint"""
        print(f"\n{'='*80}")
        print("ТЕСТ: Status Endpoint")
        print(f"{'='*80}")
        
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
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
                print(f"   Ожидает: {tasks_info.get('pending', 0)}")
                
                return True
            else:
                print(f"[FAIL] Status вернул код: {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] Ошибка получения status: {e}")
            return False
    
    def test_root_endpoint(self) -> bool:
        """Тест root endpoint"""
        print(f"\n{'='*80}")
        print("ТЕСТ: Root Endpoint")
        print(f"{'='*80}")
        
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print("[OK] Root endpoint успешен")
                print(f"   Статус: {data.get('status')}")
                print(f"   Порт: {data.get('port')}")
                print(f"   Сессия: {data.get('session_id')}")
                print(f"   Итерация: {data.get('iteration')}")
                return True
            else:
                print(f"[FAIL] Root endpoint вернул код: {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] Ошибка root endpoint: {e}")
            return False
    
    def test_stop_endpoint(self) -> bool:
        """Тест stop endpoint"""
        print(f"\n{'='*80}")
        print("ТЕСТ: Stop Endpoint")
        print(f"{'='*80}")
        
        try:
            response = requests.post(f"{self.base_url}/stop", timeout=2)
            if response.status_code == 200:
                data = response.json()
                print("[OK] Stop endpoint успешен")
                print(f"   Статус: {data.get('status')}")
                print(f"   Сообщение: {data.get('message')}")
                return True
            else:
                print(f"[FAIL] Stop endpoint вернул код: {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] Ошибка stop endpoint: {e}")
            return False
    
    def run_all_tests(self, start_server_flag: bool = True) -> bool:
        """Запуск всех тестов"""
        print("=" * 80)
        print("ТЕСТИРОВАНИЕ РЕАЛЬНОГО СЕРВЕРА")
        print("=" * 80)
        print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Проект: {self.project_dir}")
        print("=" * 80)
        
        # Проверяем, запущен ли сервер
        server_started = False
        print(f"[DEBUG] start_server_flag = {start_server_flag}")
        print(f"[DEBUG] Проверка доступности сервера на {self.base_url}...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=3)
            if response.status_code == 200:
                print("[INFO] Сервер уже запущен, используем существующий")
                print(f"[DEBUG] Сервер отвечает на /health: {response.json()}")
                server_started = False
            else:
                print(f"[WARN] Сервер вернул код {response.status_code}, но не 200")
                if start_server_flag:
                    print("[INFO] Попытка запустить сервер...")
                    server_started = self.start_server()
                    if not server_started:
                        print("[FAIL] Не удалось запустить сервер")
                        return False
                else:
                    print("[FAIL] Сервер не отвечает и start_server_flag=False")
                    return False
        except requests.exceptions.ConnectionError as e:
            # Сервер не запущен (ConnectionError)
            print(f"[DEBUG] ConnectionError: {e}")
            print("[INFO] Сервер не запущен (ConnectionError)")
            if start_server_flag:
                print("[INFO] Запускаем сервер автоматически...")
                if not self.start_server():
                    print("[FAIL] Не удалось запустить сервер автоматически")
                    print("[INFO] Возможные причины:")
                    print("  1. Порт 3456 занят другим процессом")
                    print("  2. Ошибка при запуске main.py")
                    print("  3. Недостаточно прав для запуска")
                    print("  4. HTTP сервер не запустился (проверьте логи)")
                    print("[INFO] Запустите сервер вручную: python main.py")
                    print("[INFO] Или проверьте логи в logs/codeagent.log")
                    return False
                server_started = True
                print("[OK] Сервер успешно запущен автоматически")
            else:
                print("[FAIL] Сервер не запущен и start_server_flag=False")
                print(f"[INFO] Ошибка подключения: {e}")
                print("[INFO] Запустите сервер вручную: python main.py")
                print("[INFO] Или запустите тест без флага --no-start для автоматического запуска")
                return False
        except requests.exceptions.Timeout as e:
            # Таймаут - сервер может быть перегружен
            print(f"[WARN] Таймаут при проверке сервера: {e}")
            if start_server_flag:
                print("[INFO] Попытка запустить сервер...")
                if not self.start_server():
                    print("[FAIL] Не удалось запустить сервер автоматически")
                    return False
                server_started = True
            else:
                print("[FAIL] Сервер недоступен (таймаут) и start_server_flag=False")
                return False
        except requests.exceptions.RequestException as e:
            # Другие ошибки запросов
            print(f"[DEBUG] RequestException: {e}")
            print(f"[WARN] Ошибка запроса: {e}")
            if start_server_flag:
                print("[INFO] Попытка запустить сервер...")
                if not self.start_server():
                    print("[FAIL] Не удалось запустить сервер автоматически")
                    return False
                server_started = True
            else:
                print("[FAIL] Сервер недоступен и start_server_flag=False")
                return False
        
        results = []
        
        try:
            # Тесты API
            results.append(("Health Endpoint", self.test_health_endpoint()))
            time.sleep(1)
            
            results.append(("Root Endpoint", self.test_root_endpoint()))
            time.sleep(1)
            
            results.append(("Status Endpoint", self.test_status_endpoint()))
            time.sleep(1)
            
            # Итоги
            print(f"\n{'='*80}")
            print("ИТОГИ ТЕСТИРОВАНИЯ")
            print(f"{'='*80}")
            
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            for name, result in results:
                status = "[OK] PASS" if result else "[FAIL] FAIL"
                print(f"{status}: {name}")
            
            print(f"\n[OK] Пройдено: {passed}/{total}")
            
            success = passed == total
            return success
            
        except Exception as e:
            print(f"[FAIL] Критическая ошибка при выполнении тестов: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Остановка сервера только если мы его запускали
            if start_server_flag and server_started:
                self.stop_server()


def main():
    """Главная функция"""
    import sys
    # Если передан аргумент --no-start, не запускаем сервер
    # По умолчанию start_server=True, чтобы сервер запускался автоматически
    start_server = '--no-start' not in sys.argv
    
    if start_server:
        print("[INFO] Режим автоматического запуска сервера включен")
        print("[INFO] Сервер будет запущен автоматически, если не запущен")
    else:
        print("[INFO] Режим автоматического запуска сервера отключен (--no-start)")
        print("[INFO] Сервер должен быть запущен вручную")
    
    tester = ServerTester()
    success = tester.run_all_tests(start_server_flag=start_server)
    
    if success:
        print("\n[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        return 0
    else:
        print("\n[FAIL] НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
