"""
Docker Utils - утилиты для работы с Docker
"""

import subprocess
import logging
from typing import Optional, Tuple, List
import os

logger = logging.getLogger(__name__)


class DockerChecker:
    """
    Класс для проверки доступности Docker и управления Docker-контейнерами
    """

    @staticmethod
    def is_docker_available() -> bool:
        """
        Проверяет доступность Docker

        Returns:
            bool: True если Docker доступен, False в противном случае
        """
        try:
            # Проверяем, что команда docker доступна
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning("Docker command not available or returned non-zero exit code")
                return False

            # Проверяем, что Docker daemon работает
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning("Docker daemon is not running or not accessible")
                return False

            logger.info("Docker is available and running")
            return True

        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            logger.warning(f"Docker availability check failed: {e}")
            return False

    @staticmethod
    def get_docker_version() -> Optional[str]:
        """
        Получает версию Docker

        Returns:
            Optional[str]: Версия Docker или None если не удалось получить
        """
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Парсим версию из вывода типа "Docker version 24.0.6, build ed223bc"
                version_line = result.stdout.strip()
                if 'version' in version_line.lower():
                    parts = version_line.split()
                    if len(parts) >= 3:
                        return parts[2].rstrip(',')
                return version_line

        except Exception as e:
            logger.debug(f"Failed to get Docker version: {e}")

        return None

    @staticmethod
    def check_docker_permissions() -> Tuple[bool, str]:
        """
        Проверяет права доступа к Docker

        Returns:
            Tuple[bool, str]: (успешно, сообщение)
        """
        try:
            # Пытаемся выполнить простую команду docker
            result = subprocess.run(
                ['docker', 'ps'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return True, "Docker permissions OK"
            else:
                error_msg = result.stderr.strip() or "Unknown Docker permission error"
                return False, f"Docker permission check failed: {error_msg}"

        except Exception as e:
            return False, f"Docker permission check failed: {str(e)}"

    @staticmethod
    def get_running_containers() -> List[str]:
        """
        Получает список запущенных контейнеров

        Returns:
            List[str]: Список имен контейнеров
        """
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                containers = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                return containers

        except Exception as e:
            logger.debug(f"Failed to get running containers: {e}")

        return []

    @staticmethod
    def is_container_running(container_name: str) -> bool:
        """
        Проверяет, запущен ли контейнер с указанным именем

        Args:
            container_name: Имя контейнера

        Returns:
            bool: True если контейнер запущен
        """
        running_containers = DockerChecker.get_running_containers()
        return container_name in running_containers


class DockerManager:
    """
    Класс для управления Docker-контейнерами
    """

    def __init__(self, image_name: str = "cursor-agent:latest", container_name: str = "cursor-agent-life"):
        """
        Инициализация Docker Manager

        Args:
            image_name: Имя Docker образа
            container_name: Имя контейнера
        """
        self.image_name = image_name
        self.container_name = container_name
        self.logger = logging.getLogger(__name__)

    def start_container(self, workspace_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Запускает Docker контейнер

        Args:
            workspace_path: Путь к рабочей директории для монтирования

        Returns:
            Tuple[bool, str]: (успешно, сообщение)
        """
        try:
            # Проверяем доступность Docker
            if not DockerChecker.is_docker_available():
                return False, "Docker is not available"

            # Проверяем, запущен ли уже контейнер
            if DockerChecker.is_container_running(self.container_name):
                return True, f"Container {self.container_name} is already running"

            # Формируем команду запуска
            cmd = [
                'docker', 'run', '-d',
                '--name', self.container_name,
                '-e', 'LANG=C.utf8',
                '-e', 'LC_ALL=C.utf8'
            ]

            # Добавляем монтирование рабочей директории
            if workspace_path:
                workspace_path = os.path.abspath(workspace_path)
                cmd.extend(['-v', f'{workspace_path}:/workspace:rw'])

            # Добавляем образ
            cmd.append(self.image_name)

            self.logger.info(f"Starting Docker container with command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                container_id = result.stdout.strip()
                self.logger.info(f"Docker container started: {container_id}")
                return True, f"Container started successfully: {container_id[:12]}"
            else:
                error_msg = result.stderr.strip()
                self.logger.error(f"Failed to start Docker container: {error_msg}")
                return False, f"Failed to start container: {error_msg}"

        except Exception as e:
            error_msg = f"Exception while starting Docker container: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def stop_container(self) -> Tuple[bool, str]:
        """
        Останавливает Docker контейнер

        Returns:
            Tuple[bool, str]: (успешно, сообщение)
        """
        try:
            if not DockerChecker.is_container_running(self.container_name):
                return True, f"Container {self.container_name} is not running"

            result = subprocess.run(
                ['docker', 'stop', self.container_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.logger.info(f"Docker container stopped: {self.container_name}")
                return True, "Container stopped successfully"
            else:
                error_msg = result.stderr.strip()
                self.logger.error(f"Failed to stop Docker container: {error_msg}")
                return False, f"Failed to stop container: {error_msg}"

        except Exception as e:
            error_msg = f"Exception while stopping Docker container: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def execute_command(self, command: str, working_dir: str = "/workspace") -> Tuple[bool, str, str]:
        """
        Выполняет команду в Docker контейнере

        Args:
            command: Команда для выполнения
            working_dir: Рабочая директория в контейнере

        Returns:
            Tuple[bool, str, str]: (успешно, stdout, stderr)
        """
        try:
            if not DockerChecker.is_container_running(self.container_name):
                return False, "", f"Container {self.container_name} is not running"

            cmd = [
                'docker', 'exec',
                '-w', working_dir,
                self.container_name,
                'bash', '-c', command
            ]

            self.logger.debug(f"Executing command in container: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode == 0:
                return True, stdout, stderr
            else:
                return False, stdout, stderr

        except subprocess.TimeoutExpired:
            return False, "", "Command execution timed out"
        except Exception as e:
            return False, "", f"Exception during command execution: {str(e)}"