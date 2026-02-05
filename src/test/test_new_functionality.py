
import pytest
from src.new_functionality import new_feature_function, another_new_function

def test_new_feature_function_smoke():
    """
    Smoke test for new_feature_function.
    Checks if the function returns the expected confirmation message.
    """
    assert new_feature_function() == "New functionality is working!"

def test_another_new_function_smoke():
    """
    Smoke test for another_new_function.
    Checks basic addition.
    """
    assert another_new_function(1, 2) == 3

def test_another_new_function_integration_positive_numbers():
    """
    Integration test for another_new_function with positive numbers.
    """
    assert another_new_function(5, 10) == 15

def test_another_new_function_integration_negative_numbers():
    """
    Integration test for another_new_function with negative numbers.
    """
    assert another_new_function(-1, -5) == -6

def test_another_new_function_integration_zero():
    """
    Integration test for another_new_function with zero.
    """
    assert another_new_function(0, 100) == 100
    assert another_new_function(-50, 0) == -50

def test_another_new_function_integration_float_numbers():
    """
    Integration test for another_new_function with float numbers.
    """
    assert another_new_function(1.5, 2.5) == 4.0
    assert another_new_function(-1.0, 0.5) == -0.5
