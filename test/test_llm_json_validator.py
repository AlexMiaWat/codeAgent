"""
Тесты для JsonValidator
"""

import pytest
from src.llm.validator import JsonValidator


class TestJsonValidator:
    """Тесты валидатора JSON"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.validator = JsonValidator()

    def test_validate_json_valid(self):
        """Тест валидации корректного JSON"""
        valid_json = '{"name": "test", "value": 123}'
        assert self.validator.validate_json(valid_json) is True

    def test_validate_json_invalid(self):
        """Тест валидации некорректного JSON"""
        invalid_json = '{"name": "test", "value": }'
        assert self.validator.validate_json(invalid_json) is False

    def test_extract_json_from_text_with_markdown(self):
        """Тест извлечения JSON из текста с markdown"""
        text = 'Here is some JSON:\n```json\n{"key": "value"}\n```'
        result = self.validator.extract_json_from_text(text)
        assert result == '{"key": "value"}'

    def test_extract_json_from_text_plain(self):
        """Тест извлечения JSON из обычного текста"""
        text = 'Response: {"status": "ok"}'
        result = self.validator.extract_json_from_text(text)
        assert result == '{"status": "ok"}'

    def test_validate_and_extract_valid(self):
        """Тест validate_and_extract с валидным JSON"""
        text = '```json\n{"test": "data"}\n```'
        is_valid, extracted = self.validator.validate_and_extract(text)
        assert is_valid is True
        assert extracted == '{"test": "data"}'

    def test_validate_and_extract_invalid(self):
        """Тест validate_and_extract с невалидным JSON"""
        text = '```json\n{"test": }\n```'
        is_valid, extracted = self.validator.validate_and_extract(text)
        assert is_valid is False
        assert extracted is None