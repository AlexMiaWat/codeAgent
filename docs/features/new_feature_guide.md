# Новая функция: `NewFeature`

**Дата:** 2024-05-20
**Статус:** ✅ Реализовано

## Обзор

Введена новая функция `NewFeature` в модуле `src/core/new_feature.py`. Эта функция предназначена для обработки числовых значений, позволяя удваивать их и проверять, являются ли они положительными. Также реализована вспомогательная функция `process_feature_list` для работы со списками объектов `NewFeature`.

## Класс `NewFeature`

Класс `NewFeature` инициализируется числовым значением (целым или с плавающей точкой).

### Методы:

-   `__init__(self, value)`: Конструктор, принимает числовое значение `value`. Генерирует `TypeError`, если `value` не является числом.
-   `get_doubled_value(self)`: Возвращает удвоенное значение `value`.
-   `is_positive(self)`: Возвращает `True`, если `value` положительное, иначе `False`.

## Функция `process_feature_list`

```python
def process_feature_list(features):
    """Processes a list of NewFeature objects, returning doubled positive values."""
    processed_values = []
    for feature in features:
        if isinstance(feature, NewFeature) and feature.is_positive():
            processed_values.append(feature.get_doubled_value())
    return processed_values
```

Эта функция принимает список объектов `NewFeature` и возвращает новый список, содержащий удвоенные значения только тех объектов, которые являются положительными.

## Примеры использования

```python
from src.core.new_feature import NewFeature, process_feature_list

# Создание объектов NewFeature
feature1 = NewFeature(10)
feature2 = NewFeature(-5)
feature3 = NewFeature(0)
feature4 = NewFeature(3.14)

print(f"Feature 1 doubled: {feature1.get_doubled_value()}") # Вывод: 20
print(f"Feature 1 is positive: {feature1.is_positive()}")   # Вывод: True

print(f"Feature 2 doubled: {feature2.get_doubled_value()}") # Вывод: -10
print(f"Feature 2 is positive: {feature2.is_positive()}")   # Вывод: False

# Использование process_feature_list
features_list = [feature1, feature2, feature3, feature4]
result = process_feature_list(features_list)
print(f"Processed positive doubled values: {result}") # Вывод: [20, 6.28]
```

## Тестирование

Для новой функции `NewFeature` и связанных с ней утилит были разработаны следующие тесты:

-   **Модульные тесты (Smoke Tests):** `test/test_new_feature_smoke.py`
-   **Статические тесты (Static Tests):** `test/test_new_feature_static.py`
-   **Интеграционные тесты (Integration Tests):** `test/integration/test_new_feature_integration.py`

Эти тесты обеспечивают покрытие различных сценариев использования и гарантируют корректную работу функции.
