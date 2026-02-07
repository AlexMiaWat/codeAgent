
from datetime import datetime
from typing import Union


def new_feature_function() -> str:
    """
    This function returns a confirmation message with the current timestamp.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"New functionality is working as of {current_time}!"


def another_new_function(
    x: Union[int, float],
    y: Union[int, float],
    weight_x: float = 0.5
) -> Union[int, float]:
    """
    This function calculates the weighted average of two numbers.
    It returns the weighted average of two numbers.
    """
    if not 0 <= weight_x <= 1:
        raise ValueError("weight_x must be between 0 and 1")
    return x * weight_x + y * (1 - weight_x)
