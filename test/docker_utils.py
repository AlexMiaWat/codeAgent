"""
Вспомогательные функции для работы с Docker контейнером в тестах
"""

import subprocess
import json
from typing import Dict, Any, Optional


def check_docker_container_status(container_name) -> Dict[str, Any]:
    """
    Проверка статуса Docker контейнера

    Args:
        container_name: Имя контейнера

    Returns:
        Словарь с информацией о статусе контейнера
    """
    if container_name is None:
        raise ValueError("container_name не может быть None")
    if not isinstance(container_name, str):
        raise ValueError(f"container_name должен быть строкой, получен {type(container_name)}")
    container_name = container_name.strip()
    if not container_name:
        raise ValueError("container_name не может быть пустой строкой")

    try:
        # Проверяем наличие Docker
        docker_check = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if docker_check.returncode != 0:
            return {
                "available": False,
                "error": "Docker не установлен или недоступен"
            }
        
        # Проверяем статус контейнера
        inspect_cmd = [
            "docker", "inspect",
            "--format", "{{json .State}}",
            container_name
        ]
        inspect_result = subprocess.run(
            inspect_cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if inspect_result.returncode == 0:
            try:
                state = json.loads(inspect_result.stdout.strip())
                return {
                    "available": True,
                    "exists": True,
                    "running": state.get("Status") == "running",
                    "status": state.get("Status"),
                    "started": state.get("StartedAt"),
                    "finished": state.get("FinishedAt"),
                    "restarting": state.get("Restarting", False),
                    "error": state.get("Error", "")
                }
            except json.JSONDecodeError:
                return {
                    "available": True,
                    "exists": True,
                    "running": False,
                    "error": "Не удалось распарсить статус контейнера"
                }
        else:
            # Контейнер не существует
            return {
                "available": True,
                "exists": False,
                "running": False,
                "error": f"Контейнер {container_name} не найден"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "error": "Таймаут при проверке Docker"
        }
    except FileNotFoundError:
        return {
            "available": False,
            "error": "Docker не найден в PATH"
        }
    except Exception as e:
        return {
            "available": False,
            "error": f"Ошибка при проверке Docker: {str(e)}"
        }


def get_docker_container_logs(container_name, lines: int = 20) -> str:
    """
    Получение логов Docker контейнера

    Args:
        container_name: Имя контейнера
        lines: Количество последних строк логов

    Returns:
        Строка с логами или сообщение об ошибке
    """
    if not container_name or not isinstance(container_name, str) or container_name.strip() == '':
        raise ValueError("container_name должен быть непустой строкой")

    try:
        logs_cmd = ["docker", "logs", "--tail", str(lines), container_name]
        logs_result = subprocess.run(
            logs_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if logs_result.returncode == 0:
            return logs_result.stdout
        else:
            return f"Ошибка получения логов: {logs_result.stderr}"
    except Exception as e:
        return f"Ошибка получения логов: {str(e)}"


def print_docker_container_info(container_name, prefix: str = "  "):
    """
    Вывод информации о Docker контейнере в консоль

    Args:
        container_name: Имя контейнера
        prefix: Префикс для вывода (для отступов)
    """
    if not container_name or not isinstance(container_name, str) or container_name.strip() == '':
        raise ValueError("container_name должен быть непустой строкой")

    status = check_docker_container_status(container_name)
    
    if not status.get("available", False):
        print(f"{prefix}[WARNING] Docker недоступен: {status.get('error', 'Неизвестная ошибка')}")
        return
    
    if not status.get("exists", False):
        print(f"{prefix}[INFO] Контейнер {container_name} не существует")
        print(f"{prefix}[INFO] Контейнер будет создан автоматически при первом использовании")
        return
    
    if status.get("running", False):
        print(f"{prefix}[OK] Контейнер {container_name} запущен (статус: {status.get('status', 'unknown')})")
        if status.get("started"):
            print(f"{prefix}[INFO] Запущен: {status.get('started', '')[:19]}")
    else:
        print(f"{prefix}[WARNING] Контейнер {container_name} не запущен (статус: {status.get('status', 'unknown')})")
        if status.get("error"):
            print(f"{prefix}[ERROR] Ошибка: {status.get('error')}")
    
    if status.get("restarting", False):
        print(f"{prefix}[WARNING] ⚠ Контейнер в состоянии перезапуска!")
    
    # Показываем последние логи если контейнер не запущен
    if not status.get("running", False) and status.get("exists", False):
        logs = get_docker_container_logs(container_name, lines=5)
        if logs and logs.strip():
            print(f"{prefix}[INFO] Последние логи контейнера:")
            for line in logs.strip().split('\n')[-3:]:
                if line.strip():
                    print(f"{prefix}    {line[:100]}")
