# Новая функциональность

Этот документ описывает новую функциональность, добавленную в проект.

## Модуль `src/new_functionality.py`

Модуль `src/new_functionality.py` содержит функции, демонстрирующие новую функциональность.

### Функции

#### `new_feature_function() -> str`

Функция `new_feature_function` представляет собой новую функциональность и возвращает подтверждающее сообщение.

**Возвращает:**
- `str`: Строка "New functionality is working!".

**Пример использования:**
```python
from src.new_functionality import new_feature_function

message = new_feature_function()
print(message)  # Output: New functionality is working!
```

#### `another_new_function(a: Union[int, float], b: Union[int, float]) -> Union[int, float]`

Функция `another_new_function` принимает два числа (целые или с плавающей точкой) и возвращает их сумму.

**Параметры:**
- `a` (Union[int, float]): Первое число.
- `b` (Union[int, float]): Второе число.

**Возвращает:**
- `Union[int, float]`: Сумма двух чисел.

**Пример использования:**
```python
from src.new_functionality import another_new_function

result = another_new_function(5, 3)
print(result)  # Output: 8

result_float = another_new_function(10.5, 2.3)
print(result_float) # Output: 12.8
```

## Тестирование новой функциональности

Для тестирования новой функциональности был добавлен модуль `src/test/test_new_functionality.py`.
Он содержит различные типы тестов для функций `new_feature_function` и `another_new_function`.

### Виды тестов:

-   **Тесты качества статического кода (Static Code Quality Tests):** Содержат заглушку `test_static_code_quality`, которая в реальных условиях представляла бы собой запуск линтеров (например, ruff) и статических анализаторов типов (например, mypy) как часть CI/CD пайплайна. Для данного упражнения предполагается, что качество статического кода является приемлемым.
-   **Дымовые тесты (Smoke Tests):** Проверяют базовую работоспособность функций, убеждаясь, что они выполняют свои основные операции без сбоев. Например, `test_new_feature_function_smoke`, `test_another_new_function_smoke`.
-   **Интеграционные тесты (Integration Tests):** Проверяют взаимодействие функций и их корректную работу с различными входными данными, включая граничные случаи. Например, `test_another_new_function_various_numbers` для тестирования сложения с нулем, отрицательными числами и большими значениями.

Пример запуска тестов:
```bash
pytest src/test/test_new_functionality.py
```