
import pytest
from src.new_functionality import new_feature_function, another_new_function

def test_new_feature_function_smoke():
    """
    Smoke test for new_feature_function.
    Checks if the function returns the expected confirmation message with a timestamp.
    """
    result = new_feature_function()
    assert "New functionality is working as of" in result
    # Further check the timestamp format (YYYY-MM-DD HH:MM:SS)
    timestamp_str = result.split("as of ")[1].strip("!")
    import datetime
    try:
        datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pytest.fail("Timestamp format is incorrect")


def test_another_new_function_weighted_average_smoke():
    """
    Smoke test for another_new_function with default weight.
    """
    # Default weight_x is 0.5
    assert another_new_function(10, 20) == 15.0

def test_another_new_function_weighted_average_zero_weight_x():
    """
    Integration test for another_new_function with weight_x = 0.
    Should return y.
    """
    assert another_new_function(10, 20, weight_x=0) == 20.0

def test_another_new_function_weighted_average_one_weight_x():
    """
    Integration test for another_new_function with weight_x = 1.
    Should return x.
    """
    assert another_new_function(10, 20, weight_x=1) == 10.0

def test_another_new_function_weighted_average_custom_weight_x():
    """
    Integration test for another_new_function with a custom weight_x.
    """
    assert another_new_function(10, 20, weight_x=0.25) == 17.5
    assert another_new_function(10, 20, weight_x=0.75) == 12.5
    assert another_new_function(1.0, 2.0, weight_x=0.3) == pytest.approx(1.7)

def test_another_new_function_value_error_weight_x_less_than_0():
    """
    Integration test for another_new_function, checking ValueError for weight_x < 0.
    """
    with pytest.raises(ValueError, match="weight_x must be between 0 and 1"):
        another_new_function(10, 20, weight_x=-0.1)

def test_another_new_function_value_error_weight_x_greater_than_1():
    """
    Integration test for another_new_function, checking ValueError for weight_x > 1.
    """
    with pytest.raises(ValueError, match="weight_x must be between 0 and 1"):
        another_new_function(10, 20, weight_x=1.1)

def test_another_new_function_integration_mixed_types_with_weight():
    """
    Integration test for another_new_function with mixed integer and float types and weight_x.
    """
    assert another_new_function(10, 0.5, weight_x=0.5) == 5.25 # (10*0.5) + (0.5*0.5) = 5 + 0.25
    assert another_new_function(-1.5, 5, weight_x=0.2) == pytest.approx(3.7) # (-1.5*0.2) + (5*0.8) = -0.3 + 4 = 3.7

