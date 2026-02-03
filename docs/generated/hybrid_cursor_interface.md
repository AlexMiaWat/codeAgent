# Module: `hybrid_cursor_interface`

## Class: `TaskComplexity`

```python
Сложность задачи
```

## Class: `HybridExecutionResult`

```python
Результат выполнения через гибридный интерфейс
```

## Class: `HybridCursorInterface`

```python
Гибридный интерфейс для работы с Cursor

Автоматически выбирает оптимальный метод выполнения:
- CLI для простых задач (быстро, но может не выполниться)
- Файловый интерфейс для сложных задач (надежно)
- Fallback на файловый при неудаче CLI
```

### Method: `HybridCursorInterface.__init__`

```python
Инициализация гибридного интерфейса

Args:
    cli_interface: Интерфейс CLI (если None - создается автоматически)
    file_interface: Файловый интерфейс (если None - создается автоматически)
    project_dir: Директория проекта
    prefer_cli: Предпочитать CLI даже для сложных задач (с fallback)
    verify_side_effects: Проверять side-effects после выполнения
```

### Method: `HybridCursorInterface.execute_task`

```python
Выполнение задачи с автоматическим выбором метода

Args:
    instruction: Инструкция для выполнения
    task_id: ID задачи (генерируется автоматически если None)
    complexity: Сложность задачи (AUTO для автоопределения)
    expected_files: Список ожидаемых файлов для проверки side-effects
    control_phrase: Контрольная фраза для файлового интерфейса
    timeout: Таймаут выполнения (секунды)

Returns:
    HybridExecutionResult с результатом выполнения
```

### Method: `HybridCursorInterface._determine_complexity`

```python
Автоматическое определение сложности задачи

Args:
    instruction: Инструкция для анализа

Returns:
    TaskComplexity.SIMPLE или TaskComplexity.COMPLEX
```

### Method: `HybridCursorInterface._execute_via_cli`

```python
Выполнение через CLI с опциональным fallback

Args:
    instruction: Инструкция для выполнения
    task_id: ID задачи
    expected_files: Список ожидаемых файлов
    with_fallback: Использовать fallback на файловый интерфейс при неудаче

Returns:
    HybridExecutionResult
```

### Method: `HybridCursorInterface._execute_via_file`

```python
Выполнение через файловый интерфейс

Args:
    instruction: Инструкция для выполнения
    task_id: ID задачи
    control_phrase: Контрольная фраза
    timeout: Таймаут ожидания результата

Returns:
    HybridExecutionResult
```

### Method: `HybridCursorInterface._execute_via_file_fallback`

```python
Fallback на файловый интерфейс после неудачи CLI

Args:
    instruction: Инструкция для выполнения
    task_id: ID задачи
    cli_result: Результат CLI (для логирования)

Returns:
    HybridExecutionResult
```

### Method: `HybridCursorInterface._verify_side_effects`

```python
Проверка side-effects (наличие ожидаемых файлов)

Args:
    expected_files: Список ожидаемых файлов (относительно project_dir)

Returns:
    True если все файлы существуют, False иначе
```

### Method: `HybridCursorInterface.is_available`

```python
Проверка доступности хотя бы одного интерфейса

Returns:
    True если доступен CLI или файловый интерфейс
```

## Function: `create_hybrid_cursor_interface`

```python
Фабрика для создания гибридного интерфейса

Args:
    cli_path: Путь к CLI (None для автопоиска)
    project_dir: Директория проекта
    prefer_cli: Предпочитать CLI даже для сложных задач
    verify_side_effects: Проверять side-effects после выполнения

Returns:
    HybridCursorInterface
```
