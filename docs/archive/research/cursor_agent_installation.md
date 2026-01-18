# Установка cursor-agent для автоматизации

## Текущая ситуация

**Проблема:** `cursor-agent` (официальный CLI от Cursor) не установлен в системе.

**Официальный способ установки:**
```bash
curl https://cursor.com/install -fsS | bash
```

**Требования:**
- macOS/Linux/WSL
- Или Git Bash на Windows

## Шаги установки

### Для Windows (через Git Bash)

1. Открыть Git Bash
2. Выполнить:
   ```bash
   curl https://cursor.com/install -fsS | bash
   ```
3. Добавить в PATH (если нужно):
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```
4. Проверить установку:
   ```bash
   cursor-agent --version
   ```

### Альтернатива: Проверка PATH

После установки `cursor-agent` должен быть в:
- `~/.local/bin/cursor-agent` (Linux/macOS/WSL)
- Или в системном PATH

## Проверка установки

После установки проверить:
```bash
cursor-agent --version
cursor-agent --help
```

## Использование для автоматизации

После установки можно использовать:

```bash
# Автоматическое выполнение инструкции
cursor-agent -p "инструкция" --force

# С выходом в JSON
cursor-agent -p "инструкция" --output-format json

# В определенной директории
cursor-agent -p "инструкция" --cwd /path/to/project
```

## Обновление кода Code Agent

После установки `cursor-agent`, `CursorCLIInterface` должен автоматически находить команду через `_find_cli_in_path()`.

Проверить можно через:
```python
from src.cursor_cli_interface import create_cursor_cli_interface

cli = create_cursor_cli_interface()
if cli.is_available():
    print(f"Cursor CLI найден: {cli.cli_command}")
    print(f"Версия: {cli.check_version()}")
else:
    print("Cursor CLI не найден")
```

## Следующие шаги

1. Установить `cursor-agent` через официальный скрипт
2. Проверить доступность в PATH
3. Протестировать автоматическое выполнение
4. Обновить Code Agent для использования `cursor-agent`
