
import pytest
from src.core.new_feature import new_functionality

def test_new_functionality_integration():
    assert new_functionality() == "New functionality working!"
