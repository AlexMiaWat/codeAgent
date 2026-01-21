#!/usr/bin/env python3
"""
Тест для проверки автоматического fallback режима после billing ошибок
"""

import pytest
import time
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.fallback_state_manager import FallbackStateManager, FallbackState
from src.cursor_cli_interface import CursorCLIInterface, CursorCLIResult


class TestAutomaticFallback:
    """Тесты для автоматического fallback режима"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        # Создаем временный файл для состояния
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.state_file = self.temp_file.name

    def teardown_method(self):
        """Очистка после каждого теста"""
        if os.path.exists(self.state_file):
            os.unlink(self.state_file)

    def test_fallback_state_manager_basic(self):
        """Тест базовой функциональности FallbackStateManager"""
        manager = FallbackStateManager(self.state_file)

        # Изначально fallback не активен
        assert not manager.should_use_fallback()

        # Активируем fallback
        manager.activate_fallback()

        # Теперь должен быть активен
        assert manager.should_use_fallback()

        # Проверяем статус
        status = manager.get_status()
        assert status['fallback_active'] == True
        assert status['request_count'] == 0
        assert status['max_requests'] == 25

    def test_fallback_request_counting(self):
        """Тест подсчета обращений в fallback режиме"""
        manager = FallbackStateManager(self.state_file)

        # Активируем fallback
        manager.activate_fallback()
        assert manager.should_use_fallback()

        # Записываем несколько обращений
        for i in range(5):
            manager.record_request()
            assert manager.should_use_fallback()

        # Проверяем счетчик
        status = manager.get_status()
        assert status['request_count'] == 5

    def test_fallback_auto_deactivation(self):
        """Тест автоматической деактивации после 25 обращений"""
        manager = FallbackStateManager(self.state_file)

        # Активируем fallback
        manager.activate_fallback()

        # Записываем 24 обращения (еще должен быть активен)
        for i in range(24):
            manager.record_request()
            assert manager.should_use_fallback()

        # Проверяем что после 24 обращений еще активен
        status = manager.get_status()
        assert status['fallback_active'] == True
        assert status['request_count'] == 24

        # 25-е обращение должно деактивировать fallback
        manager.record_request()
        assert not manager.should_use_fallback()

        # Проверяем статус
        status = manager.get_status()
        assert status['fallback_active'] == False
        assert status['request_count'] == 0  # Сбрасывается при деактивации

    def test_fallback_state_persistence(self):
        """Тест сохранения и загрузки состояния"""
        # Создаем первый менеджер и активируем fallback
        manager1 = FallbackStateManager(self.state_file)
        manager1.activate_fallback()
        manager1.record_request()

        # Создаем второй менеджер (имитация перезапуска)
        manager2 = FallbackStateManager(self.state_file)

        # Состояние должно сохраниться
        assert manager2.should_use_fallback()
        status = manager2.get_status()
        assert status['request_count'] == 1

    def test_fallback_time_expiration(self):
        """Тест истечения времени fallback режима"""
        manager = FallbackStateManager(self.state_file)

        # Активируем fallback с коротким временем
        manager.state.fallback_active = True
        manager.state.fallback_until = time.time() - 1  # Время уже истекло
        manager.state.request_count = 5
        manager._save_state()

        # Fallback должен быть неактивен из-за истечения времени
        assert not manager.should_use_fallback()

    @patch('src.cursor_cli_interface.CursorCLIInterface._execute_with_specific_model')
    def test_cursor_cli_automatic_fallback(self, mock_execute):
        """Тест автоматического fallback в CursorCLIInterface"""
        # Создаем интерфейс с тестовым файлом состояния
        cli = CursorCLIInterface()
        cli.fallback_state = FallbackStateManager(self.state_file)

        # Активируем fallback режим
        cli.fallback_state.activate_fallback()

        # Мокаем успешное выполнение
        mock_result = CursorCLIResult(
            success=True,
            stdout="Test output",
            stderr="",
            return_code=0,
            cli_available=True
        )
        mock_execute.return_value = mock_result

        # Выполняем команду
        result = cli.execute_with_fallback("test prompt")

        # Проверяем что команда выполнена успешно
        assert result.success
        assert result.fallback_used == True

        # Проверяем что обращение записано
        status = cli.fallback_state.get_status()
        assert status['request_count'] == 1

    @patch('src.cursor_cli_interface.CursorCLIInterface._execute_with_specific_model')
    def test_cursor_cli_billing_error_activation(self, mock_execute):
        """Тест активации fallback режима при billing error"""
        cli = CursorCLIInterface()
        cli.fallback_state = FallbackStateManager(self.state_file)

        # Мокаем billing error
        error_result = CursorCLIResult(
            success=False,
            stdout="",
            stderr="You've hit your usage limit You've saved $245 on API model usage this month with Pro.",
            return_code=1,
            cli_available=True
        )

        # Сначала возвращаем ошибку (billing), потом успех
        mock_execute.side_effect = [error_result, error_result]  # Оба раза ошибка для тестирования

        # Выполняем команду (должна активировать fallback)
        result = cli.execute_with_fallback("test prompt")

        # Проверяем что fallback активирован
        assert cli.fallback_state.should_use_fallback()

        # Проверяем статус
        status = cli.fallback_state.get_status()
        assert status['fallback_active'] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])