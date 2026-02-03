
# src/core/new_feature.py

class NewFeature:
    def __init__(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError("Value must be an integer or a float")
        self.value = value

    def get_doubled_value(self):
        return self.value * 2

    def is_positive(self):
        return self.value > 0

def process_feature_list(features):
    """Processes a list of NewFeature objects, returning doubled positive values."""
    processed_values = []
    for feature in features:
        if isinstance(feature, NewFeature) and feature.is_positive():
            processed_values.append(feature.get_doubled_value())
    return processed_values
