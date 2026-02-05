import pytest
import inspect

from core.new_feature import NewFeature, process_feature_list

# --- Static Tests ---

def test_new_feature_class_has_docstring():
    assert inspect.getdoc(NewFeature) is not None, "NewFeature class should have a docstring"

def test_new_feature_init_has_docstring():
    assert inspect.getdoc(NewFeature.__init__) is not None, "NewFeature.__init__ should have a docstring"

def test_new_feature_get_doubled_value_has_docstring():
    assert inspect.getdoc(NewFeature.get_doubled_value) is not None, "NewFeature.get_doubled_value should have a docstring"

def test_new_feature_is_positive_has_docstring():
    assert inspect.getdoc(NewFeature.is_positive) is not None, "NewFeature.is_positive should have a docstring"

def test_process_feature_list_has_docstring():
    assert inspect.getdoc(process_feature_list) is not None, "process_feature_list should have a docstring"

# --- Smoke Tests ---
def test_new_feature_smoke_test():
    feature = NewFeature(10)
    assert feature.value == 10
    assert feature.get_doubled_value() == 20
    assert feature.is_positive() is True

def test_process_feature_list_smoke_test():
    feature1 = NewFeature(5)
    feature2 = NewFeature(10)
    result = process_feature_list([feature1, feature2])
    assert result == [10, 20]

# --- Integration Tests ---

# NewFeature.__init__ tests
def test_new_feature_init_valid_int():
    feature = NewFeature(5)
    assert feature.value == 5

def test_new_feature_init_valid_float():
    feature = NewFeature(5.5)
    assert feature.value == 5.5

def test_new_feature_init_invalid_type():
    with pytest.raises(TypeError, match="Value must be an integer or a float"):
        NewFeature("invalid")

def test_new_feature_init_zero():
    feature = NewFeature(0)
    assert feature.value == 0

def test_new_feature_init_negative():
    feature = NewFeature(-10)
    assert feature.value == -10

# NewFeature.get_doubled_value tests
@pytest.mark.parametrize("input_value, expected_doubled_value", [
    (5, 10),
    (-5, -10),
    (0, 0),
    (2.5, 5.0),
])
def test_new_feature_get_doubled_value_integration(input_value, expected_doubled_value):
    feature = NewFeature(input_value)
    assert feature.get_doubled_value() == expected_doubled_value

# NewFeature.is_positive tests
@pytest.mark.parametrize("input_value, expected_is_positive", [
    (5, True),
    (-5, False),
    (0, False),
    (2.5, True),
    (-0.1, False),
])
def test_new_feature_is_positive_integration(input_value, expected_is_positive):
    feature = NewFeature(input_value)
    assert feature.is_positive() == expected_is_positive

# process_feature_list tests
def test_process_feature_list_empty():
    assert process_feature_list([]) == []

def test_process_feature_list_non_new_feature_objects():
    assert process_feature_list([1, "a", NewFeature(5)]) == [10] # Only NewFeature objects with positive values are processed

def test_process_feature_list_mixed_positive_negative():
    feature1 = NewFeature(5)
    feature2 = NewFeature(-2)
    feature3 = NewFeature(10)
    assert process_feature_list([feature1, feature2, feature3]) == [10, 20]

def test_process_feature_list_with_zeros():
    feature1 = NewFeature(0)
    feature2 = NewFeature(5)
    feature3 = NewFeature(0.0)
    assert process_feature_list([feature1, feature2, feature3]) == [10]

def test_process_feature_list_only_positive():
    feature1 = NewFeature(1)
    feature2 = NewFeature(2.5)
    assert process_feature_list([feature1, feature2]) == [2, 5.0]

def test_process_feature_list_no_positive_features():
    feature1 = NewFeature(-1)
    feature2 = NewFeature(0)
    assert process_feature_list([feature1, feature2]) == []
