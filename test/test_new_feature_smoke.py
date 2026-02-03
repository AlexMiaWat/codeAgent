
import pytest
from src.core.new_feature import NewFeature

def test_new_feature_smoke():
    feature = NewFeature("smoke_test")
    assert feature.get_name() == "smoke_test"
    assert feature.process_data("data") == "Processed: data"
