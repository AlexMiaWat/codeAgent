# Module: `cursor_cli_interface`

## Class: `CursorCLIInterface`
## Dataclass: `CursorCLIResult`

Класс данных для инкапсуляции результатов выполнения команд Cursor CLI.

```python
@dataclass
class CursorCLIResult:
    success: bool
    error_message: Optional[str]
    stdout: str
    stderr: str
    return_code: int
    cli_available: bool
```

**Поля:**
- `success` (bool): `True`, если команда выполнена успешно, иначе `False`.
- `error_message` (Optional[str]): Сообщение об ошибке, если таковая произошла.
- `stdout` (str): Стандартный вывод команды.
- `stderr` (str): Стандартный вывод ошибок команды.
- `return_code` (int): Код возврата команды.
- `cli_available` (bool): `True`, если Cursor CLI доступен, иначе `False`.


```python
Интерфейс взаимодействия с Cursor через CLI.
```

### Method: `CursorCLIInterface.__init__`

### Method: `CursorCLIInterface._check_availability_on_init`

```python
Проверяет доступность Cursor CLI при инициализации.
```

### Method: `CursorCLIInterface.is_available`

```python
Проверяет, доступен ли Cursor CLI.
```

### Method: `CursorCLIInterface.check_version`

```python
Возвращает версию Cursor CLI, если доступен.
```

### Method: `CursorCLIInterface.prepare_for_new_task`

```python
Очищает активные диалоги Cursor и подготавливает его к новой задаче.
В текущей реализации CLI это может быть эквивалентно сбросу состояния.
```

### Method: `CursorCLIInterface.execute_instruction`

```python
Выполнить команду через Cursor CLI.

Args:
    instruction: Текст инструкции для выполнения.
    task_id: Идентификатор задачи.
    working_dir: Рабочая директория для выполнения команды.
    timeout: Таймаут выполнения (в секундах).

Returns:
    Словарь с результатом выполнения, инкапсулированный в `CursorCLIResult`.
```

## Function: `create_cursor_cli_interface`

```python
Фабричная функция для создания экземпляра CursorCLIInterface.
```
