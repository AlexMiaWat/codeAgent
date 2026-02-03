# Module: `checkpoint_manager`

## Class: `TaskState`

```python
Состояние выполнения задачи
```

## Class: `CheckpointManager`

```python
Управление контрольными точками для безопасного восстановления после сбоев

Функции:
- Сохранение состояния выполнения задач
- Восстановление с последней точки
- Защита от дублирования задач
- Откат при критических ошибках
```

### Method: `CheckpointManager.__init__`

```python
Инициализация менеджера контрольных точек

Args:
    project_dir: Директория проекта
    checkpoint_file: Имя файла для хранения контрольных точек
    config: Конфигурация менеджера
```

### Method: `CheckpointManager._load_checkpoint`

```python
Загрузка контрольной точки из файла

Returns:
    Словарь с данными контрольной точки
```

### Method: `CheckpointManager._save_checkpoint`

```python
Сохранение контрольной точки в файл

Args:
    create_backup: Создать резервную копию перед сохранением
```

### Method: `CheckpointManager.mark_server_start`

```python
Отметить запуск сервера

Args:
    session_id: ID текущей сессии
```

### Method: `CheckpointManager.mark_server_stop`

```python
Отметить остановку сервера

Args:
    clean: True если останов был корректным
```

### Method: `CheckpointManager.increment_iteration`

```python
Увеличить счетчик итераций
```

### Method: `CheckpointManager.get_iteration_count`

```python
Получить текущий счетчик итераций

Returns:
    Количество выполненных итераций
```

### Method: `CheckpointManager.was_clean_shutdown`

```python
Проверка, был ли последний останов корректным

Returns:
    True если останов был корректным
```

### Method: `CheckpointManager.add_task`

```python
Добавить задачу в checkpoint

Args:
    task_id: Уникальный ID задачи
    task_text: Текст задачи
    metadata: Дополнительные метаданные
```

### Method: `CheckpointManager.mark_task_start`

```python
Отметить начало выполнения задачи

Args:
    task_id: ID задачи
```

### Method: `CheckpointManager.mark_task_completed`

```python
Отметить успешное завершение задачи

Args:
    task_id: ID задачи
    result: Результат выполнения
```

### Method: `CheckpointManager.update_instruction_progress`

```python
Обновить прогресс выполнения инструкций для задачи

Args:
    task_id: ID задачи
    instruction_num: Номер выполненной инструкции (1-based)
    total_instructions: Общее количество инструкций
```

### Method: `CheckpointManager.get_instruction_progress`

```python
Получить прогресс выполнения инструкций для задачи

Args:
    task_id: ID задачи

Returns:
    Словарь с прогрессом или None если задача не найдена
```

### Method: `CheckpointManager.mark_task_failed`

```python
Отметить неудачное выполнение задачи

Args:
    task_id: ID задачи
    error_message: Сообщение об ошибке
```

### Method: `CheckpointManager.get_current_task`

```python
Получить текущую выполняемую задачу

Returns:
    Данные текущей задачи или None
```

### Method: `CheckpointManager.get_incomplete_tasks`

```python
Получить список незавершенных задач

Returns:
    Список задач в состоянии PENDING или IN_PROGRESS
```

### Method: `CheckpointManager.get_failed_tasks`

```python
Получить список задач, завершенных с ошибкой

Returns:
    Список задач в состоянии FAILED
```

### Method: `CheckpointManager.should_retry_task`

```python
Проверить, нужно ли повторить задачу

Args:
    task_id: ID задачи
    max_attempts: Максимальное количество попыток

Returns:
    True если нужно повторить
```

### Method: `CheckpointManager._find_task`

```python
Найти задачу по ID

Args:
    task_id: ID задачи

Returns:
    Данные задачи или None
```

### Method: `CheckpointManager.is_task_completed`

```python
Проверить, была ли задача уже выполнена

ВАЖНО: Проверяет ПОСЛЕДНЮЮ попытку задачи, а не любую.
Если последняя попытка не завершена (pending/failed), задача считается невыполненной.

Args:
    task_text: Текст задачи

Returns:
    True если задача уже выполнена (последняя попытка в статусе completed)
```

### Method: `CheckpointManager.get_recovery_info`

```python
Получить информацию для восстановления после сбоя

Returns:
    Словарь с информацией о состоянии
```

### Method: `CheckpointManager.reset_interrupted_task`

```python
Сбросить состояние прерванной задачи для повторного выполнения

ВАЖНО: НЕ сбрасывает прогресс инструкций - он сохраняется для восстановления
при следующей попытке выполнения задачи
```

### Method: `CheckpointManager.clear_old_tasks`

```python
Очистить старые завершенные задачи для экономии места

Args:
    keep_last_n: Количество последних задач для сохранения
```

### Method: `CheckpointManager.get_statistics`

```python
Получить статистику выполнения задач

Returns:
    Словарь со статистикой
```

### Method: `CheckpointManager.get_completed_tasks`

```python
Получить все завершенные задачи.

Returns:
    Список завершенных задач
```

### Method: `CheckpointManager.is_healthy`

```python
Проверить здоровье менеджера контрольных точек.

Returns:
    True если менеджер в рабочем состоянии
```

### Method: `CheckpointManager.get_status`

```python
Получить статус менеджера контрольных точек.

Returns:
    Словарь со статусной информацией
```

### Method: `CheckpointManager.dispose`

```python
Очистить ресурсы менеджера контрольных точек.
```
