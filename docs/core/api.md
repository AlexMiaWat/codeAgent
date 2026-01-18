# API Reference

## Модули Code Agent

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

Основной сервер Code Agent.

```python
from src.server import CodeAgentServer

server = CodeAgentServer("config/config.yaml")
server.start()  # Запуск бесконечного цикла
```

**Методы:**

- `__init__(config_path: Optional[str])` - Инициализация сервера
- `start()` - Запуск сервера в бесконечном цикле
- `run_iteration()` - Выполнение одной итерации
- `_execute_task(todo_item: TodoItem)` - Выполнение задачи через агента
- `_load_documentation()` - Загрузка документации проекта

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
