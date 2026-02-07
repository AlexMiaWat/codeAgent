# Module: `new_functionality`

This module introduces new features to the system, including a function to confirm new functionality is active and a utility function for weighted averages.

## Function: `new_feature_function`

```python
def new_feature_function() -> str:
```

### Description
This function returns a confirmation message with the current timestamp, indicating that new functionality is active and operational.

### Returns
`str`: A string confirming the new functionality is working, including a timestamp.

## Function: `another_new_function`

```python
def another_new_function(x: Union[int, float], y: Union[int, float], weight_x: float = 0.5) -> Union[int, float]:
```

### Description
This function calculates the weighted average of two numbers, `x` and `y`. The `weight_x` parameter determines the influence of `x` on the average.

### Parameters
*   `x` (`Union[int, float]`): The first number.
*   `y` (`Union[int, float]`): The second number.
*   `weight_x` (`float`, optional): The weight assigned to `x`. This value must be between 0 and 1 (inclusive). The weight for `y` will be `1 - weight_x`. Defaults to `0.5`.

### Returns
`Union[int, float]`: The calculated weighted average of `x` and `y`.

### Raises
`ValueError`: If `weight_x` is not between 0 and 1.