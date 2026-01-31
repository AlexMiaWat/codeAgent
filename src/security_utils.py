"""
Security utilities для Code Agent.

Предоставляет функции для безопасной работы с паролями,
шифрованием и другими операциями безопасности.
"""

import hashlib
import secrets
import string
from typing import Tuple


class PasswordUtils:
    """Утилиты для работы с паролями."""

    @staticmethod
    def generate_salt(length: int = 16) -> str:
        """Генерация случайной соли."""
        return secrets.token_hex(length)

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """Хэширование пароля с солью."""
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Проверка пароля."""
        return PasswordUtils.hash_password(password, salt) == hashed_password

    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """Генерация безопасного пароля."""
        if length < 8:
            length = 8

        # Гарантируем наличие всех типов символов
        upper = secrets.choice(string.ascii_uppercase)
        lower = secrets.choice(string.ascii_lowercase)
        digit = secrets.choice(string.digits)
        special = secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")

        # Заполняем остаток
        remaining_chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        remaining_length = length - 4

        remaining = ''.join(secrets.choice(remaining_chars) for _ in range(remaining_length))

        # Перемешиваем
        password = upper + lower + digit + special + remaining
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)

        return ''.join(password_list)

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Проверка сложности пароля.

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        if len(password) < 8:
            return False, "Пароль должен содержать минимум 8 символов"

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not has_upper:
            return False, "Пароль должен содержать заглавные буквы"
        if not has_lower:
            return False, "Пароль должен содержать строчные буквы"
        if not has_digit:
            return False, "Пароль должен содержать цифры"
        if not has_special:
            return False, "Пароль должен содержать специальные символы"

        return True, "Пароль соответствует требованиям безопасности"


class SecurityValidator:
    """Валидатор безопасности."""

    @staticmethod
    def validate_input(input_str: str, max_length: int = 1000) -> bool:
        """Валидация пользовательского ввода."""
        if not input_str or len(input_str) > max_length:
            return False

        # Проверка на опасные символы
        dangerous_chars = ['<', '>', '"', "'", ';', '\\', '\n', '\r']
        return not any(char in input_str for char in dangerous_chars)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Санитизация имени файла."""
        import re
        # Удаляем опасные символы
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        return safe_name[:255]  # Ограничение длины

    @staticmethod
    def validate_path_traversal(path: str, base_path: str) -> bool:
        """Проверка на path traversal атаки."""
        from pathlib import Path, PurePath
        try:
            # Проверяем на явные попытки path traversal
            dangerous_patterns = ['..', '\\', '//', '\x00']
            if any(pattern in path for pattern in dangerous_patterns):
                # Нормализуем путь и проверяем
                normalized_path = PurePath(path).resolve()
                base_resolved = Path(base_path).resolve()
                full_path = (base_resolved / normalized_path).resolve()
                return str(full_path).startswith(str(base_resolved))
            else:
                # Безопасный путь
                return True
        except Exception:
            return False