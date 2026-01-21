"""
Точка входа в Code Agent Server

Запуск сервера агента:
    python main.py
"""

import sys
import subprocess
import socket
import time
import asyncio
import logging
import warnings
from pathlib import Path
from src.server import CodeAgentServer, _setup_logging, ServerReloadException


def setup_asyncio_exception_handling():
    """Настройка обработки необработанных исключений в asyncio задачах"""
    def handle_exception(loop, context):
        """Обработчик необработанных исключений в asyncio"""
        exception = context.get('exception')
        if exception:
            error_msg = str(exception)
            # Подавляем httpx cleanup ошибки при завершении
            if ("Event loop is closed" in error_msg and
                any(lib in error_msg.lower() for lib in ['httpx', 'anyio', 'httpcore', 'asyncclient'])):
                logging.getLogger(__name__).debug(f"Подавлено необработанное исключение cleanup HTTP клиента: {exception}")
                return

        # Для остальных ошибок используем стандартную обработку
        logging.getLogger(__name__).error(f"Необработанное исключение в asyncio задаче: {context}")

    # Устанавливаем обработчик исключений
    asyncio.get_event_loop().set_exception_handler(handle_exception)


def stop_server_processes():
    """Найти и остановить все запущенные процессы сервера"""
    try:
        if sys.platform == 'win32':
            # Windows: ищем процессы Python с main.py или server.py
            try:
                # Используем wmic для поиска процессов
                result = subprocess.run(
                    ['wmic', 'process', 'where', 'name="python.exe"', 'get', 'ProcessId,CommandLine', '/format:csv'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    pids = []
                    for line in lines:
                        if 'main.py' in line or ('server.py' in line and 'monitor_server.py' not in line):
                            # Извлекаем PID из CSV формата
                            parts = line.split(',')
                            for part in parts:
                                if part.strip().isdigit():
                                    pids.append(int(part.strip()))
                    
                    # Останавливаем найденные процессы
                    if pids:
                        for pid in pids:
                            try:
                                subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                             capture_output=True, timeout=3)
                            except Exception:
                                pass
                        print(f"Остановлено {len(pids)} процессов сервера")
                        return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback: используем taskkill по имени процесса
                try:
                    subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq *python*main.py*'],
                                 capture_output=True, timeout=5)
                    subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq *python*server.py*'],
                                 capture_output=True, timeout=5)
                except Exception:
                    pass
        else:
            # Unix/Linux/Mac: используем pkill
            try:
                # Останавливаем процессы с main.py
                subprocess.run(['pkill', '-f', 'python.*main.py'], 
                             capture_output=True, timeout=5)
                # Останавливаем процессы с server.py (но не monitor_server.py)
                subprocess.run(['pkill', '-f', 'python.*server.py'], 
                             capture_output=True, timeout=5)
                print("Процессы сервера остановлены")
                return True
            except Exception:
                pass
    except Exception as e:
        print(f"Ошибка при остановке процессов сервера: {e}")
    
    return False


def cleanup_logs():
    """Очистка всех логов перед стартом сервера"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return
    
    # Удаляем все .log файлы
    log_files = list(logs_dir.glob("*.log"))
    if not log_files:
        return
    
    failed_files = []
    
    # Первая попытка удаления
    for log_file in log_files:
        try:
            log_file.unlink()
        except (OSError, PermissionError) as e:
            # Файл заблокирован
            failed_files.append((log_file, e))
    
    # Если есть заблокированные файлы, пытаемся остановить процессы сервера
    if failed_files:
        print(f"Обнаружено {len(failed_files)} заблокированных лог-файлов. Попытка остановить процессы сервера...")
        stopped = stop_server_processes()
        
        if stopped:
            # Даем время процессам остановиться
            import time
            time.sleep(2)
            
            # Вторая попытка удаления после остановки процессов
            remaining_failed = []
            for log_file, _ in failed_files:
                try:
                    log_file.unlink()
                except Exception as err:
                    remaining_failed.append((log_file, err))
            
            if remaining_failed:
                print(f"Не удалось удалить {len(remaining_failed)} лог-файлов после остановки процессов:")
                for log_file, err in remaining_failed:
                    print(f"  - {log_file.name}: {err}")
            else:
                print(f"Все лог-файлы удалены после остановки процессов")
    
    deleted_count = len(log_files) - len(failed_files)
    if deleted_count > 0:
        print(f"Очищено {deleted_count} лог-файлов")


def check_and_free_port(port: int) -> bool:
    """
    Проверить занятость порта и освободить его, завершив старый процесс
    
    Args:
        port: Номер порта для проверки
        
    Returns:
        True если порт свободен или успешно освобожден, False иначе
    """
    def is_port_in_use(port: int) -> bool:
        """Проверка, занят ли порт"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def kill_process_on_port(port: int) -> bool:
        """Завершить процесс на порту"""
        try:
            if sys.platform == 'win32':
                # Windows: используем netstat
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
                                pid = parts[-1]
                                try:
                                    subprocess.run(
                                        ['taskkill', '/F', '/PID', pid],
                                        capture_output=True,
                                        timeout=3
                                    )
                                    print(f"Завершен процесс {pid} на порту {port}")
                                    time.sleep(2)
                                    return True
                                except Exception:
                                    pass
            else:
                # Linux/Mac: используем lsof
                try:
                    result = subprocess.run(
                        ['lsof', '-ti', f':{port}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            try:
                                subprocess.run(
                                    ['kill', '-9', pid],
                                    capture_output=True,
                                    timeout=3
                                )
                                print(f"Завершен процесс {pid} на порту {port}")
                            except Exception:
                                pass
                        time.sleep(2)
                        return True
                except FileNotFoundError:
                    # Пробуем fuser
                    try:
                        subprocess.run(
                            ['fuser', '-k', f'{port}/tcp'],
                            capture_output=True,
                            timeout=5
                        )
                        time.sleep(2)
                        return True
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print(f"Ошибка при завершении процесса на порту {port}: {e}")
        return False
    
    # Проверяем занятость порта
    if is_port_in_use(port):
        print(f"Порт {port} занят, пытаемся завершить старый процесс...")
        if kill_process_on_port(port):
            # Ждем освобождения порта
            for _ in range(10):
                if not is_port_in_use(port):
                    print(f"Порт {port} успешно освобожден")
                    return True
                time.sleep(1)
            print(f"Предупреждение: порт {port} все еще занят после попытки завершения")
            return False
        else:
            print(f"Не удалось завершить процесс на порту {port}")
            return False
    
    return True


def main():
    """Главная функция для запуска сервера"""
    # Очищаем логи перед стартом
    cleanup_logs()

    # Создаем директорию для логов если не существует
    Path("logs").mkdir(exist_ok=True)

    # Настраиваем логирование ПОСЛЕ очистки логов
    _setup_logging()

    # Импортируем logger после настройки логирования
    logger = logging.getLogger(__name__)
    
    # Загружаем конфигурацию для получения порта и настроек перезапуска
    from src.config_loader import ConfigLoader
    config = ConfigLoader("config/config.yaml")
    server_config = config.get('server', {})
    http_port = server_config.get('http_port', 3456)
    max_restarts = server_config.get('max_restarts', 3)  # Максимальное количество перезапусков подряд (по умолчанию 3)
    
    # Проверяем и освобождаем порт
    if not check_and_free_port(http_port):
        print(f"Ошибка: не удалось освободить порт {http_port}")
        print("Попробуйте завершить процесс вручную или изменить порт в config/config.yaml")
        sys.exit(1)
    
    # Настраиваем обработку asyncio исключений один раз в начале
    try:
        # Пытаемся настроить обработчик для текущего event loop, если он существует
        current_loop = asyncio.get_running_loop()
        setup_asyncio_exception_handling()
    except RuntimeError:
        pass  # Event loop еще не создан

    # Запускаем сервер с поддержкой автоперезапуска
    restart_count = 0

    while restart_count < max_restarts:
        server = None
        try:
            server = CodeAgentServer()
            asyncio.run(server.start())

            # Если дошли сюда, значит сервер завершился нормально
            # (не из-за перезапуска)
            break
            
        except ServerReloadException:
            # Полный перезапуск из-за 15 изменений кода подряд
            restart_count += 1
            if restart_count < max_restarts:
                print(f"\n{'='*80}")
                print(f"Полный перезапуск сервера (достигнуто 15 изменений кода подряд) ({restart_count}/{max_restarts})...")
                print(f"{'='*80}\n")
                time.sleep(2)
                continue
            else:
                print(f"Достигнуто максимальное количество перезапусков ({max_restarts})")
                break
        except KeyboardInterrupt:
            print("\nОстановка сервера...")
            break
        except Exception as e:
            # Детальное логирование критических ошибок
            logger.error(
                "Критическая ошибка при работе сервера",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "context": "main_loop"
                }
            )
            print(f"Критическая ошибка: {e}")
            print("Подробности в логах. Проверьте logs/codeagent.log")
            import traceback
            traceback.print_exc()
            break
        finally:
            # Корректное закрытие ресурсов сервера
            if server:
                try:
                    # Event loop может быть уже закрыт (особенно при перезапуске)
                    # Поэтому всегда создаем новый event loop для закрытия
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(server.close())
                    except asyncio.CancelledError:
                        # Задача была отменена - это нормально при перезапуске
                        logger.debug("Server close task was cancelled during reload")
                    finally:
                        new_loop.close()
                except Exception as e:
                    # Подавляем httpx cleanup ошибки при завершении
                    error_str = str(e)
                    if ("Event loop is closed" in error_str and
                        any(lib in error_str.lower() for lib in ['httpx', 'anyio', 'httpcore', 'asyncclient'])):
                        logger.debug(f"Подавлена ошибка cleanup HTTP клиента при завершении: {e}")
                    elif isinstance(e, asyncio.CancelledError):
                        logger.debug("Server close operation was cancelled")
                    else:
                        print(f"Ошибка при закрытии сервера: {e}")


if __name__ == "__main__":
    main()
