"""
Модуль загрузки конфигурации
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Импорт валидатора (после определения logger, чтобы избежать циклических импортов)
try:
    from .config_validator import ConfigValidator, ConfigValidationError
except ImportError:
    # Для случаев, когда модуль импортируется до полной инициализации
    ConfigValidator = None
    ConfigValidationError = Exception


class ConfigLoader:
    """Загрузчик конфигурации из YAML и переменных окружения"""
    
    def __init__(self, config_path: str = "config/config.yaml", allowed_base_dirs: Optional[List[Path]] = None):
        """
        Инициализация загрузчика конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации
            allowed_base_dirs: Список разрешенных базовых директорий для валидации путей
                              Если None, используется директория codeAgent
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        # Определяем разрешенные базовые директории
        if allowed_base_dirs is None:
            # По умолчанию разрешаем только директорию codeAgent
            codeagent_dir = Path(__file__).parent.parent.absolute()
            self.allowed_base_dirs: List[Path] = [codeagent_dir]
        else:
            self.allowed_base_dirs = [Path(d).absolute() for d in allowed_base_dirs]
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Загрузка конфигурации из YAML файла"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            raw_config: Dict[str, Any] = yaml.safe_load(f) or {}
        
        # Подстановка переменных окружения
        self.config = self._substitute_env_vars(raw_config)
        
        # Валидация конфигурации
        if ConfigValidator is not None:
            try:
                validator = ConfigValidator(self.config)
                validator.validate()
            except ConfigValidationError as e:
                error_msg = f"Ошибка валидации конфигурации:\n\n{str(e)}"
                error_msg += "\n\n" + "=" * 70
                error_msg += "\n\nДля решения проблем:"
                error_msg += "\n  1. Проверьте структуру config.yaml"
                error_msg += "\n  2. Убедитесь, что все обязательные поля присутствуют"
                error_msg += "\n  3. Проверьте типы и значения полей"
                error_msg += "\n  4. См. документацию: docs/guides/setup.md"

                logger.error(error_msg)
                raise ValueError(error_msg) from e

        # Дополнительная валидация LLM конфигурации
        self._validate_llm_config()
    
    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Рекурсивная подстановка переменных окружения в конфигурации
        
        Формат: ${VAR_NAME} или ${VAR_NAME:default_value}
        """
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            # Извлекаем имя переменной и значение по умолчанию
            var_expr = obj[2:-1]  # Убираем ${ и }
            if ':' in var_expr:
                var_name, default = var_expr.split(':', 1)
                return os.getenv(var_name.strip(), default.strip())
            else:
                env_value = os.getenv(var_expr.strip())
                if env_value is None:
                    raise ValueError(f"Переменная окружения не найдена: {var_expr}")
                return env_value
        return obj
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения конфигурации по ключу (с поддержкой вложенных ключей)
        
        Args:
            key: Ключ конфигурации (может быть "section.key" для вложенных значений)
            default: Значение по умолчанию
        
        Returns:
            Значение конфигурации или default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def _validate_path(self, path: Path, path_name: str = "path") -> Path:
        """
        Валидация и нормализация пути
        
        Проверяет:
        - Отсутствие path traversal атак (..)
        - Что путь находится в разрешенных директориях (для абсолютных путей)
        - Нормализует путь
        
        Args:
            path: Путь для валидации
            path_name: Имя пути для сообщений об ошибках
        
        Returns:
            Валидированный и нормализованный путь
        
        Raises:
            ValueError: Если путь невалиден или находится вне разрешенных директорий
        """
        # Нормализация пути
        try:
            normalized = path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Ошибка нормализации пути {path_name}: {path} - {e}")
        
        # Проверка на path traversal в исходном пути
        path_str = str(path)
        if '..' in path_str:
            # Разрешаем .. только если путь нормализован и находится в разрешенных директориях
            # Но для безопасности лучше запретить явное использование ..
            if path_str.count('..') > 3:  # Слишком много уровней вверх
                raise ValueError(
                    f"Путь {path_name} содержит подозрительное количество '..': {path}. "
                    f"Path traversal атаки запрещены."
                )
        
        # Для абсолютных путей проверяем, что они в разрешенных директориях
        # Но для project_dir разрешаем любой абсолютный путь (он задается пользователем)
        # Валидация project_dir происходит отдельно в get_project_dir()
        # Здесь мы только проверяем относительные пути внутри project_dir
        
        return normalized
    
    def get_project_dir(self) -> Path:
        """
        Получение базовой директории проекта
        
        Returns:
            Path к директории проекта
        """
        project_dir = self.get('project.base_dir')
        if project_dir is None:
            raise ValueError("project.base_dir не указан в конфигурации")
        
        project_path = Path(project_dir)
        
        # Проверка на path traversal в исходном пути
        project_dir_str = str(project_dir)
        if '..' in project_dir_str and project_dir_str.count('..') > 3:
            raise ValueError(
                f"Путь проекта содержит подозрительное количество '..': {project_dir}. "
                f"Path traversal атаки запрещены."
            )
        
        # Нормализация пути
        try:
            normalized_path = project_path.resolve()
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Ошибка нормализации пути проекта: {project_path} - {e}")
        
        if not normalized_path.exists():
            raise FileNotFoundError(f"Директория проекта не найдена: {normalized_path}")
        
        if not normalized_path.is_dir():
            raise ValueError(f"Путь проекта не является директорией: {normalized_path}")
        
        return normalized_path
    
    def get_docs_dir(self) -> Path:
        """
        Получение пути к директории документации
        
        Returns:
            Path к директории docs
        
        Raises:
            ValueError: Если путь невалиден
        """
        project_dir = self.get_project_dir()
        docs_dir_name = self.get('project.docs_dir', 'docs')
        
        # Проверка на path traversal в имени директории
        if '..' in str(docs_dir_name):
            raise ValueError(
                f"Имя директории документации содержит '..': {docs_dir_name}. "
                f"Path traversal атаки запрещены."
            )
        
        docs_path = project_dir / docs_dir_name
        
        # Валидация пути (относительно project_dir)
        try:
            # Для относительных путей проверяем, что они остаются внутри project_dir
            validated_path = self._validate_path(docs_path, "project.docs_dir")
            # Убеждаемся, что путь все еще внутри project_dir
            validated_path.relative_to(project_dir)
        except ValueError as e:
            logger.error(f"Ошибка валидации пути документации: {e}")
            raise
        
        return validated_path

    def _validate_llm_config(self) -> None:
        """
        Валидация LLM конфигурации

        Проверяет допустимые значения для cli_interface и других LLM настроек
        """
        llm_config = self.config.get('llm', {})

        # Валидация cli_interface
        cli_interface = llm_config.get('cli_interface', 'cursor').lower()
        valid_interfaces = ['cursor', 'gemini']

        if cli_interface not in valid_interfaces:
            raise ValueError(
                f"Недопустимое значение cli_interface: '{cli_interface}'. "
                f"Допустимые значения: {', '.join(valid_interfaces)}\n"
                f"Проверьте настройку в config/llm_settings.yaml"
            )

        # Валидация timeout
        timeout = llm_config.get('timeout', 200)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(f"Недопустимое значение timeout: {timeout}. Должно быть положительным числом.")

        # Валидация retry_attempts
        retry_attempts = llm_config.get('retry_attempts', 1)
        if not isinstance(retry_attempts, int) or retry_attempts < 0:
            raise ValueError(f"Недопустимое значение retry_attempts: {retry_attempts}. Должно быть неотрицательным целым числом.")

        logger.debug(f"LLM конфигурация валидирована: cli_interface={cli_interface}, timeout={timeout}, retry_attempts={retry_attempts}")
    
    def get_status_file(self) -> Path:
        """
        Получение пути к файлу статусов проекта
        
        Returns:
            Path к файлу codeAgentProjectStatus.md
        
        Raises:
            ValueError: Если путь невалиден
        """
        project_dir = self.get_project_dir()
        status_file_name = self.get('project.status_file', 'codeAgentProjectStatus.md')
        
        # Проверка на path traversal в имени файла
        if '..' in str(status_file_name):
            raise ValueError(
                f"Имя файла статусов содержит '..': {status_file_name}. "
                f"Path traversal атаки запрещены."
            )
        
        status_path = project_dir / status_file_name
        
        # Валидация пути (относительно project_dir)
        try:
            # Для относительных путей проверяем, что они остаются внутри project_dir
            validated_path = self._validate_path(status_path, "project.status_file")
            # Убеждаемся, что путь все еще внутри project_dir
            validated_path.relative_to(project_dir)
        except ValueError as e:
            logger.error(f"Ошибка валидации пути файла статусов: {e}")
            raise
        
        return validated_path
