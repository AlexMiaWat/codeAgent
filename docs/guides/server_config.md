# Конфигурация сервера CodeAgent

## Обзор

Этот документ описывает настройки сервера CodeAgent и их влияние на работу системы.

## Основные настройки

### Сервер (server)

#### check_interval
```yaml
server:
  check_interval: 60  # секунды между проверками задач
```

**Описание:** Интервал проверки новых задач в директории проекта.

**Значения:**
- `30-300`: Нормальные значения для активной работы
- `60`: Значение по умолчанию

#### max_iterations
```yaml
server:
  max_iterations: null  # null для бесконечного цикла
```

**Описание:** Максимальное количество итераций работы сервера.

**Значения:**
- `null`: Бесконечная работа (рекомендуется)
- `1-100`: Ограниченное количество итераций (для тестирования)

#### task_delay
```yaml
server:
  task_delay: 5  # секунды между выполнением задач
```

**Описание:** Задержка между выполнением последовательных задач.

**Значения:**
- `0-30`: Зависит от нагрузки на систему

### HTTP API

#### http_enabled
```yaml
server:
  http_enabled: true  # Включить HTTP сервер
  http_port: 3456     # Порт для HTTP сервера
```

**Описание:** Настройки HTTP сервера для мониторинга.

**Эндпоинты:**
- `GET /` - Информация о сервере
- `GET /status` - Детальный статус задач
- `GET /health` - Health check

### Автоперезапуск

#### auto_reload
```yaml
server:
  auto_reload: true              # Включить автоперезапуск
  reload_on_py_changes: true     # Перезапуск при изменении .py файлов
  max_restarts: 3                # Максимальное количество перезапусков
```

**Описание:** Система автоматического перезапуска при изменении кода.

### Автоматическая генерация TODO

#### auto_todo_generation
```yaml
server:
  auto_todo_generation:
    enabled: true                     # Включить автоматическую генерацию
    max_generations_per_session: 5    # Максимум генераций за сессию
    output_dir: "todo"                # Директория для сохранения
    session_tracker_file: "data/.codeagent_sessions.json"
```

**Описание:** Настройки автоматического создания новых задач при пустом списке.

## Система чекпоинтов

### checkpoint
```yaml
server:
  checkpoint:
    enabled: true                     # Включить систему checkpoint
    checkpoint_file: "data/.codeagent_checkpoint.json"
    max_task_attempts: 3              # Максимум попыток выполнения задачи
    keep_completed_tasks: 100         # Хранить завершенных задач
```

**Описание:** Система восстановления после сбоев.

## Логирование

### logging
```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/code_agent.log
  console: true
  color: true
  cursor_interactions: true
  screenshot_on_error: true
```

**Описание:** Настройки логирования операций сервера.

## Проект

### project
```yaml
project:
  base_dir: ${PROJECT_DIR}          # Директория целевого проекта
  docs_dir: docs                    # Директория документации
  status_file: codeAgentProjectStatus.md
  todo_format: md                   # txt, yaml, md
```

**Описание:** Пути и настройки для работы с проектом.

## Агент

### agent
```yaml
agent:
  role: "Project Executor Agent"
  goal: "Execute todo items for the project"
  backstory: |
    You are an automated code agent working on software projects.
    You read project documentation, understand requirements, and execute tasks
    from the todo list systematically.
  allow_code_execution: true
  verbose: true
```

**Описание:** Базовые настройки агента CrewAI.

## Интеграция с Cursor

### cursor
```yaml
cursor:
  interface_type: "cli"        # cli, file, api, screenshot
  cli:
    cli_path: "docker-compose-agent"
    timeout: 1000
    model: "auto"              # auto, grok, конкретная модель
    fallback_models: ["grok"]
```

**Описание:** Настройки взаимодействия с Cursor IDE.

---

*Полная конфигурация см. в `config/config.yaml`*
