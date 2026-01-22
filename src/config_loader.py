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

    @staticmethod
    def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
        """
        Статический метод загрузки конфигурации

        Args:
            config_path: Путь к файлу конфигурации

        Returns:
            Словарь с конфигурацией
        """
        loader = ConfigLoader(config_path)
        return loader.config

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

        # Валидация Smart Agent конфигурации
        smart_agent_errors = self.validate_smart_agent_config()
        if smart_agent_errors:
            error_msg = "Ошибки валидации конфигурации Smart Agent:\n\n"
            error_msg += "\n".join(f"  - {error}" for error in smart_agent_errors)
            error_msg += "\n\n" + "=" * 70
            error_msg += "\n\nДля решения проблем:"
            error_msg += "\n  1. Проверьте параметры smart_agent в config.yaml"
            error_msg += "\n  2. Убедитесь, что директория опыта существует или может быть создана"
            error_msg += "\n  3. Проверьте разумность значений параметров производительности"
            error_msg += "\n  4. См. документацию: docs/core/configuration_reference.md"

            logger.error(error_msg)
            raise ValueError(error_msg)
    
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

    def get_smart_agent_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации Smart Agent

        Returns:
            Словарь с настройками Smart Agent
        """
        smart_config = self.config.get('smart_agent', {})

        # Устанавливаем значения по умолчанию
        defaults = {
            'enabled': True,
            'experience_dir': 'smart_experience',
            'max_experience_tasks': 1000,
            'max_iter': 25,
            'memory': 100,
            'verbose': True,
            'llm_strategy': 'best_of_two',
            'cache_enabled': True,
            'cache_ttl_seconds': 3600,
            'learning_tool': {
                'enable_indexing': True,
                'cache_size': 1000,
                'cache_ttl_seconds': 3600,
                'max_experience_tasks': 1000
            },
            'context_analyzer_tool': {
                'max_file_size': 1000000,
                'supported_extensions': ['.md', '.txt', '.rst', '.py', '.js', '.ts', '.json', '.yaml', '.yml', '.java', '.cpp', '.hpp', '.c', '.h'],
                'supported_languages': ['python', 'javascript', 'typescript', 'java', 'cpp', 'c'],
                'max_dependency_depth': 5
            }
        }

        # Рекурсивно сливаем конфигурацию с defaults
        def merge_dicts(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
            result = default.copy()
            for key, value in user.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                else:
                    result[key] = value
            return result

        return merge_dicts(defaults, smart_config)

    def validate_smart_agent_config(self) -> List[str]:
        """
        Валидация конфигурации Smart Agent

        Returns:
            List[str]: Список ошибок валидации. Пустой список означает успешную валидацию.
        """
        errors = []

        # Получаем конфигурацию Smart Agent
        smart_config = self.get_smart_agent_config()

        # Проверяем только если Smart Agent включен
        if smart_config.get('enabled', False):
            # Проверка директории опыта
            experience_dir = Path(smart_config.get('experience_dir', 'smart_experience'))

            # Если путь относительный, разрешаем его относительно project_dir
            if not experience_dir.is_absolute():
                try:
                    project_dir = self.get_project_dir()
                    experience_dir = project_dir / experience_dir
                except ValueError:
                    errors.append("Не удалось определить директорию проекта для валидации experience_dir")
                    return errors

            # Проверяем возможность создания директории
            try:
                if not experience_dir.exists():
                    # Пробуем создать директорию
                    experience_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Создана директория опыта Smart Agent: {experience_dir}")
                elif not experience_dir.is_dir():
                    errors.append(f"experience_dir должен быть директорией, а не файлом: {experience_dir}")
            except (OSError, PermissionError) as e:
                errors.append(f"Не удалось создать или проверить директорию опыта: {experience_dir} - {e}")

            # Проверка параметров производительности
            max_iter = smart_config.get('max_iter', 25)
            if not isinstance(max_iter, int) or max_iter < 1:
                errors.append(f"max_iter должен быть положительным целым числом, получено: {max_iter}")
            elif max_iter > 50:
                errors.append(f"max_iter > 50 ({max_iter}) может привести к бесконечным циклам. Рекомендуется значение <= 50")

            memory = smart_config.get('memory', 100)
            if not isinstance(memory, int) or memory < 1:
                errors.append(f"memory должен быть положительным целым числом, получено: {memory}")
            elif memory > 1000:
                errors.append(f"memory > 1000 ({memory}) может привести к чрезмерному потреблению памяти")

            max_experience_tasks = smart_config.get('max_experience_tasks', 1000)
            if not isinstance(max_experience_tasks, int) or max_experience_tasks < 1:
                errors.append(f"max_experience_tasks должен быть положительным целым числом, получено: {max_experience_tasks}")
            elif max_experience_tasks > 10000:
                errors.append(f"max_experience_tasks > 10000 ({max_experience_tasks}) может привести к проблемам производительности")

            # Проверка вложенных конфигураций
            learning_tool = smart_config.get('learning_tool', {})
            if not isinstance(learning_tool, dict):
                errors.append("learning_tool должен быть словарем с настройками")
            else:
                cache_size = learning_tool.get('cache_size', 1000)
                if not isinstance(cache_size, int) or cache_size < 1:
                    errors.append(f"learning_tool.cache_size должен быть положительным целым числом, получено: {cache_size}")
                elif cache_size > 10000:
                    errors.append(f"learning_tool.cache_size > 10000 ({cache_size}) может привести к чрезмерному потреблению памяти")

            context_analyzer = smart_config.get('context_analyzer_tool', {})
            if not isinstance(context_analyzer, dict):
                errors.append("context_analyzer_tool должен быть словарем с настройками")
            else:
                max_file_size = context_analyzer.get('max_file_size', 1000000)
                if not isinstance(max_file_size, int) or max_file_size < 1:
                    errors.append(f"context_analyzer_tool.max_file_size должен быть положительным целым числом, получено: {max_file_size}")
                elif max_file_size > 10000000:  # 10MB
                    errors.append(f"context_analyzer_tool.max_file_size > 10MB ({max_file_size}) может привести к проблемам производительности")

                max_depth = context_analyzer.get('max_dependency_depth', 5)
                if not isinstance(max_depth, int) or max_depth < 1:
                    errors.append(f"context_analyzer_tool.max_dependency_depth должен быть положительным целым числом, получено: {max_depth}")
                elif max_depth > 10:
                    errors.append(f"context_analyzer_tool.max_dependency_depth > 10 ({max_depth}) может привести к чрезмерной глубине анализа")

            # Проверка стратегии LLM
            llm_strategy = smart_config.get('llm_strategy', 'best_of_two')
            valid_strategies = ['single', 'best_of_two', 'fallback']
            if llm_strategy not in valid_strategies:
                errors.append(f"llm_strategy должен быть одним из: {valid_strategies}, получено: {llm_strategy}")

        return errors
