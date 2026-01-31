"""
Тесты безопасности для MCP сервера.

Проверяет:
- Аутентификацию пользователей
- Авторизацию доступа
- Валидацию входных данных
- Защиту от распространенных атак
"""

import pytest
from pathlib import Path
import sys

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp.auth import AuthManager
from src.security_utils import PasswordUtils, SecurityValidator
from src.config_loader import ConfigLoader


class TestPasswordSecurity:
    """Тесты безопасности паролей."""

    def test_password_hashing(self):
        """Тест хэширования паролей."""
        password = "test_password_123"
        salt = PasswordUtils.generate_salt()

        hashed = PasswordUtils.hash_password(password, salt)
        assert hashed != password
        assert len(hashed) == 64  # SHA-256 hex length

        # Проверка верификации
        assert PasswordUtils.verify_password(password, hashed, salt)
        assert not PasswordUtils.verify_password("wrong_password", hashed, salt)

    def test_password_strength_validation(self):
        """Тест валидации сложности паролей."""
        # Слабые пароли
        weak_passwords = [
            "short",
            "nouppercaseordigits",
            "NOLOWERCASEORDIGITS",
            "NoDigits",
            "NoSpecial123"
        ]

        for password in weak_passwords:
            is_valid, message = PasswordUtils.validate_password_strength(password)
            assert not is_valid, f"Пароль '{password}' должен быть признан слабым"

        # Сильный пароль
        strong_password = "StrongPass123!"
        is_valid, message = PasswordUtils.validate_password_strength(strong_password)
        assert is_valid, "Пароль должен быть признан сильным"

    def test_generate_secure_password(self):
        """Тест генерации безопасных паролей."""
        password = PasswordUtils.generate_secure_password()
        assert len(password) == 12

        is_valid, message = PasswordUtils.validate_password_strength(password)
        assert is_valid, "Сгенерированный пароль должен быть сильным"


class TestInputValidation:
    """Тесты валидации входных данных."""

    def test_input_validation(self):
        """Тест валидации пользовательского ввода."""
        # Допустимые входные данные
        valid_inputs = [
            "normal_username",
            "user123",
            "test@example.com"
        ]

        for input_str in valid_inputs:
            assert SecurityValidator.validate_input(input_str), f"Ввод '{input_str}' должен быть допустимым"

        # Недопустимые входные данные
        invalid_inputs = [
            "<script>alert('xss')</script>",
            "user;name",
            "user\nline",
            "user\r\nline",
            "user\\backslash"
        ]

        for input_str in invalid_inputs:
            assert not SecurityValidator.validate_input(input_str), f"Ввод '{input_str}' должен быть недопустимым"

    def test_filename_sanitization(self):
        """Тест санитизации имен файлов."""
        dangerous_names = [
            "../../../etc/passwd",
            "file<>name.txt",
            "file:name.txt",
            "file\"name.txt",
            "file|name.txt",
            "file?name.txt",
            "file*name.txt"
        ]

        for name in dangerous_names:
            sanitized = SecurityValidator.sanitize_filename(name)
            assert "<" not in sanitized
            assert ">" not in sanitized
            assert ":" not in sanitized
            assert "|" not in sanitized
            assert "?" not in sanitized
            assert "*" not in sanitized
            assert len(sanitized) <= 255

    def test_path_traversal_protection(self):
        """Тест защиты от path traversal атак."""
        base_path = "/var/www"

        # Допустимые пути
        valid_paths = [
            "file.txt",
            "subdir/file.txt",
            "subdir/nested/file.txt"
        ]

        for path in valid_paths:
            assert SecurityValidator.validate_path_traversal(path, base_path), f"Путь '{path}' должен быть допустимым"

        # Недопустимые пути (path traversal)
        invalid_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/passwd"
        ]

        for path in invalid_paths:
            assert not SecurityValidator.validate_path_traversal(path, base_path), f"Путь '{path}' должен быть недопустимым"


class TestAuthManager:
    """Тесты менеджера аутентификации."""

    @pytest.fixture
    def config_loader(self):
        """Фикстура для загрузчика конфигурации."""
        return ConfigLoader()

    @pytest.fixture
    def auth_manager(self, config_loader):
        """Фикстура для менеджера аутентификации."""
        return AuthManager(config_loader)

    def test_user_authentication(self, auth_manager):
        """Тест аутентификации пользователей."""
        # Тест с правильными учетными данными
        user = auth_manager.authenticate_user("admin", "admin123")
        assert user is not None
        assert user.username == "admin"
        assert user.role == "admin"

        # Тест с неправильными учетными данными
        user = auth_manager.authenticate_user("admin", "wrong_password")
        assert user is None

        # Тест с несуществующим пользователем
        user = auth_manager.authenticate_user("nonexistent", "password")
        assert user is None

    def test_token_generation_and_validation(self, auth_manager):
        """Тест генерации и валидации токенов."""
        # Аутентификация и генерация токена
        user = auth_manager.authenticate_user("admin", "admin123")
        assert user is not None

        token = auth_manager.generate_token(user)
        assert token is not None
        assert len(token) > 0

        # Валидация токена
        validated_user = auth_manager.validate_token(token)
        assert validated_user is not None
        assert validated_user.username == user.username

        # Тест с недействительным токеном
        invalid_user = auth_manager.validate_token("invalid_token")
        assert invalid_user is None

    def test_permission_checking(self, auth_manager):
        """Тест проверки разрешений."""
        user = auth_manager.authenticate_user("viewer", "view123")
        assert user is not None

        # Пользователь viewer должен иметь разрешение read
        assert auth_manager.check_permission(user, "read")

        # Пользователь viewer НЕ должен иметь разрешение write
        assert not auth_manager.check_permission(user, "write")

        # Пользователь viewer НЕ должен иметь разрешение admin
        assert not auth_manager.check_permission(user, "admin")

    def test_input_validation_in_auth(self, auth_manager):
        """Тест валидации входных данных в аутентификации."""
        # Тест с опасными символами в имени пользователя
        user = auth_manager.authenticate_user("<script>", "password")
        assert user is None

        # Тест с опасными символами в пароле
        user = auth_manager.authenticate_user("admin", "<script>")
        assert user is None

        # Тест со слишком длинными входными данными
        long_input = "a" * 1000
        user = auth_manager.authenticate_user(long_input, "password")
        assert user is None


def run_tests():
    """Запуск всех тестов безопасности."""
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ БЕЗОПАСНОСТИ MCP СЕРВЕРА")
    print("="*70 + "\n")

    # Запускаем pytest
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()