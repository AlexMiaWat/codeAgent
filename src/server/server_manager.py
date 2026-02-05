import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigValidator:
    def __init__(self, config: Any, project_dir: Path, docs_dir: Path, status_file: str):
        self.config = config
        self.project_dir = project_dir
        self.docs_dir = docs_dir
        self.status_file = status_file

    def validate_config(self):
        """
        Валидация конфигурации при инициализации сервера

        Проверяет наличие обязательных параметров и их корректность.
        Выбрасывает исключения с понятными сообщениями об ошибках.

        Raises:
            ValueError: Если обязательные параметры не установлены или некорректны
            FileNotFoundError: Если директории или файлы не найдены
        """
        errors = []

        # Проверка project_dir
        if not self.project_dir:
            errors.append("PROJECT_DIR не установлен в переменных окружения или .env файле")
        elif not self.project_dir.exists():
            errors.append(
                f"Директория проекта не найдена: {self.project_dir}\n"
                f"  Убедитесь, что путь указан правильно в .env файле:\n"
                f"  PROJECT_DIR={self.project_dir}"
            )
        elif not self.project_dir.is_dir():
            errors.append(f"Путь не является директорией: {self.project_dir}")
        else:
            # Проверка прав доступа на чтение
            if not os.access(self.project_dir, os.R_OK):
                errors.append(f"Нет прав на чтение директории проекта: {self.project_dir}")
            # Проверка прав доступа на запись (для создания файлов статусов)
            if not os.access(self.project_dir, os.W_OK):
                errors.append(
                    f"Нет прав на запись в директорию проекта: {self.project_dir}\n"
                    f"  Агенту нужны права на запись для создания файлов статусов"
                )

        # Проверка docs_dir (опционально, но желательно)
        if self.docs_dir and self.docs_dir.exists():
            if not os.access(self.docs_dir, os.R_OK):
                errors.append(f"Нет прав на чтение директории документации: {self.docs_dir}")

        # Проверка конфигурационного файла
        if not self.config.config_path.exists():
            errors.append(f"Конфигурационный файл не найден: {self.config.config_path}")

        # Если есть ошибки, выбрасываем исключение с понятным сообщением
        if errors:
            error_msg = "Ошибки конфигурации:\n\n" + "\n\n".join(f"  • {e}" for e in errors)
            error_msg += "\n\n" + "=" * 70
            error_msg += "\n\nДля решения проблем:\n"
            error_msg += "  1. Проверьте наличие .env файла в корне codeAgent/\n"
            error_msg += "  2. Убедитесь, что PROJECT_DIR указан правильно\n"
            error_msg += "  3. Проверьте права доступа к директориям\n"
            error_msg += "  4. См. документацию: docs/guides/setup.md\n"
            error_msg += "  5. См. шаблон: .env.example"

            logger.error(error_msg)
            raise ValueError(error_msg)

        # Логируем успешную валидацию
        logger.debug("Валидация конфигурации пройдена успешно")
        logger.debug(f"  Project dir: {self.project_dir}")
        logger.debug(f"  Docs dir: {self.docs_dir}")
        logger.debug(f"  Status file: {self.status_file}")
