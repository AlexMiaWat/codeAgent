import pytest
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from new_functionality import new_feature_function, another_new_function

# Статические тесты (linting - обычно запускается отдельно, но для примера можно включить простой тест)
def test_static_analysis():
    # В реальном проекте здесь будет запуск flake8, pylint и т.д.
    # Для демонстрации, просто убедимся, что функции существуют.
    assert hasattr(new_functionality, 'new_feature_function')
    assert hasattr(new_functionality, 'another_new_function')

# Дымовые тесты
def test_new_feature_function_smoke():
    assert new_feature_function() == "New functionality is working!"

def test_another_new_function_smoke():
    assert another_new_function(1, 2) == 3

# Интеграционные тесты
def test_another_new_function_integration():
    # Тест на различные входные данные
    assert another_new_function(10, 20) == 30
    assert another_new_function(-1, 1) == 0
    assert another_new_function(0, 0) == 0
    assert another_new_function(1000, -500) == 500
