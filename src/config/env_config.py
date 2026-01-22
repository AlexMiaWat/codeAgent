"""
Модуль управления переменными окружения для Code Agent

Предоставляет централизованный интерфейс для работы с переменными окружения,
их валидации и получения значений с дефолтными значениями.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging
from dataclasses import dataclass, field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv(override=True)


@dataclass
class EnvConfig:
    """
    Класс для управления переменными окружения Code Agent

    Предоставляет типизированный доступ к переменным окружения
    с валидацией и значениями по умолчанию.
    """

    # Обязательные переменные
    project_dir: Path

    # API ключи (опциональные)
    openrouter_api_key: Optional[str] = None
    cursor_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Smart Agent настройки
    smart_agent_enabled: bool = False
    smart_agent_experience_dir: str = "smart_experience"
    smart_agent_project_dir: Optional[Path] = None
    smart_agent_max_experience_tasks: int = 200
    smart_agent_max_iter: int = 25
    smart_agent_memory: int = 100
    smart_agent_verbose: bool = True

    # LearningTool настройки
    learning_tool_enable_indexing: bool = True
    learning_tool_cache_size: int = 1000
    learning_tool_cache_ttl: int = 3600

    # ContextAnalyzerTool настройки
    context_analyzer_deep_analysis: bool = True
    context_analyzer_supported_languages: List[str] = field(default_factory=lambda: ['python', 'javascript', 'typescript', 'java', 'cpp'])
    context_analyzer_max_depth: int = 5

    # Дополнительные настройки
    log_level: str = "INFO"
    max_file_size: int = 1000000

    @classmethod
    def load(cls) -> 'EnvConfig':
        """
        Загрузка конфигурации из переменных окружения

        Returns:
            EnvConfig: Экземпляр с загруженными значениями

        Raises:
            ValueError: Если обязательные переменные не установлены
        """
        # Валидация обязательных переменных
        project_dir_str = os.getenv('PROJECT_DIR')
        if not project_dir_str:
            raise ValueError(
                "Обязательная переменная окружения PROJECT_DIR не установлена.\n"
                "Установите PROJECT_DIR в .env файле или переменных окружения.\n"
                "Примеры:\n"
                "  Windows: PROJECT_DIR=D:\\Space\\life\n"
                "  Linux/Mac: PROJECT_DIR=/home/user/projects/myproject"
            )

        project_dir = Path(project_dir_str).expanduser().resolve()
        if not project_dir.exists():
            logger.warning(f"Директория проекта не существует: {project_dir}")

        # Загрузка опциональных переменных
        config = cls(project_dir=project_dir)

        # API ключи
        config.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        config.cursor_api_key = os.getenv('CURSOR_API_KEY')
        config.openai_api_key = os.getenv('OPENAI_API_KEY')
        config.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        # Smart Agent настройки
        config.smart_agent_enabled = cls._parse_bool(os.getenv('SMART_AGENT_ENABLED', 'false'))
        config.smart_agent_experience_dir = os.getenv('SMART_AGENT_EXPERIENCE_DIR', 'smart_experience')

        smart_project_dir = os.getenv('SMART_AGENT_PROJECT_DIR')
        if smart_project_dir:
            config.smart_agent_project_dir = Path(smart_project_dir).expanduser().resolve()

        try:
            config.smart_agent_max_experience_tasks = int(os.getenv('SMART_AGENT_MAX_EXPERIENCE_TASKS', '200'))
        except (ValueError, TypeError):
            config.smart_agent_max_experience_tasks = 200
        try:
            config.smart_agent_max_iter = int(os.getenv('SMART_AGENT_MAX_ITER', '25'))
        except (ValueError, TypeError):
            config.smart_agent_max_iter = 25
        try:
            config.smart_agent_memory = int(os.getenv('SMART_AGENT_MEMORY', '100'))
        except (ValueError, TypeError):
            config.smart_agent_memory = 100
        config.smart_agent_verbose = cls._parse_bool(os.getenv('SMART_AGENT_VERBOSE', 'true'))

        # LearningTool настройки
        config.learning_tool_enable_indexing = cls._parse_bool(os.getenv('LEARNING_TOOL_ENABLE_INDEXING', 'true'))
        try:
            config.learning_tool_cache_size = int(os.getenv('LEARNING_TOOL_CACHE_SIZE', '1000'))
        except (ValueError, TypeError):
            config.learning_tool_cache_size = 1000
        try:
            config.learning_tool_cache_ttl = int(os.getenv('LEARNING_TOOL_CACHE_TTL', '3600'))
        except (ValueError, TypeError):
            config.learning_tool_cache_ttl = 3600

        # ContextAnalyzerTool настройки
        config.context_analyzer_deep_analysis = cls._parse_bool(os.getenv('CONTEXT_ANALYZER_DEEP_ANALYSIS', 'true'))

        languages_str = os.getenv('CONTEXT_ANALYZER_SUPPORTED_LANGUAGES', 'python,javascript,typescript,java,cpp')
        config.context_analyzer_supported_languages = [lang.strip() for lang in languages_str.split(',') if lang.strip()]

        try:
            config.context_analyzer_max_depth = int(os.getenv('CONTEXT_ANALYZER_MAX_DEPTH', '5'))
        except (ValueError, TypeError):
            config.context_analyzer_max_depth = 5

        # Дополнительные настройки
        config.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        try:
            config.max_file_size = int(os.getenv('MAX_FILE_SIZE', '1000000'))
        except (ValueError, TypeError):
            config.max_file_size = 1000000

        return config

    @staticmethod
    def _parse_bool(value: Optional[str]) -> bool:
        """Парсинг строкового значения в bool"""
        if value is None:
            return False
        return value.lower() in ('true', '1', 'yes', 'on')

    @staticmethod
    def _parse_int(value: str) -> Optional[int]:
        """Парсинг строкового значения в int с обработкой ошибок"""
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Невозможно преобразовать '{value}' в целое число, используется значение по умолчанию")
            return None

    def get_api_keys(self) -> Dict[str, Optional[str]]:
        """
        Получение всех доступных API ключей

        Returns:
            Dict[str, Optional[str]]: Словарь с API ключами
        """
        return {
            'openrouter': self.openrouter_api_key,
            'cursor': self.cursor_api_key,
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
        }

    def has_any_api_key(self) -> bool:
        """
        Проверка наличия хотя бы одного API ключа для работы с LLM

        Returns:
            bool: True если есть хотя бы один API ключ
        """
        return any([
            self.openrouter_api_key,
            self.cursor_api_key,
            self.openai_api_key,
            self.anthropic_api_key,
        ])

    def get_smart_agent_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации Smart Agent в формате словаря

        Returns:
            Dict[str, Any]: Конфигурация Smart Agent
        """
        return {
            'enabled': self.smart_agent_enabled,
            'experience_dir': self.smart_agent_experience_dir,
            'project_dir': str(self.smart_agent_project_dir) if self.smart_agent_project_dir else None,
            'max_experience_tasks': self.smart_agent_max_experience_tasks,
            'max_iter': self.smart_agent_max_iter,
            'memory': self.smart_agent_memory,
            'verbose': self.smart_agent_verbose,
        }

    def validate(self) -> List[str]:
        """
        Валидация конфигурации

        Returns:
            List[str]: Список ошибок валидации (пустой если ошибок нет)
        """
        errors = []

        # Проверка обязательных переменных
        if not self.project_dir.exists():
            errors.append(f"Директория проекта не существует: {self.project_dir}")

        # Проверка API ключей
        if not self.has_any_api_key():
            logger.warning("Не установлены API ключи. Работа с LLM будет недоступна.")

        # Проверка Smart Agent настроек
        if self.smart_agent_enabled:
            if self.smart_agent_max_experience_tasks < 10:
                errors.append("smart_agent_max_experience_tasks должно быть >= 10")
            if self.smart_agent_max_iter < 1:
                errors.append("smart_agent_max_iter должно быть >= 1")
            if self.smart_agent_memory < 10:
                errors.append("smart_agent_memory должно быть >= 10")

        # Проверка LearningTool настроек
        if self.learning_tool_cache_size < 10:
            errors.append("learning_tool_cache_size должно быть >= 10")
        if self.learning_tool_cache_ttl < 60:
            errors.append("learning_tool_cache_ttl должно быть >= 60 секунд")

        # Проверка ContextAnalyzerTool настроек
        if self.context_analyzer_max_depth < 1:
            errors.append("context_analyzer_max_depth должно быть >= 1")
        if not self.context_analyzer_supported_languages:
            errors.append("context_analyzer_supported_languages не может быть пустым")

        # Проверка дополнительных настроек
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            errors.append(f"log_level должен быть одним из: {', '.join(valid_log_levels)}")

        if self.max_file_size < 1024:  # Минимум 1KB
            errors.append("max_file_size должно быть >= 1024 байт")

        return errors

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Получение строкового значения переменной окружения

        Args:
            key: Имя переменной окружения
            default: Значение по умолчанию

        Returns:
            str or None: Значение переменной окружения или default
        """
        return os.getenv(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Получение булевого значения переменной окружения

        Args:
            key: Имя переменной окружения
            default: Значение по умолчанию

        Returns:
            bool: Булево значение переменной окружения
        """
        value = os.getenv(key)
        if value is None:
            return default
        return self._parse_bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """
        Получение целочисленного значения переменной окружения

        Args:
            key: Имя переменной окружения
            default: Значение по умолчанию

        Returns:
            int: Целочисленное значение переменной окружения
        """
        value = os.getenv(key)
        if value is None:
            return default
        parsed = self._parse_int(value)
        return parsed if parsed is not None else default

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование конфигурации в словарь

        Returns:
            Dict[str, Any]: Конфигурация в виде словаря
        """
        return {
            'project_dir': str(self.project_dir),
            'openrouter_api_key': self.openrouter_api_key,
            'cursor_api_key': self.cursor_api_key,
            'openai_api_key': self.openai_api_key,
            'anthropic_api_key': self.anthropic_api_key,
            'smart_agent_enabled': self.smart_agent_enabled,
            'smart_agent_experience_dir': self.smart_agent_experience_dir,
            'smart_agent_project_dir': str(self.smart_agent_project_dir) if self.smart_agent_project_dir else None,
            'smart_agent_max_experience_tasks': self.smart_agent_max_experience_tasks,
            'smart_agent_max_iter': self.smart_agent_max_iter,
            'smart_agent_memory': self.smart_agent_memory,
            'smart_agent_verbose': self.smart_agent_verbose,
            'learning_tool_enable_indexing': self.learning_tool_enable_indexing,
            'learning_tool_cache_size': self.learning_tool_cache_size,
            'learning_tool_cache_ttl': self.learning_tool_cache_ttl,
            'context_analyzer_deep_analysis': self.context_analyzer_deep_analysis,
            'context_analyzer_supported_languages': self.context_analyzer_supported_languages,
            'context_analyzer_max_depth': self.context_analyzer_max_depth,
            'log_level': self.log_level,
            'max_file_size': self.max_file_size,
        }