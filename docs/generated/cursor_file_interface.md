# Module: `cursor_file_interface`

## Class: `CursorFileInterface`

```python
Файловый интерфейс взаимодействия с Cursor через файловую систему

Это fallback механизм, когда Cursor CLI недоступен.
```

### Method: `CursorFileInterface.__init__`

```python
Инициализация файлового интерфейса

Args:
    project_dir: Директория проекта
    commands_dir: Директория для файлов с инструкциями
    results_dir: Директория для файлов с результатами
```

### Method: `CursorFileInterface.write_instruction`

```python
Записать инструкцию в файл

Args:
    instruction: Текст инструкции
    task_id: Идентификатор задачи
    metadata: Дополнительные метаданные (необязательно)
    new_chat: Если True, добавлять маркер для создания нового чата

Returns:
    Path к созданному файлу
```

### Method: `CursorFileInterface.instruction_file`

```python
Получить путь к файлу инструкции для задачи

Args:
    task_id: Идентификатор задачи

Returns:
    Path к файлу инструкции
```

### Method: `CursorFileInterface.result_file`

```python
Получить путь к файлу результата для задачи

Args:
    task_id: Идентификатор задачи

Returns:
    Path к файлу результата
```

### Method: `CursorFileInterface.read_result`

```python
Прочитать результат выполнения из файла

Args:
    task_id: Идентификатор задачи

Returns:
    Содержимое файла результата или None если файл не существует
```

### Method: `CursorFileInterface.check_result_exists`

```python
Проверить существование файла результата

Args:
    task_id: Идентификатор задачи

Returns:
    True если файл существует
```

### Method: `CursorFileInterface.wait_for_result`

```python
Ожидать появления файла результата

Args:
    task_id: Идентификатор задачи
    timeout: Таймаут ожидания (секунды)
    check_interval: Интервал проверки файла (секунды)
    control_phrase: Контрольная фраза, которая должна быть в файле

Returns:
    Словарь с результатом ожидания
```

### Method: `CursorFileInterface.check_control_phrase`

```python
Проверить наличие контрольной фразы в содержимом

Args:
    content: Содержимое файла
    control_phrase: Контрольная фраза для поиска

Returns:
    True если фраза найдена
```

### Method: `CursorFileInterface.cleanup_old_files`

```python
Удалить старые файлы команд и результатов

Args:
    older_than_days: Удалить файлы старше указанного количества дней
```
