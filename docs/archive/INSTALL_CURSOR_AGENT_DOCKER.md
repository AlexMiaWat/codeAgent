# Установка Cursor CLI (agent) через Docker

**Дата:** 2026-01-18  
**Статус:** ✅ **Docker образ успешно собран и готов к использованию!**

## ✅ Что выполнено

### 1. Docker образ собран ✅

- **Образ:** `cursor-agent:latest`
- **ID:** `967316c70968`
- **Размер:** 476MB
- **Версия agent:** `2026.01.17-d239e66`
- **База:** Ubuntu 22.04

### 2. Проверка установки ✅

```bash
# Проверка версии
docker compose -f docker/docker-compose.agent.yml run --rm agent --version
# Output: 2026.01.17-d239e66 ✅

# Проверка помощи
docker compose -f docker/docker-compose.agent.yml run --rm agent --help
# Output: Usage: agent [options] [command] [prompt...] ✅
```

### 3. Файлы созданы ✅

- ✅ `docker/Dockerfile.agent` - Dockerfile для сборки
- ✅ `docker/docker-compose.agent.yml` - Docker Compose конфигурация
- ✅ `docker/README.md` - Документация
- ✅ `scripts/agent.bat` - Wrapper скрипт
- ✅ `INSTALL_CURSOR_AGENT_DOCKER.md` - Эта инструкция

## ⚠️ Требуется настройка: Аутентификация

Agent требует `CURSOR_API_KEY` для выполнения инструкций.

### Как получить CURSOR_API_KEY

**Способ 1: Через Cursor IDE**
1. Открой Cursor IDE
2. Settings → Account → API Keys
3. Создай новый API ключ или используй существующий

**Способ 2: Через веб-интерфейс**
1. Зайди на https://cursor.com/settings
2. API Keys → Create new key
3. Скопируй ключ

**Способ 3: Через agent login (интерактивно)**
```bash
docker compose -f docker/docker-compose.agent.yml run --rm -it agent login
```

### Как установить CURSOR_API_KEY

**Вариант 1: Через .env файл (рекомендуется)**

Добавить в `.env` файл проекта (`d:\Space\codeAgent\.env`):

```env
CURSOR_API_KEY=your_api_key_here
```

Docker Compose автоматически загрузит переменную из `.env`.

**Вариант 2: Через переменную окружения**

```bash
# Windows CMD
set CURSOR_API_KEY=your_api_key_here

# PowerShell
$env:CURSOR_API_KEY="your_api_key_here"

# Git Bash / WSL
export CURSOR_API_KEY=your_api_key_here
```

**Вариант 3: Передать при запуске**

```bash
docker compose -f docker/docker-compose.agent.yml run --rm \
  -e CURSOR_API_KEY=your_api_key_here \
  agent -p "instruction"
```

## Использование

### Базовое использование (с API ключом в .env)

```bash
# Docker Compose автоматически загрузит CURSOR_API_KEY из .env
docker compose -f docker/docker-compose.agent.yml run --rm \
  agent -p "Create file test.txt with content 'Hello'"
```

### С передачей API ключа напрямую

```bash
docker compose -f docker/docker-compose.agent.yml run --rm \
  -e CURSOR_API_KEY \
  agent -p "Create file test.txt with content 'Hello'"
```

### Для целевого проекта (D:\Space\life)

Инструкции выполняются в контексте `/workspace` (смонтирован из `D:\Space\life`):

```bash
# Выполнение в контексте проекта
docker compose -f docker/docker-compose.agent.yml run --rm \
  -e CURSOR_API_KEY \
  agent -p "Create file docs/results/test.md with report"
```

### Режимы работы

```bash
# Plan mode - проектирование подхода
docker compose -f docker/docker-compose.agent.yml run --rm \
  -e CURSOR_API_KEY \
  agent -p "design API structure" --mode=plan

# Ask mode - только чтение, без изменений
docker compose -f docker/docker-compose.agent.yml run --rm \
  -e CURSOR_API_KEY \
  agent -p "analyze code structure" --mode=ask
```

## Интеграция с Code Agent

### Следующий шаг: Обновить Code Agent

После настройки `CURSOR_API_KEY`, нужно обновить `CursorCLIInterface` для автоматического использования Docker.

**План обновления:**

1. Обновить `_find_cli_in_path()` для проверки Docker образа `cursor-agent:latest`
2. Обновить `execute()` для формирования команды Docker Compose
3. Передавать `CURSOR_API_KEY` из `.env` в контейнер

**Пример обновления:**

```python
# В src/cursor_cli_interface.py
def _find_cli_in_path(self) -> tuple[Optional[str], bool]:
    # ... стандартный поиск ...
    
    # Проверка Docker образа
    try:
        result = subprocess.run(
            ["docker", "images", "-q", "cursor-agent:latest"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip():
            return "docker-compose-agent", True
    except:
        pass
```

## Структура

```
d:\Space\codeAgent\
├── docker/
│   ├── Dockerfile.agent          # ✅ Dockerfile
│   ├── docker-compose.agent.yml  # ✅ Docker Compose конфигурация
│   └── README.md                 # Документация
├── scripts/
│   └── agent.bat                 # ✅ Wrapper скрипт
├── .env                          # ⚠️ Добавить CURSOR_API_KEY
└── INSTALL_CURSOR_AGENT_DOCKER.md # ✅ Эта инструкция
```

## Следующие шаги

### 1. Получить CURSOR_API_KEY

Через Cursor IDE или веб-интерфейс (см. выше).

### 2. Добавить в .env файл

```env
# Добавить в d:\Space\codeAgent\.env
CURSOR_API_KEY=your_api_key_here
```

### 3. Протестировать выполнение

```bash
# Тест через Docker
docker compose -f docker/docker-compose.agent.yml run --rm \
  agent -p "echo 'Test from Docker agent'"
```

### 4. Обновить Code Agent

Обновить `CursorCLIInterface` для автоматического использования Docker (см. раздел "Интеграция").

### 5. Протестировать полный цикл

Протестировать автоматическое выполнение задач на целевом проекте.

## Документация

- **Подробная инструкция:** `INSTALL_CURSOR_AGENT_DOCKER.md` (этот файл)
- **Docker README:** `docker/README.md`
- **Официальная документация Cursor CLI:** https://cursor.com/docs/cli/overview
- **Получение API ключа:** https://cursor.com/settings
