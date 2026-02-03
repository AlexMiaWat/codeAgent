
import inspect
from new_functionality import some_new_function, another_new_function

def test_some_new_function_has_docstring():
    """Verify some_new_function has a docstring."""
    assert inspect.getdoc(some_new_function) is not None, "some_new_function should have a docstring"

def test_another_new_function_has_docstring():
    """Verify another_new_function has a docstring."""
    assert inspect.getdoc(another_new_function) is not None, "another_new_function should have a docstring"

# Assuming no type hints for now, but this is where you'd add checks for them
# def test_some_new_function_type_hints():
#     """Verify some_new_function has type hints."""
#     signature = inspect.signature(some_new_function)
#     assert all(param.annotation is not inspect.Parameter.empty for param in signature.parameters.values()), "some_new_function should have type hints"
