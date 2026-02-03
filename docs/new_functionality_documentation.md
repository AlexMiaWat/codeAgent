# Новая функциональность

Этот документ описывает новую функциональность, добавленную в проект.

## Модуль `src/new_functionality.py`

Модуль `src/new_functionality.py` содержит набор утилитарных функций для базовых операций.

### Функции

#### `greet(name: str) -> str`

Функция `greet` принимает на вход строковое имя и возвращает приветствие.

**Параметры:**
- `name` (str): Имя человека для приветствия.

**Возвращает:**
- `str`: Строка приветствия, например "Hello, [name]!".

**Пример использования:**
```python
from src.new_functionality import greet

message = greet("World")
print(message)  # Output: Hello, World!
```

#### `add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]`

Функция `add` принимает два числа (целые или с плавающей точкой) и возвращает их сумму.

**Параметры:**
- `a` (Union[int, float]): Первое число.
- `b` (Union[int, float]): Второе число.

**Возвращает:**
- `Union[int, float]`: Сумма двух чисел.

**Пример использования:**
```python
from src.new_functionality import add

result = add(5, 3)
print(result)  # Output: 8

result_float = add(10.5, 2.3)
print(result_float) # Output: 12.8
```

#### `divide(a: Union[int, float], b: Union[int, float]) -> Union[int, float]`

Функция `divide` принимает два числа (целые или с плавающей точкой) и возвращает результат их деления.
В случае попытки деления на ноль генерирует исключение `ValueError`.

**Параметры:**
- `a` (Union[int, float]): Делимое.
- `b` (Union[int, float]): Делитель.

**Возвращает:**
- `Union[int, float]`: Результат деления.

**Вызывает:**
- `ValueError`: Если `b` равно нулю.

**Пример использования:**
```python
from src.new_functionality import divide

result = divide(10, 2)
print(result)  # Output: 5.0

try:
    divide(5, 0)
except ValueError as e:
    print(e)  # Output: Cannot divide by zero
```

## Тестирование новой функциональности

Для тестирования новой функциональности был добавлен модуль `src/test/test_new_functionality.py`.
Он содержит различные типы тестов для функций `greet`, `add` и `divide`.

### Виды тестов:

-   **Тесты качества статического кода (Static Code Quality Tests):** Содержат заглушку `test_static_code_quality`, которая в реальных условиях представляла бы собой запуск линтеров (например, ruff) и статических анализаторов типов (например, mypy) как часть CI/CD пайплайна. Для данного упражнения предполагается, что качество статического кода является приемлемым.
-   **Дымовые тесты (Smoke Tests):** Проверяют базовую работоспособность функций, убеждаясь, что они выполняют свои основные операции без сбоев. Например, `test_greet_smoke`, `test_add_smoke`, `test_divide_smoke`.
-   **Интеграционные тесты (Integration Tests):** Проверяют взаимодействие функций и их корректную работу с различными входными данными, включая граничные случаи. Например, `test_greet_multiple_names` для проверки приветствия с разными именами, `test_add_various_numbers` для тестирования сложения с нулем, отрицательными числами и большими значениями, а также `test_divide_edge_cases` для проверки деления на 1, дробных результатов и обработки деления на ноль.

Пример запуска тестов:
```bash
pytest src/test/test_new_functionality.py
```
