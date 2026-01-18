# Решение для автоматизации Cursor на Windows

## Проблема

**Официальный `cursor-agent` НЕ поддерживает Windows напрямую:**
- Установщик `curl https://cursor.com/install -fsS | bash` работает только на Linux/macOS/WSL
- На Windows (Git Bash) получаем: `Unsupported operating system: MINGW64_NT-10.0-26200`

## Варианты решения для Windows

### Вариант 1: WSL (Windows Subsystem for Linux) ✅ РЕКОМЕНДУЕТСЯ

Если WSL доступен:

```bash
# В WSL
curl https://cursor.com/install -fsS | bash
export PATH="$HOME/.local/bin:$PATH"
cursor-agent --version
```

**Преимущества:**
- Официальная поддержка Cursor CLI
- Полная автоматизация
- Все возможности `cursor-agent`

**Недостатки:**
- Требует установки WSL
- Проект должен быть доступен из WSL

### Вариант 2: Файловый интерфейс + Расширение Cursor ⚠️ ТРЕБУЕТ РАЗРАБОТКИ

**Текущее состояние:**
- ✅ Code Agent создает файлы инструкций
- ❌ Нет автоматического выполнения (требуется ручное участие)

**Решение:**
- Создать расширение для Cursor, которое:
  1. Автоматически читает файлы из `cursor_commands/`
  2. Создает новый чат
  3. Выполняет инструкции
  4. Сохраняет результаты в `cursor_results/`

**Преимущества:**
- Работает на Windows без дополнительных компонентов
- Полная интеграция с Cursor IDE

**Недостатки:**
- Требует разработки расширения
- Зависит от внутреннего API Cursor

### Вариант 3: Background Agents API ⚠️ ОГРАНИЧЕНИЯ

**Требования:**
- API ключ CURSOR_API_KEY
- Проект на GitHub (не локальный)

**Преимущества:**
- Официальный API от Cursor
- Полная автоматизация

**Недостатки:**
- Работает только с GitHub репозиториями
- Требует API ключ
- Не работает с локальными проектами напрямую

### Вариант 4: Использование `cursor.CMD` с параметрами ❌ НЕ РАБОТАЕТ

**Проблема:**
- `cursor.CMD` - это обычный редактор, не CLI агент
- Не поддерживает параметры `-p`, `--force`, `--mode=plan`
- Предупреждение: `'p' is not in the list of known options`

## Рекомендация для Code Agent

### Для Windows:

**Кратковременное решение:**
- Использовать файловый интерфейс с инструкциями для пользователя
- Документировать процесс ручного выполнения

**Долгосрочное решение:**
1. **Установить WSL** и использовать `cursor-agent` через WSL
2. **Или создать расширение для Cursor** для автоматического чтения файлов инструкций
3. **Или использовать Background Agents API** (если проект на GitHub)

### Обновление кода:

Для автоматического обнаружения `cursor-agent` через WSL:

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
            ["wsl", "which", "cursor-agent"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            wsl_path = result.stdout.strip()
            # Возвращаем команду для запуска через WSL
            return f"wsl cursor-agent", True
    except:
        pass
    
    return None, False
```

## Следующие шаги

1. **Проверить доступность WSL** на системе
2. **Если WSL доступен** - установить `cursor-agent` через WSL
3. **Если WSL недоступен** - рассмотреть создание расширения или использование Background Agents API
4. **Обновить Code Agent** для поддержки WSL путей
