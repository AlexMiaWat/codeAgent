# Новая функциональность

Этот документ описывает новую функциональность, добавленную в проект.

## Модуль `src/new_functionality.py`

Модуль `src/new_functionality.py` содержит функции, демонстрирующие новую функциональность.

### Функции

#### `new_feature_function() -> str`

Функция `new_feature_function` возвращает динамическое сообщение с текущей меткой времени.

**Возвращает:**
- `str`: Строка, подтверждающая работу новой функциональности, с включенной текущей датой и временем.

**Пример использования:**
```python
from src.new_functionality import new_feature_function

message = new_feature_function()
print(message)  # Output: New functionality is working as of YYYY-MM-DD HH:MM:SS!
```

#### `another_new_function(x: Union[int, float], y: Union[int, float], weight_x: float = 0.5) -> Union[int, float]`

Функция `another_new_function` вычисляет взвешенное среднее двух чисел.

**Параметры:**
- `x` (Union[int, float]): Первое число.
- `y` (Union[int, float]): Второе число.
- `weight_x` (float, optional): Вес для первого числа `x`. Должен быть в диапазоне от 0 до 1. По умолчанию 0.5. Если `weight_x` равен `w`, то `y` имеет вес `1-w`.

**Возвращает:**
- `Union[int, float]`: Взвешенное среднее двух чисел.

**Вызывает:**
- `ValueError`: Если `weight_x` не находится в диапазоне от 0 до 1.

**Пример использования:**
```python
from src.new_functionality import another_new_function

result = another_new_function(10, 20, 0.75)
print(result)  # Output: 12.5 (10 * 0.75 + 20 * 0.25)

result_default_weight = another_new_function(5, 15)
print(result_default_weight) # Output: 10.0 (5 * 0.5 + 15 * 0.5)

try:
    another_new_function(10, 20, 1.5)
except ValueError as e:
    print(e) # Output: weight_x must be between 0 and 1
```

## Тестирование новой функциональности

Для тестирования новой функциональности был добавлен модуль `src/test/test_new_functionality.py`.
Он содержит различные типы тестов для функций `new_feature_function` и `another_new_function`.

### Виды тестов:

### Тесты качества статического кода (Static Code Quality Tests):

Для обеспечения качества кода и соответствия стандартам стиля, *используется и регулярно запускается* статический анализатор кода `flake8`.

**Пример запуска статического анализатора:**
```bash
flake8 src/new_functionality.py
flake8 test/test_new_functionality.py
```

В реальных условиях, запуск линтеров (например, `flake8`) и статических анализаторов типов (например, `mypy`) должен быть интегрирован в CI/CD пайплайн для автоматической проверки качества кода при каждом изменении.

-   **Дымовые тесты (Smoke Tests):** Проверяют базовую работоспособность функций, убеждаясь, что они выполняют свои основные операции без сбоев. Например, `test_new_feature_function_smoke`, `test_another_new_function_smoke`.
-   **Интеграционные тесты (Integration Tests):** Проверяют взаимодействие функций и их корректную работу с различными входными данными, включая граничные случаи. Например, `test_another_new_function_various_numbers` для тестирования сложения с нулем, отрицательными числами и большими значениями.

Пример запуска тестов:
```bash
pytest src/test/test_new_functionality.py
```