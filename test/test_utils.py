"""
Вспомогательные функции для загрузки настроек в тестах
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(override=True)


def get_test_config_values() -> Dict[str, Any]:
    """
    Получить настройки для тестов из конфигурации

    Returns:
        Словарь с настройками для тестов
    """
    # Загружаем PROJECT_DIR из переменных окружения
    project_dir = os.getenv("PROJECT_DIR")
    if not project_dir:
        # По умолчанию используем текущую директорию для тестов
        project_dir = str(Path(__file__).parent.parent)

    # Настройки CLI
    cli_path = os.getenv("CURSOR_CLI_PATH", "docker-compose-agent")
    container_name = os.getenv("CURSOR_CONTAINER_NAME", "cursor-agent")

    # Настройки агента
    agent_role = os.getenv("AGENT_ROLE", "Test Agent")

    return {
        "project_dir": project_dir,
        "cli_path": cli_path,
        "container_name": container_name,
        "agent_role": agent_role,
        "timeout": int(os.getenv("CLI_TIMEOUT", "1000")),
    }


def get_project_dir() -> str:
    """Получить директорию проекта из настроек"""
    config = get_test_config_values()
    return config["project_dir"]


def get_cli_path() -> str:
    """Получить путь к CLI из настроек"""
    config = get_test_config_values()
    return config["cli_path"]


def get_container_name() -> str:
    """Получить имя контейнера из настроек"""
    config = get_test_config_values()
    return config["container_name"]


def get_agent_role() -> str:
    """Получить роль агента из настроек"""
    config = get_test_config_values()
    return config["agent_role"]


def get_cli_timeout() -> int:
    """Получить таймаут CLI из настроек"""
    config = get_test_config_values()
    return config["timeout"]