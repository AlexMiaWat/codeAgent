# Docker установка Cursor CLI (agent)

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
