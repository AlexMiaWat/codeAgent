# Интеграция с официальным Cursor CLI

**Источник:** [Cursor CLI Documentation](https://cursor.com/docs/cli/overview)

## Официальная команда: `agent`

**ВАЖНО:** Официальная команда Cursor CLI называется `agent`, а не `cursor-agent`!

### Установка

```bash
# Установка через официальный скрипт
curl https://cursor.com/install -fsS | bash
```

После установки команда `agent` должна быть доступна в PATH (`~/.local/bin/agent`).

### Основные команды

#### Интерактивный режим

```bash
# Запуск интерактивной сессии
agent

# Запуск с начальным промптом
agent "refactor the auth module to use JWT tokens"
```

#### Non-interactive режим (для автоматизации)

```bash
# Выполнение с выводом результата
agent -p "find and fix performance issues"

# С указанием модели
agent -p "find and fix performance issues" --model "gpt-5"

# С форматированием вывода
agent -p "review these changes for security issues" --output-format text
```

#### Режимы работы

| Режим | Описание | Параметр |
|-------|----------|----------|
| **Agent** | Полный доступ ко всем инструментам (по умолчанию) | `--mode=agent` |
| **Plan** | Проектирование подхода перед кодированием | `--mode=plan` |
| **Ask** | Только чтение, без изменений | `--mode=ask` |

#### Управление сессиями

```bash
# Список всех чатов
agent ls

# Возобновить последний чат
agent resume

# Возобновить конкретный чат
agent --resume="chat-id-here"
```

#### Cloud Agent (для фонового выполнения)

```bash
# Отправить задачу в Cloud Agent (фоновое выполнение)
& refactor the auth module and add comprehensive tests
```

## Обновление Code Agent

### 1. Обновление `CursorCLIInterface`

Команда `agent` теперь имеет приоритет в поиске:

```python
CLI_COMMAND_NAMES = [
    "agent",          # Официальная команда ✅
    "cursor-agent",   # Альтернатива
    "cursor",
    "cursor-cli"
]
```

### 2. Использование правильной команды

Вместо `cursor-agent -p "instruction"` теперь:
```python
# Правильная команда
result = cli.execute(
    prompt="find and fix performance issues",
    working_dir="/path/to/project"
)

# Формируется команда:
# agent -p "find and fix performance issues"
```

### 3. Поддержка режимов

```python
# Выполнение в режиме Plan
result = cli.execute(
    prompt="refactor auth module",
    additional_args=["--mode=plan"]
)

# Выполнение в режиме Ask (только чтение)
result = cli.execute(
    prompt="analyze code structure",
    additional_args=["--mode=ask"]
)
```

### 4. Управление сессиями

```python
# Список сессий
result = subprocess.run(
    ["agent", "ls"],
    capture_output=True,
    text=True
)

# Возобновление сессии
result = cli.execute(
    prompt="continue previous task",
    additional_args=["--resume=chat-id-here"]
)
```

## Установка на Windows

### Через WSL (Ubuntu)

1. **Установить Ubuntu в WSL:**
   ```powershell
   # В PowerShell от имени администратора
   wsl --install -d Ubuntu
   ```

2. **Установить agent в WSL:**
   ```bash
   # В Ubuntu WSL
   curl https://cursor.com/install -fsS | bash
   export PATH="$HOME/.local/bin:$PATH"
   agent --version
   ```

3. **Добавить в PATH (если нужно):**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Проверка установки

```bash
# Проверка версии
agent --version

# Проверка помощи
agent --help

# Тест выполнения
agent -p "echo 'test'" --output-format text
```

## Интеграция с Code Agent

### Автоматическое обнаружение

`CursorCLIInterface` автоматически ищет команду `agent` в PATH:

```python
from src.cursor_cli_interface import create_cursor_cli_interface

cli = create_cursor_cli_interface()
if cli.is_available():
    print(f"Agent найден: {cli.cli_command}")
    # Теперь cli.cli_command = "agent"
else:
    print("Agent не найден - требуется установка")
```

### Выполнение инструкций

```python
# Автоматическое выполнение через agent
result = cli.execute(
    prompt="Create test file with hello world",
    working_dir="/path/to/project",
    timeout=300
)

if result.success:
    print("Задача выполнена успешно")
    print(result.stdout)
else:
    print(f"Ошибка: {result.error_message}")
```

## Режимы работы для Code Agent

### Agent mode (по умолчанию)

Полный доступ ко всем инструментам - для сложных задач кодирования:
```python
result = cli.execute(
    prompt="Refactor auth module to use JWT tokens"
)
```

### Plan mode

Проектирование подхода перед кодированием:
```python
result = cli.execute(
    prompt="Design API structure for user management",
    additional_args=["--mode=plan"]
)
```

### Ask mode

Только чтение и анализ, без изменений:
```python
result = cli.execute(
    prompt="Analyze code structure and suggest improvements",
    additional_args=["--mode=ask"]
)
```

## Примеры использования

### Пример 1: Создание файла

```python
instruction = """Create a new file src/utils/helpers.py with:
- A function `greet(name: str) -> str` that returns a greeting
- A function `calculate_sum(a: int, b: int) -> int` that returns the sum
- Include type hints and docstrings"""

result = cli.execute(
    prompt=instruction,
    working_dir="/path/to/project"
)
```

### Пример 2: Рефакторинг

```python
instruction = """Refactor the authentication module:
1. Extract JWT token generation to a separate utility
2. Add proper error handling
3. Update tests to cover new structure"""

result = cli.execute(
    prompt=instruction,
    additional_args=["--mode=plan"]  # Сначала план, потом выполнение
)
```

### Пример 3: Анализ кода

```python
instruction = """Analyze the codebase and identify:
- Code smells
- Performance bottlenecks
- Security vulnerabilities"""

result = cli.execute(
    prompt=instruction,
    additional_args=["--mode=ask"]  # Только чтение, без изменений
)
```

## Ожидаемые результаты

После правильной установки и настройки:

1. ✅ Команда `agent` доступна в системе
2. ✅ `CursorCLIInterface` автоматически находит команду
3. ✅ Автоматическое выполнение инструкций работает
4. ✅ Результаты возвращаются через stdout/stderr
5. ✅ Поддержка различных режимов работы

## Следующие шаги

1. **Установить agent через официальный скрипт**
2. **Обновить Code Agent для использования команды `agent`**
3. **Протестировать автоматическое выполнение**
4. **Настроить режимы работы для разных типов задач**
