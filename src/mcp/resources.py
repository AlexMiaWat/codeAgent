"""
Resource Manager для MCP сервера.

Предоставляет доступ к ресурсам проекта через MCP протокол.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import ConfigLoader


@dataclass
class MCPResource:
    """MCP ресурс."""
    uri: str
    name: str
    description: str
    mime_type: str
    size: Optional[int] = None
    last_modified: Optional[str] = None


@dataclass
class MCPResourceContent:
    """Содержимое MCP ресурса."""
    uri: str
    mime_type: str
    text: Optional[str] = None
    blob: Optional[str] = None  # base64 для бинарных данных


class ResourceManager:
    """
    Менеджер ресурсов для MCP сервера.

    Предоставляет доступ к документации, исходному коду и конфигурации проекта.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.logger = logging.getLogger(__name__)
        self.project_root = Path.cwd()

        # Настраиваемые директории ресурсов
        self.resource_dirs = {
            "docs": self.project_root / "docs",
            "src": self.project_root / "src",
            "config": self.project_root / "config",
            "examples": self.project_root / "examples",
            "logs": self.project_root / "logs",
        }

        # Поддерживаемые MIME типы
        self.mime_types = {
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".py": "text/x-python",
            ".json": "application/json",
            ".yaml": "application/yaml",
            ".yml": "application/yaml",
            ".toml": "application/toml",
            ".ini": "text/plain",
            ".log": "text/plain",
            ".sh": "text/x-shellscript",
            ".bat": "text/x-batchfile",
            ".sql": "text/x-sql",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "text/javascript",
            ".ts": "text/typescript",
        }

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        Получить список всех доступных ресурсов.

        Returns:
            Список ресурсов в формате MCP
        """
        resources = []

        for dir_name, dir_path in self.resource_dirs.items():
            if dir_path.exists():
                dir_resources = await self._scan_directory(dir_name, dir_path)
                resources.extend(dir_resources)

        # Сортировка по URI
        resources.sort(key=lambda r: r["uri"])

        self.logger.info(f"Listed {len(resources)} resources")
        return resources

    async def _scan_directory(self, prefix: str, directory: Path) -> List[Dict[str, Any]]:
        """Сканирование директории для ресурсов."""
        resources = []

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file() and not self._is_ignored_file(file_path):
                    resource = await self._create_resource(prefix, file_path)
                    if resource:
                        resources.append(resource)
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")

        return resources

    def _is_ignored_file(self, file_path: Path) -> bool:
        """Проверка, следует ли игнорировать файл."""
        # Игнорировать скрытые файлы и директории
        if file_path.name.startswith('.'):
            return True

        # Игнорировать временные файлы
        if file_path.suffix in ['.tmp', '.temp', '.bak', '.swp', '.pyc', '.pyo']:
            return True

        # Игнорировать большие бинарные файлы
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return True
        except OSError:
            return True

        return False

    async def _create_resource(self, prefix: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Создание MCP ресурса из файла."""
        try:
            # Получение относительного пути
            relative_path = file_path.relative_to(self.project_root)
            uri = f"file://{relative_path}"

            # Определение MIME типа
            mime_type = self.mime_types.get(file_path.suffix.lower(), "text/plain")

            # Получение размера файла
            stat = file_path.stat()
            size = stat.st_size

            # Получение времени последнего изменения
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

            return {
                "uri": uri,
                "name": file_path.name,
                "description": f"{prefix.upper()} file: {relative_path}",
                "mimeType": mime_type,
                "size": size,
                "lastModified": last_modified,
            }

        except Exception as e:
            self.logger.error(f"Error creating resource for {file_path}: {e}")
            return None

    async def read_resource(self, uri: str) -> MCPResourceContent:
        """
        Чтение содержимого ресурса.

        Args:
            uri: URI ресурса

        Returns:
            Содержимое ресурса
        """
        if not uri.startswith("file://"):
            raise ValueError(f"Unsupported URI scheme: {uri}")

        # Извлечение пути из URI
        file_path_str = uri[7:]  # Удаляем "file://"
        file_path = self.project_root / file_path_str

        # Безопасность: проверка что файл находится в разрешенных директориях
        if not self._is_path_allowed(file_path):
            raise PermissionError(f"Access denied to file: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Определение MIME типа
        mime_type = self.mime_types.get(file_path.suffix.lower(), "text/plain")

        # Чтение файла
        try:
            if mime_type.startswith("text/"):
                # Текстовый файл
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return MCPResourceContent(
                    uri=uri,
                    mime_type=mime_type,
                    text=content
                )
            else:
                # Бинарный файл (base64)
                with open(file_path, 'rb') as f:
                    import base64
                    content = base64.b64encode(f.read()).decode('utf-8')
                return MCPResourceContent(
                    uri=uri,
                    mime_type=mime_type,
                    blob=content
                )

        except UnicodeDecodeError:
            # Если файл не может быть прочитан как текст, читаем как бинарный
            with open(file_path, 'rb') as f:
                import base64
                content = base64.b64encode(f.read()).decode('utf-8')
            return MCPResourceContent(
                uri=uri,
                mime_type="application/octet-stream",
                blob=content
            )
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise

    def _is_path_allowed(self, file_path: Path) -> bool:
        """Проверка, разрешен ли доступ к пути."""
        try:
            # Разрешение пути для обработки симлинков
            resolved_path = file_path.resolve()

            # Проверка что путь находится в корне проекта
            resolved_path.relative_to(self.project_root)

            # Проверка что путь находится в разрешенных директориях
            for allowed_dir in self.resource_dirs.values():
                try:
                    resolved_path.relative_to(allowed_dir)
                    return True
                except ValueError:
                    continue

            return False

        except Exception:
            return False

    async def get_resource_info(self, uri: str) -> Optional[Dict[str, Any]]:
        """Получение информации о ресурсе без чтения содержимого."""
        try:
            content = await self.read_resource(uri)
            return {
                "uri": uri,
                "mimeType": content.mime_type,
                "size": len(content.text or content.blob or ""),
            }
        except Exception as e:
            self.logger.error(f"Error getting resource info for {uri}: {e}")
            return None

    async def search_resources(self, query: str, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Поиск ресурсов по запросу.

        Args:
            query: Поисковый запрос
            directory: Ограничение поиска директорией (опционально)

        Returns:
            Список найденных ресурсов
        """
        all_resources = await self.list_resources()
        matching_resources = []

        query_lower = query.lower()

        for resource in all_resources:
            # Фильтр по директории
            if directory and not resource["uri"].startswith(f"file://{directory}/"):
                continue

            # Поиск по имени и описанию
            if (query_lower in resource["name"].lower() or
                query_lower in resource["description"].lower()):
                matching_resources.append(resource)

        return matching_resources