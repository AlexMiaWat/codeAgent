# API Reference

## Модули Code Agent

### core

#### ServerCore (`src/core/server_core.py`)

Базовый компонент цикла выполнения задач.

```python
from src.core.server_core import ServerCore, TaskExecutor, RevisionExecutor, TodoGenerator

# Создание обработчиков (протоколы)
def task_executor(todo_item, task_number, total_tasks):
    # Логика выполнения задачи
    return True

def revision_executor():
    # Логика ревизии проекта
    return True

def todo_generator():
    # Логика генерации TODO
    return True

# Инициализация ServerCore
server_core = ServerCore(
    todo_manager=todo_manager,
    checkpoint_manager=checkpoint_manager,
    status_manager=status_manager,
    server_logger=server_logger,
    task_executor=task_executor,
    revision_executor=revision_executor,
    todo_generator=todo_generator,
    config=config_dict,
    auto_todo_enabled=True,
    task_delay=5
)

# Выполнение итерации
success, tasks_completed = server_core.execute_iteration()
```

**Методы:**

- `__init__(todo_manager, checkpoint_manager, status_manager, server_logger, task_executor, revision_executor, todo_generator, config, auto_todo_enabled, task_delay)` - Инициализация
- `execute_iteration() -> tuple[bool, list]` - Выполнение полной итерации цикла
- `execute_single_task() -> bool` - Выполнение отдельной задачи
- `sync_revision_state(revision_done: bool)` - Синхронизация состояния ревизии

**Протоколы:**

- `TaskExecutor(todo_item, task_number, total_tasks) -> bool` - Выполнение задачи
- `RevisionExecutor() -> bool` - Выполнение ревизии проекта
- `TodoGenerator() -> bool` - Генерация нового TODO списка

---

#### Абстрактные базовые классы (`src/core/abstract_base.py`)

```python
from src.core.abstract_base import BaseComponent, ConfigurableComponent, MetricsEnabledComponent

class MyComponent(BaseComponent):
    """Пример реализации базового компонента"""

    def get_component_name(self) -> str:
        return "MyComponent"

    def get_component_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> bool:
        # Инициализация компонента
        return True

    def shutdown(self) -> bool:
        # Завершение работы компонента
        return True
```

**Классы:**

- `BaseComponent` - Наследует `IServerComponent`, предоставляет базовую функциональность
- `ConfigurableComponent` - Добавляет поддержку конфигурации через `IConfigurable`
- `MetricsEnabledComponent` - Добавляет поддержку сбора метрик через `IMetricsCollector`

---

#### Интерфейсы (`src/core/interfaces.py`)

```python
from src.core.interfaces import IServerComponent, IConfigurable, IMetricsCollector

class MyService(IServerComponent):
    """Пример реализации интерфейса компонента"""

    def get_component_name(self) -> str:
        return "MyService"

    def get_component_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True
```

**Интерфейсы:**

- `IServerComponent` - Базовый интерфейс всех серверных компонентов
- `IConfigurable` - Интерфейс конфигурируемых компонентов
- `IMetricsCollector` - Интерфейс сборщиков метрик производительности

---

#### ConfigurationManager (`src/core/configuration_manager.py`)

Управление конфигурацией системы.

```python
from src.core.configuration_manager import ConfigurationManager

config_manager = ConfigurationManager(config_dict)
value = config_manager.get('server.port', default=3456)
config_manager.validate_config()
```

**Методы:**

- `__init__(config: dict)` - Инициализация с конфигурацией
- `get(key: str, default: Any)` - Получение значения
- `validate_config()` - Валидация конфигурации
- `reload_config(new_config: dict)` - Перезагрузка конфигурации

---

### config_loader

#### `ConfigLoader`

Загрузчик конфигурации из YAML и переменных окружения.

```python
from src.config_loader import ConfigLoader

config = ConfigLoader("config/config.yaml")
project_dir = config.get_project_dir()
value = config.get('server.check_interval', default=60)
```

**Методы:**

- `__init__(config_path: str)` - Инициализация загрузчика
- `get(key: str, default: Any)` - Получение значения конфигурации
- `get_project_dir()` - Получение пути к директории проекта
- `get_docs_dir()` - Получение пути к директории документации
- `get_status_file()` - Получение пути к файлу статусов

---

### status_manager

#### `StatusManager`

Управление файлом статусов проекта.

```python
from src.status_manager import StatusManager
from pathlib import Path

status_file = Path("project/codeAgentProjectStatus.md")
manager = StatusManager(status_file)
manager.append_status("Задача выполнена", level=2)
manager.update_task_status("Задача 1", "Выполнено", "Детали...")
```

**Методы:**

- `__init__(status_file: Path)` - Инициализация менеджера
- `read_status()` - Чтение текущего статуса
- `write_status(content: str)` - Перезапись файла статусов
- `append_status(message: str, level: int)` - Добавление статуса
- `update_task_status(task_name: str, status: str, details: Optional[str])` - Обновление статуса задачи
- `add_separator()` - Добавление разделителя

---

### todo_manager

#### `TodoManager`

Управление todo-листом проекта.

```python
from src.todo_manager import TodoManager, TodoItem
from pathlib import Path

project_dir = Path("D:/Space/life")
manager = TodoManager(project_dir, todo_format="txt")
pending = manager.get_pending_tasks()
manager.mark_task_done("Задача 1")
```

**Методы:**

- `__init__(project_dir: Path, todo_format: str)` - Инициализация менеджера
- `get_pending_tasks()` - Получение непройденных задач
- `get_all_tasks()` - Получение всех задач
- `mark_task_done(task_text: str)` - Отметка задачи как выполненной
- `get_task_hierarchy()` - Получение иерархии задач

#### `TodoItem`

Элемент todo-листа.

```python
item = TodoItem("Текст задачи", level=0, done=False)
print(item.text)  # Текст задачи
print(item.level)  # Уровень вложенности
print(item.done)   # Выполнена ли задача
```

**Атрибуты:**

- `text: str` - Текст задачи
- `level: int` - Уровень вложенности
- `done: bool` - Выполнена ли задача
- `parent: Optional[TodoItem]` - Родительский элемент
- `children: List[TodoItem]` - Дочерние элементы

---

### agents.executor_agent

#### `create_executor_agent()`

Создание агента-исполнителя CrewAI.

```python
from src.agents.executor_agent import create_executor_agent
from pathlib import Path

project_dir = Path("D:/Space/life")
agent = create_executor_agent(
    project_dir=project_dir,
    docs_dir=project_dir / "docs",
    role="Project Executor Agent",
    goal="Execute tasks",
    allow_code_execution=True
)
```

**Параметры:**

- `project_dir: Path` - Директория проекта
- `docs_dir: Optional[Path]` - Директория документации
- `role: str` - Роль агента
- `goal: str` - Цель агента
- `backstory: Optional[str]` - История агента
- `allow_code_execution: bool` - Разрешить выполнение кода
- `verbose: bool` - Подробный вывод

**Возвращает:**

`Agent` - Настроенный агент CrewAI

---

### server

#### `CodeAgentServer`

Основной сервер Code Agent с поддержкой HTTP API и автоперезапуска.

```python
from src.server import CodeAgentServer

server = CodeAgentServer("config/config.yaml")
server.start()  # Запуск бесконечного цикла с HTTP сервером
```

**Методы:**

- `__init__(config_path: Optional[str])` - Инициализация сервера
- `start()` - Запуск сервера в бесконечном цикле с HTTP сервером и file watcher
- `run_iteration()` - Выполнение одной итерации
- `_execute_task(todo_item: TodoItem)` - Выполнение задачи через агента
- `_load_documentation()` - Загрузка документации проекта
- `_setup_http_server()` - Настройка и запуск HTTP сервера на порту 3456
- `_setup_file_watcher()` - Настройка отслеживания изменений .py файлов
- `_check_port_in_use(port: int)` - Проверка занятости порта
- `_kill_process_on_port(port: int)` - Завершение процесса на порту

**HTTP API:**

Сервер автоматически запускает Flask HTTP сервер на порту 3456 (настраивается в config):

**Endpoints:**
- `GET /health` - Проверка работоспособности сервера
- `GET /` - Общая информация о сервере и статистика
- `GET /status` - Подробный статус сервера, задач и текущей активности
- `POST /stop` - Остановить сервер после завершения текущей итерации
- `POST /restart` - Перезапустить сервер после завершения текущей итерации

**Детальная документация:** См. [api_endpoints.md](api_endpoints.md)

**Автоперезапуск:**

При изменении любых `.py` файлов в `src/` или корне проекта сервер автоматически перезапускается.

---

## Примеры использования

### Базовая настройка и запуск

```python
from src.server import CodeAgentServer

# Создание и запуск сервера
server = CodeAgentServer()
server.start()
```

### Работа со статусами

```python
from src.status_manager import StatusManager
from pathlib import Path

status_file = Path("project/codeAgentProjectStatus.md")
manager = StatusManager(status_file)

# Добавление статуса
manager.append_status("Новая итерация начата", level=2)

# Обновление задачи
manager.update_task_status(
    task_name="Инициализация проекта",
    status="Выполнено",
    details="Проект успешно инициализирован"
)
```

### Работа с todo-листом

```python
from src.todo_manager import TodoManager
from pathlib import Path

project_dir = Path("D:/Space/life")
manager = TodoManager(project_dir, todo_format="txt")

# Получение задач
pending = manager.get_pending_tasks()
print(f"Непройденных задач: {len(pending)}")

for task in pending:
    print(f"- {task.text}")

# Отметка задачи как выполненной
manager.mark_task_done("Первая задача")
```

### Создание кастомного агента

```python
from src.agents.executor_agent import create_executor_agent
from pathlib import Path

agent = create_executor_agent(
    project_dir=Path("D:/Space/life"),
    role="Custom Agent",
    goal="Custom goal",
    backstory="Custom backstory",
    allow_code_execution=True
)
```

---

## Конфигурация

### Формат config.yaml

```yaml
project:
  base_dir: ${PROJECT_DIR}
  docs_dir: docs
  status_file: codeAgentProjectStatus.md
  todo_format: txt

agent:
  role: "Project Executor Agent"
  goal: "Execute tasks"
  backstory: "..."
  allow_code_execution: true
  verbose: true

server:
  check_interval: 60
  task_delay: 5
  max_iterations: null
```

### Переменные окружения

- `PROJECT_DIR` - Директория проекта
- `OPENAI_API_KEY` - API ключ OpenAI
- `ANTHROPIC_API_KEY` - API ключ Anthropic
- `OLLAMA_API_URL` - URL для Ollama

---

## Расширение функциональности

### Добавление кастомных инструментов

```python
from crewai_tools import BaseTool

class CustomTool(BaseTool):
    name: str = "Custom Tool"
    description: str = "Description of custom tool"
    
    def _run(self, argument: str) -> str:
        # Ваша логика
        return "Result"
```

### Добавление специализированных агентов

```python
from crewai import Agent

custom_agent = Agent(
    role="Specialist",
    goal="Specialized goal",
    backstory="Specialized backstory",
    tools=[CustomTool()]
)
```

---

## Типы данных

### TodoItem

```python
class TodoItem:
    text: str
    level: int
    done: bool
    parent: Optional['TodoItem']
    children: List['TodoItem']
```

### ConfigLoader

```python
class ConfigLoader:
    config: Dict[str, Any]
    config_path: Path
```

### StatusManager

```python
class StatusManager:
    status_file: Path
```

### TodoManager

```python
class TodoManager:
    project_dir: Path
    todo_file: Optional[Path]
    items: List[TodoItem]
```

---

## Smart Agent

### create_smart_agent()

Создание интеллектуального агента с поддержкой машинного обучения и Docker.

```python
from src.agents import create_smart_agent
from pathlib import Path

# Базовое создание агента
agent = create_smart_agent(
    project_dir=Path("my_project"),
    goal="Execute complex tasks with enhanced intelligence",
    backstory="Smart agent with learning capabilities",
    allow_code_execution=True,
    use_docker=None,  # Автоопределение Docker (None), принудительно (True), отключить (False)
    verbose=True,
    use_llm_manager=True,
    llm_config_path="config/llm_settings.yaml",
    experience_dir="smart_experience"
)
```

**Параметры:**

- `project_dir: Path` - Директория проекта для анализа
- `goal: str` - Цель агента (опционально)
- `backstory: str` - История/контекст агента (опционально)
- `allow_code_execution: bool` - Разрешить выполнение кода (по умолчанию: True)
- `use_docker: Optional[bool]` - ✅ **НОВОЕ** - Использовать Docker: None=авто, True=принудительно, False=отключить
- `verbose: bool` - Подробный вывод (по умолчанию: True)
- `use_llm_manager: bool` - Использовать LLM Manager (по умолчанию: True)
- `llm_config_path: str` - Путь к конфигурации LLM (по умолчанию: "config/llm_settings.yaml")
- `experience_dir: str` - Директория для хранения опыта (по умолчанию: "smart_experience")

**Возвращает:** Настроенный CrewAI агент с инструментами LearningTool, ContextAnalyzerTool и опционально CodeInterpreterTool.

---

### Docker Utils

#### DockerChecker

Класс для проверки доступности Docker и управления контейнерами.

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

**Статические методы:**

- `is_docker_available() -> bool` - Проверяет доступность Docker daemon
- `get_docker_version() -> Optional[str]` - Возвращает версию Docker
- `check_docker_permissions() -> Tuple[bool, str]` - Проверяет права доступа к Docker
- `get_running_containers() -> List[str]` - Возвращает список имен запущенных контейнеров
- `is_container_running(container_name: str) -> bool` - Проверяет статус конкретного контейнера

#### DockerManager

Класс для управления Docker-контейнерами.

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

**Методы:**

- `__init__(image_name: str, container_name: str)` - Инициализация менеджера
- `start_container(workspace_path: Optional[str]) -> Tuple[bool, str]` - Запуск контейнера с монтированием workspace
- `stop_container() -> Tuple[bool, str]` - Остановка контейнера
- `execute_command(command: str, working_dir: str) -> Tuple[bool, str, str]` - Выполнение команды в контейнере

---

### LearningTool

Инструмент машинного обучения для анализа предыдущих задач и обучения на опыте.

```python
from src.tools import LearningTool

tool = LearningTool(experience_dir="smart_experience")

# Получение статистики выполнения
stats = tool._run("get_statistics")

# Анализ предыдущих задач
analysis = tool._run("analyze_previous_tasks")

# Поиск похожих задач
similar = tool._run("find_similar_task", task_description="Create API endpoint")
```

**Методы:**

- `_run(action: str, **kwargs)` - Выполнение действия инструмента
- Поддерживаемые действия: `get_statistics`, `analyze_previous_tasks`, `find_similar_task`, `store_experience`

---

### ContextAnalyzerTool

Инструмент для анализа структуры проекта и зависимостей.

```python
from src.tools import ContextAnalyzerTool

tool = ContextAnalyzerTool(project_dir=Path("my_project"))

# Анализ структуры проекта
structure = tool._run("analyze_project")

# Поиск зависимостей файла
deps = tool._run("find_dependencies", file_path="src/main.py")

# Анализ связей между файлами
links = tool._run("analyze_file_links")
```

**Методы:**

- `_run(action: str, **kwargs)` - Выполнение действия инструмента
- Поддерживаемые действия: `analyze_project`, `find_dependencies`, `analyze_file_links`
