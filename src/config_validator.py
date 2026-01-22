"""
Модуль валидации конфигурации YAML

Проверяет структуру и значения конфигурационного файла config.yaml
"""

from typing import Dict, Any, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Исключение для ошибок валидации конфигурации"""
    
    def __init__(self, message: str, path: str = "", errors: Optional[List[str]] = None):
        """
        Инициализация ошибки валидации
        
        Args:
            message: Основное сообщение об ошибке
            path: Путь к полю в конфигурации (например, "project.base_dir")
            errors: Список дополнительных ошибок
        """
        super().__init__(message)
        self.message = message
        self.path = path
        self.errors = errors or []
    
    def __str__(self) -> str:
        """Форматированное представление ошибки"""
        result = self.message
        if self.path:
            result += f" (путь: {self.path})"
        if self.errors:
            result += "\nДополнительные ошибки:\n" + "\n".join(f"  - {e}" for e in self.errors)
        return result


class ConfigValidator:
    """Валидатор конфигурации Code Agent"""
    
    # Обязательные секции
    REQUIRED_SECTIONS = ['project', 'agent', 'server']
    
    # Схема валидации для секции project
    PROJECT_SCHEMA = {
        'base_dir': {
            'required': True,
            'type': str,
            'description': 'Базовая директория проекта (должна содержать ${PROJECT_DIR})'
        },
        'docs_dir': {
            'required': False,
            'type': str,
            'default': 'docs',
            'description': 'Директория с документацией'
        },
        'status_file': {
            'required': False,
            'type': str,
            'default': 'codeAgentProjectStatus.md',
            'description': 'Файл статусов проекта'
        },
        'todo_format': {
            'required': False,
            'type': str,
            'default': 'md',
            'allowed_values': ['txt', 'yaml', 'md'],
            'description': 'Формат todo-листа'
        }
    }
    
    # Схема валидации для секции agent
    AGENT_SCHEMA = {
        'role': {
            'required': False,
            'type': str,
            'default': 'Project Executor Agent',
            'description': 'Роль агента'
        },
        'goal': {
            'required': False,
            'type': str,
            'default': 'Execute todo items for the project',
            'description': 'Цель агента'
        },
        'backstory': {
            'required': False,
            'type': str,
            'description': 'История/контекст агента'
        },
        'allow_code_execution': {
            'required': False,
            'type': bool,
            'default': True,
            'description': 'Разрешить выполнение кода'
        },
        'verbose': {
            'required': False,
            'type': bool,
            'default': True,
            'description': 'Подробный вывод'
        },
        'tools': {
            'required': False,
            'type': list,
            'description': 'Список инструментов'
        },
        'model': {
            'required': False,
            'type': str,
            'description': 'Модель LLM'
        },
        'allowed_models': {
            'required': False,
            'type': list,
            'description': 'Список разрешенных моделей'
        }
    }
    
    # Схема валидации для секции server
    SERVER_SCHEMA = {
        'check_interval': {
            'required': False,
            'type': int,
            'default': 60,
            'min_value': 1,
            'max_value': 3600,
            'description': 'Интервал проверки задач в секундах'
        },
        'max_iterations': {
            'required': False,
            'type': (int, type(None)),
            'description': 'Максимальное количество итераций (null для бесконечного цикла)'
        },
        'task_delay': {
            'required': False,
            'type': int,
            'default': 5,
            'min_value': 0,
            'max_value': 300,
            'description': 'Задержка между задачами в секундах'
        },
        'http_enabled': {
            'required': False,
            'type': bool,
            'default': True,
            'description': 'Включить HTTP сервер'
        },
        'http_port': {
            'required': False,
            'type': int,
            'default': 3456,
            'min_value': 1024,
            'max_value': 65535,
            'description': 'Порт для HTTP сервера'
        },
        'auto_reload': {
            'required': False,
            'type': bool,
            'default': True,
            'description': 'Включить автоперезапуск'
        },
        'reload_on_py_changes': {
            'required': False,
            'type': bool,
            'default': True,
            'description': 'Перезапускать при изменении .py файлов'
        },
        'max_restarts': {
            'required': False,
            'type': int,
            'default': 3,
            'min_value': 1,
            'max_value': 100,
            'description': 'Максимальное количество перезапусков'
        },
        'auto_todo_generation': {
            'required': False,
            'type': dict,
            'description': 'Настройки автоматической генерации TODO'
        },
        'checkpoint': {
            'required': False,
            'type': dict,
            'description': 'Настройки системы контрольных точек'
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация валидатора
        
        Args:
            config: Словарь с конфигурацией
        """
        self.config = config
        self.errors: List[str] = []
    
    def validate(self) -> None:
        """
        Валидация всей конфигурации
        
        Raises:
            ConfigValidationError: Если конфигурация невалидна
        """
        self.errors = []
        
        # Проверка обязательных секций
        self._validate_required_sections()
        
        # Валидация секций
        if 'project' in self.config:
            self._validate_section('project', self.PROJECT_SCHEMA)
        
        if 'agent' in self.config:
            self._validate_section('agent', self.AGENT_SCHEMA)
        
        if 'server' in self.config:
            self._validate_section('server', self.SERVER_SCHEMA)
        
        # Если есть ошибки, выбрасываем исключение
        if self.errors:
            error_msg = f"Обнаружено {len(self.errors)} ошибок валидации конфигурации"
            raise ConfigValidationError(error_msg, errors=self.errors)
        
        logger.debug("Валидация конфигурации пройдена успешно")
    
    def _validate_required_sections(self) -> None:
        """Проверка наличия обязательных секций"""
        for section in self.REQUIRED_SECTIONS:
            if section not in self.config:
                self.errors.append(f"Отсутствует обязательная секция: {section}")
    
    def _validate_section(self, section_name: str, schema: Dict[str, Dict[str, Any]]) -> None:
        """
        Валидация секции конфигурации
        
        Args:
            section_name: Имя секции
            schema: Схема валидации для секции
        """
        section = self.config.get(section_name, {})
        
        if not isinstance(section, dict):
            self.errors.append(f"Секция '{section_name}' должна быть словарем")
            return
        
        # Проверка каждого поля схемы
        for field_name, field_schema in schema.items():
            field_path = f"{section_name}.{field_name}"
            value = section.get(field_name)
            
            # Проверка обязательности
            if field_schema.get('required', False) and value is None:
                self.errors.append(
                    f"Обязательное поле отсутствует: {field_path} "
                    f"({field_schema.get('description', '')})"
                )
                continue
            
            # Если значение отсутствует и не обязательное, пропускаем
            if value is None:
                continue
            
            # Проверка типа
            expected_type = field_schema.get('type')
            if expected_type:
                if not self._check_type(value, expected_type):
                    expected_type_str = self._type_to_string(expected_type)
                    actual_type_str = type(value).__name__
                    self.errors.append(
                        f"Неверный тип для {field_path}: ожидается {expected_type_str}, "
                        f"получен {actual_type_str}"
                    )
                    continue
            
            # Проверка разрешенных значений
            if 'allowed_values' in field_schema:
                if value not in field_schema['allowed_values']:
                    allowed = ', '.join(str(v) for v in field_schema['allowed_values'])
                    self.errors.append(
                        f"Недопустимое значение для {field_path}: '{value}'. "
                        f"Разрешенные значения: {allowed}"
                    )
            
            # Проверка диапазона для чисел
            if isinstance(value, (int, float)):
                if 'min_value' in field_schema and value < field_schema['min_value']:
                    self.errors.append(
                        f"Значение {field_path} слишком мало: {value}. "
                        f"Минимальное значение: {field_schema['min_value']}"
                    )
                if 'max_value' in field_schema and value > field_schema['max_value']:
                    self.errors.append(
                        f"Значение {field_path} слишком велико: {value}. "
                        f"Максимальное значение: {field_schema['max_value']}"
                    )
            
            # Специальные проверки для вложенных структур
            if field_name == 'auto_todo_generation' and isinstance(value, dict):
                self._validate_auto_todo_generation(field_path, value)
            elif field_name == 'checkpoint' and isinstance(value, dict):
                self._validate_checkpoint(field_path, value)
    
    def _validate_auto_todo_generation(self, path: str, config: Dict[str, Any]) -> None:
        """Валидация настроек автоматической генерации TODO"""
        if 'enabled' in config and not isinstance(config['enabled'], bool):
            self.errors.append(f"{path}.enabled должен быть булевым значением")
        
        if 'max_generations_per_session' in config:
            max_gen = config['max_generations_per_session']
            if not isinstance(max_gen, int) or max_gen < 1 or max_gen > 100:
                self.errors.append(
                    f"{path}.max_generations_per_session должен быть целым числом от 1 до 100"
                )
    
    def _validate_checkpoint(self, path: str, config: Dict[str, Any]) -> None:
        """Валидация настроек checkpoint"""
        if 'enabled' in config and not isinstance(config['enabled'], bool):
            self.errors.append(f"{path}.enabled должен быть булевым значением")
        
        if 'max_task_attempts' in config:
            max_attempts = config['max_task_attempts']
            if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 100:
                self.errors.append(
                    f"{path}.max_task_attempts должен быть целым числом от 1 до 100"
                )
    
    def _check_type(self, value: Any, expected_type: Union[type, tuple]) -> bool:
        """
        Проверка типа значения
        
        Args:
            value: Значение для проверки
            expected_type: Ожидаемый тип (может быть tuple для нескольких типов)
        
        Returns:
            True если тип соответствует
        """
        if isinstance(expected_type, tuple):
            return isinstance(value, expected_type)
        return isinstance(value, expected_type)
    
    def _type_to_string(self, type_obj: Union[type, tuple]) -> str:
        """Преобразование типа в строку для сообщений об ошибках"""
        if isinstance(type_obj, tuple):
            return ' или '.join(t.__name__ for t in type_obj)
        return type_obj.__name__


def validate_config(config: Dict[str, Any]) -> None:
    """
    Валидация конфигурации (удобная функция-обертка)
    
    Args:
        config: Словарь с конфигурацией
    
    Raises:
        ConfigValidationError: Если конфигурация невалидна
    """
    validator = ConfigValidator(config)
    validator.validate()
