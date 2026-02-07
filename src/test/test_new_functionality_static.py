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
    assert hints.get('a') == Union[int, float], "another_new_function parameter 'a' should be Union[int, float]"
    assert hints.get('b') == Union[int, float], "another_new_function parameter 'b' should be Union[int, float]"
    assert hints.get('return') == Union[int, float], "another_new_function should return Union[int, float]"

# Add more static tests if needed, e.g., type hints, complexity, etc.
