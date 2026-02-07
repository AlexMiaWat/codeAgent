
import re
import pytest
from src.new_functionality import new_feature_function, another_new_function


# Static Tests
def test_new_feature_function_exists():
    assert callable(new_feature_function)


def test_another_new_function_exists():
    assert callable(another_new_function)


def test_new_feature_function_signature():
    import inspect
    sig = inspect.signature(new_feature_function)
    assert len(sig.parameters) == 0


def test_another_new_function_signature():
    import inspect
    sig = inspect.signature(another_new_function)
    assert len(sig.parameters) == 3
    assert 'x' in sig.parameters
    assert 'y' in sig.parameters
    assert 'weight_x' in sig.parameters
    assert sig.parameters['weight_x'].default == 0.5


# Smoke Tests
def test_new_feature_function_smoke():
    message = new_feature_function()
    # Check if the message matches the expected format with a timestamp
    expected_pattern = (
        r"New functionality is working as of "
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}!"
    )
    assert re.match(expected_pattern, message)


def test_another_new_function_smoke_default_weight():
    # Expected: 5 * 0.5 + 15 * 0.5 = 2.5 + 7.5 = 10.0
    assert another_new_function(5, 15) == 10.0


def test_another_new_function_smoke_custom_weight():
    # Expected: 10 * 0.75 + 20 * 0.25 = 7.5 + 5.0 = 12.5
    assert another_new_function(10, 20, 0.75) == 12.5


# Integration Tests (testing with various valid and invalid inputs, also edge cases)
def test_another_new_function_integration_zero_weight():
    # Expected: 10 * 0 + 20 * 1 = 20
    assert another_new_function(10, 20, 0.0) == 20.0


def test_another_new_function_integration_one_weight():
    # Expected: 10 * 1 + 20 * 0 = 10
    assert another_new_function(10, 20, 1.0) == 10.0


def test_another_new_function_integration_negative_numbers():
    # Expected: -10 * 0.5 + -20 * 0.5 = -5 + -10 = -15.0
    assert another_new_function(-10, -20) == -15.0


def test_another_new_function_integration_float_numbers():
    # Expected: (10.5 * 0.4) + (20.5 * 0.6)
    #           = 4.2 + 12.3 = 16.5
    assert another_new_function(10.5, 20.5, 0.4) == pytest.approx(16.5)


def test_another_new_function_value_error_weight_less_than_zero():
    with pytest.raises(ValueError, match="weight_x must be between 0 and 1"):
        another_new_function(10, 20, -0.1)


def test_another_new_function_value_error_weight_greater_than_one():
    with pytest.raises(ValueError, match="weight_x must be between 0 and 1"):
        another_new_function(10, 20, 1.1)


# Test for potential errors
def test_another_new_function_type_error():
    with pytest.raises(TypeError):
        another_new_function(1, "a")
