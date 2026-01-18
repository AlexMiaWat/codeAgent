"""
Модуль загрузки конфигурации
"""

import os
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()


class ConfigLoader:
    """Загрузчик конфигурации из YAML и переменных окружения"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Инициализация загрузчика конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации из YAML файла"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}
        
        # Подстановка переменных окружения
        self._substitute_env_vars(self.config)
    
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
        if not project_path.exists():
            raise FileNotFoundError(f"Директория проекта не найдена: {project_path}")
        
        return project_path.absolute()
    
    def get_docs_dir(self) -> Path:
        """
        Получение пути к директории документации
        
        Returns:
            Path к директории docs
        """
        project_dir = self.get_project_dir()
        docs_dir_name = self.get('project.docs_dir', 'docs')
        return project_dir / docs_dir_name
    
    def get_status_file(self) -> Path:
        """
        Получение пути к файлу статусов проекта
        
        Returns:
            Path к файлу codeAgentProjectStatus.md
        """
        project_dir = self.get_project_dir()
        status_file_name = self.get('project.status_file', 'codeAgentProjectStatus.md')
        return project_dir / status_file_name
