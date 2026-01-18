# Исследование Cursor CLI для автоматического выполнения

## Проблема

Текущая реализация использует `cursor.CMD -p`, но это **НЕ команда для автоматического выполнения инструкций**.

Из `cursor.CMD --help` видно, что это обычный редактор Cursor IDE с параметрами для открытия файлов/папок, но **НЕ для выполнения инструкций**.

## Вывод из `cursor.CMD --help`

```
Usage: cursor.exe [options][paths...]
Options:
  -d --diff <file> <file>                    Compare two files
  -m --merge <path1> <path2> <base> <result> Perform a three-way merge
  -a --add <folder>                          Add folder(s) to the last active window
  -g --goto <file:line[:character]>          Open a file at the path
  -n --new-window                            Force to open a new window
  -r --reuse-window                          Force to open a file or folder
  -w --wait                                  Wait for the files to be closed
  -h --help                                  Print usage
```

**Проблема:** Нет параметров для выполнения инструкций (`-p`, `--print`, `--force`).

## Что нужно найти

Для автоматического выполнения нужна команда **`cursor-agent`**, которая:

1. Поддерживает режимы `--mode=plan` и `--mode=ask`
2. Имеет параметры `-p` / `--print` для non-interactive режима
3. Поддерживает `--force` для автоматического применения изменений
4. Может работать в headless режиме

## Текущий статус

- ❌ `cursor-agent` не найден в PATH
- ✅ `cursor.CMD` найден, но это обычный редактор, не CLI агент
- ⚠️ Команда `cursor.CMD -p` выдает предупреждение: `'p' is not in the list of known options`

## Решения

### Вариант 1: Установка cursor-agent

Возможно, `cursor-agent` - это отдельная утилита, которую нужно установить:

```bash
# Возможные варианты установки:
npm install -g cursor-agent
# или
cursor install-agent
# или отдельная загрузка
```

### Вариант 2: Использование Background Agents API

Для автоматизации через API (требует API ключ):

```python
import requests

def create_cursor_agent(instruction: str, repository: str):
    """Создать агента через Background Agents API"""
    api_key = os.getenv("CURSOR_API_KEY")
    response = requests.post(
        "https://api.cursor.com/v0/agents",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "repository": repository,
            "instruction": instruction
        }
    )
    return response.json()
```

### Вариант 3: Использование файлового интерфейса с автоматизацией

Файловый интерфейс работает, но требует **полуавтоматического** участия:
- Code Agent создает файл инструкции
- **Расширение для Cursor** автоматически читает файл и выполняет инструкцию
- Code Agent ожидает результат

### Вариант 4: Использование MCP (Model Context Protocol)

Если Cursor поддерживает MCP, можно использовать MCP серверы для автоматизации.

## Рекомендации

1. **Найти/установить `cursor-agent` CLI утилиту**
2. **Или использовать Background Agents API** (если доступен API ключ)
3. **Или создать расширение для Cursor** для автоматического чтения файлов инструкций
4. **Или использовать файловый интерфейс** как временное решение до автоматизации

## Следующие шаги

1. Проверить документацию Cursor на предмет установки `cursor-agent`
2. Проверить наличие API ключа для Background Agents API
3. Протестировать файловый интерфейс с автоматизацией
4. Рассмотреть создание расширения для Cursor
