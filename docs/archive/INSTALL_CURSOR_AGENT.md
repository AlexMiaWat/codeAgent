# Установка официального Cursor CLI (`agent`)

**Документация:** https://cursor.com/docs/cli/overview

## ⚠️ ВАЖНО: Команда называется `agent`, а не `cursor-agent`!

## Быстрая установка

### Для Linux/macOS/WSL

```bash
# Установка через официальный скрипт
curl https://cursor.com/install -fsS | bash

# Проверка установки
agent --version

# Если команда не найдена, добавь в PATH
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Установка на Windows

### Вариант 1: Через WSL (Ubuntu) ✅ РЕКОМЕНДУЕТСЯ

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

4. **Проверка из Windows:**
   ```bash
   wsl agent --version
   ```

### Вариант 2: Использование напрямую из WSL

После установки в WSL, Code Agent может вызывать команду через WSL:

```python
# Code Agent автоматически найдет agent в WSL
cli = create_cursor_cli_interface()
if cli.is_available():
    # Команда будет: wsl agent -p "instruction"
    result = cli.execute(prompt="...")
```

## Проверка установки

```bash
# Проверка версии
agent --version

# Проверка помощи
agent --help

# Тест выполнения (создаст файл test.txt)
agent -p "Create file test.txt with content 'Hello World'"
```

## Интеграция с Code Agent

После установки `agent`, Code Agent автоматически найдет команду через `CursorCLIInterface`:

```python
from src.cursor_cli_interface import create_cursor_cli_interface

cli = create_cursor_cli_interface()
if cli.is_available():
    print(f"Agent найден: {cli.cli_command}")
    # cli.cli_command будет "agent" или "wsl agent" (если в WSL)
else:
    print("Agent не найден - требуется установка")
```

## Использование

### Интерактивный режим

```bash
agent
agent "refactor the auth module"
```

### Non-interactive режим (для автоматизации)

```bash
agent -p "find and fix performance issues"
agent -p "create test file" --output-format text
```

### Режимы работы

```bash
# Agent mode (по умолчанию) - полный доступ
agent -p "refactor code"

# Plan mode - проектирование подхода
agent -p "design API" --mode=plan

# Ask mode - только чтение, без изменений
agent -p "analyze code" --mode=ask
```

## Обновление

```bash
# Обновление agent
agent update
# или
curl https://cursor.com/install -fsS | bash
```

## Troubleshooting

### Команда не найдена

Если `agent` не найден после установки:

1. Проверь PATH:
   ```bash
   echo $PATH
   ls ~/.local/bin/agent
   ```

2. Добавь в PATH:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. Проверь права:
   ```bash
   chmod +x ~/.local/bin/agent
   ```

### WSL проблемы

Если agent установлен в WSL, но не доступен из Windows:

1. Проверь через WSL:
   ```bash
   wsl agent --version
   ```

2. Убедись, что PATH настроен в WSL:
   ```bash
   wsl echo $PATH
   wsl ls ~/.local/bin/agent
   ```

## Ссылки

- **Официальная документация:** https://cursor.com/docs/cli/overview
- **Документация режимов:** https://cursor.com/docs/agent/modes
