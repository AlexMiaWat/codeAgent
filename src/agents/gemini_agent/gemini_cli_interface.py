"""
Интерфейс взаимодействия с Gemini CLI

Этот модуль предоставляет возможность выполнения команд через Gemini CLI агент,
если он доступен в системе.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class GeminiCLIResult:
    """Результат выполнения команды через Gemini CLI"""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    cli_available: bool
    error_message: Optional[str] = None


class GeminiCLIInterface:
    """
    Интерфейс взаимодействия с Gemini CLI

    Использует gemini_agent_cli.py для выполнения инструкций.
    """

    def __init__(
        self,
        project_dir: Optional[str] = None,
        timeout: int = 300,
        container_name: Optional[str] = None
    ):
        """
        Инициализация интерфейса Gemini CLI

        Args:
            project_dir: Директория целевого проекта
            timeout: Таймаут по умолчанию для выполнения команд (секунды)
            container_name: Имя Docker контейнера для Gemini CLI
        """
        self.project_dir = Path(project_dir) if project_dir else None
        self.timeout = timeout
        self.container_name = container_name
        self.use_docker = bool(container_name)
        self.cli_available = self._check_cli_availability()

        logger.debug(f"Инициализация GeminiCLIInterface: timeout={timeout} секунд, use_docker={self.use_docker}")

    def _check_cli_availability(self) -> bool:
        """
        Проверка доступности Gemini CLI

        Returns:
            True если CLI доступен, False иначе
        """
        if self.use_docker:
            try:
                # 1. Проверяем наличие docker-compose файла
                compose_file = Path(__file__).parent.parent.parent.parent / "docker" / "docker-compose.gemini.yml"
                if not compose_file.exists():
                    logger.warning(f"Docker compose файл не найден: {compose_file}")
                    return False

                # 2. Проверяем, что Docker доступен
                docker_check = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
                if docker_check.returncode != 0:
                    logger.warning("Docker не установлен или недоступен")
                    return False

                # 3. Проверяем наличие docker compose
                compose_check = subprocess.run(["docker", "compose", "--version"], capture_output=True, text=True, timeout=5)
                if compose_check.returncode != 0:
                    logger.warning("Docker Compose не установлен или недоступен")
                    return False
                
                # 4. Проверяем наличие образа gemini-agent:latest
                image_check = subprocess.run(["docker", "images", "-q", "gemini-agent:latest"], capture_output=True, text=True, timeout=5)
                if not image_check.stdout.strip():
                    logger.warning("Docker образ gemini-agent:latest не найден. Создайте образ: docker compose -f docker/docker-compose.gemini.yml build")
                    return False

                logger.debug("Gemini CLI (Docker) доступен и готов к использованию")
                return True

            except Exception as e:
                logger.warning(f"Ошибка при проверке доступности Gemini CLI (Docker): {e}")
                return False
        else:
            # Локальный режим (без Docker)
            try:
                # Проверяем наличие gemini_agent_cli.py
                cli_path = Path(__file__).parent / "gemini_agent_cli.py"
                if not cli_path.exists():
                    logger.warning(f"Gemini CLI не найден: {cli_path}")
                    return False

                # Проверяем наличие GOOGLE_API_KEY
                load_dotenv()
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    logger.warning("GOOGLE_API_KEY не найден в переменных окружения")
                    return False

                # Проверяем, можем ли выполнить python скрипт
                result = subprocess.run(
                    [sys.executable, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode != 0:
                    logger.warning("Python не доступен для выполнения CLI")
                    return False

                logger.debug("Gemini CLI (локально) доступен")
                return True

            except Exception as e:
                logger.warning(f"Ошибка при проверке доступности Gemini CLI (локально): {e}")
                return False

    def is_available(self) -> bool:
        """
        Проверка доступности Gemini CLI

        Returns:
            True если CLI доступен, False иначе
        """
        return self.cli_available

    def _ensure_docker_container_running(self, compose_file: Path) -> Dict[str, Any]:
        """
        Проверяет статус Docker контейнера и запускает его, если он остановлен.
        """
        try:
            # Проверяем статус контейнера
            container_name = self.container_name
            inspect_cmd = ["docker", "inspect", "--format", "{{.State.Status}}", container_name]
            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=5)

            if inspect_result.returncode == 0:
                status = inspect_result.stdout.strip()
                if status == "running":
                    return {"running": True}

            # Контейнер не запущен - запускаем заново
            logger.info(f"Запуск Docker контейнера {container_name}...")
            up_cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d"]
            up_result = subprocess.run(up_cmd, capture_output=True, text=True, timeout=30)

            if up_result.returncode == 0:
                logger.info("Docker контейнер успешно запущен")
                import time
                time.sleep(3)  # Даем время на запуск
                return {"running": True}
            else:
                logger.error(f"Ошибка запуска контейнера: {up_result.stderr}")
                return {"running": False, "error": up_result.stderr}

        except Exception as e:
            logger.error(f"Ошибка при работе с Docker контейнером: {e}")
            return {"running": False, "error": str(e)}

    def execute_instruction(
        self,
        instruction: str,
        task_id: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        wait_for_file: Optional[str] = None,
        control_phrase: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполнить инструкцию через Gemini CLI
        """
        if not self.cli_available:
            return {
                "task_id": task_id,
                "success": False,
                "error_message": "Gemini CLI недоступен"
            }

        exec_timeout = timeout if timeout is not None else self.timeout

        # Определяем файл результата и контрольную фразу
        # Если wait_for_file передан, используем его, иначе дефолтный
        output_file = wait_for_file if wait_for_file else f"docs/results/result_{task_id}.md"
        # Если control_phrase передана, используем ее, иначе дефолтную
        # ВАЖНО: Если control_phrase не передана, используем "Задача выполнена успешно!" как дефолт
        target_control_phrase = control_phrase if control_phrase else "Задача выполнена успешно!"

        if self.use_docker:
            # --- Логика для Docker ---
            compose_file = Path(__file__).parent.parent.parent / "docker" / "docker-compose.gemini.yml"
            container_status = self._ensure_docker_container_running(compose_file)
            if not container_status.get("running"):
                return {
                    "task_id": task_id,
                    "success": False,
                    "error_message": f"Не удалось запустить Docker контейнер: {container_status.get('error')}"
                }

            import shlex
            api_key = os.getenv("GOOGLE_API_KEY")

            # Путь к скрипту внутри контейнера
            cli_path_in_container = "/usr/local/bin/gemini_agent_cli.py"
            
            # Формируем команду для выполнения внутри контейнера
            inner_cmd_parts = [
                "python",
                cli_path_in_container,
                shlex.quote(instruction),
                shlex.quote(output_file),
                shlex.quote(target_control_phrase),
                "--project_path",
                "/workspace" # В контейнере проект всегда в /workspace
            ]
            inner_cmd = " ".join(inner_cmd_parts)

            # Формируем полную команду docker exec
            cmd = ["docker", "exec"]
            if api_key:
                cmd.extend(["-e", f"GOOGLE_API_KEY={api_key}"])
            
            cmd.extend([
                self.container_name,
                "bash", "-c",
                inner_cmd
            ])
            
            logger.info(f"Выполнение команды через Gemini CLI (Docker): {' '.join(cmd)}")
            project_path_for_log = "/workspace"
            
        else:
            # --- Локальная логика ---
            cli_path = Path(__file__).parent / "gemini_agent_cli.py"
            project_path = working_dir or (str(self.project_dir) if self.project_dir else os.getcwd())

            cmd = [
                sys.executable,
                str(cli_path),
                instruction,
                output_file,
                target_control_phrase,
                "--project_path", project_path
            ]
            logger.info(f"Выполнение команды через Gemini CLI (локально): {' '.join(cmd)}")
            project_path_for_log = project_path

        logger.debug(f"Рабочая директория: {project_path_for_log}")
        logger.debug(f"Таймаут: {exec_timeout} секунд")

        try:
            result = subprocess.run(
                cmd,
                # Локально cwd нужен, для докера нет, так как он определяется в docker-compose
                cwd=project_path if not self.use_docker and Path(project_path).exists() else None,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                encoding='utf-8',
                errors='replace'
            )

            success = result.returncode == 0
            if success:
                logger.info(f"Команда Gemini CLI выполнена успешно (Docker: {self.use_docker})")
            else:
                logger.warning(f"Команда Gemini CLI (Docker: {self.use_docker}) завершилась с кодом {result.returncode}")
                logger.warning(f"Stderr: {result.stderr}")

            return {
                "task_id": task_id,
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "cli_available": True,
                "error_message": None if success else f"CLI вернул код {result.returncode}"
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Таймаут выполнения команды Gemini CLI ({exec_timeout} сек)")
            return {
                "task_id": task_id,
                "success": False,
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "cli_available": True,
                "error_message": f"Таймаут выполнения ({exec_timeout} секунд)"
            }

        except Exception as e:
            logger.error(f"Ошибка при выполнении команды Gemini CLI: {e}")
            return {
                "task_id": task_id,
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "cli_available": True,
                "error_message": f"Исключение: {str(e)}"
            }


def create_gemini_cli_interface(
    project_dir: Optional[str] = None,
    timeout: int = 300,
    container_name: Optional[str] = None
) -> GeminiCLIInterface:
    """
    Фабричная функция для создания интерфейса Gemini CLI

    Args:
        project_dir: Директория целевого проекта
        timeout: Таймаут по умолчанию
        container_name: Имя Docker контейнера

    Returns:
        Экземпляр GeminiCLIInterface
    """
    return GeminiCLIInterface(
        project_dir=project_dir,
        timeout=timeout,
        container_name=container_name
    )