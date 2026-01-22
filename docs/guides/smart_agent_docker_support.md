# Поддержка Docker в Smart Agent

## Обзор

Smart Agent поддерживает опциональное использование Docker для безопасного выполнения кода. Если Docker недоступен, агент автоматически переключается в fallback режим без выполнения кода.

## Режимы работы

### 1. Полный режим (с Docker)

**Требования:**
- Docker установлен и запущен
- Пользователь имеет права на выполнение Docker команд
- Установлен `crewai_tools` с `CodeInterpreterTool`

**Возможности:**
- Безопасное выполнение кода в изолированных контейнерах
- CodeInterpreterTool для анализа и выполнения кода
- Полная функциональность code execution

### 2. Fallback режим (без Docker)

**Когда активируется:**
- Docker не установлен
- Docker daemon не запущен
- Нет прав доступа к Docker
- Ошибки импорта CodeInterpreterTool
- Явное отключение через параметр `use_docker=False`

**Возможности:**
- Анализ кода и документации
- Обучение на предыдущих задачах
- Рекомендации на основе опыта
- Анализ структуры проекта
- Поиск зависимостей и связей

## Конфигурация

### Параметры create_smart_agent()

```python
from src.agents import create_smart_agent
from pathlib import Path

# Автоопределение (рекомендуется)
agent = create_smart_agent(
    project_dir=Path("my_project"),
    use_docker=None  # Автоопределение доступности Docker
)

# Принудительное включение Docker
agent = create_smart_agent(
    project_dir=Path("my_project"),
    use_docker=True  # Требует Docker, иначе fallback
)

# Принудительное отключение Docker
agent = create_smart_agent(
    project_dir=Path("my_project"),
    use_docker=False  # Всегда fallback режим
)
```

### Переменные окружения

- `DOCKER_AVAILABLE` - принудительно установить статус Docker (true/false)

## Docker Utils

Smart Agent включает утилиты для работы с Docker:

### DockerChecker

```python
from src.tools import DockerChecker

# Проверка доступности Docker
available = DockerChecker.is_docker_available()

# Получение версии Docker
version = DockerChecker.get_docker_version()

# Проверка прав доступа
perms_ok, perms_msg = DockerChecker.check_docker_permissions()

# Получение списка запущенных контейнеров
containers = DockerChecker.get_running_containers()

# Проверка конкретного контейнера
is_running = DockerChecker.is_container_running("cursor-agent-life")
```

### DockerManager

```python
from src.tools import DockerManager

# Создание менеджера
manager = DockerManager(
    image_name="cursor-agent:latest",
    container_name="cursor-agent-life"
)

# Запуск контейнера
success, message = manager.start_container(workspace_path="/path/to/project")

# Остановка контейнера
success, message = manager.stop_container()

# Выполнение команды в контейнере
success, stdout, stderr = manager.execute_command("python --version")
```

## Обработка ошибок

### Логирование

Smart Agent ведет подробное логирование процесса определения Docker:

```
INFO: Docker auto-detection: available
INFO: CodeInterpreterTool added successfully (Docker available)
```

```
INFO: Docker auto-detection: not available
INFO: CodeInterpreterTool skipped (Docker not available - fallback mode)
```

```
WARNING: Docker forced but not available - falling back to no code execution
ERROR: Docker check failed: [error message]
```

### Fallback поведение

При недоступности Docker:

1. **CodeInterpreterTool не добавляется** в список инструментов
2. **allow_code_execution устанавливается в False** для агента
3. **Backstory обновляется** для отражения ограничений
4. **Агент продолжает работу** с LearningTool и ContextAnalyzerTool

## Тестирование

### Тесты без Docker

```bash
# Запуск тестов в fallback режиме
pytest test/test_smart_agent_integration.py::TestSmartAgentIntegration::test_smart_agent_docker_fallback_mode -v

# Тест автоопределения
pytest test/test_smart_agent_integration.py::TestSmartAgentIntegration::test_smart_agent_docker_auto_detection_fallback -v

# Тест принудительного режима
pytest test/test_smart_agent_integration.py::TestSmartAgentIntegration::test_smart_agent_docker_forced_fallback_warning -v
```

### Моки для тестирования

```python
from unittest.mock import patch

# Мокаем недоступность Docker
with patch('src.tools.docker_utils.DockerChecker.is_docker_available', return_value=False):
    agent = create_smart_agent(project_dir=Path("."), use_docker=None)
    # Агент будет в fallback режиме
```

## Советы по использованию

### Рекомендации

1. **Используйте автоопределение** (`use_docker=None`) для автоматического выбора режима
2. **В CI/CD средах** явно отключайте Docker если он не нужен
3. **Для разработки** с Docker получаете максимальную функциональность
4. **Для анализа кода** fallback режим полностью функционален

### Производительность

- **С Docker**: +CodeInterpreterTool, но требуется время на запуск контейнеров
- **Без Docker**: Быстрее запуск, меньше зависимостей, но без code execution

### Безопасность

- **С Docker**: Код выполняется в изолированных контейнерах
- **Без Docker**: Нет рисков выполнения кода, только анализ

## Troubleshooting

### Docker не обнаруживается

1. Проверьте установку: `docker --version`
2. Проверьте запуск daemon: `docker info`
3. Проверьте права: `docker ps`

### CodeInterpreterTool не работает

1. Установите crewai_tools: `pip install crewai[tools]`
2. Проверьте Docker доступность
3. Проверьте логи агента

### Fallback режим не активируется

1. Проверьте логи на ошибки Docker проверки
2. Явно установите `use_docker=False` для тестирования
3. Проверьте, что LearningTool и ContextAnalyzerTool работают

## Архитектура

```
SmartAgent Creation Flow:
1. Проверка Docker доступности
2. Определение режима (full/fallback)
3. Добавление инструментов:
   - Full: CodeInterpreterTool + LearningTool + ContextAnalyzerTool
   - Fallback: LearningTool + ContextAnalyzerTool
4. Настройка backstory в зависимости от режима
5. Создание CrewAI агента
```

## Расширение

Для добавления новых инструментов с поддержкой Docker:

```python
# В create_smart_agent()
if docker_available:
    try:
        tools.append(DockerDependentTool())
    except Exception as e:
        logger.warning(f"Docker tool failed: {e}")
else:
    tools.append(FallbackTool())
```