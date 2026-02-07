import datetime
from typing import Union

def new_feature_function():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"New functionality is working as of {current_time}!"

def another_new_function(x: Union[int, float], y: Union[int, float], weight_x: float = 0.5) -> Union[int, float]:
    if not (0 <= weight_x <= 1):
        raise ValueError("weight_x must be between 0 and 1")
    return (x * weight_x) + (y * (1 - weight_x))
