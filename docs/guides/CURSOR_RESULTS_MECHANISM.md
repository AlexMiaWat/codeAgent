# Механизм создания отчетов в cursor_results/

## Обзор

Директория `cursor_results/` в целевом проекте используется для хранения результатов выполнения инструкций от Cursor Agent. Важно понимать, что **Code Agent НЕ создает эти файлы напрямую** - он только создает директорию и ожидает появления файлов результатов.

## Как создаются отчеты

### 1. Создание директории

**Кто:** Code Agent  
**Когда:** При инициализации `CursorFileInterface`  
**Где:** `src/cursor_file_interface.py`

```python
def __init__(self, project_dir: Path, commands_dir: str = "cursor_commands", results_dir: str = "cursor_results", ...):
    self.results_dir = self.project_dir / results_dir
    # Создаем директории если их нет
    self.results_dir.mkdir(parents=True, exist_ok=True)
```

**Результат:** Создается директория `{project_dir}/cursor_results/` если её нет.

### 2. Создание файла инструкции

**Кто:** Code Agent  
**Когда:** При отправке инструкции Cursor  
**Где:** `src/cursor_file_interface.py::write_instruction()`

```python
def write_instruction(self, instruction: str, task_id: str, ...):
    # Создает файл: cursor_commands/instruction_{task_id}_NEW_CHAT.txt
    # В файле указывается ожидаемый файл результата:
    # cursor_results/result_{task_id}.txt
```

**Результат:** Создается файл инструкции, который содержит:
- Текст инструкции для Cursor
- Путь к ожидаемому файлу результата: `cursor_results/result_{task_id}.txt`
- Инструкции для пользователя (если используется файловый интерфейс)

### 3. Создание файла результата

**Кто:** Cursor Agent (или пользователь вручную)  
**Когда:** После выполнения инструкции  
**Где:** В целевом проекте `{project_dir}/cursor_results/result_{task_id}.txt`

#### Вариант A: Автоматическое создание через Cursor CLI

Если используется Cursor CLI (через Docker или локально):

1. Code Agent отправляет инструкцию через CLI:
   ```python
   cli.execute(prompt=instruction, new_chat=True)
   ```

2. Cursor Agent выполняет инструкцию и **автоматически создает файл результата**:
   ```
   {project_dir}/cursor_results/result_{task_id}.txt
   ```

3. В конце файла должна быть контрольная фраза (например, "Задача выполнена!")

#### Вариант B: Ручное создание (файловый интерфейс)

Если используется файловый интерфейс (fallback):

1. Code Agent создает файл инструкции:
   ```
   {project_dir}/cursor_commands/instruction_{task_id}_NEW_CHAT.txt
   ```

2. **Пользователь должен вручную:**
   - Открыть Cursor IDE
   - Прочитать файл инструкции
   - Создать новый чат в Cursor
   - Скопировать инструкцию в чат
   - Выполнить инструкцию в Cursor
   - **Создать файл результата:**
     ```bash
     # Вручную создать файл:
     echo "Результат выполнения задачи
     Задача выполнена!" > {project_dir}/cursor_results/result_{task_id}.txt
     ```

### 4. Ожидание и чтение результата

**Кто:** Code Agent  
**Когда:** После отправки инструкции  
**Где:** `src/cursor_file_interface.py::wait_for_result()`

```python
def wait_for_result(self, task_id: str, timeout: int = 300, ...):
    file_path = self.results_dir / f"result_{task_id}.txt"
    
    # Ожидает появления файла с проверкой каждые 2 секунды
    while time.time() - start_time < timeout:
        if file_path.exists():
            # Проверяет контрольную фразу
            content = file_path.read_text(encoding='utf-8')
            if control_phrase in content:
                return {"success": True, "content": content, ...}
        time.sleep(check_interval)
    
    # Таймаут если файл не появился
    return {"success": False, "error": "Таймаут ожидания файла"}
```

**Результат:** Code Agent читает файл результата и продолжает работу.

## Полный цикл работы

```
┌─────────────┐
│ Code Agent  │
└──────┬──────┘
       │
       │ 1. Создает директорию cursor_results/
       │
       │ 2. Создает файл инструкции:
       │    cursor_commands/instruction_{task_id}_NEW_CHAT.txt
       │
       ▼
┌─────────────────────────────────────┐
│  Файл инструкции содержит:          │
│  - Текст инструкции                 │
│  - Путь к ожидаемому результату:   │
│    cursor_results/result_{task_id}.txt│
└─────────────────────────────────────┘
       │
       │ 3. Отправка инструкции Cursor
       │    (через CLI или файловый интерфейс)
       │
       ▼
┌─────────────┐
│Cursor Agent │
└──────┬──────┘
       │
       │ 4. Выполняет инструкцию
       │
       │ 5. Создает файл результата:
       │    cursor_results/result_{task_id}.txt
       │    (с контрольной фразой в конце)
       │
       ▼
┌─────────────┐
│ Code Agent  │
└──────┬──────┘
       │
       │ 6. Ожидает появления файла
       │    (проверка каждые 2 секунды, таймаут 300s)
       │
       │ 7. Читает файл результата
       │
       │ 8. Проверяет контрольную фразу
       │
       │ 9. Продолжает работу с результатом
       │
       ▼
   [Следующая инструкция]
```

## Важные детали

### Формат файла результата

Файл результата должен содержать:
1. **Описание выполненной работы**
2. **Контрольную фразу в конце** (например, "Задача выполнена!" или "Отчет завершен!")

Пример:
```txt
Результат выполнения задачи: Создать функцию валидации email

Выполнено:
1. Создан файл validators.py
2. Добавлена функция validate_email()
3. Написаны тесты

Задача выполнена!
```

### Контрольная фраза

Контрольная фраза используется для синхронизации:
- Code Agent ждет появления файла
- Проверяет наличие контрольной фразы
- Только после этого считает задачу выполненной

Это предотвращает чтение неполных файлов.

### Таймаут ожидания

По умолчанию Code Agent ждет файл результата **300 секунд (5 минут)**.

Если файл не появился:
- Code Agent логирует предупреждение
- Возвращает ошибку таймаута
- Может продолжить с следующей инструкцией или повторить попытку

### Размер файла

Максимальный размер файла результата: **10 MB** (по умолчанию).

Если файл больше:
- Code Agent не читает его
- Логирует ошибку
- Возвращает ошибку "Файл результата слишком большой"

## Диагностика проблем

### Файл результата не создается

**Причины:**
1. Cursor CLI не выполнил инструкцию автоматически
2. Пользователь не создал файл вручную (при файловом интерфейсе)
3. Неправильный путь к файлу результата

**Решение:**
1. Проверить логи Cursor CLI
2. Проверить статус Docker контейнера (если используется)
3. Проверить файл инструкции в `cursor_commands/`
4. Создать файл результата вручную для тестирования

### Файл создан, но Code Agent его не находит

**Причины:**
1. Неправильный `task_id` в имени файла
2. Файл создан в неправильной директории
3. Контрольная фраза отсутствует или неверна

**Решение:**
1. Проверить имя файла: должно быть `result_{task_id}.txt`
2. Проверить путь: `{project_dir}/cursor_results/`
3. Проверить наличие контрольной фразы в конце файла

### Таймаут ожидания

**Причины:**
1. Cursor Agent долго выполняет задачу
2. Файл не создается вообще

**Решение:**
1. Увеличить таймаут в конфигурации
2. Проверить, выполняется ли инструкция в Cursor
3. Проверить логи Cursor Agent

## Примеры использования

### Автоматическое создание (CLI)

```python
# Code Agent отправляет инструкцию
result = cli.execute(
    prompt="Создай файл test.txt с текстом 'Hello'",
    new_chat=True
)

# Cursor Agent автоматически:
# 1. Выполняет инструкцию
# 2. Создает файл: cursor_results/result_{task_id}.txt
# 3. Записывает результат с контрольной фразой

# Code Agent читает результат
wait_result = cursor_file.wait_for_result(
    task_id=task_id,
    control_phrase="Задача выполнена!"
)
```

## Технические детали: Вызовы Cursor CLI

### Цепочка вызовов в коде

```
CodeAgentServer._execute_task_via_cursor()
  → _execute_cursor_instruction_with_retry()
    → execute_cursor_instruction(instruction, task_id, timeout)
      → cli.execute_instruction(instruction, task_id, working_dir, timeout)
        → cli.execute(prompt, working_dir, timeout, new_chat=True)
          → [Формирование команды Docker/Local/WSL]
```

### Параметры из конфигурации

**Файл:** `config/config.yaml`

```yaml
cursor:
  cli:
    cli_path: "docker-compose-agent"  # Маркер для Docker
    timeout: 1000                      # Таймаут в секундах
    headless: true                      # Headless режим (не используется для agent -p)
    model: ""                           # Пустая строка = Auto (рекомендуется)
    # Или конкретная модель:
    # model: "claude-haiku"
    # model: "gpt-4o-mini"

agent:
  role: "Project Executor Agent"        # Роль агента
```

**Переменные окружения:**
- `CURSOR_API_KEY` - из `.env` файла в `d:\Space\codeAgent\.env`
- `PROJECT_DIR` - целевой проект (например, `D:\Space\life`)

### Вариант 1: Docker (текущий режим)

**Когда используется:** `cli_path == "docker-compose-agent"`

**Инициализация интерфейса:**
```python
# src/server.py::_init_cursor_cli()
cli_interface = create_cursor_cli_interface(
    cli_path="docker-compose-agent",
    timeout=1000,
    headless=True,
    project_dir="D:\\Space\\life",
    agent_role="Project Executor Agent"
)
```

**Выполнение инструкции:**
```python
# src/cursor_cli_interface.py::execute()
result = cli.execute(
    prompt="Создай файл test.txt с текстом 'Hello'",
    working_dir="D:\\Space\\life",
    timeout=1000,
    new_chat=True
)
```

**Формируемая Docker команда:**

**Базовые компоненты:**
```python
# 1. Базовая команда agent
agent_base_cmd = "/root/.local/bin/agent"

# 2. Модель (если указана в конфиге)
model_flag = ""  # Если model == "" в конфиге
# ИЛИ
model_flag = " -m claude-haiku"  # Если model == "claude-haiku" в конфиге

# 3. Экранированный prompt
import shlex
escaped_prompt = shlex.quote(prompt)

# 4. Полная команда agent
agent_full_cmd = f'{agent_base_cmd}{model_flag} -p {escaped_prompt} --force --approve-mcps'
```

**Полная Docker команда:**
```bash
docker exec \
  -e CURSOR_API_KEY=sk_cursor_xxx \
  cursor-agent-life \
  bash -c 'export CURSOR_API_KEY=sk_cursor_xxx && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && /root/.local/bin/agent -p "Создай файл test.txt с текстом '\''Hello'\''" --force --approve-mcps'
```

**Примеры с разными конфигурациями:**

**Пример 1: Автоматический выбор модели (рекомендуется)**
```yaml
# config/config.yaml
cursor:
  cli:
    model: ""  # Пустая строка
```

**Команда:**
```bash
docker exec -e CURSOR_API_KEY=xxx cursor-agent-life bash -c 'export CURSOR_API_KEY=xxx && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && /root/.local/bin/agent -p "instruction" --force --approve-mcps'
```
*Примечание: Флаг `-m` не добавляется, Cursor выбирает модель автоматически*

**Пример 2: Конкретная модель**
```yaml
# config/config.yaml
cursor:
  cli:
    model: "claude-haiku"
```

**Команда:**
```bash
docker exec -e CURSOR_API_KEY=xxx cursor-agent-life bash -c 'export CURSOR_API_KEY=xxx && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && /root/.local/bin/agent -m "claude-haiku" -p "instruction" --force --approve-mcps'
```
*Примечание: Добавлен флаг `-m "claude-haiku"`*

**Пример 3: Продолжение существующего чата**
```python
result = cli.execute(
    prompt="Продолжи задачу",
    new_chat=False,
    chat_id="chat-123"
)
```

**Команда:**
```bash
docker exec -e CURSOR_API_KEY=xxx cursor-agent-life bash -c 'export CURSOR_API_KEY=xxx && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && /root/.local/bin/agent --resume chat-123 -p "Продолжи задачу" --force --approve-mcps'
```
*Примечание: Добавлен флаг `--resume chat-123`*

**Параметры команды:**
- `--force` - принудительное применение изменений без подтверждения
- `--approve-mcps` - автоматическое одобрение MCP серверов/инструментов
- `-p "<prompt>"` - инструкция для выполнения (non-interactive режим)
- `-m "<model>"` - модель LLM (только если указана в конфиге, иначе Auto)
- `--resume <chat_id>` - продолжение существующего чата (если `new_chat=False`)

**Переменные окружения в контейнере:**
- `CURSOR_API_KEY` - передается через `-e` флаг и `export` в bash
- `LANG=C.UTF-8` - поддержка UTF-8 (кириллица)
- `LC_ALL=C.UTF-8` - поддержка UTF-8
- `AGENT_WORKING_DIR=/workspace` - из docker-compose.agent.yml
- `AGENT_HOME=/root` - из docker-compose.agent.yml

**Рабочая директория:**
- Устанавливается в docker-compose.agent.yml: `working_dir: /workspace`
- Монтируется из хост-системы: `../../life:/workspace:rw`
- В команде: `cd /workspace` перед выполнением agent

### Вариант 2: Локальный CLI

**Когда используется:** `agent` найден в PATH или указан путь

**Команда:**
```bash
agent -p "instruction" --force --approve-mcps
```

**⚠️ ВАЖНО:** Для локального CLI модель НЕ передается через флаг `-m`, даже если указана в конфиге. Это может быть ошибкой в коде.

**Код:** `src/cursor_cli_interface.py:1139-1140`
```python
# Для локального CLI модель не добавляется
cmd.extend(["-p", prompt, "--force", "--approve-mcps"])
```

### Вариант 3: WSL

**Когда используется:** Windows + `agent` найден в WSL

**Команда:**
```bash
wsl agent -p "instruction" --force --approve-mcps
```

**Конвертация пути:**
```python
# Windows: D:\Space\life -> WSL: /mnt/d/space/life
wsl_path = effective_working_dir.replace('\\', '/').replace(':', '').lower()
exec_cwd = f"/mnt/{wsl_path[0]}{wsl_path[1:]}"
```

**⚠️ ВАЖНО:** Для WSL модель также НЕ передается через флаг `-m`.

### Проверка использования модели

**Текущая реализация:**
- ✅ **Docker:** Модель читается из конфига и передается через `-m` флаг
- ❌ **Локальный CLI:** Модель НЕ передается (возможная ошибка)
- ❌ **WSL:** Модель НЕ передается (возможная ошибка)

**Код проверки модели (только для Docker):**
```python
# src/cursor_cli_interface.py:1066-1083
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
```

**Рекомендация:** Для локального и WSL вариантов также добавить поддержку модели из конфига.

### Полный пример вызова с параметрами

**Конфигурация:**
```yaml
# config/config.yaml
cursor:
  cli:
    cli_path: "docker-compose-agent"
    timeout: 1000
    model: ""  # Auto

agent:
  role: "Project Executor Agent"
```

```env
# .env
CURSOR_API_KEY=sk_cursor_xxx
PROJECT_DIR=D:\Space\life
```

**Вызов в коде:**
```python
# 1. Инициализация
cli = create_cursor_cli_interface(
    cli_path="docker-compose-agent",
    timeout=1000,
    headless=True,
    project_dir="D:\\Space\\life",
    agent_role="Project Executor Agent"
)

# 2. Выполнение инструкции
result = cli.execute_instruction(
    instruction="Создай файл test.txt с текстом 'Hello'",
    task_id="task_001",
    working_dir="D:\\Space\\life",
    timeout=1000
)
```

**Внутренний вызов:**
```python
# cli.execute_instruction() вызывает:
cli.execute(
    prompt="Создай файл test.txt с текстом 'Hello'",
    working_dir="D:\\Space\\life",
    timeout=1000,
    new_chat=True  # Всегда True для execute_instruction()
)
```

**Итоговая команда:**
```bash
docker exec \
  -e CURSOR_API_KEY=sk_cursor_xxx \
  cursor-agent-life \
  bash -c 'export CURSOR_API_KEY=sk_cursor_xxx && export LANG=C.UTF-8 LC_ALL=C.UTF-8 && cd /workspace && /root/.local/bin/agent -p "Создай файл test.txt с текстом '\''Hello'\''" --force --approve-mcps'
```

**Параметры subprocess.run():**
```python
subprocess.run(
    cmd,  # Команда выше
    input=None,  # stdin не используется
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    timeout=1000,  # Из конфига или параметра
    cwd=None,  # Рабочая директория уже в команде (cd /workspace)
    env=None,  # Переменные окружения в команде
    text=True,
    encoding='utf-8',
    errors='replace'
)
```

### Передача роли агента

**Роль агента НЕ передается напрямую в команду agent.** Вместо этого она настраивается через файлы в целевом проекте.

**Инициализация роли:**
```python
# src/cursor_cli_interface.py::_setup_agent_role()
def _setup_agent_role(self, project_dir: str, agent_role: str) -> None:
    project_path = Path(project_dir)
    
    # 1. Проверка .cursor/rules (Cursor автоматически читает)
    cursor_rules_dir = project_path / ".cursor" / "rules"
    if cursor_rules_dir.exists():
        logger.debug("Директория .cursor/rules существует, роль агента будет настроена через правила")
    
    # 2. Создание AGENTS.md (если не существует)
    agents_md = project_path / "AGENTS.md"
    if not agents_md.exists() and agent_role:
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
```

**Файлы, которые Cursor CLI читает автоматически:**
1. `.cursor/rules` - правила и инструкции для агента
2. `AGENTS.md` - описание ролей агентов (создается автоматически)
3. `CLAUDE.md` - контекст для Claude API

**Важно:** Роль агента настраивается один раз при инициализации интерфейса, а не при каждом вызове.

### Управление сессиями (чатами)

**Создание нового чата:**
```python
result = cli.execute(
    prompt="Инструкция",
    new_chat=True  # По умолчанию
)
# Команда: agent -p "Инструкция" --force --approve-mcps
```

**Продолжение существующего чата:**
```python
# Автоматическое продолжение последнего чата
result = cli.execute(
    prompt="Продолжи задачу",
    new_chat=False
)
# Команда: agent --resume <last_chat_id> -p "Продолжи задачу" --force --approve-mcps

# Явное указание chat_id
result = cli.execute(
    prompt="Продолжи задачу",
    chat_id="chat-123"
)
# Команда: agent --resume chat-123 -p "Продолжи задачу" --force --approve-mcps
```

**Остановка активных чатов:**
```python
# Останавливает все процессы agent в контейнере
cli.stop_active_chats()

# Docker команда:
# docker exec cursor-agent-life bash -c "pkill -f 'agent.*-p' || pkill -f '/root/.local/bin/agent' || true"
```

**Очистка перед новой задачей:**
```python
# Останавливает активные чаты и сбрасывает chat_id
cli.prepare_for_new_task()
```

### Обработка таймаутов

**Базовый таймаут:**
- Из конфига: `timeout: 1000` секунд
- Для Docker: минимум 600 секунд (10 минут)

**Умное продление для Docker:**
```python
max_timeout_retries = 5
current_timeout = exec_timeout

for retry in range(max_timeout_retries):
    try:
        result = subprocess.run(cmd, timeout=current_timeout, ...)
        break
    except subprocess.TimeoutExpired:
        if use_docker and retry < max_timeout_retries - 1:
            # Проверка активности контейнера
            container_active = self._check_docker_container_activity("cursor-agent-life")
            if container_active:
                # Продление таймаута в 2 раза
                current_timeout = exec_timeout * 2
                continue
```

**Коды возврата:**
- `0` - успешное выполнение
- `137` - SIGKILL (для Docker может быть нормальным, если процесс выполнился в фоне)
- `143` - SIGTERM (может быть нормальным, если процесс завершился корректно)
- Другие коды - ошибка

### Экранирование промпта

**Для Docker используется `shlex.quote()`:**
```python
import shlex
escaped_prompt = shlex.quote(prompt)
# Пример: "Создай файл 'test.txt'" -> "'Создай файл '\''test.txt'\'''"
```

**Поддержка кириллицы:**
```bash
export LANG=C.UTF-8 LC_ALL=C.UTF-8
```

### Автоматический запуск Docker контейнера

**Проверка и запуск:**
```python
# src/cursor_cli_interface.py::_ensure_docker_container_running()
container_status = self._ensure_docker_container_running(compose_file)

# Если контейнер не запущен:
# docker compose -f docker/docker-compose.agent.yml up -d
```

**Проверка статуса:**
```bash
docker inspect --format "{{.State.Status}}" cursor-agent-life
# Возвращает: running, exited, created, restarting
```

**Обработка проблем:**
- Если контейнер в состоянии `restarting` - удаляется и создается заново
- Проверка здоровья контейнера через `docker exec cursor-agent-life echo ok`

### Ручное создание (файловый интерфейс)

```python
# Code Agent создает файл инструкции
cursor_file.write_instruction(
    instruction="Создай файл test.txt",
    task_id="task_001",
    new_chat=True
)

# Пользователь вручную:
# 1. Открывает Cursor IDE
# 2. Читает cursor_commands/instruction_task_001_NEW_CHAT.txt
# 3. Выполняет инструкцию в Cursor
# 4. Создает файл:
#    echo "Результат: файл создан
#    Задача выполнена!" > cursor_results/result_task_001.txt

# Code Agent ждет и читает результат
wait_result = cursor_file.wait_for_result(
    task_id="task_001",
    control_phrase="Задача выполнена!"
)
```

## Выявленные проблемы и рекомендации

### Проблема 1: Модель не передается для локального и WSL вариантов

**Описание:**
Модель из конфига (`cursor.cli.model`) читается и передается через флаг `-m` только для Docker варианта. Для локального CLI и WSL модель не передается, даже если указана в конфиге.

**Код проблемы:**
```python
# src/cursor_cli_interface.py:1122, 1140
# Для WSL и локального CLI модель не добавляется
cmd.extend(["-p", prompt, "--force", "--approve-mcps"])
# Нет проверки model из конфига
```

**Рекомендация:**
Добавить чтение модели из конфига и для локального/WSL вариантов:
```python
# Для локального и WSL также нужно добавить:
model_name = cli_config.get('model', '').strip()
if model_name:
    cmd.extend(["-m", model_name])
```

### Проблема 2: Роль агента настраивается только при инициализации

**Описание:**
Роль агента настраивается через файлы проекта (`.cursor/rules`, `AGENTS.md`) только при создании интерфейса. Если роль изменилась в конфиге, нужно пересоздать интерфейс.

**Рекомендация:**
Добавить проверку изменения роли и обновление файлов при необходимости.

### Проблема 3: CURSOR_API_KEY может не передаваться корректно

**Описание:**
CURSOR_API_KEY передается двумя способами:
1. Через `-e` флаг docker exec
2. Через `export` в bash команде

Если `.env` файл не найден или ключ не установлен, команда выполнится без ключа, что приведет к ошибке аутентификации.

**Рекомендация:**
Добавить проверку наличия CURSOR_API_KEY перед выполнением команды и явное сообщение об ошибке, если ключ отсутствует.

## Диагностика вызовов

### Логирование

**Уровень INFO:**
```python
logger.info(f"Выполнение команды через Cursor CLI: {' '.join(cmd)}")
```

**Уровень DEBUG:**
```python
logger.debug(f"Рабочая директория: {exec_cwd}")
logger.debug(f"Таймаут: {exec_timeout} секунд")
if use_docker:
    logger.debug(f"Docker Compose файл: {compose_file}")
    if cursor_api_key:
        logger.debug("CURSOR_API_KEY передан в Docker контейнер")
    logger.debug(f"Использование модели из конфига: {model_name}")
```

### Проверка команды перед выполнением

**Для отладки можно добавить:**
```python
# Перед subprocess.run()
logger.debug(f"Полная команда: {' '.join(cmd)}")
logger.debug(f"Bash команда: {bash_env_export if use_docker else 'N/A'}")
```

### Проверка результата

**После выполнения:**
```python
if result.returncode == 0:
    logger.info("Команда Cursor CLI выполнена успешно")
else:
    logger.warning(f"Команда Cursor CLI завершилась с кодом {result.returncode}")
    if result_stderr:
        logger.debug(f"Stderr: {result_stderr[:500]}")
```

## Связанные файлы

- `src/cursor_file_interface.py` - Реализация файлового интерфейса
- `src/cursor_cli_interface.py` - Реализация CLI интерфейса (строки 889-1347)
- `src/server.py` - Использование в основном сервере (строки 395-473, 1357-1506)
- `config/config.yaml` - Конфигурация параметров
- `docker/docker-compose.agent.yml` - Docker конфигурация
- `docs/integration/cursor_integration.md` - Общая документация по интеграции
