"""
Интерфейс взаимодействия с Cursor через CLI

Этот модуль предоставляет возможность выполнения команд через Cursor CLI,
если он доступен в системе. В противном случае возвращает информацию
о недоступности для использования fallback на файловый интерфейс.
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

try:
    from .prompt_formatter import PromptFormatter
except ImportError:
    # Fallback если модуль еще не создан
    PromptFormatter = None

logger = logging.getLogger(__name__)


@dataclass
class CursorCLIResult:
    """Результат выполнения команды через Cursor CLI"""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    cli_available: bool
    error_message: Optional[str] = None


class CursorCLIInterface:
    """
    Интерфейс взаимодействия с Cursor через CLI
    
    Использует официальную команду `agent` для выполнения инструкций в headless режиме.
    Согласно официальной документации: https://cursor.com/docs/cli/overview
    
    Автоматически проверяет доступность CLI при инициализации.
    """
    
    # Возможные имена команды Cursor CLI
    # Официальная команда согласно https://cursor.com/docs/cli/overview
    CLI_COMMAND_NAMES = [
        "agent",          # Официальная команда (устанавливается через curl https://cursor.com/install)
        "cursor-agent",   # Альтернативное имя (может быть установлено отдельно)
        "cursor",
        "cursor-cli"
    ]
    
    def __init__(
        self,
        cli_path: Optional[str] = None,
        default_timeout: int = 300,
        headless: bool = True,
        project_dir: Optional[str] = None,
        agent_role: Optional[str] = None
    ):
        """
        Инициализация интерфейса Cursor CLI
        
        Args:
            cli_path: Путь к исполняемому файлу Cursor CLI (если None - поиск в PATH)
            default_timeout: Таймаут по умолчанию для выполнения команд (секунды)
            headless: Использовать headless режим
            project_dir: Директория целевого проекта (для установки рабочей директории)
            agent_role: Роль агента для настройки через .cursor/rules или AGENTS.md
        """
        self.default_timeout = default_timeout
        self.headless = headless
        self.cli_command = None
        self.cli_available = False
        self.project_dir = Path(project_dir) if project_dir else None
        self.agent_role = agent_role
        self.current_chat_id: Optional[str] = None  # Текущий активный chat_id для продолжения диалога
        
        # Поиск доступного CLI
        if cli_path:
            # Специальный маркер для Docker
            if cli_path == "docker-compose-agent":
                self.cli_command = "docker-compose-agent"
                # Проверяем доступность Docker и возможность запустить контейнер
                compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
                docker_available = self._check_docker_availability(compose_file)
                self.cli_available = docker_available
                if docker_available:
                    logger.info("Использование Docker Compose для Cursor CLI - Docker доступен")
                else:
                    logger.warning("Docker Compose указан, но Docker недоступен или контейнер не может быть запущен")
            elif os.path.exists(cli_path) and os.access(cli_path, os.X_OK):
                self.cli_command = cli_path
                self.cli_available = True
                logger.info(f"Cursor CLI найден по указанному пути: {cli_path}")
            else:
                logger.warning(f"Указанный путь к Cursor CLI недоступен: {cli_path}")
        else:
            # Поиск в PATH
            self.cli_command, self.cli_available = self._find_cli_in_path()
            if self.cli_available:
                logger.info(f"Cursor CLI найден в PATH: {self.cli_command}")
            else:
                logger.warning("Cursor CLI не найден в системе")
    
    def _find_cli_in_path(self) -> tuple[Optional[str], bool]:
        """
        Поиск команды Cursor CLI в системном PATH
        Включает проверку через WSL и Docker для Windows
        
        Приоритет:
        1. Стандартный PATH (agent, cursor-agent, etc.)
        2. WSL (если Windows)
        3. Docker (cursor-agent:latest образ)
        
        Returns:
            Кортеж (путь к команде, доступна ли)
        """
        # Сначала проверяем стандартный PATH
        for cmd_name in self.CLI_COMMAND_NAMES:
            cmd_path = shutil.which(cmd_name)
            if cmd_path:
                return cmd_path, True
        
        # Если не найдено и это Windows, проверяем через WSL
        if os.name == 'nt':  # Windows
            try:
                # Проверяем наличие agent в WSL
                result = subprocess.run(
                    ["wsl", "which", "agent"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    # Agent найден в WSL - возвращаем команду для запуска через WSL
                    logger.info("Agent найден в WSL")
                    return "wsl agent", True
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                # WSL недоступен или ошибка - игнорируем
                pass
        
        # Если не найдено, проверяем Docker образ
        try:
            # Проверяем наличие Docker образа cursor-agent:latest
            result = subprocess.run(
                ["docker", "images", "-q", "cursor-agent:latest"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # Проверяем также наличие docker compose
                compose_result = subprocess.run(
                    ["docker", "compose", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if compose_result.returncode == 0:
                    logger.info("Agent найден в Docker (cursor-agent:latest)")
                    # Возвращаем специальный маркер для Docker
                    return "docker-compose-agent", True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            # Docker недоступен или ошибка - игнорируем
            logger.debug(f"Docker проверка не удалась: {e}")
            pass
        
        return None, False
    
    def _check_docker_availability(self, compose_file: Path) -> bool:
        """
        Проверить доступность Docker и возможность запустить контейнер
        
        Args:
            compose_file: Путь к docker-compose.agent.yml
            
        Returns:
            True если Docker доступен и compose файл существует, False иначе
        """
        try:
            # Проверяем наличие docker-compose файла
            if not compose_file.exists():
                logger.warning(f"Docker compose файл не найден: {compose_file}")
                return False
            
            # Проверяем, что Docker доступен
            docker_check = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if docker_check.returncode != 0:
                logger.warning("Docker не установлен или недоступен")
                return False
            
            # Проверяем наличие docker compose
            compose_check = subprocess.run(
                ["docker", "compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if compose_check.returncode != 0:
                logger.warning("Docker Compose не установлен или недоступен")
                return False
            
            # Проверяем наличие образа cursor-agent:latest
            image_check = subprocess.run(
                ["docker", "images", "-q", "cursor-agent:latest"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if not image_check.stdout.strip():
                logger.warning("Docker образ cursor-agent:latest не найден. Создайте образ: docker compose -f docker/docker-compose.agent.yml build")
                return False
            
            logger.debug("Docker доступен и готов к использованию")
            return True
            
        except subprocess.TimeoutExpired:
            logger.warning("Таймаут при проверке Docker")
            return False
        except FileNotFoundError:
            logger.warning("Docker не найден в системе")
            return False
        except Exception as e:
            logger.warning(f"Ошибка при проверке Docker: {e}")
            return False
    
    def _check_docker_container_activity(self, container_name: str) -> bool:
        """
        Проверить, активен ли Docker контейнер (выполняется ли в нем процесс)
        
        Args:
            container_name: Имя контейнера
            
        Returns:
            True если контейнер активен и выполняет процессы
        """
        try:
            # Проверяем количество процессов в контейнере
            ps_cmd = [
                "docker", "exec", container_name,
                "bash", "-c",
                "ps aux | grep -E 'agent|cursor' | grep -v grep | wc -l"
            ]
            ps_result = subprocess.run(
                ps_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if ps_result.returncode == 0:
                process_count = int(ps_result.stdout.strip())
                if process_count > 0:
                    logger.debug(f"Контейнер активен: {process_count} процессов agent/cursor")
                    return True
                else:
                    logger.debug("Контейнер не выполняет процессы agent/cursor")
                    return False
            
            # Дополнительная проверка - статус контейнера
            inspect_cmd = [
                "docker", "inspect",
                "--format", "{{.State.Status}}",
                container_name
            ]
            inspect_result = subprocess.run(
                inspect_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if inspect_result.returncode == 0:
                status = inspect_result.stdout.strip()
                is_active = status == "running"
                logger.debug(f"Статус контейнера: {status}, активен: {is_active}")
                return is_active
            
            return False
            
        except Exception as e:
            logger.warning(f"Ошибка проверки активности контейнера: {e}")
            return False
    
    def _ensure_docker_container_running(self, compose_file: Path) -> Dict[str, Any]:
        """
        Проверяет статус Docker контейнера и запускает его, если он остановлен.
        Также проверяет, что контейнер не в состоянии постоянного перезапуска.
        
        Args:
            compose_file: Путь к docker-compose.agent.yml
            
        Returns:
            Словарь с информацией о статусе контейнера
        """
        try:
            # Сначала проверяем, что Docker вообще работает
            docker_check = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if docker_check.returncode != 0:
                logger.error("Docker не запущен или недоступен")
                return {
                    "running": False,
                    "error": "Docker не запущен. Запустите Docker Desktop и повторите попытку."
                }
            
            # Проверяем статус конкретного контейнера
            container_name = "cursor-agent-life"
            inspect_cmd = [
                "docker", "inspect",
                "--format", "{{.State.Status}}",
                container_name
            ]
            inspect_result = subprocess.run(
                inspect_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if inspect_result.returncode == 0:
                status = inspect_result.stdout.strip()
                logger.debug(f"Docker контейнер {container_name} статус: {status}")
                
                # Проверяем, что контейнер не в состоянии Restarting
                if status == "restarting":
                    logger.error(f"Контейнер {container_name} постоянно перезапускается! Удаляем проблемный контейнер...")
                    # Останавливаем и удаляем проблемный контейнер
                    subprocess.run(["docker", "stop", container_name], timeout=10, capture_output=True)
                    subprocess.run(["docker", "rm", container_name], timeout=10, capture_output=True)
                    logger.info(f"Проблемный контейнер {container_name} удален, будет создан заново")
                    status = "removed"
                
                if status == "running":
                    # Дополнительно проверяем, что контейнер отвечает
                    health_check = subprocess.run(
                        ["docker", "exec", container_name, "echo", "ok"],
                        capture_output=True,
                        timeout=5
                    )
                    if health_check.returncode == 0:
                        logger.debug("Docker контейнер работает корректно")
                        return {"running": True}
                    else:
                        logger.warning("Контейнер запущен, но не отвечает. Перезапускаем...")
                        subprocess.run(["docker", "restart", container_name], timeout=15, capture_output=True)
                        import time
                        time.sleep(3)
                        return {"running": True}
            
            # Контейнер не запущен или работает некорректно - запускаем заново
            logger.info(f"Запуск Docker контейнера {container_name}...")
            up_cmd = [
                "docker", "compose",
                "-f", str(compose_file),
                "up", "-d"
            ]
            up_result = subprocess.run(
                up_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if up_result.returncode == 0:
                logger.info("Docker контейнер успешно запущен")
                # Даем контейнеру время на запуск и проверяем статус
                import time
                time.sleep(3)
                
                # Проверяем, что контейнер действительно запустился
                final_check = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if final_check.returncode == 0:
                    final_status = final_check.stdout.strip()
                    if final_status == "running":
                        logger.info("Контейнер успешно запущен и работает")
                        return {"running": True}
                    elif final_status == "restarting":
                        logger.error(f"Контейнер сразу начал перезапускаться! Проверьте логи: docker logs {container_name}")
                        return {
                            "running": False,
                            "error": f"Контейнер постоянно перезапускается. Проверьте логи: docker logs {container_name}"
                        }
                    else:
                        logger.error(f"Контейнер запущен, но в состоянии: {final_status}")
                        return {
                            "running": False,
                            "error": f"Контейнер в неожиданном состоянии: {final_status}"
                        }
                
                return {"running": True}
            else:
                logger.error(f"Ошибка запуска контейнера: {up_result.stderr}")
                return {
                    "running": False,
                    "error": up_result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Таймаут при проверке/запуске Docker контейнера")
            return {
                "running": False,
                "error": "Таймаут при проверке/запуске контейнера"
            }
        except Exception as e:
            logger.error(f"Ошибка при работе с Docker контейнером: {e}")
            return {
                "running": False,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """
        Проверка доступности Cursor CLI
        
        Returns:
            True если CLI доступен, False иначе
        """
        # Для Docker дополнительно проверяем статус контейнера
        if self.cli_command == "docker-compose-agent":
            # Проверяем статус контейнера (без запуска, только проверка)
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Status}}", "cursor-agent-life"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    status = result.stdout.strip()
                    # Контейнер доступен если он running или stopped (можно запустить)
                    return status in ["running", "exited", "created"]
            except Exception:
                # При ошибке проверки используем базовую доступность
                pass
        
        return self.cli_available
    
    def check_version(self) -> Optional[str]:
        """
        Проверка версии Cursor CLI
        
        Returns:
            Версия CLI или None если недоступен
        """
        if not self.cli_available:
            return None
        
        # Для Docker проверяем версию через exec в контейнере
        if self.cli_command == "docker-compose-agent":
            try:
                # Сначала проверяем/запускаем контейнер
                compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
                container_status = self._ensure_docker_container_running(compose_file)
                if not container_status.get("running"):
                    logger.warning(f"Контейнер не запущен: {container_status.get('error')}")
                    return None
                
                # Проверяем версию agent в контейнере
                result = subprocess.run(
                    ["docker", "exec", "cursor-agent-life", "/root/.local/bin/agent", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    logger.warning(f"Не удалось получить версию agent в контейнере: {result.stderr}")
                    return None
            except subprocess.TimeoutExpired:
                logger.warning("Таймаут при проверке версии agent в контейнере")
                return None
            except Exception as e:
                logger.error(f"Ошибка при проверке версии agent в контейнере: {e}")
                return None
        
        # Для локального CLI
        try:
            result = subprocess.run(
                [self.cli_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"Не удалось получить версию CLI: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning("Таймаут при проверке версии CLI")
            return None
        except Exception as e:
            logger.error(f"Ошибка при проверке версии CLI: {e}")
            return None
    
    def _setup_agent_role(self, project_dir: str, agent_role: str) -> None:
        """
        Настроить роль агента в целевом проекте через .cursor/rules или AGENTS.md
        
        Cursor CLI автоматически читает файлы:
        - .cursor/rules - правила и инструкции для агента
        - AGENTS.md - описание ролей агентов
        - CLAUDE.md - контекст для Claude API
        
        Args:
            project_dir: Директория целевого проекта
            agent_role: Роль агента для настройки
        """
        project_path = Path(project_dir)
        if not project_path.exists():
            logger.warning(f"Директория проекта не существует: {project_dir}")
            return
        
        # Проверяем существование .cursor/rules - Cursor автоматически читает их
        cursor_rules_dir = project_path / ".cursor" / "rules"
        if cursor_rules_dir.exists():
            logger.debug(f"Директория .cursor/rules существует, роль агента будет настроена через правила")
            # Cursor CLI автоматически использует .cursor/rules, дополнительная настройка не требуется
        
        # Можно создать AGENTS.md с описанием роли (опционально)
        agents_md = project_path / "AGENTS.md"
        if not agents_md.exists() and agent_role:
            try:
                content = f"""# Agent Roles

## {agent_role}

This agent role is used for automated project tasks execution.

**Role:** {agent_role}

**Capabilities:**
- Execute tasks from todo lists
- Update project documentation
- Modify code according to project requirements
- Maintain code quality and best practices
"""
                agents_md.write_text(content, encoding='utf-8')
                logger.info(f"Создан файл AGENTS.md с ролью агента: {agent_role}")
            except Exception as e:
                logger.warning(f"Не удалось создать AGENTS.md: {e}")
    
    def list_chats(self) -> list[str]:
        """
        Получить список доступных чатов через 'agent ls'
        
        Returns:
            Список chat_id или пустой список при ошибке
        """
        if not self.cli_available:
            logger.warning("Cursor CLI недоступен для list_chats")
            return []
        
        try:
            use_docker = self.cli_command == "docker-compose-agent"
            
            if use_docker:
                cmd = [
                    "docker", "exec", "-i",
                    "cursor-agent-life",
                    "bash", "-c",
                    "cd /workspace && /root/.local/bin/agent ls"
                ]
            else:
                cmd = [self.cli_command, "ls"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Парсим вывод 'agent ls' для извлечения chat_id
                # ИСПРАВЛЕНИЕ: Фильтруем ANSI escape sequences и невалидные строки
                import re
                chat_ids = []
                
                # Убираем ANSI escape sequences
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean_output = ansi_escape.sub('', result.stdout)
                
                for line in clean_output.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('['):
                        continue  # Пропускаем пустые строки, комментарии и ANSI escape
                    
                    # Игнорируем строки с только спецсимволами
                    if re.match(r'^[\s\-=:]+$', line):
                        continue
                    
                    # Предполагаем формат: chat_id или описание chat_id
                    parts = line.split()
                    if parts:
                        potential_id = parts[0]
                        # Фильтруем невалидные chat_id (должны быть алфавитно-цифровые или UUID)
                        if re.match(r'^[a-zA-Z0-9\-_]+$', potential_id) and len(potential_id) > 2:
                            chat_ids.append(potential_id)
                
                logger.debug(f"Найдено {len(chat_ids)} chat IDs: {chat_ids[:5]}")
                return chat_ids
            else:
                logger.warning(f"Ошибка при получении списка чатов: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка в list_chats: {e}")
            return []
    
    def resume_chat(self, chat_id: Optional[str] = None) -> bool:
        """
        Возобновить чат (установить текущий chat_id для продолжения диалога)
        
        Args:
            chat_id: ID чата для возобновления (если None - использует последний)
            
        Returns:
            True если чат успешно возобновлен
        """
        if chat_id:
            self.current_chat_id = chat_id
            logger.info(f"Установлен chat_id для продолжения диалога: {chat_id}")
            return True
        else:
            # Пробуем получить последний чат через 'agent resume'
            try:
                use_docker = self.cli_command == "docker-compose-agent"
                
                if use_docker:
                    cmd = [
                        "docker", "exec", "-i",
                        "cursor-agent-life",
                        "bash", "-c",
                        "cd /workspace && /root/.local/bin/agent resume --dry-run 2>&1 || /root/.local/bin/agent ls | head -n 1"
                    ]
                else:
                    cmd = [self.cli_command, "resume", "--dry-run"]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Парсим вывод для получения chat_id
                if result.returncode == 0 or result.stdout.strip():
                    output = result.stdout.strip()
                    # Упрощенная логика - предполагаем, что первая строка содержит chat_id
                    if output:
                        self.current_chat_id = output.split()[0] if output.split() else None
                        logger.info(f"Автоматически возобновлен чат: {self.current_chat_id}")
                        return True
                
                logger.warning("Не удалось определить chat_id для возобновления")
                return False
                
            except Exception as e:
                logger.error(f"Ошибка при возобновлении чата: {e}")
                return False
    
    def stop_active_chats(self) -> bool:
        """
        Остановить все активные чаты/диалоги в Docker контейнере
        
        Returns:
            True если остановка выполнена успешно
        """
        if not self.cli_available:
            logger.warning("Cursor CLI недоступен для остановки чатов")
            return False
        
        try:
            use_docker = self.cli_command == "docker-compose-agent"
            
            if use_docker:
                # Останавливаем все процессы agent в контейнере
                logger.info("Остановка активных процессов agent в Docker контейнере...")
                
                # Находим и убиваем все процессы agent
                # pkill возвращает 1 если процессов не найдено - это нормально
                kill_cmd = [
                    "docker", "exec", "cursor-agent-life",
                    "bash", "-c",
                    "pkill -f 'agent.*-p' || pkill -f '/root/.local/bin/agent' || true"
                ]
                
                result = subprocess.run(
                    kill_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Команда с || true всегда возвращает 0
                # Проверяем, были ли найдены процессы через stderr или попытку поиска
                # Если pkill не нашел процессы - это нормально (их может не быть)
                if result.returncode == 0:
                    # Проверяем, действительно ли процессы были остановлены
                    # Пытаемся найти процессы еще раз - если их нет, значит остановка успешна
                    check_cmd = [
                        "docker", "exec", "cursor-agent-life",
                        "bash", "-c",
                        "pgrep -f 'agent.*-p' || pgrep -f '/root/.local/bin/agent' || true"
                    ]
                    check_result = subprocess.run(
                        check_cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    # Если pgrep ничего не нашел (процессы остановлены) или нашел что-то (значит остановка частичная)
                    if not check_result.stdout.strip():
                        logger.info("Активные процессы agent остановлены (или их не было)")
                    else:
                        logger.info(f"Попытка остановки выполнена (найдено процессов: {len(check_result.stdout.strip().split())})")
                    return True
                else:
                    logger.warning(f"Не удалось остановить процессы: {result.stderr or result.stdout}")
                    return False
            else:
                # Для не-Docker окружения - пытаемся убить процессы локально
                logger.info("Остановка активных процессов agent...")
                try:
                    if sys.platform == 'win32':
                        # Windows
                        subprocess.run(
                            ["taskkill", "/F", "/FI", "WINDOWTITLE eq *agent*"],
                            capture_output=True,
                            timeout=5
                        )
                    else:
                        # Unix
                        subprocess.run(
                            ["pkill", "-f", "agent"],
                            capture_output=True,
                            timeout=5
                        )
                    logger.info("Процессы agent остановлены")
                    return True
                except Exception as e:
                    logger.warning(f"Ошибка при остановке процессов: {e}")
                    return False
                
        except Exception as e:
            logger.error(f"Ошибка при остановке активных чатов: {e}")
            return False
    
    def clear_chat_queue(self) -> bool:
        """
        Очистить очередь диалогов (удалить все чаты)
        
        Returns:
            True если очистка выполнена успешно
        """
        if not self.cli_available:
            logger.warning("Cursor CLI недоступен для очистки очереди")
            return False
        
        try:
            # Сначала останавливаем активные чаты
            self.stop_active_chats()
            
            # Получаем список всех чатов
            chat_ids = self.list_chats()
            
            if not chat_ids:
                logger.info("Нет чатов для удаления")
                return True
            
            logger.info(f"Найдено {len(chat_ids)} чатов для удаления")
            
            use_docker = self.cli_command == "docker-compose-agent"
            
            # Удаляем каждый чат (если есть такая команда в agent)
            # Примечание: agent может не поддерживать прямого удаления чатов,
            # поэтому мы просто останавливаем процессы и сбрасываем текущий chat_id
            deleted_count = 0
            
            # ПРИМЕЧАНИЕ: Cursor agent CLI может не поддерживать команду delete
            # В этом случае мы просто останавливаем процессы и сбрасываем chat_id
            # Чаты могут остаться в базе данных agent, но активные процессы будут остановлены
            logger.debug(f"Попытка удаления {len(chat_ids)} чатов (команда может не поддерживаться)")
            
            for chat_id in chat_ids:
                try:
                    # Пытаемся удалить через команду (если существует)
                    if use_docker:
                        cmd = [
                            "docker", "exec", "cursor-agent-life",
                            "bash", "-c",
                            f"cd /workspace && /root/.local/bin/agent delete {chat_id} 2>&1 || true"
                        ]
                    else:
                        cmd = [self.cli_command, "delete", chat_id]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    # Проверяем вывод - если команда не поддерживается, будет сообщение об ошибке
                    output = (result.stdout + result.stderr).lower()
                    if "unknown command" in output or "invalid command" in output or "not found" in output:
                        # Команда не поддерживается - это нормально
                        logger.debug(f"Команда delete не поддерживается для чата {chat_id}")
                    elif result.returncode == 0 and "deleted" in output.lower():
                        deleted_count += 1
                        logger.debug(f"Чат {chat_id} удален")
                    
                except Exception as e:
                    logger.debug(f"Не удалось удалить чат {chat_id}: {e}")
                    # Продолжаем удаление остальных
            
            # Сбрасываем текущий chat_id
            self.current_chat_id = None
            
            if deleted_count > 0:
                logger.info(f"Удалено {deleted_count} из {len(chat_ids)} чатов")
            else:
                # Если ни один чат не удален, это нормально - команда delete может не поддерживаться
                # Главное - процессы остановлены и chat_id сброшен
                logger.info(f"Процессы остановлены, chat_id сброшен. Чаты могут остаться в базе agent (это нормально, если команда delete не поддерживается)")
            
            return True
                
        except Exception as e:
            logger.error(f"Ошибка при очистке очереди чатов: {e}")
            return False
    
    def prepare_for_new_task(self) -> bool:
        """
        Подготовка к новой задаче: остановка активных чатов и очистка очереди
        
        Returns:
            True если подготовка выполнена успешно
        """
        logger.info("Подготовка к новой задаче: очистка активных диалогов...")
        
        # Останавливаем активные чаты
        stop_result = self.stop_active_chats()
        
        # Очищаем очередь
        clear_result = self.clear_chat_queue()
        
        # Сбрасываем текущий chat_id
        self.current_chat_id = None
        
        if stop_result or clear_result:
            logger.info("Подготовка к новой задаче завершена")
            return True
        else:
            logger.warning("Подготовка к новой задаче выполнена с предупреждениями")
            return True  # Все равно продолжаем, даже если были предупреждения
    
    def execute(
        self,
        prompt: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        additional_args: Optional[list[str]] = None,
        new_chat: bool = True,
        chat_id: Optional[str] = None
    ) -> CursorCLIResult:
        """
        Выполнить команду через Cursor CLI
        
        Args:
            prompt: Инструкция/промпт для выполнения
            working_dir: Рабочая директория (если None - текущая)
            timeout: Таймаут выполнения (если None - используется default_timeout)
            additional_args: Дополнительные аргументы для команды
            new_chat: Если True, пытаться создать новый чат (пробует различные параметры)
            
        Returns:
            CursorCLIResult с результатом выполнения
        """
        if not self.cli_available:
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                cli_available=False,
                error_message="Cursor CLI недоступен в системе"
            )
        
        # Формируем команду согласно официальной документации
        # https://cursor.com/docs/cli/overview
        # Команда: agent -p "instruction" для non-interactive режима
        # Для продолжения диалога: agent --resume="chat-id" -p "instruction"
        
        # Определяем рабочую директорию (приоритет: working_dir -> project_dir -> текущая)
        effective_working_dir = working_dir or (str(self.project_dir) if self.project_dir else None)
        
        # Определяем, используется ли Docker или WSL
        use_docker = self.cli_command == "docker-compose-agent"
        use_wsl = self.cli_command and self.cli_command.startswith("wsl ") and not use_docker
        
        # Управление сессией (новый чат или продолжение)
        resume_chat_id = None
        if chat_id:
            resume_chat_id = chat_id
        elif not new_chat and self.current_chat_id:
            resume_chat_id = self.current_chat_id
        elif not new_chat:
            # Пытаемся автоматически возобновить последний чат
            self.resume_chat()
            resume_chat_id = self.current_chat_id
        
        # Переменные для Docker
        compose_file = None
        cursor_api_key = None
        exec_cwd = None
        
        if use_docker:
            # Команда через Docker Compose
            compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
            if not compose_file.exists():
                logger.error(f"Docker Compose файл не найден: {compose_file}")
                return CursorCLIResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    cli_available=False,
                    error_message=f"Docker Compose файл не найден: {compose_file}"
                )
            
            # Читаем CURSOR_API_KEY из .env
            cursor_api_key = None
            env_file = Path(__file__).parent.parent / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                cursor_api_key = os.getenv("CURSOR_API_KEY")
                if cursor_api_key:
                    logger.info(f"CURSOR_API_KEY загружен из .env (длина: {len(cursor_api_key)})")
                else:
                    logger.warning("CURSOR_API_KEY не найден в .env файле")
            else:
                logger.warning(f".env файл не найден: {env_file}")
            
            # Проверяем и запускаем контейнер если нужно (с повторными попытками)
            max_retries = 3
            for attempt in range(max_retries):
                container_status = self._ensure_docker_container_running(compose_file)
                if container_status["running"]:
                    break
                
                if attempt < max_retries - 1:
                    logger.warning(f"Попытка {attempt + 1}/{max_retries}: Контейнер не запущен, повторная попытка...")
                    import time
                    time.sleep(2)
                else:
                    logger.error(f"Не удалось запустить Docker контейнер после {max_retries} попыток")
                    return CursorCLIResult(
                        success=False,
                        stdout="",
                        stderr="",
                        return_code=-1,
                        cli_available=False,
                        error_message=f"Не удалось запустить Docker контейнер после {max_retries} попыток: {container_status.get('error')}"
                    )
            
            # Формируем Docker команду для exec (выполнение в запущенном контейнере)
            # Используем docker exec напрямую с именем контейнера
            # Имя контейнера: cursor-agent-life (из docker-compose.agent.yml)
            # Используем bash -c для избежания проблем с конвертацией путей на Windows
            # Устанавливаем UTF-8 локаль для поддержки кириллицы
            # Используем одинарные кавычки для bash -c и двойные для prompt внутри
            # ИСПРАВЛЕНИЕ: Используем script для создания pseudo-TTY, чтобы обойти проблему Ink
            # Ink требует TTY для работы в "raw mode", но Docker без -t его не предоставляет
            # script -q создает виртуальный TTY, что позволяет Ink работать
            # Решение на основе рекомендаций экспертов (Grok, GPT)
            
            # ВАЖНО: Используем shlex.quote для правильного экранирования всех аргументов
            # Это гарантирует безопасную передачу prompt с любыми символами (русский, кавычки, и т.д.)
            import shlex
            
            # Формируем команду agent с учетом сессии (новый чат или продолжение)
            # ВАЖНО: Храним аргументы БЕЗ экранирования, экранируем только при формировании команды
            agent_cmd_parts_raw = ["/root/.local/bin/agent"]
            
            # Если нужно продолжить диалог, добавляем --resume
            if resume_chat_id:
                agent_cmd_parts_raw.extend(["--resume", resume_chat_id])
                logger.debug(f"Продолжение диалога с chat_id: {resume_chat_id}")
            
            # ИСПРАВЛЕНИЕ: Многострочные инструкции - сохраняем как есть для stdin
            # prompt будет передан через stdin, поэтому нормализация не требуется
            # Но сохраняем normalized_prompt для не-Docker команд (которые используют -p с аргументом)
            normalized_prompt = prompt.replace('\r\n', ' ').replace('\n', ' ').strip()
            normalized_prompt = ' '.join(normalized_prompt.split())
            
            # КРИТИЧНО: Для Docker НЕ добавляем -p с prompt в команду
            # prompt будет передан через stdin
            # НЕ добавляем: agent_cmd_parts_raw.extend(["-p", normalized_prompt])
            
            # ИСПРАВЛЕНИЕ: Формируем команду для script через bash переменную
            # Используем shlex.quote только для безопасного экранирования всей команды
            # Формат: script -q -c "agent_cmd='...'; $agent_cmd" /dev/null
            # Но нужно правильно экранировать для передачи через bash -c в docker exec
            
            # ИСПРАВЛЕНИЕ: Формируем команду БЕЗ экранирования для передачи в bash переменную
            # shlex.join создает строку с одинарными кавычками, что создает проблему при оборачивании
            # Решение: НЕ использовать shlex.join, а передавать команду как простую строку
            # Экранирование будет происходить на уровне bash переменной
            
            # КРИТИЧНОЕ ИСПРАВЛЕНИЕ: Передаем инструкцию через stdin вместо кавычек
            # Это полностью решает проблемы с экранированием, русским текстом и "Unterminated quoted string"
            # Формат: printf "%s" "$PROMPT" | script -q -c "agent -p" /dev/null
            # Или: echo "$PROMPT" | script -q -c "agent -p" /dev/null
            
            # Формируем команду agent БЕЗ prompt (prompt пойдет через stdin)
            # Убираем -p и prompt из agent_cmd_parts_raw
            agent_base_cmd_parts = ["/root/.local/bin/agent"]
            
            # Добавляем флаги, если есть
            if resume_chat_id:
                agent_base_cmd_parts.extend(["--resume", resume_chat_id])
                logger.debug(f"Продолжение диалога с chat_id: {resume_chat_id}")
            
            # Agent команда БЕЗ prompt
            agent_base_cmd = ' '.join(str(arg) for arg in agent_base_cmd_parts)
            
            # НОВОЕ РЕШЕНИЕ: Передаем prompt напрямую через аргумент -p
            # Используем shlex.quote для безопасного экранирования prompt
            import shlex
            
            # Экранируем prompt для bash
            escaped_prompt = shlex.quote(prompt)
            
            # Читаем модель из конфигурации (если указана)
            # ПРИМЕЧАНИЕ: Пустая строка = "Auto" - Cursor сам выберет оптимальную модель (рекомендуется)
            model_flag = ""
            try:
                from .config_loader import ConfigLoader
                config = ConfigLoader()
                cursor_config = config.get('cursor', {})
                cli_config = cursor_config.get('cli', {})
                model_name = cli_config.get('model', '').strip()
                
                if model_name:
                    # Модель указана в конфиге - используем ее через -m флаг
                    model_flag = f" -m {shlex.quote(model_name)}"
                    logger.debug(f"Использование модели из конфига: {model_name}")
                # Если модель не указана (пустая строка) - используем "Auto" (не добавляем -m флаг)
            except Exception as e:
                # Если не удалось прочитать конфиг - используем "Auto" (не добавляем -m флаг)
                logger.debug(f"Не удалось прочитать модель из конфига: {e}. Используем Auto (без -m флага).")
            
            # Формируем команду agent с prompt
            agent_full_cmd = f'{agent_base_cmd}{model_flag} -p {escaped_prompt} --force --approve-mcps'
            
            # Docker команда: выполняем agent напрямую без script (agent сам управляет TTY)
            # КРИТИЧНО: Передаем CURSOR_API_KEY в контейнер через -e флаг docker exec
            # И экспортируем переменную в bash команде для надежности
            cmd = ["docker", "exec"]
            
            # Передаем CURSOR_API_KEY если он доступен
            if cursor_api_key:
                cmd.extend(["-e", f"CURSOR_API_KEY={cursor_api_key}"])
                # Дополнительно экспортируем в bash команде (на случай если -e не сработает)
                bash_env_export = f'export CURSOR_API_KEY={shlex.quote(cursor_api_key)} && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && {agent_full_cmd}'
            else:
                bash_env_export = f'export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && {agent_full_cmd}'
            
            cmd.extend([
                "cursor-agent-life",
                "bash", "-c",
                bash_env_export
            ])
            
            # Prompt передается через printf в bash команде, stdin subprocess НЕ используется
            
            # Рабочая директория уже настроена в docker-compose.agent.yml
            exec_cwd = None
            
        elif use_wsl:
            # Команда через WSL: разбиваем "wsl agent" на ["wsl", "agent"]
            agent_cmd = self.cli_command.split()  # ["wsl", "agent"]
            cmd = agent_cmd.copy()
            
            # Добавляем --resume если нужно продолжить диалог
            if resume_chat_id:
                cmd.extend(["--resume", resume_chat_id])
            
            # Добавляем -p для non-interactive режима с флагами полного доступа
            cmd.extend(["-p", prompt, "--force", "--approve-mcps"])
            
            exec_cwd = None
            if effective_working_dir and os.name == 'nt':
                # Конвертируем Windows путь в WSL путь
                wsl_path = effective_working_dir.replace('\\', '/').replace(':', '').lower()
                exec_cwd = f"/mnt/{wsl_path[0]}{wsl_path[1:]}"
            elif effective_working_dir and Path(effective_working_dir).exists():
                exec_cwd = effective_working_dir
        else:
            # Обычная команда (локальный agent)
            cmd = [self.cli_command]
            
            # Добавляем --resume если нужно продолжить диалог
            if resume_chat_id:
                cmd.extend(["--resume", resume_chat_id])
            
            # Добавляем -p для non-interactive режима с флагами полного доступа
            cmd.extend(["-p", prompt, "--force", "--approve-mcps"])
            
            # Устанавливаем рабочую директорию
            exec_cwd = None
            if effective_working_dir and Path(effective_working_dir).exists():
                exec_cwd = effective_working_dir
        
        # Управление сессиями:
        # - agent -p "prompt" - создает новый чат автоматически (new_chat=True)
        # - agent --resume="chat-id" -p "prompt" - продолжает существующий чат (new_chat=False)
        # Параметр --headless не требуется для agent -p (это и так non-interactive режим)
        
        # Дополнительные аргументы (только для не-Docker команд)
        if additional_args and not use_docker:
            cmd.extend(additional_args)
        elif additional_args and use_docker:
            # Для Docker добавляем аргументы после "agent"
            agent_idx = cmd.index("agent")
            cmd[agent_idx + 1:agent_idx + 1] = additional_args
        
        # Определяем таймаут (увеличиваем для Docker, так как agent может работать долго)
        exec_timeout = timeout if timeout is not None else self.default_timeout
        if use_docker:
            exec_timeout = max(exec_timeout, 600)  # Минимум 10 минут для Docker
        
        logger.info(f"Выполнение команды через Cursor CLI: {' '.join(cmd)}")
        logger.debug(f"Рабочая директория: {exec_cwd or (working_dir or os.getcwd())}")
        logger.debug(f"Таймаут: {exec_timeout} секунд")
        if use_docker:
            logger.debug(f"Docker Compose файл: {compose_file}")
            if cursor_api_key:
                logger.debug("CURSOR_API_KEY передан в Docker контейнер")
        
        try:
            # Для Docker передаем CURSOR_API_KEY через переменные окружения
            env = None
            exec_cmd = cmd
            stdin_input = None
            
            # Умная обработка таймаута с проверкой активности контейнера
            max_timeout_retries = 5  # Максимум 5 продлений таймаута
            current_timeout = exec_timeout
            
            for retry in range(max_timeout_retries):
                try:
                    # Выполняем команду
                    if use_docker:
                        # Для Docker захватываем stderr для диагностики, но не stdout (может быть большим)
                        result = subprocess.run(
                            exec_cmd,
                            input=stdin_input,
                            stdout=subprocess.PIPE,  # Захватываем stdout
                            stderr=subprocess.PIPE,  # Захватываем stderr для диагностики
                            timeout=current_timeout,
                            cwd=exec_cwd if exec_cwd else None,
                            env=env,
                            text=True,
                            encoding='utf-8',
                            errors='replace'
                        )
                        # Коды возврата для Docker:
                        # 0 - успех
                        # 137 - SIGKILL (процесс убит, но может быть фоновым)
                        # 143 - SIGTERM (процесс завершен по сигналу, может быть нормальным завершением)
                        # Сначала устанавливаем success только для кода 0, остальные обрабатываем ниже
                        success = result.returncode == 0
                        result_stdout = result.stdout if result.stdout else "(нет вывода)"
                        result_stderr = result.stderr if result.stderr else ""
                        
                        # Логируем вывод для диагностики
                        if result.returncode not in [0, 137, 143]:
                            logger.warning(f"Agent вернул код {result.returncode}")
                            if result_stderr:
                                logger.warning(f"Stderr: {result_stderr[:500]}")
                            if result_stdout:
                                logger.debug(f"Stdout: {result_stdout[:500]}")
                        elif result.returncode == 143:
                            # Код 143 (SIGTERM) - логируем как информационное сообщение
                            logger.debug(f"Agent вернул код 143 (SIGTERM) - процесс был прерван, но может быть успешным")
                    else:
                        result = subprocess.run(
                            exec_cmd,
                            input=stdin_input,
                            capture_output=True,
                            text=True,
                            timeout=current_timeout,
                            cwd=exec_cwd if exec_cwd else None,
                            encoding='utf-8',
                            errors='replace',
                            env=env
                        )
                        success = result.returncode == 0
                        result_stdout = result.stdout
                        result_stderr = result.stderr
                    
                    # Команда завершилась - выходим из цикла
                    break
                    
                except subprocess.TimeoutExpired:
                    # Таймаут! Проверяем, идет ли генерация
                    if use_docker and retry < max_timeout_retries - 1:
                        logger.warning(f"Таймаут {current_timeout}с (попытка {retry + 1}/{max_timeout_retries})")
                        logger.info("Проверка активности Docker контейнера...")
                        
                        # Проверяем статус контейнера
                        container_active = self._check_docker_container_activity("cursor-agent-life")
                        
                        if container_active:
                            # Контейнер активен - продлеваем таймаут
                            current_timeout = exec_timeout * 2
                            logger.info(f"Контейнер активен, генерация продолжается. Продление таймаута до {current_timeout}с")
                            continue  # Повторяем попытку с увеличенным таймаутом
                        else:
                            # Контейнер не активен - что-то пошло не так
                            logger.error("Контейнер не активен или завис. Перезапуск...")
                            subprocess.run(["docker", "restart", "cursor-agent-life"], timeout=15, capture_output=True)
                            import time
                            time.sleep(5)
                            logger.info("Контейнер перезапущен, повторная попытка...")
                            current_timeout = exec_timeout  # Сбрасываем таймаут
                            continue
                    else:
                        # Исчерпаны попытки или не Docker
                        logger.error(f"Таймаут выполнения команды после {retry + 1} попыток ({current_timeout}с)")
                        raise
            
            if success:
                logger.info("Команда Cursor CLI выполнена успешно")
            else:
                logger.warning(f"Команда Cursor CLI завершилась с кодом {result.returncode}")
                if result_stderr:
                    logger.debug(f"Stderr: {result_stderr[:500]}")
                    
                    # Проверяем на критические ошибки аккаунта
                    stderr_lower = result_stderr.lower()
                    if "unpaid invoice" in stderr_lower or "pay your invoice" in stderr_lower:
                        logger.error("=" * 80)
                        logger.error("КРИТИЧЕСКАЯ ОШИБКА: Неоплаченный счет в Cursor")
                        logger.error("=" * 80)
                        logger.error("Для продолжения работы необходимо оплатить счет:")
                        logger.error("https://cursor.com/dashboard")
                        logger.error("=" * 80)
                        error_msg = "Неоплаченный счет в Cursor. Требуется оплата: https://cursor.com/dashboard"
                    else:
                        error_msg = f"CLI вернул код {result.returncode}"
                else:
                    error_msg = f"CLI вернул код {result.returncode}"
                
                # Если код 137 (SIGKILL) или 143 (SIGTERM) и используется Docker - это может быть нормально
                if result.returncode == 137 and use_docker:
                    logger.info("Код 137 (SIGKILL) для Docker - agent выполнился в фоне, проверяем результат по файлам")
                    success = True  # Считаем успехом для Docker
                    error_msg = None
                elif result.returncode == 143 and use_docker:
                    logger.warning("Код 143 (SIGTERM) для Docker - процесс был прерван. Это может быть нормально, если процесс завершился корректно перед прерыванием")
                    # Код 143 может быть нормальным, если процесс был завершен корректно
                    # Проверяем stderr - если нет ошибок, считаем успехом
                    if not result_stderr or "error" not in result_stderr.lower():
                        logger.info("Процесс завершился корректно перед прерыванием (код 143)")
                        success = True
                        error_msg = None
                    else:
                        # Есть ошибки - оставляем как неуспех
                        error_msg = f"Процесс прерван (код 143): {result_stderr[:200]}"
            
            return CursorCLIResult(
                success=success,
                stdout=result_stdout,
                stderr=result_stderr,
                return_code=result.returncode,
                cli_available=True,
                error_message=None if success else error_msg
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Таймаут выполнения команды Cursor CLI ({exec_timeout} сек)")
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                cli_available=True,
                error_message=f"Таймаут выполнения ({exec_timeout} секунд)"
            )
            
        except FileNotFoundError:
            # CLI мог быть удален между проверкой и выполнением
            logger.error("Cursor CLI не найден при выполнении команды")
            self.cli_available = False
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                cli_available=False,
                error_message="Cursor CLI не найден"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды Cursor CLI: {e}", exc_info=True)
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                cli_available=True,
                error_message=f"Исключение: {str(e)}"
            )
    
    def execute_instruction(
        self,
        instruction: str,
        task_id: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Выполнить инструкцию для задачи через Cursor CLI
        
        Удобный метод для выполнения инструкций с логированием.
        
        Args:
            instruction: Текст инструкции для выполнения
            task_id: Идентификатор задачи
            working_dir: Рабочая директория
            timeout: Таймаут выполнения
            
        Returns:
            Словарь с результатом выполнения
        """
        logger.info(f"Выполнение инструкции для задачи {task_id} через Cursor CLI")
        
        result = self.execute(
            prompt=instruction,
            working_dir=working_dir,
            timeout=timeout,
            new_chat=True  # Всегда создаем новый чат для новой задачи
        )
        
        return {
            "task_id": task_id,
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "cli_available": result.cli_available,
            "error_message": result.error_message
        }


def create_cursor_cli_interface(
    cli_path: Optional[str] = None,
    timeout: int = 300,
    headless: bool = True,
    project_dir: Optional[str] = None,
    agent_role: Optional[str] = None
) -> CursorCLIInterface:
    """
    Фабричная функция для создания интерфейса Cursor CLI
    
    Args:
        cli_path: Путь к CLI (если None - поиск в PATH)
        timeout: Таймаут по умолчанию
        headless: Использовать headless режим
        project_dir: Директория целевого проекта (для установки рабочей директории)
        agent_role: Роль агента для настройки через .cursor/rules или AGENTS.md
        
    Returns:
        Экземпляр CursorCLIInterface
    """
    interface = CursorCLIInterface(
        cli_path=cli_path,
        default_timeout=timeout,
        headless=headless,
        project_dir=project_dir,
        agent_role=agent_role
    )
    
    # Настраиваем роль агента в целевом проекте (если указана)
    if project_dir and agent_role:
        interface._setup_agent_role(project_dir, agent_role)
    
    return interface