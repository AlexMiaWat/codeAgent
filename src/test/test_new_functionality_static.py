import pytest
import inspect
from typing import get_type_hints, Union

from src.new_functionality import new_feature_function, another_new_function

def test_new_feature_function_has_docstring():
    """Verify new_feature_function has a docstring."""
    assert inspect.getdoc(new_feature_function) is not None, "new_feature_function should have a docstring"

def test_another_new_function_has_docstring():
    """Verify another_new_function has a docstring."""
    assert inspect.getdoc(another_new_function) is not None, "another_new_function should have a docstring"

def test_new_feature_function_type_hints():
    """Verify new_feature_function has correct type hints."""
    hints = get_type_hints(new_feature_function)
    assert hints.get('return') == str, "new_feature_function should return str"

def test_another_new_function_type_hints():
    """Verify another_new_function has correct type hints."""
    hints = get_type_hints(another_new_function)
    assert hints.get('x') == Union[int, float], "another_new_function parameter 'x' should be Union[int, float]"
    assert hints.get('y') == Union[int, float], "another_new_function parameter 'y' should be Union[int, float]"
    assert hints.get('weight_x') == float, "another_new_function parameter 'weight_x' should be float"
    assert another_new_function.__defaults__ is not None and another_new_function.__defaults__[0] == 0.5, "another_new_function parameter 'weight_x' should have a default value of 0.5"
    assert hints.get('return') == Union[int, float], "another_new_function should return Union[int, float]"

# Add more static tests if needed, e.g., type hints, complexity, etc.
