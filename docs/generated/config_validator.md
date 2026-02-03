# Module: `config_validator`

## Class: `ConfigValidationError`

```python
Исключение для ошибок валидации конфигурации
```

### Method: `ConfigValidationError.__init__`

```python
Инициализация ошибки валидации

Args:
    message: Основное сообщение об ошибке
    path: Путь к полю в конфигурации (например, "project.base_dir")
    errors: Список дополнительных ошибок
```

### Method: `ConfigValidationError.__str__`

```python
Форматированное представление ошибки
```

## Class: `ConfigValidator`

```python
Валидатор конфигурации Code Agent
```

### Method: `ConfigValidator.load_and_validate`

```python
Загрузка и валидация конфигурации

Args:
    config_path: Путь к файлу конфигурации

Returns:
    Валидированная конфигурация

Raises:
    ConfigValidationError: Если конфигурация невалидна
```

### Method: `ConfigValidator.__init__`

```python
Инициализация валидатора

Args:
    config: Словарь с конфигурацией
```

### Method: `ConfigValidator.validate`

```python
Валидация всей конфигурации

Raises:
    ConfigValidationError: Если конфигурация невалидна
```

### Method: `ConfigValidator._validate_required_sections`

```python
Проверка наличия обязательных секций
```

### Method: `ConfigValidator._validate_section`

```python
Валидация секции конфигурации

Args:
    section_name: Имя секции
    schema: Схема валидации для секции
```

### Method: `ConfigValidator._validate_auto_todo_generation`

```python
Валидация настроек автоматической генерации TODO
```

### Method: `ConfigValidator._validate_checkpoint`

```python
Валидация настроек checkpoint
```

### Method: `ConfigValidator._validate_learning_tool`

```python
Валидация настроек LearningTool
```

### Method: `ConfigValidator._validate_context_analyzer_tool`

```python
Валидация настроек ContextAnalyzerTool
```

### Method: `ConfigValidator._check_type`

```python
Проверка типа значения

Args:
    value: Значение для проверки
    expected_type: Ожидаемый тип (может быть tuple для нескольких типов)

Returns:
    True если тип соответствует
```

### Method: `ConfigValidator._type_to_string`

```python
Преобразование типа в строку для сообщений об ошибках
```

## Function: `validate_config`

```python
Валидация конфигурации (удобная функция-обертка)

Args:
    config: Словарь с конфигурацией

Raises:
    ConfigValidationError: Если конфигурация невалидна
```
