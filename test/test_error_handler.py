import pytest
from src.error_handler import IntelligentErrorHandler, ErrorAnalysis, Fix

def test_analyze_file_not_found_error():
    handler = IntelligentErrorHandler()
    try:
        raise FileNotFoundError("test_file.txt")
    except FileNotFoundError as e:
        error_analysis = handler.analyze_error(e, {"file": "test_file.txt"})
        assert error_analysis.error_type == "FileNotFoundError"
        assert error_analysis.severity == "high"
        assert "Check file path and permissions." in error_analysis.details["suggestion"]

def test_suggest_fix_file_not_found():
    handler = IntelligentErrorHandler()
    error_analysis = ErrorAnalysis("FileNotFoundError", "File not found", "high", {"file": "test_file.txt"})
    fix = handler.suggest_fix(error_analysis)
    assert fix is not None
    assert "Ensure the file exists" in fix.suggested_action

def test_auto_fix_permission_error():
    handler = IntelligentErrorHandler()
    try:
        raise PermissionError("Permission denied")
    except PermissionError as e:
        fixed = handler.auto_fix(e)
        assert fixed is True

def test_analyze_value_error():
    handler = IntelligentErrorHandler()
    try:
        raise ValueError("Invalid input")
    except ValueError as e:
        error_analysis = handler.analyze_error(e, {"input_param": "abc"})
        assert error_analysis.error_type == "ValueError"
        assert error_analysis.severity == "medium"
        assert "Verify input values." in error_analysis.details["suggestion"]

def test_no_fix_suggested():
    handler = IntelligentErrorHandler()
    error_analysis = ErrorAnalysis("KeyError", "Key not found", "low", {"key": "non_existent"})
    fix = handler.suggest_fix(error_analysis)
    assert fix is None
