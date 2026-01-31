#!/usr/bin/env python3
"""
Скрипт для генерации хэшированных паролей пользователей.
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from security_utils import PasswordUtils

def generate_user_hashes():
    """Генерация хэшей паролей для пользователей."""
    users = ["admin", "developer", "viewer"]

    print("Генерация безопасных хэшированных паролей:")
    print("=" * 60)
    print("⚠️  ВНИМАНИЕ: Сохраните сгенерированные пароли в надежном месте!")
    print("   Они не могут быть восстановлены из хэшей.")
    print("=" * 60)

    generated_users = {}

    for username in users:
        # Генерируем безопасный пароль
        password = PasswordUtils.generate_secure_password(16)
        salt = PasswordUtils.generate_salt()
        hashed = PasswordUtils.hash_password(password, salt)

        generated_users[username] = {
            "password": password,
            "salt": salt,
            "hash": hashed
        }

        print(f"\n👤 Пользователь: {username}")
        print(f"🔑 Пароль: {password}")
        print(f"🧂 Соль: {salt}")
        print(f"🔒 Хэш: {hashed}")

    print("\n" + "=" * 60)
    print("📝 Обновите config/users.yaml с этими значениями")
    print("💾 Сохраните пароли в менеджере паролей!")

    return generated_users

def update_users_config(generated_users):
    """Обновление config/users.yaml с новыми хэшами."""
    import yaml
    from pathlib import Path

    config_path = Path("config/users.yaml")

    # Создаем структуру пользователей для YAML
    users_config = {"users": {}}

    for username, data in generated_users.items():
        role = username if username in ["admin", "developer", "viewer"] else "viewer"
        permissions = {
            "admin": ["read", "write", "delete", "admin"],
            "developer": ["read", "write"],
            "viewer": ["read"]
        }.get(role, ["read"])

        users_config["users"][username] = {
            "password_hash": data["hash"],
            "salt": data["salt"],
            "role": role,
            "permissions": permissions,
            "active": True
        }

    # Записываем в файл
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(users_config, f, default_flow_style=False, allow_unicode=True, indent=2)

    print(f"✅ Конфигурация пользователей обновлена: {config_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Генерация безопасных паролей для пользователей MCP сервера")
    parser.add_argument("--update-config", action="store_true",
                       help="Автоматически обновить config/users.yaml")

    args = parser.parse_args()

    generated_users = generate_user_hashes()

    if args.update_config:
        update_users_config(generated_users)