# Docker установка Cursor CLI (agent)

## Сводка: Установка agent через Docker

**Дата:** 2026-01-18
**Статус:** ✅ **Успешно установлено!**

### ✅ Что сделано

#### 1. Docker образ собран

- **Образ:** `cursor-agent:latest`
- **Размер:** 476MB
- **Версия agent:** `2026.01.17-d239e66`
- **База:** Ubuntu 22.04

#### 2. Файлы созданы

- ✅ `docker/Dockerfile.agent` - Dockerfile для сборки
- ✅ `docker/docker-compose.agent.yml` - Docker Compose конфигурация
- ✅ `docker/README.md` - Документация
- ✅ `scripts/agent.bat` - Wrapper скрипт (опционально)
- ✅ `INSTALL_CURSOR_AGENT_DOCKER.md` - Подробная инструкция

#### 3. Проверка установки

```bash
# Проверка версии
docker compose -f docker/docker-compose.agent.yml run --rm agent --version
# Output: 2026.01.17-d239e66 ✅

# Проверка помощи
docker compose -f docker/docker-compose.agent.yml run --rm agent --help
# Output: Usage: agent [options] [command] [prompt...] ✅
```

### ⚠️ Требуется настройка

#### Аутентификация

Agent требует `CURSOR_API_KEY` для выполнения инструкций:

```bash
# Установить API ключ
export CURSOR_API_KEY=your_api_key_here  # Linux/WSL
set CURSOR_API_KEY=your_api_key_here     # Windows CMD
$env:CURSOR_API_KEY="your_cursor_api_key_here"  # PowerShell

# Или добавить в .env файл проекта
echo CURSOR_API_KEY=your_api_key_here >> .env
```

**Получение API ключа:**
- Через Cursor IDE: Settings → Account → API Keys
- Через веб: https://cursor.com/settings → API Keys

### Использование

#### Базовое выполнение

```bash
# С переменной окружения
docker compose -f docker/docker-compose.agent.yml run --rm \
  -e CURSOR_API_KEY \
  agent -p "Create file test.txt with content 'Hello'"

# С .env файлом (Docker Compose загрузит автоматически)
docker compose -f docker/docker-compose.agent.yml run --rm \
  agent -p "instruction"
```

#### Для целевого проекта (D:\Space\life)

```bash
# Выполнение в контексте проекта
docker compose -f docker/docker-compose.agent.yml run --rm \
  -e CURSOR_API_KEY \
  agent -p "Create file docs/results/report.md"
```

### Интеграция с Code Agent

После настройки `CURSOR_API_KEY`, можно обновить `CursorCLIInterface` для автоматического использования Docker.

**План интеграции:**
1. Обновить `_find_cli_in_path()` для проверки Docker образа
2. Обновить `execute()` для поддержки Docker команд
3. Передавать `CURSOR_API_KEY` из `.env` в контейнер

### Следующие шаги

1. **Получить CURSOR_API_KEY** (через Cursor IDE или веб-интерфейс)
2. **Добавить в .env** файл проекта
3. **Протестировать выполнение** через Docker
4. **Обновить Code Agent** для автоматического использования Docker

### Документация

- **Подробная инструкция:** `INSTALL_CURSOR_AGENT_DOCKER.md`
- **Docker README:** `docker/README.md`
- **Официальная документация:** https://cursor.com/docs/cli/overview

---

## Обзор

Этот Docker контейнер позволяет использовать официальный Cursor CLI (`agent`) на Windows через Docker, обходя ограничения установщика, который не поддерживает MINGW64 (Git Bash).

## Требования

- Docker установлен и работает
- Docker Compose (обычно входит в Docker Desktop)

## Быстрый старт

### 1. Сборка образа

```bash
cd d:\Space\codeAgent
docker-compose -f docker/docker-compose.agent.yml build
```

### 2. Проверка установки

```bash
docker-compose -f docker/docker-compose.agent.yml run --rm agent --version
```

### 3. Тест выполнения

```bash
docker-compose -f docker/docker-compose.agent.yml run --rm agent -p "echo 'Hello from agent'"
```

## Использование

### Выполнение инструкции через agent

```bash
docker-compose -f docker/docker-compose.agent.yml run --rm agent -p "Create a test file test.txt with content 'Hello World'"
```

### С указанием рабочей директории

```bash
docker-compose -f docker/docker-compose.agent.yml run --rm -w /workspace/D:\Space\life agent -p "instruction"
```

### Интерактивный режим

```bash
docker-compose -f docker/docker-compose.agent.yml run --rm agent
```

### Режимы работы

```bash
# Plan mode
docker-compose -f docker/docker-compose.agent.yml run --rm agent -p "instruction" --mode=plan

# Ask mode
docker-compose -f docker/docker-compose.agent.yml run --rm agent -p "instruction" --mode=ask
```

## Интеграция с Code Agent

После настройки Docker, Code Agent может использовать `docker-compose` для запуска `agent`.

Обновить `CursorCLIInterface` для поддержки Docker:

```python
# В config.yaml можно добавить:
cursor:
  cli:
    use_docker: true
    docker_compose_file: "docker/docker-compose.agent.yml"
```

## Преимущества Docker решения

1. ✅ **Работает на Windows** - не требует WSL или Linux
2. ✅ **Изолированное окружение** - не влияет на хост-систему
3. ✅ **Воспроизводимость** - одинаковое окружение на всех машинах
4. ✅ **Простое обновление** - пересборка образа

## Структура

```
docker/
├── Dockerfile.agent          # Dockerfile для сборки образа
├── docker-compose.agent.yml  # Docker Compose конфигурация
└── README.md                 # Этот файл
```

## Troubleshooting

### Проблема: "Cannot connect to the Docker daemon"

**Решение:** Убедитесь, что Docker Desktop запущен.

### Проблема: "Permission denied" при монтировании томов

**Решение:** На Windows используйте правильные пути. Docker Compose автоматически конвертирует пути.

### Проблема: Agent не находит файлы проекта

**Решение:** Убедитесь, что рабочая директория смонтирована правильно в `docker-compose.agent.yml`.

## Обновление

Для обновления agent в контейнере:

```bash
# Пересобрать образ
docker-compose -f docker/docker-compose.agent.yml build --no-cache

# Или обновить через сам agent
docker-compose -f docker/docker-compose.agent.yml run --rm agent update
```
