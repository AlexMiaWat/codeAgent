# Module: `prompt_formatter`

## Class: `PromptFormatter`

```python
Форматирует инструкции в строгий формат для Cursor Agent
```

### Method: `PromptFormatter.format_system_prompt`

```python
Формирует системный промпт для настройки агента

Args:
    agent_role: Роль агента (например, "Project Executor Agent")
    
Returns:
    Системный промпт в строгом формате
```

### Method: `PromptFormatter.format_task_instruction`

```python
Формирует инструкцию задачи в строгом ACTION/TASK формате

Args:
    task_description: Описание задачи (человеческий язык)
    action_type: Тип действия (execute, create, modify, analyze)
    constraints: Дополнительные ограничения
    output_path: Путь для вывода результата (если нужен)
    
Returns:
    Инструкция в строгом формате
```

### Method: `PromptFormatter.format_execution_prompt`

```python
Формирует промпт для принудительного выполнения задачи

Returns:
    Промпт для выполнения
```

### Method: `PromptFormatter.parse_instruction_to_action_format`

```python
Преобразует человеческую инструкцию в строгий ACTION/TASK формат

Args:
    instruction: Исходная инструкция (человеческий язык)
    output_path: Путь для сохранения результата
    
Returns:
    Инструкция в строгом формате
```

### Method: `PromptFormatter.format_task_with_execution_guarantee`

```python
Формирует инструкцию с явным указанием немедленного выполнения

Этот формат добавляет дополнительные указания для гарантии выполнения задачи
агентом в non-interactive режиме.

Args:
    task_name: Название задачи
    task_description: Подробное описание задачи
    output_file: Файл для сохранения результата
    control_phrase: Контрольная фраза для подтверждения выполнения
    additional_constraints: Дополнительные ограничения
    
Returns:
    Инструкция с явным указанием выполнения
```
