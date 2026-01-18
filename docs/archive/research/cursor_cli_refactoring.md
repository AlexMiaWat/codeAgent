# Переработка Cursor CLI интерфейса согласно документации

**Дата:** 2026-01-18  
**Источник:** [Cursor CLI Documentation](https://cursor.com/docs/cli/overview)

## Требования проекта

### 0. Важно открывать диалог в рамках целевого проекта с нужной ролью агента

**Реализовано:**
- ✅ Добавлен параметр `project_dir` в `CursorCLIInterface.__init__()`
- ✅ Рабочая директория устанавливается в целевой проект (`/workspace` в Docker)
- ✅ Роль агента настраивается через `.cursor/rules` (Cursor автоматически читает)
- ✅ Метод `_setup_agent_role()` создает `AGENTS.md` с описанием роли при необходимости

### 1. Важно держать диалог и передавать несколько команд, получать ответы в рамках одного диалога

**Реализовано:**
- ✅ Добавлено управление `current_chat_id` для отслеживания активного чата
- ✅ Метод `list_chats()` - получение списка доступных чатов через `agent ls`
- ✅ Метод `resume_chat(chat_id)` - возобновление чата по ID
- ✅ Параметр `new_chat=False` в `execute()` - продолжение существующего диалога
- ✅ Автоматическое использование `--resume="chat-id"` при `new_chat=False`

**Пример использования:**
```python
cli = create_cursor_cli_interface(project_dir="/path/to/project")

# Первая команда - создает новый чат
result1 = cli.execute("Create file test1.txt", new_chat=True)

# Вторая команда - продолжает тот же диалог
result2 = cli.execute("Now create test2.txt", new_chat=False)

# Или явно указать chat_id
cli.resume_chat("chat-123")
result3 = cli.execute("Add content to test1.txt", chat_id="chat-123")
```

### 2. Создавать новые чаты

**Реализовано:**
- ✅ `agent -p "prompt"` автоматически создает новый чат (new_chat=True по умолчанию)
- ✅ `new_chat=True` сбрасывает `current_chat_id`, создавая новый контекст
- ✅ Для новой задачи всегда используется `new_chat=True` (в `execute_instruction()`)

## Изменения в коде

### 1. Обновлен `CursorCLIInterface.__init__()`

```python
def __init__(
    self,
    cli_path: Optional[str] = None,
    default_timeout: int = 300,
    headless: bool = True,
    project_dir: Optional[str] = None,  # ✅ Новое
    agent_role: Optional[str] = None    # ✅ Новое
):
    self.project_dir = Path(project_dir) if project_dir else None
    self.agent_role = agent_role
    self.current_chat_id: Optional[str] = None  # ✅ Новое
```

### 2. Добавлен метод `_setup_agent_role()`

Настраивает роль агента в целевом проекте через `.cursor/rules` или `AGENTS.md`.

### 3. Добавлены методы управления сессиями

- `list_chats()` - список доступных чатов через `agent ls`
- `resume_chat(chat_id)` - возобновление чата

### 4. Обновлен метод `execute()`

```python
def execute(
    self,
    prompt: str,
    working_dir: Optional[str] = None,
    timeout: Optional[int] = None,
    additional_args: Optional[list[str]] = None,
    new_chat: bool = True,          # ✅ Улучшено
    chat_id: Optional[str] = None   # ✅ Новое
) -> CursorCLIResult:
```

**Логика:**
- Если `chat_id` указан → использует его для `--resume`
- Если `new_chat=False` и `current_chat_id` установлен → продолжает диалог
- Если `new_chat=True` → создает новый чат (по умолчанию для `agent -p`)

### 5. Обновлена команда для Docker

**Было:**
```python
f'export LANG=C.utf8 LC_ALL=C.utf8 && cd /workspace && /root/.local/bin/agent -p \'{escaped_prompt}\''
```

**Стало:**
```python
# С поддержкой --resume для продолжения диалога
agent_cmd_parts = ["/root/.local/bin/agent"]
if resume_chat_id:
    agent_cmd_parts.append(f'--resume=\'{escaped_chat_id}\'')
agent_cmd_parts.extend(["-p", f'\'{escaped_prompt}\''])
agent_cmd = ' '.join(agent_cmd_parts)
f'export LANG=C.utf8 LC_ALL=C.utf8 && cd /workspace && {agent_cmd}'
```

## Использование

### Создание нового чата

```python
cli = create_cursor_cli_interface(
    cli_path="docker-compose-agent",
    project_dir="/path/to/target/project",
    agent_role="Project Executor Agent"
)

# Новый чат
result = cli.execute("Create file test.txt", new_chat=True)
```

### Продолжение диалога

```python
# Продолжение текущего диалога
result1 = cli.execute("Create file test1.txt", new_chat=True)
result2 = cli.execute("Now create test2.txt", new_chat=False)  # Продолжает тот же чат
result3 = cli.execute("List files", new_chat=False)  # Продолжает тот же чат
```

### Явное указание chat_id

```python
# Получить список чатов
chats = cli.list_chats()

# Возобновить конкретный чат
cli.resume_chat("chat-123")

# Или указать в execute()
result = cli.execute("Continue task", chat_id="chat-123")
```

## Интеграция с CodeAgentServer

Обновлен `_init_cursor_cli()` в `server.py`:

```python
cli_interface = create_cursor_cli_interface(
    cli_path=cli_path,
    timeout=timeout,
    headless=headless,
    project_dir=str(self.project_dir),      # ✅ Целевой проект
    agent_role=agent_config.get('role')     # ✅ Роль агента
)
```

Теперь Code Agent автоматически:
1. Устанавливает рабочую директорию в целевой проект
2. Настраивает роль агента через `.cursor/rules` или `AGENTS.md`
3. Поддерживает продолжение диалога в рамках одной задачи

## Следующие шаги

1. ✅ Реализовано - управление сессиями
2. ✅ Реализовано - работа в целевом проекте
3. ✅ Реализовано - настройка роли агента
4. **Тестирование** - проверить работу с реальными задачами
