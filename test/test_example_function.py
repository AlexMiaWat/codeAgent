
import pytest
from src.core.example_function import new_function

# Static Tests
def test_new_function_static_type_hints():
    """
    Checks if new_function has type hints for arguments and return value.
    This is a basic static check. More sophisticated checks would involve
    using a type checker like mypy.
    """
    assert new_function.__annotations__.get('name') == str
    assert new_function.__annotations__.get('return') == str
