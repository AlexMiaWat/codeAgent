# Module: `config_loader`

## Class: `ConfigLoader`

```python
Загрузчик конфигурации из YAML и переменных окружения
```

### Method: `ConfigLoader.load_config`

```python
Статический метод загрузки конфигурации

Args:
    config_path: Путь к файлу конфигурации

Returns:
    Словарь с конфигурацией
```

### Method: `ConfigLoader.__init__`

```python
Инициализация загрузчика конфигурации

Args:
    config_path: Путь к файлу конфигурации
    allowed_base_dirs: Список разрешенных базовых директорий для валидации путей
                      Если None, используется директория codeAgent
```

### Method: `ConfigLoader._load_config`

```python
Загрузка конфигурации из YAML файла
```

### Method: `ConfigLoader._substitute_env_vars`

```python
Рекурсивная подстановка переменных окружения в конфигурации

Формат: ${VAR_NAME} или ${VAR_NAME:default_value}
```

### Method: `ConfigLoader.get`

```python
Получение значения конфигурации по ключу (с поддержкой вложенных ключей)

Args:
    key: Ключ конфигурации (может быть "section.key" для вложенных значений)
    default: Значение по умолчанию

Returns:
    Значение конфигурации или default
```

### Method: `ConfigLoader._validate_path`

```python
Валидация и нормализация пути

Проверяет:
- Отсутствие path traversal атак (..)
- Что путь находится в разрешенных директориях (для абсолютных путей)
- Нормализует путь

Args:
    path: Путь для валидации
    path_name: Имя пути для сообщений об ошибках

Returns:
    Валидированный и нормализованный путь

Raises:
    ValueError: Если путь невалиден или находится вне разрешенных директорий
```

### Method: `ConfigLoader.get_project_dir`

```python
Получение базовой директории проекта

Returns:
    Path к директории проекта
```

### Method: `ConfigLoader.get_docs_dir`

```python
Получение пути к директории документации

Returns:
    Path к директории docs

Raises:
    ValueError: Если путь невалиден
```

### Method: `ConfigLoader.get_status_file`

```python
Получение пути к файлу статусов проекта

Returns:
    Path к файлу codeAgentProjectStatus.md

Raises:
    ValueError: Если путь невалиден
```

### Method: `ConfigLoader.get_smart_agent_config`

```python
Получение конфигурации Smart Agent

Returns:
    Словарь с настройками Smart Agent
```

### Method: `ConfigLoader.validate_smart_agent_config`

```python
Валидация конфигурации Smart Agent

Returns:
    List[str]: Список ошибок валидации. Пустой список означает успешную валидацию.
```
