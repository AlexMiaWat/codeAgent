# Настройка полного доступа для Cursor CLI

## Обзор

Этот документ описывает настройку Cursor CLI для автоматического выполнения команд без запросов разрешений. Это необходимо для полной автоматизации работы Code Agent.

## Что было настроено

### 1. Конфигурация разрешений (`.cursor/cli-config.json`)

Создан файл конфигурации с полным списком разрешенных операций:

**Разрешенные операции:**
- **Shell команды**: git, npm, python, pytest, pip, docker, make, bash и др.
- **Чтение файлов**: src/**, docs/**, test/**, config/**, *.md, *.py, *.json, *.yaml
- **Запись файлов**: src/**, docs/**, test/**, config/**, *.md, *.py, *.json, *.yaml

**Запрещенные операции (для безопасности):**
- Запись в файлы с секретами: *.env, credentials*, secrets*, *_key*, *_secret*
- Опасные команды: rm -rf /, dd, mkfs, format

### 2. Одобрение MCP серверов (`.cursor/mcp-approvals.json`)

Предварительно одобрены все MCP серверы:
- `life-docs` - документация проекта Life
- `playwright` - автоматизация браузера
- `filesystem` - работа с файловой системой
- `git` - Git операции

### 3. Обновление Cursor CLI интерфейса

В `src/cursor_cli_interface.py` добавлены флаги для всех типов выполнения:

```python
# Для Docker
bash_pipe_cmd = f'printf "%s\\n" "{escaped_prompt}" | agent -p --force --approve-mcps'

# Для WSL
cmd.extend(["-p", prompt, "--force", "--approve-mcps"])

# Для локального agent
cmd.extend(["-p", prompt, "--force", "--approve-mcps"])
```

**Флаги:**
- `--force` - автоматически применяет изменения файлов без подтверждения
- `--approve-mcps` - автоматически одобряет использование MCP серверов/инструментов

### 4. Обновление конфигурации проекта

В `config/config.yaml` добавлены настройки:

```yaml
cursor:
  cli:
    auto_approve: true        # Автоматическое одобрение всех действий
    force_mode: true          # Принудительное применение изменений
    approve_mcps: true        # Автоматическое одобрение MCP
  
  permissions:
    enabled: true
    config_file: ".cursor/cli-config.json"
    mcp_approvals_file: ".cursor/mcp-approvals.json"
    allow_shell: [git, npm, python, pytest, ...]
    allow_read: [src/**, docs/**, ...]
    allow_write: [src/**, docs/**, ...]
    deny_write: [**/*.env, **/credentials*, ...]
```

## Как это работает

### Процесс выполнения команды

1. **Code Agent** формирует инструкцию для Cursor
2. **Cursor CLI** получает команду с флагами `--force --approve-mcps`
3. **Cursor** проверяет разрешения в `.cursor/cli-config.json`
4. **Cursor** проверяет одобрение MCP в `.cursor/mcp-approvals.json`
5. **Cursor** выполняет команду **без запросов разрешений**
6. **Cursor** возвращает результат Code Agent

### Пример команды

```bash
# Docker (как настроено в проекте)
docker exec -i cursor-agent bash -c \
  'export LANG=C.utf8 LC_ALL=C.utf8 && cd /workspace && \
   script -q -c "printf \"%s\\n\" \"Создай файл test.py\" | agent -p --force --approve-mcps" /dev/null'

# Локальный agent
agent -p "Создай файл test.py" --force --approve-mcps

# WSL
wsl agent -p "Создай файл test.py" --force --approve-mcps
```

## Безопасность

### Что защищено

✅ **Секретные файлы** - запрещена запись в:
- `*.env` файлы
- `credentials*` файлы
- `secrets*` файлы
- `*_key*` и `*_secret*` файлы

✅ **Опасные команды** - запрещены:
- `rm -rf /` и подобные
- `dd` (низкоуровневое копирование)
- `mkfs` (форматирование дисков)
- `format` (форматирование)

### Что разрешено

✅ **Все операции в рамках проекта**:
- Чтение/запись в `src/`, `docs/`, `test/`, `config/`
- Git операции
- Запуск тестов
- Установка зависимостей
- Docker операции

## Проверка настроек

### 1. Проверить конфигурацию разрешений

```bash
# Проверить, что файл существует
ls -la .cursor/cli-config.json

# Проверить содержимое
cat .cursor/cli-config.json
```

### 2. Проверить одобрение MCP

```bash
# Проверить, что файл существует
ls -la .cursor/mcp-approvals.json

# Проверить содержимое
cat .cursor/mcp-approvals.json
```

### 3. Тестовая команда

```bash
# Локальный agent
agent -p "Создай файл test_permissions.txt с текстом 'Hello World'" --force --approve-mcps

# Docker (если настроен)
docker exec -i cursor-agent bash -c \
  'printf "%s\n" "Создай файл test_permissions.txt" | agent -p --force --approve-mcps'
```

### 4. Проверить логи

```bash
# Проверить логи Code Agent
tail -f logs/code_agent.log

# Проверить логи Cursor CLI
# (если доступны в Docker или локально)
```

## Устранение проблем

### Проблема: Cursor все еще запрашивает разрешения

**Решение:**

1. Проверьте, что файлы конфигурации существуют:
   ```bash
   ls -la .cursor/cli-config.json
   ls -la .cursor/mcp-approvals.json
   ```

2. Проверьте, что флаги добавлены в команду:
   ```bash
   # Должно быть: agent -p "..." --force --approve-mcps
   # Проверьте логи: logs/code_agent.log
   ```

3. Проверьте версию Cursor CLI:
   ```bash
   agent --version
   # Должна быть версия 2026 или новее
   ```

### Проблема: MCP серверы не работают

**Решение:**

1. Проверьте одобрение MCP:
   ```bash
   cat .cursor/mcp-approvals.json
   ```

2. Вручную одобрите MCP сервер:
   ```bash
   cursor-agent mcp login <server-name>
   ```

3. Проверьте, что флаг `--approve-mcps` присутствует в команде

### Проблема: Запрещенные операции

**Решение:**

1. Проверьте список `deny` в `.cursor/cli-config.json`
2. Если операция безопасна, добавьте её в `allow`
3. Перезапустите Code Agent

## Дополнительная настройка

### Добавление новых разрешений

Отредактируйте `.cursor/cli-config.json`:

```json
{
  "permissions": {
    "allow": [
      "Shell(новая-команда)",
      "Read(новый/путь/**)",
      "Write(новый/путь/**)"
    ]
  }
}
```

### Добавление нового MCP сервера

Отредактируйте `.cursor/mcp-approvals.json`:

```json
{
  "approvals": {
    "новый-сервер": {
      "approved": true,
      "timestamp": "2026-01-18T00:00:00Z",
      "auto_approve": true
    }
  }
}
```

### Глобальная конфигурация

Для применения настроек ко всем проектам:

```bash
# Скопируйте конфигурацию в глобальную директорию
cp .cursor/cli-config.json ~/.cursor/cli-config.json
cp .cursor/mcp-approvals.json ~/.cursor/mcp-approvals.json
```

## Рекомендации

### ✅ Рекомендуется

1. **Использовать в доверенных окружениях** - только для проектов, которым вы доверяете
2. **Регулярно проверять логи** - контролировать выполняемые операции
3. **Обновлять deny-список** - добавлять опасные операции по мере обнаружения
4. **Тестировать на изолированных проектах** - перед применением к важным проектам

### ⚠️ Не рекомендуется

1. **Использовать на production серверах** - только для разработки
2. **Давать доступ к системным директориям** - ограничьтесь проектом
3. **Разрешать запись в системные файлы** - /etc, /usr, /bin и т.д.
4. **Отключать deny-список** - всегда держите базовые запреты

## Ссылки

- [Cursor CLI Documentation](https://docs.cursor.com/cli/overview)
- [Cursor CLI Permissions](https://docs.cursor.com/cli/reference/permissions)
- [Cursor CLI Headless Mode](https://docs.cursor.com/cli/headless)
- [MCP (Model Context Protocol)](https://docs.cursor.com/advanced/model-context-protocol)

## История изменений

### 2026-01-18 - Начальная настройка

- ✅ Создан `.cursor/cli-config.json` с полными разрешениями
- ✅ Создан `.cursor/mcp-approvals.json` с одобрением MCP серверов
- ✅ Обновлен `src/cursor_cli_interface.py` с флагами `--force --approve-mcps`
- ✅ Обновлен `config/config.yaml` с настройками разрешений
- ✅ Создана документация по настройке

## Поддержка

Если возникли проблемы:

1. Проверьте логи: `logs/code_agent.log`
2. Проверьте конфигурацию: `.cursor/cli-config.json`
3. Проверьте одобрения MCP: `.cursor/mcp-approvals.json`
4. Обратитесь к документации Cursor CLI
5. Создайте issue в репозитории проекта
