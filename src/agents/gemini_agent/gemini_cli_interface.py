"""
Интерфейс взаимодействия с Gemini CLI

Этот модуль предоставляет возможность выполнения команд через Gemini CLI агент,
если он доступен в системе.
"""

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        container_name: Optional[str] = None,
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
        self.current_session_id: Optional[str] = None

        logger.debug(
            f"Инициализация GeminiCLIInterface: timeout={timeout} секунд, use_docker={self.use_docker}"
        )

    def _check_cli_availability(self) -> bool:
        """
        Проверка доступности Gemini CLI

        Returns:
            True если CLI доступен, False иначе
        """
        if self.use_docker:
            try:
                # 1. Проверяем наличие docker-compose файла
                compose_file = (
                    Path(__file__).parent.parent.parent.parent
                    / "docker"
                    / "docker-compose.gemini.yml"
                )
                if not compose_file.exists():
                    logger.warning(f"Docker compose файл не найден: {compose_file}")
                    return False

                # 2. Проверяем, что Docker доступен
                docker_check = subprocess.run(
                    ["docker", "--version"], capture_output=True, text=True, timeout=5
                )
                if docker_check.returncode != 0:
                    logger.warning("Docker не установлен или недоступен")
                    return False

                # 3. Проверяем наличие docker compose
                compose_check = subprocess.run(
                    ["docker", "compose", "--version"], capture_output=True, text=True, timeout=5
                )
                if compose_check.returncode != 0:
                    logger.warning("Docker Compose не установлен или недоступен")
                    return False

                # 4. Проверяем наличие образа gemini-agent:latest
                image_check = subprocess.run(
                    ["docker", "images", "-q", "gemini-agent:latest"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if not image_check.stdout.strip():
                    logger.warning(
                        "Docker образ gemini-agent:latest не найден. Создайте образ: docker compose -f docker/docker-compose.gemini.yml build"
                    )
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
                    [sys.executable, "--version"], capture_output=True, text=True, timeout=5
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

    def check_version(self) -> Optional[str]:
        """
        Проверка версии Gemini CLI

        Returns:
            Версия CLI или None если недоступен
        """
        if not self.cli_available:
            return None

        if self.use_docker:
            try:
                # Сначала проверяем/запускаем контейнер
                compose_file = (
                    Path(__file__).parent.parent.parent.parent
                    / "docker"
                    / "docker-compose.gemini.yml"
                )
                container_status = self._ensure_docker_container_running(compose_file)
                if not container_status.get("running"):
                    logger.warning(f"Контейнер не запущен: {container_status.get('error')}")
                    return None

                # Путь к скрипту внутри контейнера
                cli_path_in_container = "/usr/local/bin/gemini_agent_cli.py"

                # Проверяем версию agent в контейнере
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        self.container_name,
                        "python",
                        cli_path_in_container,
                        "--version",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    logger.warning(
                        f"Не удалось получить версию gemini_agent_cli в контейнере: {result.stderr}"
                    )
                    return None
            except subprocess.TimeoutExpired:
                logger.warning("Таймаут при проверке версии gemini_agent_cli в контейнере")
                return None
            except Exception as e:
                logger.error(f"Ошибка при проверке версии gemini_agent_cli в контейнере: {e}")
                return None
        else:
            # Для локального CLI
            try:
                cli_path = Path(__file__).parent / "gemini_agent_cli.py"
                result = subprocess.run(
                    [sys.executable, str(cli_path), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    logger.warning(
                        f"Не удалось получить версию gemini_agent_cli локально: {result.stderr}"
                    )
                    return None
            except Exception as e:
                logger.error(f"Ошибка при проверке версии gemini_agent_cli локально: {e}")
                return None

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
                    # Дополнительная проверка активности процессов внутри
                    if not self._check_docker_container_activity(container_name):
                        logger.warning(
                            f"Контейнер {container_name} запущен, но процессы gemini_agent_cli не обнаружены"
                        )
                    return {"running": True}
                elif status == "restarting":
                    logger.warning(
                        f"Контейнер {container_name} находится в состоянии 'restarting'. Перезапуск..."
                    )
                    subprocess.run(
                        ["docker", "rm", "-f", container_name], capture_output=True, timeout=10
                    )
                elif status == "exited" or status == "paused":
                    logger.info(f"Контейнер {container_name} в состоянии '{status}'. Запуск...")
                else:
                    logger.warning(f"Контейнер {container_name} в неожиданном состоянии: {status}")

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

    def _check_docker_container_activity(self, container_name: str) -> bool:
        """
        Проверить, активен ли Docker контейнер (выполняется ли в нем процесс)

        Args:
            container_name: Имя контейнера

        Returns:
            True если контейнер активен и выполняет процессы gemini_agent_cli
        """
        try:
            # Проверяем количество процессов в контейнере
            ps_cmd = [
                "docker",
                "exec",
                container_name,
                "bash",
                "-c",
                "ps aux | grep 'gemini_agent_cli' | grep -v grep | wc -l",
            ]
            ps_result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)

            if ps_result.returncode == 0:
                try:
                    process_count = int(ps_result.stdout.strip())
                    if process_count > 0:
                        logger.debug(
                            f"Контейнер активен: {process_count} процессов gemini_agent_cli"
                        )
                        return True
                except ValueError:
                    pass

            return False
        except Exception as e:
            logger.warning(f"Ошибка при проверке активности процессов в контейнере: {e}")
            return False

    def _verify_side_effects(self, expected_files: List[str]) -> bool:
        """
        Проверка side-effects (наличие ожидаемых файлов)

        Args:
            expected_files: Список ожидаемых файлов (относительно project_dir)

        Returns:
            True если все файлы существуют, False иначе
        """
        if not expected_files:
            return True

        if not self.project_dir:
            logger.warning("Невозможно проверить side-effects: project_dir не задан")
            return True  # Предполагаем успех если проверить нельзя

        for file_path in expected_files:
            full_path = self.project_dir / file_path
            if not full_path.exists():
                logger.debug(f"Ожидаемый файл не найден: {full_path}")
                return False

        logger.debug(f"Все ожидаемые файлы найдены: {len(expected_files)}")
        return True

    def stop_active_chats(self) -> bool:
        """
        Остановить все активные процессы gemini_agent_cli

        Returns:
            True если остановка выполнена успешно
        """
        if not self.cli_available:
            logger.warning("Gemini CLI недоступен для остановки процессов")
            return False

        try:
            if self.use_docker:
                logger.debug("Остановка активных процессов gemini_agent_cli в Docker контейнере...")
                kill_cmd = [
                    "docker",
                    "exec",
                    self.container_name,
                    "bash",
                    "-c",
                    "pkill -f 'gemini_agent_cli' || true",
                ]
                subprocess.run(kill_cmd, capture_output=True, text=True, timeout=15)
                return True
            else:
                # Локально сложнее безопасно убить процессы, но попробуем по имени
                logger.debug("Остановка активных процессов gemini_agent_cli локально...")
                if sys.platform == "win32":
                    kill_cmd = [
                        "taskkill",
                        "/F",
                        "/IM",
                        "python.exe",
                        "/FI",
                        "WINDOWTITLE eq gemini_agent_cli*",
                    ]
                    # Это может быть ненадежно, так как python.exe может не иметь такого заголовка
                    # Проще пропустить для локального режима или использовать psutil если он есть
                    pass
                else:
                    kill_cmd = ["pkill", "-f", "gemini_agent_cli"]
                    subprocess.run(kill_cmd, capture_output=True, text=True, timeout=5)
                return True
        except Exception as e:
            logger.error(f"Ошибка при остановке процессов Gemini CLI: {e}")
            return False

    def resume_chat(self, chat_id: Optional[str] = None) -> bool:
        """
        Возобновить чат (установить текущий session_id для продолжения диалога)

        Args:
            chat_id: ID сессии (чата) для возобновления

        Returns:
            True если сессия установлена
        """
        if chat_id:
            self.current_session_id = chat_id
            logger.info(f"Установлен session_id для продолжения диалога Gemini: {chat_id}")
            return True
        return False

    def execute_instruction(
        self,
        instruction: str,
        task_id: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        wait_for_file: Optional[str] = None,
        control_phrase: Optional[str] = None,
        session_id: Optional[str] = None,
        expected_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Выполнить инструкцию через Gemini CLI
        """
        if not self.cli_available:
            return {"task_id": task_id, "success": False, "error_message": "Gemini CLI недоступен"}

        exec_timeout = timeout if timeout is not None else self.timeout

        # Используем переданный session_id или текущий в интерфейсе
        target_session_id = session_id or self.current_session_id

        # Определяем файл результата и контрольную фразу
        # Если wait_for_file передан, используем его, иначе дефолтный
        output_file = wait_for_file if wait_for_file else f"docs/results/result_{task_id}.md"
        # Если control_phrase передана, используем ее, иначе дефолтную
        # ВАЖНО: Если control_phrase не передана, используем "Задача выполнена успешно!" как дефолт
        target_control_phrase = control_phrase if control_phrase else "Задача выполнена успешно!"

        if self.use_docker:
            # --- Логика для Docker ---
            compose_file = (
                Path(__file__).parent.parent.parent.parent / "docker" / "docker-compose.gemini.yml"
            )
            container_status = self._ensure_docker_container_running(compose_file)
            if not container_status.get("running"):
                return {
                    "task_id": task_id,
                    "success": False,
                    "error_message": f"Не удалось запустить Docker контейнер: {container_status.get('error')}",
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
                "/workspace",  # В контейнере проект всегда в /workspace
            ]

            if target_session_id:
                inner_cmd_parts.extend(["--session_id", shlex.quote(target_session_id)])

            inner_cmd = " ".join(inner_cmd_parts)

            # Формируем полную команду docker exec
            cmd = ["docker", "exec"]
            if api_key:
                cmd.extend(["-e", f"GOOGLE_API_KEY={api_key}"])

            cmd.extend([self.container_name, "bash", "-c", inner_cmd])

            logger.info(f"Выполнение команды через Gemini CLI (Docker): {' '.join(cmd)}")
            project_path_for_log = "/workspace"

        else:
            # --- Локальная логика ---
            cli_path = Path(__file__).parent / "gemini_agent_cli.py"
            project_path = working_dir or (
                str(self.project_dir) if self.project_dir else os.getcwd()
            )

            cmd = [
                sys.executable,
                str(cli_path),
                instruction,
                output_file,
                target_control_phrase,
                "--project_path",
                project_path,
            ]

            if target_session_id:
                cmd.extend(["--session_id", target_session_id])

            logger.info(f"Выполнение команды через Gemini CLI (локально): {' '.join(cmd)}")
            project_path_for_log = project_path

        logger.debug(f"Рабочая директория: {project_path_for_log}")
        logger.debug(f"Таймаут: {exec_timeout} секунд")

        try:
            import subprocess
            import threading

            process = subprocess.Popen(
                cmd,
                cwd=project_path if not self.use_docker and Path(project_path).exists() else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,  # Line buffered
            )

            stdout_lines = []
            stderr_lines = []

            def read_pipe(pipe, lines_list, is_stderr=False):
                for line in iter(pipe.readline, ""):
                    if line:
                        lines_list.append(line)
                        try:
                            if is_stderr:
                                sys.stderr.write(line)
                                sys.stderr.flush()
                            else:
                                sys.stdout.write(line)
                                sys.stdout.flush()
                        except UnicodeEncodeError:
                            # Fallback for systems with non-utf-8 terminals (e.g. Windows CP1251)
                            safe_line = line.encode(sys.stdout.encoding, errors="replace").decode(
                                sys.stdout.encoding
                            )
                            if is_stderr:
                                sys.stderr.write(safe_line)
                                sys.stderr.flush()
                            else:
                                sys.stdout.write(safe_line)
                                sys.stdout.flush()
                pipe.close()

            stdout_thread = threading.Thread(
                target=read_pipe, args=(process.stdout, stdout_lines, False)
            )
            stderr_thread = threading.Thread(
                target=read_pipe, args=(process.stderr, stderr_lines, True)
            )

            stdout_thread.start()
            stderr_thread.start()

            # Ждем завершения процесса с таймаутом
            try:
                return_code = process.wait(timeout=exec_timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                # Читаем то, что успело прийти
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)
                raise

            stdout_thread.join()
            stderr_thread.join()

            stdout = "".join(stdout_lines)
            stderr = "".join(stderr_lines)

            success = return_code == 0

            # Проверка side-effects
            side_effects_ok = True
            if success and expected_files:
                side_effects_ok = self._verify_side_effects(expected_files)
                if not side_effects_ok:
                    logger.warning(
                        f"Команда Gemini CLI выполнена, но side-effects не подтверждены: {expected_files}"
                    )
                    success = False  # Считаем неудачей если файлы не созданы

            if success:
                logger.info(f"Команда Gemini CLI выполнена успешно (Docker: {self.use_docker})")
            else:
                if not side_effects_ok:
                    error_msg = (
                        f"Side-effects не подтверждены (отсутствуют файлы: {expected_files})"
                    )
                else:
                    error_msg = f"CLI вернул код {return_code}"

                logger.warning(
                    f"Команда Gemini CLI (Docker: {self.use_docker}) завершилась неуспешно"
                )
                # stderr уже выведен в консоль

            return {
                "task_id": task_id,
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "cli_available": True,
                "side_effects_verified": side_effects_ok,
                "error_message": None if success else error_msg,
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Таймаут выполнения команды Gemini CLI ({exec_timeout} сек)")
            if self.use_docker:
                logger.warning("Попытка остановить зависшие процессы в Docker контейнере...")
                self.stop_active_chats()
            return {
                "task_id": task_id,
                "success": False,
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "cli_available": True,
                "error_message": f"Таймаут выполнения ({exec_timeout} секунд)",
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
                "error_message": f"Исключение: {str(e)}",
            }


def create_gemini_cli_interface(
    project_dir: Optional[str] = None, timeout: int = 300, container_name: Optional[str] = None
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
        project_dir=project_dir, timeout=timeout, container_name=container_name
    )
