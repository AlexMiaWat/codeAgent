# Статус установки cursor-agent

## Текущая ситуация

**Дата:** 2026-01-18  
**Проблема:** `cursor-agent` (официальный CLI от Cursor) не установлен в системе.

## Результаты проверки

### ✅ Что найдено:

1. **WSL доступен** - можно установить `cursor-agent` через WSL
2. **cursor.CMD доступен** - но это обычный редактор, не CLI агент

### ❌ Что не найдено:

1. **cursor-agent не установлен** - не найден в PATH
2. **cursor-agent не установлен в WSL** - требует установки

## Официальный способ установки

Для Linux/macOS/WSL:
```bash
curl https://cursor.com/install -fsS | bash
```

После установки `cursor-agent` должен быть в `~/.local/bin/cursor-agent`.

## Проблема с установкой на Windows

**Ошибка при установке через Git Bash:**
```
Unsupported operating system: MINGW64_NT-10.0-26200
```

**Причина:** Официальный установщик не поддерживает MINGW64 (Git Bash на Windows).

**Решение:** Установка через WSL (Windows Subsystem for Linux).

## Следующие шаги для установки через WSL

1. **Проверить WSL дистрибутив:**
   ```bash
   wsl --list --verbose
   ```

2. **Войти в WSL и установить cursor-agent:**
   ```bash
   wsl
   curl https://cursor.com/install -fsS | bash
   export PATH="$HOME/.local/bin:$PATH"
   cursor-agent --version
   ```

3. **Обновить PATH в WSL:**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

4. **Протестировать установку:**
   ```bash
   wsl cursor-agent --version
   ```

## Обновление Code Agent для поддержки WSL

После установки `cursor-agent` через WSL, нужно обновить `CursorCLIInterface` для поддержки запуска через WSL:

```python
# src/cursor_cli_interface.py
def _find_cli_in_path(self) -> tuple[Optional[str], bool]:
    """Поиск cursor-agent включая WSL"""
    # Стандартный поиск
    for cmd_name in self.CLI_COMMAND_NAMES:
        cmd_path = shutil.which(cmd_name)
        if cmd_path:
            return cmd_path, True
    
    # Проверка через WSL
    try:
        result = subprocess.run(
            ["wsl", "cursor-agent", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "wsl cursor-agent", True
    except:
        pass
    
    return None, False
```

## Рекомендации

**Для автоматизации на Windows:**

1. **Установить cursor-agent через WSL** (если WSL доступен) ✅ РЕКОМЕНДУЕТСЯ
2. **Обновить Code Agent** для поддержки WSL путей
3. **Протестировать автоматическое выполнение** через WSL

**Альтернативы (если WSL недоступен):**

- Создать расширение для Cursor для автоматического чтения файлов инструкций
- Использовать Background Agents API (для GitHub репозиториев)

## Статус

**Текущий:** ⚠️ Требуется установка `cursor-agent` через WSL  
**Следующий шаг:** Установить `cursor-agent` в WSL и протестировать
