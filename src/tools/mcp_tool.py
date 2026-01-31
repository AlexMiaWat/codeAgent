"""
MCP Tool - инструмент для доступа к Model Context Protocol ресурсам.

Позволяет агентам взаимодействовать с MCP сервером для получения
контекста проекта, ресурсов и выполнения операций.
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from urllib.parse import urljoin

from crewai import tool


logger = logging.getLogger(__name__)


class MCPClient:
    """
    Клиент для взаимодействия с MCP сервером.
    """

    def __init__(self, base_url: str = "http://localhost:3000", token: Optional[str] = None):
        """
        Инициализация MCP клиента.

        Args:
            base_url: Базовый URL MCP сервера
            token: JWT токен для аутентификации (опционально)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()

        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Выполнение HTTP запроса к MCP серверу."""
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"MCP request failed: {method} {url} - {e}")
            raise

    def list_resources(self) -> List[Dict[str, Any]]:
        """Получение списка доступных ресурсов."""
        return self._make_request("GET", "/resources")

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Чтение ресурса по URI."""
        return self._make_request("GET", f"/resources/{uri}")

    def list_tools(self) -> List[Dict[str, Any]]:
        """Получение списка доступных инструментов."""
        return self._make_request("GET", "/tools")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Вызов инструмента с аргументами."""
        data = {
            "tool": tool_name,
            "arguments": arguments
        }
        return self._make_request("POST", "/tools/call", json=data)

    def list_prompts(self) -> List[Dict[str, Any]]:
        """Получение списка доступных промптов."""
        return self._make_request("GET", "/prompts")

    def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Получение промпта с аргументами."""
        data = arguments or {}
        return self._make_request("POST", f"/prompts/{prompt_name}", json=data)

    def search_files(self, query: str, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Поиск по файлам проекта."""
        params = {"q": query}
        if file_types:
            params["types"] = ",".join(file_types)
        return self._make_request("GET", "/search/files", params=params)

    def get_project_structure(self) -> Dict[str, Any]:
        """Получение структуры проекта."""
        return self._make_request("GET", "/project/structure")

    def get_file_content(self, path: str, start_line: Optional[int] = None,
                        end_line: Optional[int] = None) -> str:
        """Получение содержимого файла."""
        params = {}
        if start_line is not None:
            params["start_line"] = start_line
        if end_line is not None:
            params["end_line"] = end_line

        response = self._make_request("GET", f"/files/{path}", params=params)
        return response.get("content", "")

    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик сервера."""
        return self._make_request("GET", "/metrics")


# Глобальный клиент MCP (инициализируется при первом использовании)
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> Optional[MCPClient]:
    """Получение MCP клиента (ленивая инициализация)."""
    global _mcp_client

    if _mcp_client is None:
        try:
            # Попытка подключения к локальному MCP серверу
            _mcp_client = MCPClient()
            # Тестовое подключение
            _mcp_client.list_resources()
            logger.info("MCP client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize MCP client: {e}")
            _mcp_client = None

    return _mcp_client


@tool("search_project_files")
def search_project_files(query: str, file_types: Optional[str] = None) -> str:
    """
    Поиск по файлам проекта.

    Args:
        query: Поисковый запрос
        file_types: Типы файлов для поиска (опционально, через запятую: py,md,txt,json,yaml)

    Returns:
        Результаты поиска в формате JSON
    """
    client = get_mcp_client()
    if not client:
        return "MCP server not available"

    try:
        types_list = [t.strip() for t in file_types.split(',')] if file_types else None
        results = client.search_files(query, types_list)
        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Search failed: {e}"


@tool("read_project_file")
def read_project_file(file_path: str, start_line: Optional[int] = None,
                     end_line: Optional[int] = None) -> str:
    """
    Чтение содержимого файла проекта.

    Args:
        file_path: Путь к файлу относительно корня проекта
        start_line: Начальная строка (опционально)
        end_line: Конечная строка (опционально)

    Returns:
        Содержимое файла
    """
    client = get_mcp_client()
    if not client:
        return "MCP server not available"

    try:
        return client.get_file_content(file_path, start_line, end_line)
    except Exception as e:
        return f"Failed to read file: {e}"


@tool("get_project_structure")
def get_project_structure() -> str:
    """
    Получение структуры проекта.

    Returns:
        Структура проекта в формате JSON
    """
    client = get_mcp_client()
    if not client:
        return "MCP server not available"

    try:
        structure = client.get_project_structure()
        return json.dumps(structure, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Failed to get project structure: {e}"


@tool("list_project_resources")
def list_project_resources() -> str:
    """
    Получение списка доступных ресурсов проекта.

    Returns:
        Список ресурсов в формате JSON
    """
    client = get_mcp_client()
    if not client:
        return "MCP server not available"

    try:
        resources = client.list_resources()
        return json.dumps(resources, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Failed to list resources: {e}"


@tool("call_mcp_tool")
def call_mcp_tool(tool_name: str, arguments: str) -> str:
    """
    Вызов MCP инструмента с аргументами.

    Args:
        tool_name: Имя инструмента
        arguments: Аргументы в формате JSON строки

    Returns:
        Результат выполнения инструмента
    """
    client = get_mcp_client()
    if not client:
        return "MCP server not available"

    try:
        args_dict = json.loads(arguments) if arguments else {}
        result = client.call_tool(tool_name, args_dict)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return "Invalid JSON arguments"
    except Exception as e:
        return f"Tool call failed: {e}"


@tool("get_server_metrics")
def get_server_metrics() -> str:
    """
    Получение метрик сервера.

    Returns:
        Метрики в формате JSON
    """
    client = get_mcp_client()
    if not client:
        return "MCP server not available"

    try:
        metrics = client.get_metrics()
        return json.dumps(metrics, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Failed to get metrics: {e}"


@tool("analyze_code_context")
def analyze_code_context(file_path: str, line_number: Optional[int] = None) -> str:
    """
    Анализ контекста кода в файле.

    Args:
        file_path: Путь к файлу
        line_number: Номер строки для анализа (опционально)

    Returns:
        Анализ контекста
    """
    client = get_mcp_client()
    if not client:
        return "MCP server not available"

    try:
        # Получаем содержимое файла
        content = client.get_file_content(file_path)

        # Если указана строка, анализируем контекст вокруг неё
        if line_number:
            lines = content.split('\n')
            if 1 <= line_number <= len(lines):
                # Получаем контекст вокруг строки
                start = max(1, line_number - 5)
                end = min(len(lines), line_number + 5)
                context_lines = lines[start-1:end]
                context = '\n'.join(f"{i+start}: {line}" for i, line in enumerate(context_lines))

                return f"Code context around line {line_number} in {file_path}:\n\n{context}"
            else:
                return f"Line number {line_number} is out of range"

        return f"Full content of {file_path}:\n\n{content}"

    except Exception as e:
        return f"Failed to analyze code context: {e}"