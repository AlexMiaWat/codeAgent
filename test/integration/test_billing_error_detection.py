#!/usr/bin/env python3
"""
Тест для проверки обнаружения billing ошибок в cursor_cli_interface.py
"""

import pytest
from src.cursor_cli_interface import CursorCLIInterface, CursorCLIResult


class TestBillingErrorDetection:
    """Тесты для обнаружения различных типов billing ошибок"""

    def test_usage_limit_error_detection(self):
        """Тест обнаружения ошибки usage limit"""
        cli = CursorCLIInterface()

        # Создаем мок результат с ошибкой usage limit
        result = CursorCLIResult(
            success=False,
            stdout="",
            stderr="You've hit your usage limit You've saved $245 on API model usage this month with Pro. Switch to a different model or set a Spend Limit to continue with Auto. Your usage limits will reset when your monthly cycle ends on 2/16/2026.",
            return_code=1,
            cli_available=True
        )

        resilience_config = {
            'fallback_on_errors': ['billing_error', 'timeout', 'model_unavailable', 'unknown_error']
        }

        # Проверяем, что ошибка распознается как billing error
        should_fallback = cli._should_trigger_fallback(result, resilience_config)
        assert should_fallback, "Usage limit error should trigger fallback"

    def test_unpaid_invoice_error_detection(self):
        """Тест обнаружения ошибки unpaid invoice"""
        cli = CursorCLIInterface()

        # Создаем мок результат с ошибкой unpaid invoice
        result = CursorCLIResult(
            success=False,
            stdout="",
            stderr="ActionRequiredError: You've hit an unpaid invoice. Please pay your invoice to continue.",
            return_code=1,
            cli_available=True
        )

        resilience_config = {
            'fallback_on_errors': ['billing_error', 'timeout', 'model_unavailable', 'unknown_error']
        }

        # Проверяем, что ошибка распознается как billing error
        should_fallback = cli._should_trigger_fallback(result, resilience_config)
        assert should_fallback, "Unpaid invoice error should trigger fallback"

    def test_spend_limit_error_detection(self):
        """Тест обнаружения ошибки spend limit"""
        cli = CursorCLIInterface()

        # Создаем мок результат с ошибкой spend limit
        result = CursorCLIResult(
            success=False,
            stdout="",
            stderr="Error: You have reached your spend limit. Please upgrade your plan or wait for the next billing cycle.",
            return_code=1,
            cli_available=True
        )

        resilience_config = {
            'fallback_on_errors': ['billing_error', 'timeout', 'model_unavailable', 'unknown_error']
        }

        # Проверяем, что ошибка распознается как billing error
        should_fallback = cli._should_trigger_fallback(result, resilience_config)
        assert should_fallback, "Spend limit error should trigger fallback"

    def test_non_billing_error_no_fallback(self):
        """Тест, что не-billing ошибки не вызывают fallback для billing_error"""
        cli = CursorCLIInterface()

        # Создаем мок результат с обычной ошибкой
        result = CursorCLIResult(
            success=False,
            stdout="",
            stderr="Error: Model not available",
            return_code=1,
            cli_available=True
        )

        resilience_config = {
            'fallback_on_errors': ['billing_error']  # Только billing errors
        }

        # Проверяем, что обычная ошибка не вызывает fallback
        should_fallback = cli._should_trigger_fallback(result, resilience_config)
        assert not should_fallback, "Non-billing error should not trigger billing fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])