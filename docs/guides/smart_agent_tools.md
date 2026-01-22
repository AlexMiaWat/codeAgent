# Инструменты Smart Agent

## Обзор

Smart Agent использует специализированные инструменты для эффективного выполнения задач:

- **LearningTool**: Обучение на предыдущих задачах и накопление опыта
- **ContextAnalyzerTool**: Анализ структуры проекта и поиск релевантной информации
- **CodeInterpreterTool**: Безопасное выполнение кода в Docker контейнерах (опционально)

## LearningTool

### Назначение

LearningTool позволяет агенту учиться на предыдущих выполнениях задач, накапливая опыт и предоставляя рекомендации для будущих задач.

### Основные возможности

#### Накопление опыта

```python
from src.tools.learning_tool import LearningTool

# Создание инструмента с настройками
tool = LearningTool(
    experience_dir="smart_experience",
    max_experience_tasks=1000
)

# Сохранение выполненной задачи
task_data = {
    "task_id": "task_123",
    "description": "Создать функцию валидации email",
    "success": True,
    "execution_time": 45.2,
    "timestamp": "2026-01-22T12:00:00",
    "patterns": ["validation", "email", "function"],
    "context": {
        "project_files": ["src/validators.py", "tests/test_validators.py"],
        "dependencies": ["email-validator"],
        "technologies": ["python", "pytest"]
    },
    "result": {
        "files_created": ["src/validators.py"],
        "files_modified": [],
        "errors": []
    }
}

tool.save_task_experience(task_data)
```

#### Поиск похожих задач

```python
# Поиск задач по описанию
similar_tasks = tool.find_similar_tasks(
    description="Создать валидатор для email адресов",
    limit=5
)

# Получение рекомендаций
recommendations = tool.get_recommendations(
    current_task="validation",
    project_context={"language": "python", "framework": "none"}
)
```

#### Статистика и аналитика

```python
# Получение общей статистики
stats = tool.get_statistics()

# Структура ответа:
{
    "total_tasks": 150,
    "success_rate": 0.87,
    "average_time": 42.5,
    "top_patterns": ["validation", "api", "database"],
    "recent_tasks": [...]
}
```

### Конфигурация

#### Параметры инициализации

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `experience_dir` | str/Path | "smart_experience" | Директория для хранения опыта |
| `max_experience_tasks` | int | 1000 | Максимальное количество задач в памяти |

#### Формат хранения данных

Данные хранятся в JSON файле `experience.json`:

```json
{
  "version": "1.0",
  "last_updated": "2026-01-22T12:00:00",
  "tasks": [
    {
      "id": "task_123",
      "description": "Создать функцию валидации email",
      "success": true,
      "execution_time": 45.2,
      "timestamp": "2026-01-22T12:00:00",
      "patterns": ["validation", "email"],
      "context": {...},
      "result": {...}
    }
  ],
  "patterns": {
    "validation": {
      "count": 15,
      "success_rate": 0.93,
      "avg_time": 38.5,
      "related_tasks": ["task_123", "task_456"]
    }
  }
}
```

## ContextAnalyzerTool

### Назначение

ContextAnalyzerTool анализирует структуру проекта, находит релевантные файлы и предоставляет контекстную информацию для выполнения задач.

### Основные возможности

#### Анализ структуры проекта

```python
from src.tools.context_analyzer_tool import ContextAnalyzerTool

# Создание инструмента
tool = ContextAnalyzerTool(
    project_dir="/path/to/project",
    docs_dir="/path/to/project/docs",
    max_file_size=1000000  # 1MB
)

# Анализ структуры проекта
structure = tool.analyze_project_structure()

# Структура ответа:
{
    "project_root": "/path/to/project",
    "directories": ["src", "tests", "docs", "config"],
    "file_types": {
        ".py": 25,
        ".md": 10,
        ".yaml": 5
    },
    "main_languages": ["python"],
    "frameworks_detected": ["pytest", "crewai"],
    "config_files": ["pyproject.toml", "config/config.yaml"]
}
```

#### Поиск зависимостей файлов

```python
# Поиск файлов, связанных с конкретным файлом
dependencies = tool.find_file_dependencies("src/main.py")

# Структура ответа:
{
    "file": "src/main.py",
    "imports": ["src.utils", "src.config"],
    "imported_by": ["tests/test_main.py"],
    "related_files": ["src/utils.py", "src/config.py", "README.md"]
}
```

#### Получение контекста задачи

```python
# Получение контекста для задачи
context = tool.get_task_context(
    task_description="Добавить функцию валидации email в utils.py",
    max_files=5
)

# Структура ответа:
{
    "relevant_files": [
        {
            "path": "src/utils.py",
            "relevance_score": 0.95,
            "reason": "Основной файл утилит",
            "content_preview": "..."
        },
        {
            "path": "tests/test_utils.py",
            "relevance_score": 0.87,
            "reason": "Тесты для utils.py",
            "content_preview": "..."
        }
    ],
    "project_patterns": ["validation", "utilities"],
    "similar_tasks": [...]
}
```

### Unicode поддержка (новая возможность 2026-01-22)

```python
# Нормализация текста для улучшения поиска
from src.tools.context_analyzer_tool import normalize_unicode_text

# Обработка различных языков и кодировок
text = "Créer une fonction de validation d'email"
normalized = normalize_unicode_text(text)
# Результат: "creer une fonction de validation d'email"

# Case-insensitive поиск
search_results = tool.find_relevant_files(
    task_description="Создать валидатор email",  # На русском
    use_unicode_normalization=True
)
```

### Анализ компонентов

```python
# Детальный анализ конкретного компонента
component_analysis = tool.analyze_component("src/validators.py")

# Структура ответа:
{
    "file": "src/validators.py",
    "language": "python",
    "functions": [
        {
            "name": "validate_email",
            "signature": "def validate_email(email: str) -> bool:",
            "docstring": "Validate email address format",
            "complexity": "low"
        }
    ],
    "classes": [],
    "imports": ["re", "typing"],
    "dependencies": ["email-validator"],
    "test_coverage": "85%"
}
```

### Конфигурация

#### Параметры инициализации

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `project_dir` | str/Path | "." | Корневая директория проекта |
| `docs_dir` | str/Path | "docs" | Директория с документацией |
| `max_file_size` | int | 1000000 | Максимальный размер файла для анализа (байты) |
| `supported_extensions` | list | [".py", ".md", ".txt", ".yaml", ".yml", ".json"] | Поддерживаемые расширения файлов |

#### Поддерживаемые языки и форматы

- **Python**: Анализ функций, классов, импортов
- **Markdown**: Поиск по заголовкам и содержимому
- **YAML/JSON**: Парсинг конфигурационных файлов
- **Plain text**: Полнотекстовый поиск

## CodeInterpreterTool (опционально)

### Назначение

CodeInterpreterTool позволяет безопасно выполнять код в изолированных Docker контейнерах.

### Требования

- Docker установлен и запущен
- Доступ к Docker daemon
- Образ `cursor-agent:latest` (создается автоматически)

### Использование

```python
from crewai_tools import CodeInterpreterTool

# Создание инструмента (только если Docker доступен)
tool = CodeInterpreterTool()

# Выполнение кода
result = tool._run(
    code="""
def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Тест функции
print(validate_email('test@example.com'))
print(validate_email('invalid-email'))
""",
    libraries_used=["re"]
)
```

### Безопасность

- Код выполняется в изолированных контейнерах
- Нет доступа к файловой системе хоста
- Ограниченные системные ресурсы
- Автоматическая очистка после выполнения

## Интеграция в Smart Agent

### Автоматическая настройка инструментов

Smart Agent автоматически настраивает доступные инструменты:

```python
# В create_smart_agent()
tools = []

# Всегда доступные инструменты
tools.append(LearningTool(experience_dir=experience_dir))
tools.append(ContextAnalyzerTool(project_dir=project_dir))

# Опционально: CodeInterpreterTool (только с Docker)
if docker_available:
    try:
        tools.append(CodeInterpreterTool())
        logger.info("CodeInterpreterTool added successfully")
    except Exception as e:
        logger.warning(f"CodeInterpreterTool failed: {e}")
```

### Оптимизация производительности

| Инструмент | Время выполнения | Зависимости | Кэширование |
|------------|------------------|-------------|-------------|
| LearningTool | < 50ms | Файловая система | Да (JSON) |
| ContextAnalyzerTool | 100-500ms | Файловая система | Да (анализ структуры) |
| CodeInterpreterTool | 1-10s | Docker | Нет (свежий контейнер) |

## Тестирование инструментов

### LearningTool тесты

```bash
# Тесты инициализации и основных функций
pytest test/test_learning_tool_static.py -v

# Интеграционные тесты
pytest test/test_learning_tool_integration.py -v
```

### ContextAnalyzerTool тесты

```bash
# Тесты инициализации и основных функций
pytest test/test_context_analyzer_static.py -v

# Интеграционные тесты
pytest test/test_context_analyzer_integration.py -v
```

### Совместное тестирование

```bash
# Тесты взаимодействия инструментов в Smart Agent
pytest test/test_tools_integration.py -v
```

## Troubleshooting

### LearningTool проблемы

**Проблема:** Директория опыта не создается
```
Решение: Проверьте права доступа к директории experience_dir
```

**Проблема:** Коррупция файла experience.json
```
Решение: Удалите файл experience.json, он будет создан заново
```

### ContextAnalyzerTool проблемы

**Проблема:** UnicodeDecodeError при чтении файлов
```
Решение: Добавлена автоматическая обработка кодировок UTF-8/UTF-16
```

**Проблема:** Слишком большой файл для анализа
```
Решение: Увеличьте max_file_size или исключите большие файлы
```

**Проблема:** Неправильный поиск по не-ASCII тексту
```
Решение: Используйте normalize_unicode_text() для нормализации
```

### CodeInterpreterTool проблемы

**Проблема:** Docker недоступен
```
Решение: Smart Agent автоматически переключается в fallback режим
```

**Проблема:** Контейнер не запускается
```
Решение: Проверьте логи Docker: docker logs cursor-agent-life
```

## Будущие улучшения

### Планируемые возможности

1. **Машинное обучение**: Автоматическое обнаружение паттернов в коде
2. **Кэширование результатов**: Ускорение повторяющихся операций
3. **Параллельная обработка**: Одновременный анализ нескольких файлов
4. **Интеграция с LSP**: Использование Language Server Protocol
5. **Семантический поиск**: Понимание смысла кода, а не только текста