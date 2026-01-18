"""
Интерфейс взаимодействия с Cursor через CLI

Этот модуль предоставляет возможность выполнения команд через Cursor CLI,
если он доступен в системе. В противном случае возвращает информацию
о недоступности для использования fallback на файловый интерфейс.
"""

import os
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
                self.cli_available = True
                logger.info("Использование Docker Compose для Cursor CLI")
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
    
    def _ensure_docker_container_running(self, compose_file: Path) -> Dict[str, Any]:
        """
        Проверяет статус Docker контейнера и запускает его, если он остановлен
        
        Args:
            compose_file: Путь к docker-compose.agent.yml
            
        Returns:
            Словарь с информацией о статусе контейнера
        """
        try:
            # Проверяем статус контейнера
            check_cmd = [
                "docker", "compose",
                "-f", str(compose_file),
                "ps", "-q"
            ]
            result = subprocess.run(
                check_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Если контейнер запущен (есть ID), возвращаем успех
            if result.returncode == 0 and result.stdout.strip():
                logger.debug("Docker контейнер уже запущен")
                return {"running": True, "container_id": result.stdout.strip()}
            
            # Контейнер не запущен - запускаем его
            logger.info("Запуск Docker контейнера...")
            up_cmd = [
                "docker", "compose",
                "-f", str(compose_file),
                "up", "-d"  # -d для запуска в фоне
            ]
            up_result = subprocess.run(
                up_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if up_result.returncode == 0:
                logger.info("Docker контейнер успешно запущен")
                # Даем контейнеру немного времени на запуск
                import time
                time.sleep(2)
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
        return self.cli_available
    
    def check_version(self) -> Optional[str]:
        """
        Проверка версии Cursor CLI
        
        Returns:
            Версия CLI или None если недоступен
        """
        if not self.cli_available:
            return None
        
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
            env_file = Path(__file__).parent.parent / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                cursor_api_key = os.getenv("CURSOR_API_KEY")
                if cursor_api_key:
                    logger.debug("CURSOR_API_KEY загружен из .env")
            
            # Проверяем и запускаем контейнер если нужно
            container_status = self._ensure_docker_container_running(compose_file)
            if not container_status["running"]:
                logger.warning(f"Не удалось запустить Docker контейнер: {container_status.get('error')}")
                return CursorCLIResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    cli_available=False,
                    error_message=f"Не удалось запустить Docker контейнер: {container_status.get('error')}"
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
            
            # ИСПРАВЛЕНИЕ: agent -p читает из stdin через pipe
            # Используем printf в bash для передачи prompt через pipe
            # Формат: printf "%s\n" "prompt" | agent -p
            # Экранируем normalized_prompt для безопасной передачи в printf
            # printf понимает escape-последовательности, поэтому экранируем только кавычки и спецсимволы
            escaped_for_printf = normalized_prompt.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            # Добавляем флаги --force и --approve-mcps для полного доступа без запросов разрешений
            bash_pipe_cmd = f'printf "%s\\n" "{escaped_for_printf}" | {agent_base_cmd} -p --force --approve-mcps'
            script_cmd = f'script -q -c "{bash_pipe_cmd}" /dev/null'
            
            # Docker команда: prompt уже включен в bash команду через printf
            cmd = [
                "docker", "exec",
                "-i",  # -i для TTY (если потребуется)
                "cursor-agent-life",
                "bash", "-c",
                f'export LANG=C.utf8 LC_ALL=C.utf8 && cd /workspace && {script_cmd}'
            ]
            
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
        
        # Определяем таймаут
        exec_timeout = timeout if timeout is not None else self.default_timeout
        
        logger.info(f"Выполнение команды через Cursor CLI: {' '.join(cmd)}")
        logger.debug(f"Рабочая директория: {exec_cwd or (working_dir or os.getcwd())}")
        logger.debug(f"Таймаут: {exec_timeout} секунд")
        if use_docker:
            logger.debug(f"Docker Compose файл: {compose_file}")
            if cursor_api_key:
                logger.debug("CURSOR_API_KEY передан в Docker контейнер")
        
        try:
            # Для Docker передаем CURSOR_API_KEY через переменные окружения
            # Примечание: для exec CURSOR_API_KEY уже установлен в docker-compose.agent.yml
            # через environment, поэтому дополнительная передача не требуется
            env = None
            
            exec_cmd = cmd
            
            # ИСПРАВЛЕНИЕ: prompt уже включен в bash команду через printf
            # stdin не используется для передачи prompt
            # Но оставляем stdin=None для ясности (если понадобится в будущем)
            stdin_input = None
            
            # Выполняем команду
            result = subprocess.run(
                exec_cmd,
                input=stdin_input,  # stdin не используется (prompt в bash команде)
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                cwd=exec_cwd if exec_cwd else None,
                encoding='utf-8',
                errors='replace',  # Обработка ошибок кодировки
                env=env  # Передаем переменные окружения для Docker
            )
            
            success = result.returncode == 0
            
            if success:
                logger.info("Команда Cursor CLI выполнена успешно")
            else:
                logger.warning(f"Команда Cursor CLI завершилась с кодом {result.returncode}")
                logger.debug(f"Stderr: {result.stderr[:500]}")
            
            return CursorCLIResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                cli_available=True,
                error_message=None if success else f"CLI вернул код {result.returncode}"
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