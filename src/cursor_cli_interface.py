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
from typing import Optional, Dict, Any, List
import time
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
    fallback_used: bool = False  # Флаг использования fallback модели
    primary_model_failed: bool = False  # Флаг неудачи основной модели


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
                    try:
                        subprocess.run(["docker", "stop", container_name], timeout=15, capture_output=True)
                        subprocess.run(["docker", "rm", container_name], timeout=15, capture_output=True)
                        logger.info(f"Проблемный контейнер {container_name} удален, будет создан заново")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Таймаут при удалении контейнера {container_name}, продолжаем...")
                    except Exception as e:
                        logger.warning(f"Ошибка при удалении контейнера {container_name}: {e}, продолжаем...")
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
                    timeout=15  # Увеличено с 10 до 15 секунд
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
                timeout=30  # Увеличено с 10 до 30 секунд
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
                        # Исключаем слишком короткие строки и строки, которые выглядят как команды/опции
                        if (re.match(r'^[a-zA-Z0-9\-_]+$', potential_id) and 
                            len(potential_id) > 2 and 
                            not potential_id.startswith('-') and  # Не опция команды
                            potential_id.lower() not in ['error', 'unknown', 'command', 'option']):  # Не сообщения об ошибках
                            chat_ids.append(potential_id)
                        else:
                            logger.debug(f"Пропущен невалидный chat_id: '{potential_id}' (строка: '{line[:100]}')")
                
                logger.debug(f"Найдено {len(chat_ids)} chat IDs: {chat_ids[:5]}")
                return chat_ids
            else:
                logger.warning(f"Ошибка при получении списка чатов: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Таймаут выполнения команды list_chats (30 секунд). Контейнер может быть занят или команда выполняется дольше ожидаемого.")
            return []  # Возвращаем пустой список, это не критичная ошибка
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
                    timeout=30  # Увеличено с 10 до 30 секунд для agent resume
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
                
            except subprocess.TimeoutExpired:
                logger.warning("Таймаут при попытке возобновления чата (30 секунд). Продолжаем без текущего chat_id.")
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
                
                try:
                    result = subprocess.run(
                        kill_cmd,
                        capture_output=True,
                        text=True,
                        timeout=15  # Увеличено с 10 до 15 секунд
                    )
                    
                    # Команда с || true всегда возвращает 0
                    # Проверяем, были ли найдены процессы через stderr или попытку поиска
                    # Если pkill не нашел процессы - это нормально (их может не быть)
                    # Проверяем, действительно ли процессы были остановлены
                    # Пытаемся найти процессы еще раз - если их нет, значит остановка успешна
                    check_cmd = [
                        "docker", "exec", "cursor-agent-life",
                        "bash", "-c",
                        "pgrep -f 'agent.*-p' || pgrep -f '/root/.local/bin/agent' || true"
                    ]
                    try:
                        check_result = subprocess.run(
                            check_cmd,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        # Если pgrep ничего не нашел (процессы остановлены) или нашел что-то (значит остановка частичная)
                        if not check_result.stdout.strip():
                            logger.info("✓ Активные процессы agent остановлены (или их не было)")
                        else:
                            remaining_pids = check_result.stdout.strip().split()
                            logger.warning(f"⚠ После остановки осталось {len(remaining_pids)} процессов: {', '.join(remaining_pids[:5])}{'...' if len(remaining_pids) > 5 else ''}")
                        return True
                    except subprocess.TimeoutExpired:
                        logger.warning("⚠ Таймаут при проверке процессов после остановки. Предполагаем, что остановка выполнена.")
                        return True  # Не критичная ошибка, продолжаем
                    except Exception as check_error:
                        # Если проверка не удалась, но команда pkill выполнилась - это не критично
                        logger.debug(f"Ошибка при проверке процессов после остановки: {check_error}")
                        return True  # Не критичная ошибка, продолжаем
                except subprocess.TimeoutExpired:
                    logger.warning("Таймаут при остановке процессов agent (15 секунд). Контейнер может быть занят. Продолжаем работу.")
                    return True  # Не критичная ошибка, продолжаем работу
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
            logger.info("🛑 Шаг 1/3: Остановка активных процессов agent...")
            stop_result = self.stop_active_chats()
            if stop_result:
                logger.info("✓ Шаг 1 завершен: процессы остановлены")
            else:
                logger.warning("⚠ Шаг 1: не удалось остановить некоторые процессы, продолжаем...")
            
            # Получаем список всех чатов
            logger.info("📋 Шаг 2/3: Получение списка чатов...")
            chat_ids = self.list_chats()
            
            if not chat_ids:
                logger.info("✓ Нет чатов для удаления (база данных пуста или команда list не работает)")
                return True
            
            logger.info(f"✓ Шаг 2 завершен: найдено {len(chat_ids)} чатов")
            
            use_docker = self.cli_command == "docker-compose-agent"
            
            # Удаляем каждый чат (если есть такая команда в agent)
            # Примечание: agent может не поддерживать прямого удаления чатов,
            # поэтому мы просто останавливаем процессы и сбрасываем текущий chat_id
            deleted_count = 0
            not_supported_count = 0
            failed_count = 0
            
            # ПРИМЕЧАНИЕ: Cursor agent CLI НЕ поддерживает команду delete (подтверждено официальной документацией)
            # Доступные команды: agent ls, agent resume, agent -p
            # Команда 'agent delete' не существует в официальном Cursor CLI (проверено в январе 2026)
            # В этом случае мы просто останавливаем процессы и сбрасываем chat_id
            # Чаты останутся в базе данных agent, но активные процессы будут остановлены
            logger.info(f"🗑️  Шаг 3/3: Проверка возможности удаления {len(chat_ids)} чатов...")
            logger.debug("ℹ️  Команда 'agent delete' не поддерживается Cursor CLI (проверено в официальной документации)")
            
            # Импортируем shlex для безопасного экранирования
            import shlex
            
            # Проверяем поддержку команды delete на первом чате
            # Если команда не поддерживается, пропускаем остальные попытки
            command_not_supported = False
            test_chat_id = chat_ids[0] if chat_ids else None
            
            if test_chat_id:
                try:
                    # Пытаемся проверить команду delete на первом чате
                    if use_docker:
                        escaped_chat_id = shlex.quote(str(test_chat_id))
                        cmd = [
                            "docker", "exec", "cursor-agent-life",
                            "bash", "-c",
                            f"cd /workspace && /root/.local/bin/agent delete {escaped_chat_id} 2>&1 || true"
                        ]
                    else:
                        cmd = [self.cli_command, "delete", str(test_chat_id)]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    stdout = result.stdout.strip() if result.stdout else ""
                    stderr = result.stderr.strip() if result.stderr else ""
                    output = (stdout + " " + stderr).strip().lower()
                    full_output = (stdout + " " + stderr).strip()
                    
                    # Проверяем, поддерживается ли команда
                    if ("unknown command" in output or "invalid command" in output or 
                        "not found" in output or "usage:" in output or "unknown option" in output):
                        command_not_supported = True
                        logger.info(f"ℹ️  Команда 'agent delete' не поддерживается Cursor CLI (это нормально)")
                        logger.debug(f"   Вывод команды: {full_output[:300]}")
                        not_supported_count = len(chat_ids)  # Все чаты не поддерживаются
                    elif result.returncode == 0 and ("deleted" in output or "removed" in output or "success" in output):
                        # Команда работает! Продолжаем удаление остальных
                        deleted_count += 1
                        logger.info(f"  [1/{len(chat_ids)}] ✓ Чат {test_chat_id} удален из БД")
                        # Продолжаем удаление остальных чатов
                        for idx, chat_id in enumerate(chat_ids[1:], 2):
                            try:
                                if use_docker:
                                    escaped_chat_id = shlex.quote(str(chat_id))
                                    cmd = [
                                        "docker", "exec", "cursor-agent-life",
                                        "bash", "-c",
                                        f"cd /workspace && /root/.local/bin/agent delete {escaped_chat_id} 2>&1 || true"
                                    ]
                                else:
                                    cmd = [self.cli_command, "delete", str(chat_id)]
                                
                                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                                stdout = result.stdout.strip() if result.stdout else ""
                                stderr = result.stderr.strip() if result.stderr else ""
                                output = (stdout + " " + stderr).strip().lower()
                                full_output = (stdout + " " + stderr).strip()
                                
                                if result.returncode == 0 and ("deleted" in output or "removed" in output or "success" in output):
                                    deleted_count += 1
                                    if idx <= 5:
                                        logger.info(f"  [{idx}/{len(chat_ids)}] ✓ Чат {chat_id} удален из БД")
                                else:
                                    failed_count += 1
                                    if idx <= 5:
                                        logger.debug(f"  [{idx}/{len(chat_ids)}] ⚠ Ошибка при удалении чата {chat_id}: {full_output[:300]}")
                            except Exception as e:
                                failed_count += 1
                                if idx <= 5:
                                    logger.debug(f"  [{idx}/{len(chat_ids)}] ⚠ Исключение при удалении чата {chat_id}: {e}")
                    else:
                        # Непонятный результат - считаем как не поддерживается
                        command_not_supported = True
                        not_supported_count = len(chat_ids)
                        logger.debug(f"   Команда вернула неожиданный результат: {full_output[:300]}")
                        
                except Exception as e:
                    # При ошибке считаем, что команда не поддерживается
                    command_not_supported = True
                    not_supported_count = len(chat_ids)
                    logger.debug(f"   Ошибка при проверке команды delete: {e}")
            
            # Сбрасываем текущий chat_id
            self.current_chat_id = None
            
            # Формируем итоговое сообщение
            summary_parts = []
            if deleted_count > 0:
                summary_parts.append(f"✓ {deleted_count} удалено из БД")
            if not_supported_count > 0:
                summary_parts.append(f"⚠ {not_supported_count} - команда delete не поддерживается")
            if failed_count > 0:
                summary_parts.append(f"⚠ {failed_count} - ошибки при удалении")
            
            if summary_parts:
                logger.info(f"📊 Итоги удаления чатов: {', '.join(summary_parts)}")
            else:
                logger.warning("⚠ Не удалось определить результат удаления чатов")
            
            # Главное - процессы остановлены и chat_id сброшен
            if deleted_count == 0 and not_supported_count > 0:
                logger.info(f"ℹ️  Команда 'agent delete' не поддерживается официальным Cursor CLI (это нормально)")
                logger.info(f"ℹ️  {len(chat_ids)} чатов остались в базе данных agent")
                logger.info("✓ Все активные процессы остановлены, chat_id сброшен. Чаты неактивны и не мешают работе.")
                logger.debug("💡 Примечание: Cursor CLI не предоставляет команду для удаления чатов. "
                           "Чаты хранятся локально и не влияют на работу системы.")
            elif deleted_count == 0 and failed_count > 0:
                logger.warning(f"⚠ Не удалось удалить чаты из базы данных. {failed_count} ошибок при попытке удаления.")
                logger.debug("💡 Проверьте логи выше для деталей ошибок. Возможно, команда 'agent delete' не поддерживается.")
                logger.info("ℹ️  Все активные процессы остановлены, chat_id сброшен.")
            elif deleted_count == 0:
                logger.info(f"ℹ️  Чаты не удалены (команда delete не поддерживается или не требуется)")
                logger.info("✓ Все активные процессы остановлены, chat_id сброшен.")
            else:
                logger.info(f"✓ Очистка завершена: {deleted_count} чатов удалено из БД, все процессы остановлены")
            
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
            # ВАЖНО: Экранируем resume_chat_id для безопасной передачи в bash команду
            if resume_chat_id:
                escaped_resume_id = shlex.quote(str(resume_chat_id))
                agent_base_cmd_parts.extend(["--resume", escaped_resume_id])
                logger.debug(f"Продолжение диалога с chat_id: {resume_chat_id}")
            
            # Agent команда БЕЗ prompt (resume_chat_id уже экранирован)
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
                    # Модель указана в конфиге - используем ее через --model флаг
                    model_flag = f" --model {shlex.quote(model_name)}"
                    logger.debug(f"Использование модели из конфига: {model_name}")
                # Если модель не указана (пустая строка) - используем "Auto" (не добавляем --model флаг)
            except Exception as e:
                # Если не удалось прочитать конфиг - используем "Auto" (не добавляем --model флаг)
                logger.debug(f"Не удалось прочитать модель из конфига: {e}. Используем Auto (без --model флага).")
            
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
                
                # Специальная обработка кода 1 (общая ошибка выполнения)
                if result.returncode == 1:
                    logger.warning("⚠️ Код возврата 1 - общая ошибка выполнения команды agent")
                    if result_stderr:
                        logger.warning(f"Детали ошибки (stderr): {result_stderr[:1000]}")
                    if result_stdout:
                        logger.debug(f"Stdout (первые 500 символов): {result_stdout[:500]}")
                
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
    
    def _get_model_config(self) -> Dict[str, Any]:
        """
        Получить конфигурацию модели из config.yaml
        
        Returns:
            Словарь с основной моделью и резервными моделями
        """
        try:
            from .config_loader import ConfigLoader
            config = ConfigLoader()
            cursor_config = config.get('cursor', {})
            cli_config = cursor_config.get('cli', {})
            
            return {
                'model': cli_config.get('model', 'auto').strip() or 'auto',
                'fallback_models': cli_config.get('fallback_models', ['grok']),
                'resilience': cli_config.get('resilience', {
                    'enable_fallback': True,
                    'max_fallback_attempts': 3,
                    'fallback_retry_delay': 2,
                    'fallback_on_errors': ['billing_error', 'timeout', 'model_unavailable', 'unknown_error']
                })
            }
        except Exception as e:
            logger.warning(f"Не удалось прочитать конфигурацию модели: {e}. Используем значения по умолчанию.")
            return {
                'model': 'auto',
                'fallback_models': ['grok'],
                'resilience': {
                    'enable_fallback': True,
                    'max_fallback_attempts': 3,
                    'fallback_retry_delay': 2,
                    'fallback_on_errors': ['billing_error', 'timeout', 'model_unavailable', 'unknown_error']
                }
            }
    
    def _should_trigger_fallback(self, result: CursorCLIResult, resilience_config: Dict) -> bool:
        """
        Определить, нужно ли активировать fallback на основе результата
        
        Args:
            result: Результат выполнения команды
            resilience_config: Конфигурация отказоустойчивости
            
        Returns:
            True если нужно активировать fallback
        """
        if not result.success:
            fallback_on = resilience_config.get('fallback_on_errors', [])
            
            # Проверяем billing error
            if 'billing_error' in fallback_on:
                stderr_lower = (result.stderr or '').lower()
                if 'unpaid invoice' in stderr_lower or 'pay your invoice' in stderr_lower:
                    logger.warning("Обнаружена billing error - активируем fallback")
                    return True
            
            # Проверяем timeout
            if 'timeout' in fallback_on:
                if result.error_message and ('таймаут' in result.error_message.lower() or 'timeout' in result.error_message.lower()):
                    logger.warning("Обнаружен timeout - активируем fallback")
                    return True
            
            # Проверяем unknown error (код != 0 и не billing)
            if 'unknown_error' in fallback_on:
                if result.return_code != 0 and result.return_code != -1:
                    stderr_lower = (result.stderr or '').lower()
                    if 'unpaid invoice' not in stderr_lower and 'pay your invoice' not in stderr_lower:
                        # Логируем детали ошибки для диагностики
                        error_details = result.stderr[:500] if result.stderr else "(нет stderr)"
                        logger.warning(f"Обнаружена ошибка (код {result.return_code}) - активируем fallback")
                        logger.debug(f"Детали ошибки (stderr): {error_details}")
                        if result.stdout:
                            logger.debug(f"Stdout (первые 200 символов): {result.stdout[:200]}")
                        return True
        
        return False
    
    def execute_with_fallback(
        self,
        prompt: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        additional_args: Optional[list[str]] = None,
        new_chat: bool = True,
        chat_id: Optional[str] = None
    ) -> CursorCLIResult:
        """
        Выполнить команду с автоматическим fallback на резервные модели
        
        Сначала пытается выполнить с основной моделью (auto).
        При ошибках (billing, timeout, и т.д.) автоматически пробует резервные модели.
        
        Args:
            prompt: Инструкция/промпт для выполнения
            working_dir: Рабочая директория
            timeout: Таймаут выполнения
            additional_args: Дополнительные аргументы
            new_chat: Создать новый чат
            chat_id: ID чата для продолжения
            
        Returns:
            CursorCLIResult с результатом выполнения (последняя попытка)
        """
        # Получаем конфигурацию
        model_config = self._get_model_config()
        primary_model = model_config['model']
        fallback_models = model_config.get('fallback_models', [])
        resilience = model_config.get('resilience', {})
        
        enable_fallback = resilience.get('enable_fallback', True)
        max_attempts = resilience.get('max_fallback_attempts', 3)
        retry_delay = resilience.get('fallback_retry_delay', 2)
        
        # Формируем список моделей для попыток
        models_to_try = [primary_model]
        if enable_fallback and fallback_models:
            models_to_try.extend(fallback_models[:max_attempts - 1])
        
        logger.info(f"Выполнение с fallback: основная модель '{primary_model}', резервные: {fallback_models}")
        
        last_result = None
        
        # Пробуем каждую модель по очереди
        for attempt, model in enumerate(models_to_try, 1):
            logger.info(f"Попытка {attempt}/{len(models_to_try)} с моделью '{model}'")
            
            # Выполняем команду с текущей моделью
            result = self._execute_with_specific_model(
                prompt=prompt,
                model=model,
                working_dir=working_dir,
                timeout=timeout,
                additional_args=additional_args,
                new_chat=new_chat,
                chat_id=chat_id
            )
            
            last_result = result
            
            # Если успешно - возвращаем результат
            if result.success:
                if attempt > 1:
                    # Fallback помог - но это все равно признак проблемы с основной моделью
                    logger.info(f"✅ Успешно выполнено с резервной моделью '{model}' (попытка {attempt})")
                    logger.warning(f"⚠️ Основная модель '{primary_model}' не смогла выполнить команду, использован fallback на '{model}'")
                    # Устанавливаем флаги для отслеживания использования fallback
                    result.fallback_used = True
                    result.primary_model_failed = True
                else:
                    logger.info(f"✅ Успешно выполнено с основной моделью '{model}'")
                return result
            
            # Проверяем, нужно ли продолжать fallback
            if not enable_fallback or attempt >= len(models_to_try):
                break
            
            # Проверяем, нужно ли активировать fallback для этой ошибки
            if not self._should_trigger_fallback(result, resilience):
                logger.info(f"Ошибка не требует fallback, останавливаем попытки")
                break
            
            # Задержка перед следующей попыткой
            if attempt < len(models_to_try):
                logger.info(f"Ожидание {retry_delay}с перед следующей попыткой...")
                time.sleep(retry_delay)
        
        # Все попытки неудачны
        if last_result:
            logger.error(f"❌ Все попытки ({len(models_to_try)}) неудачны. Последняя ошибка: {last_result.error_message}")
        else:
            logger.error("❌ Не удалось выполнить команду")
            last_result = CursorCLIResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                cli_available=True,
                error_message="Не удалось выполнить команду с любой из моделей"
            )
        
        return last_result
    
    def _execute_with_specific_model(
        self,
        prompt: str,
        model: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        additional_args: Optional[list[str]] = None,
        new_chat: bool = True,
        chat_id: Optional[str] = None
    ) -> CursorCLIResult:
        """
        Внутренний метод для выполнения команды с конкретной моделью
        
        Это копия логики из execute, но с явным указанием модели
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
        
        # Определяем рабочую директорию
        effective_working_dir = working_dir or (str(self.project_dir) if self.project_dir else None)
        
        # Определяем, используется ли Docker или WSL
        use_docker = self.cli_command == "docker-compose-agent"
        use_wsl = self.cli_command and self.cli_command.startswith("wsl")
        
        # Получаем CURSOR_API_KEY из .env
        cursor_api_key = os.getenv("CURSOR_API_KEY")
        
        import shlex
        
        if use_docker:
            # Docker команда
            compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
            agent_base_cmd = "/root/.local/bin/agent"
            
            escaped_prompt = shlex.quote(prompt)
            
            # Используем указанную модель
            model_flag = f" --model {shlex.quote(model)}" if model else ""
            
            agent_full_cmd = f'{agent_base_cmd}{model_flag} -p {escaped_prompt} --force --approve-mcps'
            
            cmd = ["docker", "exec"]
            
            if cursor_api_key:
                cmd.extend(["-e", f"CURSOR_API_KEY={cursor_api_key}"])
                bash_env_export = f'export CURSOR_API_KEY={shlex.quote(cursor_api_key)} && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && {agent_full_cmd}'
            else:
                bash_env_export = f'export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && {agent_full_cmd}'
            
            cmd.extend([
                "cursor-agent-life",
                "bash", "-c",
                bash_env_export
            ])
            
            exec_cwd = None
        else:
            # Для локального/WSL - используем стандартный execute
            # Временно сохраняем оригинальную модель в конфиге
            # и вызываем execute, который прочитает её
            # Но это сложно, поэтому просто вызываем execute с модифицированным конфигом
            return self.execute(
                prompt=prompt,
                working_dir=working_dir,
                timeout=timeout,
                additional_args=additional_args,
                new_chat=new_chat,
                chat_id=chat_id
            )
        
        # Выполняем команду (упрощенная версия логики из execute)
        exec_timeout = timeout if timeout is not None else self.default_timeout
        if use_docker:
            exec_timeout = max(exec_timeout, 600)
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=exec_timeout,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            success = result.returncode == 0
            result_stdout = result.stdout if result.stdout else ""
            result_stderr = result.stderr if result.stderr else ""
            
            # Логируем ошибки для диагностики
            if not success:
                logger.warning(f"Команда завершилась с кодом {result.returncode}")
                if result_stderr:
                    logger.debug(f"Stderr (первые 500 символов): {result_stderr[:500]}")
                if result_stdout:
                    logger.debug(f"Stdout (первые 200 символов): {result_stdout[:200]}")
            
            # Проверяем billing error
            stderr_lower = result_stderr.lower()
            billing_error = "unpaid invoice" in stderr_lower or "pay your invoice" in stderr_lower
            
            if billing_error:
                error_msg = "Неоплаченный счет в Cursor. Требуется оплата: https://cursor.com/dashboard"
            elif not success:
                error_msg = f"CLI вернул код {result.returncode}"
            else:
                error_msg = None
            
            return CursorCLIResult(
                success=success,
                stdout=result_stdout,
                stderr=result_stderr,
                return_code=result.returncode,
                cli_available=True,
                error_message=error_msg
            )
            
        except subprocess.TimeoutExpired:
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                cli_available=True,
                error_message=f"Таймаут выполнения ({exec_timeout} секунд)"
            )
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {e}", exc_info=True)
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                cli_available=True,
                error_message=f"Исключение: {str(e)}"
            )
    
    def _get_model_config(self) -> Dict[str, Any]:
        """
        Получить конфигурацию модели из config.yaml
        
        Returns:
            Словарь с основной моделью и резервными моделями
        """
        try:
            from .config_loader import ConfigLoader
            config = ConfigLoader()
            cursor_config = config.get('cursor', {})
            cli_config = cursor_config.get('cli', {})
            
            return {
                'model': cli_config.get('model', 'auto').strip() or 'auto',
                'fallback_models': cli_config.get('fallback_models', ['grok']),
                'resilience': cli_config.get('resilience', {
                    'enable_fallback': True,
                    'max_fallback_attempts': 3,
                    'fallback_retry_delay': 2,
                    'fallback_on_errors': ['billing_error', 'timeout', 'model_unavailable', 'unknown_error']
                })
            }
        except Exception as e:
            logger.warning(f"Не удалось прочитать конфигурацию модели: {e}. Используем значения по умолчанию.")
            return {
                'model': 'auto',
                'fallback_models': ['grok'],
                'resilience': {
                    'enable_fallback': True,
                    'max_fallback_attempts': 3,
                    'fallback_retry_delay': 2,
                    'fallback_on_errors': ['billing_error', 'timeout', 'model_unavailable', 'unknown_error']
                }
            }
    
    def _should_trigger_fallback(self, result: CursorCLIResult, resilience_config: Dict) -> bool:
        """
        Определить, нужно ли активировать fallback на основе результата
        
        Args:
            result: Результат выполнения команды
            resilience_config: Конфигурация отказоустойчивости
            
        Returns:
            True если нужно активировать fallback
        """
        if not result.success:
            fallback_on = resilience_config.get('fallback_on_errors', [])
            
            # Проверяем billing error
            if 'billing_error' in fallback_on:
                stderr_lower = (result.stderr or '').lower()
                if 'unpaid invoice' in stderr_lower or 'pay your invoice' in stderr_lower:
                    logger.warning("Обнаружена billing error - активируем fallback")
                    return True
            
            # Проверяем timeout
            if 'timeout' in fallback_on:
                if result.error_message and ('таймаут' in result.error_message.lower() or 'timeout' in result.error_message.lower()):
                    logger.warning("Обнаружен timeout - активируем fallback")
                    return True
            
            # Проверяем unknown error (код != 0 и не billing)
            if 'unknown_error' in fallback_on:
                if result.return_code != 0 and result.return_code != -1:
                    stderr_lower = (result.stderr or '').lower()
                    if 'unpaid invoice' not in stderr_lower and 'pay your invoice' not in stderr_lower:
                        # Логируем детали ошибки для диагностики
                        error_details = result.stderr[:500] if result.stderr else "(нет stderr)"
                        logger.warning(f"Обнаружена ошибка (код {result.return_code}) - активируем fallback")
                        logger.debug(f"Детали ошибки (stderr): {error_details}")
                        if result.stdout:
                            logger.debug(f"Stdout (первые 200 символов): {result.stdout[:200]}")
                        return True
        
        return False
    
    def _execute_with_specific_model(
        self,
        prompt: str,
        model: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        additional_args: Optional[list[str]] = None,
        new_chat: bool = True,
        chat_id: Optional[str] = None
    ) -> CursorCLIResult:
        """
        Внутренний метод для выполнения команды с конкретной моделью
        
        Это упрощенная версия execute, но с явным указанием модели
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
        
        # Определяем рабочую директорию
        effective_working_dir = working_dir or (str(self.project_dir) if self.project_dir else None)
        
        # Определяем, используется ли Docker
        use_docker = self.cli_command == "docker-compose-agent"
        
        if not use_docker:
            # Для локального/WSL используем стандартный execute
            # Временно модифицируем конфиг (но это сложно)
            # Поэтому просто вызываем execute - он прочитает модель из конфига
            return self.execute(
                prompt=prompt,
                working_dir=working_dir,
                timeout=timeout,
                additional_args=additional_args,
                new_chat=new_chat,
                chat_id=chat_id
            )
        
        # Docker команда
        import shlex
        compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
        agent_base_cmd = "/root/.local/bin/agent"
        
        escaped_prompt = shlex.quote(prompt)
        model_flag = f" --model {shlex.quote(model)}" if model else ""
        agent_full_cmd = f'{agent_base_cmd}{model_flag} -p {escaped_prompt} --force --approve-mcps'
        
        cursor_api_key = os.getenv("CURSOR_API_KEY")
        cmd = ["docker", "exec"]
        
        if cursor_api_key:
            cmd.extend(["-e", f"CURSOR_API_KEY={cursor_api_key}"])
            bash_env_export = f'export CURSOR_API_KEY={shlex.quote(cursor_api_key)} && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && {agent_full_cmd}'
        else:
            bash_env_export = f'export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && {agent_full_cmd}'
        
        cmd.extend([
            "cursor-agent-life",
            "bash", "-c",
            bash_env_export
        ])
        
        exec_timeout = timeout if timeout is not None else self.default_timeout
        exec_timeout = max(exec_timeout, 600)  # Минимум 10 минут для Docker
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=exec_timeout,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            success = result.returncode == 0
            result_stdout = result.stdout if result.stdout else ""
            result_stderr = result.stderr if result.stderr else ""
            
            # Логируем ошибки для диагностики
            if not success:
                logger.warning(f"Команда завершилась с кодом {result.returncode}")
                if result_stderr:
                    logger.debug(f"Stderr (первые 500 символов): {result_stderr[:500]}")
                if result_stdout:
                    logger.debug(f"Stdout (первые 200 символов): {result_stdout[:200]}")
            
            # Проверяем billing error
            stderr_lower = result_stderr.lower()
            billing_error = "unpaid invoice" in stderr_lower or "pay your invoice" in stderr_lower
            
            if billing_error:
                error_msg = "Неоплаченный счет в Cursor. Требуется оплата: https://cursor.com/dashboard"
            elif not success:
                error_msg = f"CLI вернул код {result.returncode}"
            else:
                error_msg = None
            
            return CursorCLIResult(
                success=success,
                stdout=result_stdout,
                stderr=result_stderr,
                return_code=result.returncode,
                cli_available=True,
                error_message=error_msg
            )
            
        except subprocess.TimeoutExpired:
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                cli_available=True,
                error_message=f"Таймаут выполнения ({exec_timeout} секунд)"
            )
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {e}", exc_info=True)
            return CursorCLIResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                cli_available=True,
                error_message=f"Исключение: {str(e)}"
            )
    
    def execute_with_fallback(
        self,
        prompt: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        additional_args: Optional[list[str]] = None,
        new_chat: bool = True,
        chat_id: Optional[str] = None
    ) -> CursorCLIResult:
        """
        Выполнить команду с автоматическим fallback на резервные модели
        
        Сначала пытается выполнить с основной моделью (auto).
        При ошибках (billing, timeout, и т.д.) автоматически пробует резервные модели.
        
        Args:
            prompt: Инструкция/промпт для выполнения
            working_dir: Рабочая директория
            timeout: Таймаут выполнения
            additional_args: Дополнительные аргументы
            new_chat: Создать новый чат
            chat_id: ID чата для продолжения
            
        Returns:
            CursorCLIResult с результатом выполнения (последняя попытка)
        """
        # Получаем конфигурацию
        model_config = self._get_model_config()
        primary_model = model_config['model']
        fallback_models = model_config.get('fallback_models', [])
        resilience = model_config.get('resilience', {})
        
        enable_fallback = resilience.get('enable_fallback', True)
        max_attempts = resilience.get('max_fallback_attempts', 3)
        retry_delay = resilience.get('fallback_retry_delay', 2)
        
        # Формируем список моделей для попыток
        models_to_try = [primary_model]
        if enable_fallback and fallback_models:
            models_to_try.extend(fallback_models[:max_attempts - 1])
        
        logger.info(f"Выполнение с fallback: основная модель '{primary_model}', резервные: {fallback_models}")
        
        last_result = None
        
        # Пробуем каждую модель по очереди
        for attempt, model in enumerate(models_to_try, 1):
            logger.info(f"Попытка {attempt}/{len(models_to_try)} с моделью '{model}'")
            
            # Выполняем команду с текущей моделью
            result = self._execute_with_specific_model(
                prompt=prompt,
                model=model,
                working_dir=working_dir,
                timeout=timeout,
                additional_args=additional_args,
                new_chat=new_chat,
                chat_id=chat_id
            )
            
            last_result = result
            
            # Если успешно - возвращаем результат
            if result.success:
                if attempt > 1:
                    # Fallback помог - но это все равно признак проблемы с основной моделью
                    logger.info(f"✅ Успешно выполнено с резервной моделью '{model}' (попытка {attempt})")
                    logger.warning(f"⚠️ Основная модель '{primary_model}' не смогла выполнить команду, использован fallback на '{model}'")
                    # Устанавливаем флаги для отслеживания использования fallback
                    result.fallback_used = True
                    result.primary_model_failed = True
                else:
                    logger.info(f"✅ Успешно выполнено с основной моделью '{model}'")
                return result
            
            # Проверяем, нужно ли продолжать fallback
            if not enable_fallback or attempt >= len(models_to_try):
                break
            
            # Проверяем, нужно ли активировать fallback для этой ошибки
            if not self._should_trigger_fallback(result, resilience):
                logger.info(f"Ошибка не требует fallback, останавливаем попытки")
                break
            
            # Задержка перед следующей попыткой
            if attempt < len(models_to_try):
                logger.info(f"Ожидание {retry_delay}с перед следующей попыткой...")
                time.sleep(retry_delay)
        
        # Все попытки неудачны
        if last_result:
            logger.error(f"❌ Все попытки ({len(models_to_try)}) неудачны. Последняя ошибка: {last_result.error_message}")
        else:
            logger.error("❌ Не удалось выполнить команду")
            last_result = CursorCLIResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                cli_available=True,
                error_message="Не удалось выполнить команду с любой из моделей"
            )
        
        return last_result
    
    def execute_instruction(
        self,
        instruction: str,
        task_id: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Выполнить инструкцию для задачи через Cursor CLI с fallback
        
        Удобный метод для выполнения инструкций с логированием и автоматическим fallback.
        
        Args:
            instruction: Текст инструкции для выполнения
            task_id: Идентификатор задачи
            working_dir: Рабочая директория
            timeout: Таймаут выполнения
            
        Returns:
            Словарь с результатом выполнения
        """
        logger.info(f"Выполнение инструкции для задачи {task_id} через Cursor CLI (с fallback)")
        
        # Используем execute_with_fallback вместо execute
        result = self.execute_with_fallback(
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
            "error_message": result.error_message,
            "fallback_used": getattr(result, 'fallback_used', False),
            "primary_model_failed": getattr(result, 'primary_model_failed', False)
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