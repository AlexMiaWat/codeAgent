"""
Authentication Manager для MCP сервера.

Реализует базовую аутентификацию с JWT токенами.
"""

import jwt
import logging
import secrets
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import ConfigLoader
from security_utils import PasswordUtils, SecurityValidator


@dataclass
class User:
    """Пользователь системы."""
    id: str
    username: str
    role: str  # admin, developer, viewer
    permissions: list[str]


@dataclass
class AuthToken:
    """JWT токен."""
    token: str
    user_id: str
    expires_at: datetime
    issued_at: datetime


class AuthManager:
    """
    Менеджер аутентификации для MCP сервера.

    Поддерживает JWT токены и ролевая модель доступа.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.logger = logging.getLogger(__name__)

        # Настройки JWT
        self.secret_key = self._get_secret_key()
        self.algorithm = "HS256"
        self.token_expire_hours = 24

        # Пользователи (в продакшене хранить в БД)
        self.users: Dict[str, User] = {}
        self.tokens: Dict[str, AuthToken] = {}

        # Инициализация пользователей
        self._initialize_users()

    def _get_secret_key(self) -> str:
        """Получение секретного ключа для JWT."""
        # В продакшене использовать environment variable
        return secrets.token_hex(32)

    def _initialize_users(self):
        """Инициализация пользователей системы."""
        try:
            import yaml
            config_path = Path("config/users.yaml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    users_config = yaml.safe_load(f)

                if users_config and "users" in users_config:
                    for user_id, user_data in users_config["users"].items():
                        if user_data.get("active", True):
                            user = User(
                                id=user_id,
                                username=user_id,
                                role=user_data["role"],
                                permissions=user_data["permissions"]
                            )
                            self.users[user_id] = user
                self.logger.info(f"Loaded {len(self.users)} users from config")
            else:
                self.logger.warning("users.yaml not found, using empty user list")
        except Exception as e:
            self.logger.error(f"Error loading users config: {e}")
            self.users = {}

    def _hash_password(self, password: str, salt: str) -> str:
        """Хэширование пароля с солью."""
        return PasswordUtils.hash_password(password, salt)

    def _verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Проверка пароля."""
        return PasswordUtils.verify_password(password, hashed_password, salt)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя.

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            Пользователь или None если аутентификация не удалась
        """
        # Валидация входных данных
        if not SecurityValidator.validate_input(username, 50) or not SecurityValidator.validate_input(password, 100):
            self.logger.warning("Invalid input format for authentication")
            return None

        if username not in self.users:
            self.logger.warning(f"User not found: {username}")
            return None

        user = self.users[username]
        user_config = self._get_user_config(username)

        if not user_config:
            self.logger.warning(f"No config found for user: {username}")
            return None

        stored_hash = user_config.get("password_hash")
        salt = user_config.get("salt")

        if not stored_hash or not salt:
            self.logger.warning(f"Invalid password config for user: {username}")
            return None

        if self._verify_password(password, stored_hash, salt):
            self.logger.info(f"User {username} authenticated successfully")
            return user

        self.logger.warning(f"Failed authentication attempt for user: {username}")
        return None

    def _get_user_config(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение конфигурации пользователя."""
        try:
            # Используем абсолютный путь относительно корня проекта
            project_root = Path.cwd()
            config_path = project_root / "config" / "users.yaml"

            if not config_path.exists():
                self.logger.warning(f"Users config file not found: {config_path}")
                return None

            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                users_config = yaml.safe_load(f) or {}

            users_section = users_config.get("users", {})
            return users_section.get(username)
        except Exception as e:
            self.logger.error(f"Error loading user config: {e}")
            return None

    def generate_token(self, user: User) -> str:
        """
        Генерация JWT токена для пользователя.

        Args:
            user: Пользователь

        Returns:
            JWT токен
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.token_expire_hours)

        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp())
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Сохранение токена
        auth_token = AuthToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at,
            issued_at=now
        )
        self.tokens[token] = auth_token

        self.logger.info(f"Generated token for user {user.username}")
        return token

    def validate_token(self, token: str) -> Optional[User]:
        """
        Валидация JWT токена.

        Args:
            token: JWT токен

        Returns:
            Пользователь или None если токен недействителен
        """
        try:
            # Декодирование токена
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Проверка срока действия
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                self.logger.warning("Token expired")
                return None

            # Получение пользователя
            user_id = payload.get("sub")
            if user_id not in self.users:
                self.logger.warning(f"User {user_id} not found")
                return None

            user = self.users[user_id]

            # Проверка что токен активен
            if token not in self.tokens:
                self.logger.warning("Token not found in active tokens")
                return None

            self.logger.debug(f"Token validated for user {user.username}")
            return user

        except jwt.ExpiredSignatureError:
            self.logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error validating token: {e}")
            return None

    def revoke_token(self, token: str) -> bool:
        """
        Отзыв токена.

        Args:
            token: JWT токен

        Returns:
            True если токен был отозван
        """
        if token in self.tokens:
            del self.tokens[token]
            self.logger.info("Token revoked")
            return True

        return False

    def get_user_permissions(self, user: User) -> list[str]:
        """
        Получение разрешений пользователя.

        Args:
            user: Пользователь

        Returns:
            Список разрешений
        """
        return user.permissions

    def check_permission(self, user: User, permission: str) -> bool:
        """
        Проверка разрешения пользователя.

        Args:
            user: Пользователь
            permission: Разрешение для проверки

        Returns:
            True если разрешение есть
        """
        return permission in user.permissions

    def get_user_by_token(self, token: str) -> Optional[User]:
        """
        Получение пользователя по токену.

        Args:
            token: JWT токен

        Returns:
            Пользователь или None
        """
        return self.validate_token(token)

    def cleanup_expired_tokens(self):
        """Очистка истекших токенов."""
        now = datetime.utcnow()
        expired_tokens = [
            token for token, auth_token in self.tokens.items()
            if auth_token.expires_at < now
        ]

        for token in expired_tokens:
            del self.tokens[token]

        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")

    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение активных сессий.

        Returns:
            Информация об активных сессиях
        """
        sessions = {}
        now = datetime.utcnow()

        for token, auth_token in self.tokens.items():
            if auth_token.expires_at > now:
                user = self.users.get(auth_token.user_id)
                if user:
                    sessions[token] = {
                        "user_id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "issued_at": auth_token.issued_at.isoformat(),
                        "expires_at": auth_token.expires_at.isoformat(),
                    }

        return sessions

    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Вход пользователя в систему.

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            Информация о сессии или None
        """
        user = self.authenticate_user(username, password)
        if not user:
            return None

        token = self.generate_token(user)

        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "permissions": user.permissions
            },
            "expires_in": self.token_expire_hours * 3600  # секунды
        }

    def logout(self, token: str) -> bool:
        """
        Выход пользователя из системы.

        Args:
            token: JWT токен

        Returns:
            True если выход успешен
        """
        return self.revoke_token(token)