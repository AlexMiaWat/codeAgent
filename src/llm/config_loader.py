"""
ConfigLoader - загрузчик конфигурации

Ответственность:
- Загрузка конфигурации из YAML файлов
- Подстановка переменных окружения
- Валидация конфигурации
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict
from .types import IConfigLoader

logger = logging.getLogger(__name__)


class ConfigLoader(IConfigLoader):
    """
    Загрузчик конфигурации - управляет загрузкой и обработкой конфигурационных файлов

    Предоставляет:
    - Загрузку YAML конфигурации
    - Подстановку переменных окружения
    - Валидацию структуры конфигурации
    """

    def __init__(self):
        """Инициализация загрузчика конфигурации"""
        pass

    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Загрузить конфигурацию из файла

        Args:
            config_path: Путь к конфигурационному файлу

        Returns:
            Загруженная конфигурация

        Raises:
            FileNotFoundError: Если файл не найден
            yaml.YAMLError: Если файл содержит некорректный YAML
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML config {config_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load config {config_path}: {e}")
            raise

        logger.info(f"Loaded config from {config_path}")

        # Подстановка переменных окружения
        config = self.substitute_env_vars(config)

        return config

    def substitute_env_vars(self, obj: Any) -> Any:
        """
        Рекурсивная подстановка переменных окружения в объекте

        Поддерживает формат: ${VAR_NAME} или ${VAR_NAME:default_value}

        Args:
            obj: Объект для обработки (dict, list, str, etc.)

        Returns:
            Объект с подставленными переменными окружения
        """
        if isinstance(obj, dict):
            return {k: self.substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            return self._substitute_single_env_var(obj)
        else:
            return obj

    def _substitute_single_env_var(self, var_expr: str) -> str:
        """
        Подставить одну переменную окружения

        Args:
            var_expr: Выражение вида ${VAR_NAME} или ${VAR_NAME:default}

        Returns:
            Значение переменной окружения или default

        Raises:
            ValueError: Если переменная не найдена и нет default значения
        """
        # Удаляем ${ и }
        content = var_expr[2:-1]

        # Проверяем на наличие default значения
        if ':' in content:
            var_name, default_value = content.split(':', 1)
        else:
            var_name = content
            default_value = None

        # Получаем значение переменной
        env_value = os.getenv(var_name.strip())

        if env_value is not None:
            return env_value
        elif default_value is not None:
            logger.debug(f"Using default value for env var {var_name}: {default_value}")
            return default_value.strip()
        else:
            raise ValueError(f"Environment variable not found: {var_name}")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Проверить валидность конфигурации

        Args:
            config: Конфигурация для проверки

        Returns:
            True если конфигурация валидна
        """
        try:
            # Проверяем наличие обязательных секций
            if 'llm' not in config:
                logger.error("Missing 'llm' section in config")
                return False

            llm_config = config['llm']

            # Проверяем наличие провайдера по умолчанию
            if 'default_provider' not in llm_config:
                logger.error("Missing 'default_provider' in llm config")
                return False

            default_provider = llm_config['default_provider']

            # Проверяем наличие конфигурации провайдера
            if 'providers' not in config:
                logger.error("Missing 'providers' section in config")
                return False

            if default_provider not in config['providers']:
                logger.error(f"Default provider '{default_provider}' not found in providers")
                return False

            provider_config = config['providers'][default_provider]

            # Проверяем наличие обязательных полей провайдера
            required_fields = ['base_url', 'models']
            for field in required_fields:
                if field not in provider_config:
                    logger.error(f"Missing required field '{field}' in provider '{default_provider}'")
                    return False

            logger.info("Config validation passed")
            return True

        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            return False