
import pytest
from src.new_functionality import some_new_function, another_new_function

# Smoke Tests
def test_some_new_function_smoke():
    assert some_new_function(1, 2) == 3

def test_another_new_function_smoke():
    assert another_new_function("hello") == "HELLO"

# Integration Tests for some_new_function
@pytest.mark.parametrize("a, b, expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (0, 0, 0),
    (100, -50, 50),
    (-10, -20, -30),
])
def test_some_new_function_integration(a, b, expected):
    assert some_new_function(a, b) == expected

# Integration Tests for another_new_function
@pytest.mark.parametrize("text, expected", [
    ("world", "WORLD"),
    ("Python rocks", "PYTHON ROCKS"),
    ("", ""),
    ("123", "123"),
    ("hello world!", "HELLO WORLD!"),
    ("   leading/trailing spaces   ", "   LEADING/TRAILING SPACES   "), # Added a new case
])
def test_another_new_function_integration(text, expected):
    assert another_new_function(text) == expected

# Integration Test: Chaining functions
def test_chained_functions_integration():
    result_sum = some_new_function(5, 7)
    result_processed = another_new_function(str(result_sum))
    assert result_processed == "12" # 5 + 7 = 12, then "12".upper() = "12"

# Integration Test: Edge case for another_new_function with numbers in string
def test_another_new_function_numbers_integration():
    assert another_new_function("123test456") == "123TEST456"

# Integration Test: Edge case for another_new_function with special characters
def test_another_new_function_special_chars_integration():
    assert another_new_function("!@#$%^&*()") == "!@#$%^&*()"

