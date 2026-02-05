import pytest

import new_functionality # Import the module itself
from new_functionality import new_feature_function, another_new_function

# Статические тесты (linting - обычно запускается отдельно, но для примера можно включить простой тест)
def test_static_analysis_placeholders():
    # В реальном проекте здесь будет запуск flake8, pylint и т.д.
    # Для демонстрации, просто убедимся, что функции существуют в модуле.
    assert hasattr(new_functionality, 'new_feature_function')
    assert hasattr(new_functionality, 'another_new_function')

# Дымовые тесты
def test_new_feature_function_smoke():
    assert new_feature_function() == "New functionality is working!"

def test_another_new_function_smoke():
    assert another_new_function(1, 2) == 3

# Интеграционные тесты
@pytest.mark.parametrize("a, b, expected", [
    (10, 20, 30),
    (-1, 1, 0),
    (0, 0, 0),
    (1000, -500, 500),
    (5, 0, 5), # Edge case: adding zero
    (0, 5, 5), # Edge case: adding zero
    (-5, -10, -15), # Edge case: negative numbers
    (1.5, 2.5, 4.0), # Edge case: float numbers
])
def test_another_new_function_integration(a, b, expected):
    assert another_new_function(a, b) == expected
