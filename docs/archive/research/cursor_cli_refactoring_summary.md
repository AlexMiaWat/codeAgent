# Переработка Cursor CLI интерфейса

**Дата:** 2026-01-18  
**Статус:** ✅ **Переработка завершена согласно документации**

## ✅ Реализовано

### 0. Открывать диалог в рамках целевого проекта с нужной ролью агента

**Изменения:**
- ✅ Добавлен параметр `project_dir` в `CursorCLIInterface.__init__()`
- ✅ Добавлен параметр `agent_role` для настройки роли
- ✅ Рабочая директория устанавливается в целевой проект (`/workspace` в Docker)
- ✅ Метод `_setup_agent_role()` создает `AGENTS.md` с описанием роли при необходимости
- ✅ Cursor автоматически читает `.cursor/rules` для настройки поведения агента

**Пример:**
```python
cli = create_cursor_cli_interface(
    cli_path="docker-compose-agent",
    project_dir="/path/to/target/project",
    agent_role="Project Executor Agent"
)
```

### 1. Держать диалог и передавать несколько команд, получать ответы в рамках одного диалога

**Изменения:**
- ✅ Добавлено управление `current_chat_id` для отслеживания активного чата
- ✅ Метод `list_chats()` - получение списка доступных чатов через `agent ls`
- ✅ Метод `resume_chat(chat_id)` - возобновление чата по ID
- ✅ Параметр `new_chat=False` в `execute()` - продолжение существующего диалога
- ✅ Автоматическое использование `--resume="chat-id"` при `new_chat=False`

**Пример использования:**
```python
# Первая команда - создает новый чат
result1 = cli.execute("Create file test1.txt", new_chat=True)

# Вторая команда - продолжает тот же диалог
result2 = cli.execute("Now create test2.txt", new_chat=False)

# Третья команда - продолжает тот же диалог
result3 = cli.execute("List all files", new_chat=False)
```

**Команды:**
- Новый чат: `agent -p "prompt"` (new_chat=True)
- Продолжение: `agent --resume="chat-id" -p "prompt"` (new_chat=False)

### 2. Создавать новые чаты

**Изменения:**
- ✅ `agent -p "prompt"` автоматически создает новый чат (new_chat=True по умолчанию)
- ✅ `new_chat=True` сбрасывает `current_chat_id`, создавая новый контекст
- ✅ Для новой задачи всегда используется `new_chat=True` (в `execute_instruction()`)

**Пример:**
```python
# Создание нового чата для каждой задачи
for task in tasks:
    result = cli.execute_instruction(
        instruction=task.instruction,
        task_id=task.id,
        new_chat=True  # Всегда новый чат для новой задачи
    )
```

## Изменения в коде

### 1. `CursorCLIInterface.__init__()`

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

### 2. Новые методы

**`list_chats()`** - список доступных чатов:
```python
chats = cli.list_chats()  # Возвращает список chat_id
```

**`resume_chat(chat_id)`** - возобновление чата:
```python
cli.resume_chat("chat-123")  # Устанавливает current_chat_id
# или автоматически
cli.resume_chat()  # Автоматически находит последний чат
```

**`_setup_agent_role()`** - настройка роли агента в проекте:
```python
cli._setup_agent_role(project_dir, agent_role)
# Создает AGENTS.md с описанием роли (если не существует)
```

### 3. Обновлен `execute()`

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

**Логика управления сессиями:**
1. Если `chat_id` указан → использует его для `--resume`
2. Если `new_chat=False` и `current_chat_id` установлен → продолжает диалог
3. Если `new_chat=False` и `current_chat_id` не установлен → автоматически возобновляет последний чат
4. Если `new_chat=True` → создает новый чат (по умолчанию для `agent -p`)

### 4. Обновлена команда для Docker

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

### 5. Интеграция с CodeAgentServer

Обновлен `_init_cursor_cli()` в `server.py`:

```python
agent_config = self.config.get('agent', {})
cli_interface = create_cursor_cli_interface(
    cli_path=cli_path,
    timeout=timeout,
    headless=headless,
    project_dir=str(self.project_dir),      # ✅ Целевой проект
    agent_role=agent_config.get('role')     # ✅ Роль агента
)
```

## Использование

### Создание нового чата для задачи

```python
cli = create_cursor_cli_interface(
    cli_path="docker-compose-agent",
    project_dir="/path/to/target/project",
    agent_role="Project Executor Agent"
)

# Новый чат для каждой задачи
result = cli.execute_instruction(
    instruction="Create file test.txt",
    task_id="task_001"
)
```

### Продолжение диалога в рамках одной задачи

```python
# Первая команда - новый чат
result1 = cli.execute("Create file test1.txt", new_chat=True)

# Последующие команды - продолжение диалога
result2 = cli.execute("Now add content to test1.txt", new_chat=False)
result3 = cli.execute("List all test files", new_chat=False)
```

### Явное управление чатами

```python
# Получить список чатов
chats = cli.list_chats()

# Возобновить конкретный чат
cli.resume_chat("chat-123")
result = cli.execute("Continue task", chat_id="chat-123")
```

## Структура

```
CursorCLIInterface
├── __init__(project_dir, agent_role)    # ✅ Рабочая директория и роль
├── _setup_agent_role()                  # ✅ Настройка роли в проекте
├── list_chats()                         # ✅ Список доступных чатов
├── resume_chat(chat_id)                 # ✅ Возобновление чата
└── execute(new_chat, chat_id)           # ✅ Управление сессиями
    ├── Новый чат: agent -p "prompt"
    └── Продолжение: agent --resume="chat-id" -p "prompt"
```

## Следующие шаги

1. ✅ **Реализовано** - управление сессиями (list_chats, resume_chat)
2. ✅ **Реализовано** - работа в целевом проекте (project_dir)
3. ✅ **Реализовано** - настройка роли агента (_setup_agent_role)
4. ✅ **Реализовано** - поддержка --resume для продолжения диалога
5. **Тестирование** - проверить работу с реальными задачами

## Документация

- **Cursor CLI Docs:** https://cursor.com/docs/cli/overview
- **Рефакторинг:** `docs/cursor_cli_refactoring.md`
- **Итоговый отчет:** Этот файл
