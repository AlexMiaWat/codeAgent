# Изменения: Интеграция с официальным Cursor CLI

**Дата:** 2026-01-18  
**Источник:** [Cursor CLI Documentation](https://cursor.com/docs/cli/overview)

## Обновления

### 1. Обновление `CLI_COMMAND_NAMES`

**Было:**
```python
CLI_COMMAND_NAMES = [
    "cursor-agent",
    "cursor",
    "cursor-cli"
]
```

**Стало:**
```python
CLI_COMMAND_NAMES = [
    "agent",          # ✅ Официальная команда (приоритет)
    "cursor-agent",   # Альтернатива
    "cursor",
    "cursor-cli"
]
```

**Причина:** Согласно официальной документации, команда называется `agent`, а не `cursor-agent`.

### 2. Упрощение команды выполнения

**Было:**
```python
cmd = [self.cli_command, "-p", prompt]
if new_chat:
    cmd.append("--new-chat")  # Не поддерживается
if self.headless:
    cmd.append("--headless")  # Не поддерживается
```

**Стало:**
```python
cmd = [self.cli_command, "-p", prompt]
# Параметры --new-chat и --headless не требуются для agent -p
```

**Причина:** Согласно документации, `agent -p` автоматически создает новый контекст для каждой команды. Параметры `--new-chat` и `--headless` не нужны.

### 3. Поддержка WSL для Windows

**Добавлено:**
```python
def _find_cli_in_path(self) -> tuple[Optional[str], bool]:
    # ... стандартный поиск ...
    
    # Проверка через WSL для Windows
    if os.name == 'nt':  # Windows
        result = subprocess.run(["wsl", "which", "agent"], ...)
        if result.returncode == 0:
            return "wsl agent", True
```

**Преимущества:**
- Автоматическое обнаружение `agent` в WSL
- Автоматическая конвертация Windows путей в WSL пути
- Прозрачная работа через WSL

### 4. Правильная обработка WSL команд

**Добавлено:**
```python
if self.cli_command.startswith("wsl "):
    # Разбиваем "wsl agent" на ["wsl", "agent"]
    agent_cmd = self.cli_command.split()
    cmd = agent_cmd + ["-p", prompt]
    
    # Конвертируем D:\Space\life -> /mnt/d/Space/life
    if working_dir and os.name == 'nt':
        wsl_path = working_dir.replace('\\', '/').replace(':', '').lower()
        exec_cwd = f"/mnt/{wsl_path[0]}{wsl_path[1:]}"
```

**Преимущества:**
- Правильное формирование команды для WSL
- Автоматическая конвертация путей
- Прозрачная работа с Windows проектами через WSL

## Установка

### Официальный способ

```bash
# Установка через официальный скрипт
curl https://cursor.com/install -fsS | bash

# Проверка
agent --version
```

### Для Windows (через WSL)

```bash
# В Ubuntu WSL
curl https://cursor.com/install -fsS | bash
export PATH="$HOME/.local/bin:$PATH"
agent --version
```

## Использование

### Non-interactive режим (для автоматизации)

```python
from src.cursor_cli_interface import create_cursor_cli_interface

cli = create_cursor_cli_interface()
result = cli.execute(
    prompt="Create test file with hello world",
    working_dir="/path/to/project"
)

if result.success:
    print(result.stdout)
```

### С режимами

```python
# Plan mode - проектирование подхода
result = cli.execute(
    prompt="Design API structure",
    additional_args=["--mode=plan"]
)

# Ask mode - только чтение
result = cli.execute(
    prompt="Analyze code structure",
    additional_args=["--mode=ask"]
)
```

## Документация

- **Официальная документация:** https://cursor.com/docs/cli/overview
- **Режимы работы:** https://cursor.com/docs/agent/modes
- **Установка:** См. `INSTALL_CURSOR_AGENT.md`

## Статус

✅ **Код обновлен** для использования официальной команды `agent`  
✅ **Поддержка WSL** реализована  
✅ **Упрощена команда выполнения** согласно документации  
⏳ **Требуется установка `agent`** через официальный скрипт
