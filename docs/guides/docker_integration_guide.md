# Интеграция Code Agent с Cursor CLI через Docker

**Дата:** 2026-01-18  
**Статус:** ✅ Docker образ собран и готов к использованию

## Что реализовано

### 1. Dockerfile для agent

**Файл:** `docker/Dockerfile.agent`

Создает Ubuntu-образ с установленным `agent` через официальный скрипт.

### 2. Docker Compose конфигурация

**Файл:** `docker/docker-compose.agent.yml`

Настроена для:
- Сборки образа `cursor-agent:latest`
- Монтирования целевой директории проекта (`D:\Space\your-project`)
- Запуска `agent` в контейнере

### 3. Wrapper скрипт (опционально)

**Файл:** `scripts/agent.bat`

Позволяет использовать `agent.bat` вместо длинной команды Docker Compose.

## Быстрый старт

### 1. Проверка сборки

```bash
cd d:\Space\codeAgent
docker compose -f docker/docker-compose.agent.yml build
```

**Статус:** ✅ Образ собран успешно

### 2. Проверка версии

```bash
docker compose -f docker/docker-compose.agent.yml run --rm agent --version
```

### 3. Тест выполнения

```bash
docker compose -f docker/docker-compose.agent.yml run --rm agent -p "echo 'Test from Docker'"
```

## Использование

### Базовое выполнение

```bash
# Выполнение инструкции
docker compose -f docker/docker-compose.agent.yml run --rm agent -p "Create file test.txt with content 'Hello'"
```

### Для целевого проекта (D:\Space\your-project)

Инструкции выполняются в контексте `/workspace` (который смонтирован из `D:\Space\your-project`):

```bash
docker compose -f docker/docker-compose.agent.yml run --rm agent -p "Create file docs/results/test.md with report"
```

### Через wrapper скрипт (если добавлен в PATH)

```bash
# Добавить scripts в PATH или использовать полный путь
d:\Space\codeAgent\scripts\agent.bat -p "instruction"
```

## Интеграция с Code Agent

### Вариант 1: Автоматическое обнаружение Docker

Обновить `CursorCLIInterface` для проверки Docker:

```python
def _find_cli_in_path(self) -> tuple[Optional[str], bool]:
    # ... стандартный поиск ...
    
    # Проверка Docker (если agent не найден напрямую)
    try:
        # Проверяем доступность docker compose
        result = subprocess.run(
            ["docker", "compose", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Проверяем наличие образа cursor-agent:latest
            result = subprocess.run(
                ["docker", "images", "-q", "cursor-agent:latest"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip():
                # Возвращаем специальный маркер для Docker
                return "docker-compose-agent", True
    except:
        pass
```

### Вариант 2: Использование через docker-compose напрямую

Обновить `execute()` для поддержки Docker:

```python
def execute(self, prompt, working_dir=None, timeout=None, ...):
    # ...
    if self.cli_command == "docker-compose-agent":
        # Формируем команду для Docker
        compose_file = Path(__file__).parent.parent / "docker" / "docker-compose.agent.yml"
        cmd = [
            "docker", "compose",
            "-f", str(compose_file),
            "run", "--rm",
            "agent", "-p", prompt
        ]
        # ... остальная логика
```

## Структура

```
d:\Space\codeAgent\
├── docker/
│   ├── Dockerfile.agent          # Dockerfile для сборки
│   ├── docker-compose.agent.yml  # Docker Compose конфигурация
│   └── README.md                 # Документация
├── scripts/
│   └── agent.bat                 # Wrapper скрипт (опционально)
└── docs/
    └── docker_integration_guide.md  # Этот файл
```

## Преимущества Docker решения

1. ✅ **Работает на Windows** - не требует WSL или Linux
2. ✅ **Изолированное окружение** - не влияет на хост-систему
3. ✅ **Воспроизводимость** - одинаковое окружение везде
4. ✅ **Простое обновление** - пересборка образа
5. ✅ **Готово к использованию** - образ уже собран

## Следующие шаги

1. **Протестировать выполнение через Docker:**
   ```bash
   docker compose -f docker/docker-compose.agent.yml run --rm agent -p "Create test file"
   ```

2. **Обновить Code Agent** для автоматического использования Docker

3. **Протестировать полный цикл** на целевом проекте

## Документация

- **Подробная инструкция:** `INSTALL_CURSOR_AGENT_DOCKER.md`
- **Docker README:** `docker/README.md`
- **Официальная документация Cursor CLI:** https://cursor.com/docs/cli/overview
