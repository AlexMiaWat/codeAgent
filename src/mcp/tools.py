"""
Tools Manager для MCP сервера.

Предоставляет инструменты (tools) для MCP протокола.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import ConfigLoader


@dataclass
class MCPTool:
    """MCP инструмент."""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class ToolResult:
    """Результат выполнения инструмента."""
    content: List[Dict[str, Any]]
    is_error: bool = False


class ToolsManager:
    """
    Менеджер инструментов для MCP сервера.

    Предоставляет различные инструменты для работы с проектом.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.logger = logging.getLogger(__name__)
        self.tools: Dict[str, MCPTool] = {}
        self.tool_handlers: Dict[str, Callable] = {}

        self._initialize_tools()

    def _initialize_tools(self):
        """Инициализация доступных инструментов."""
        # Инструмент для запуска тестов
        self.tools["run_tests"] = MCPTool(
            name="run_tests",
            description="Запуск автоматических тестов проекта",
            input_schema={
                "type": "object",
                "properties": {
                    "test_pattern": {
                        "type": "string",
                        "description": "Шаблон для поиска тестов (например, 'test_*.py')"
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Подробный вывод",
                        "default": False
                    }
                },
                "required": []
            }
        )
        self.tool_handlers["run_tests"] = self._handle_run_tests

        # Инструмент для проверки кода
        self.tools["code_check"] = MCPTool(
            name="code_check",
            description="Проверка качества кода (линтинг, типизация)",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Путь к файлу для проверки"
                    },
                    "check_type": {
                        "type": "string",
                        "enum": ["lint", "type_check", "security", "all"],
                        "description": "Тип проверки",
                        "default": "all"
                    }
                },
                "required": ["file_path"]
            }
        )
        self.tool_handlers["code_check"] = self._handle_code_check

        # Инструмент для сборки проекта
        self.tools["build_project"] = MCPTool(
            name="build_project",
            description="Сборка проекта",
            input_schema={
                "type": "object",
                "properties": {
                    "build_type": {
                        "type": "string",
                        "enum": ["development", "production", "test"],
                        "description": "Тип сборки",
                        "default": "development"
                    },
                    "clean": {
                        "type": "boolean",
                        "description": "Очистка перед сборкой",
                        "default": False
                    }
                },
                "required": []
            }
        )
        self.tool_handlers["build_project"] = self._handle_build_project

        self.logger.info(f"Initialized {len(self.tools)} tools")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Получить список всех доступных инструментов.

        Returns:
            Список инструментов в формате MCP
        """
        tools_list = []
        for tool in self.tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })

        return tools_list

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Вызвать инструмент.

        Args:
            name: Имя инструмента
            arguments: Аргументы для инструмента

        Returns:
            Результат выполнения
        """
        if name not in self.tool_handlers:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Tool '{name}' not found"
                }],
                is_error=True
            )

        try:
            handler = self.tool_handlers[name]
            return await handler(arguments)
        except Exception as e:
            self.logger.error(f"Error calling tool {name}: {e}")
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Error executing tool '{name}': {str(e)}"
                }],
                is_error=True
            )

    async def _handle_run_tests(self, arguments: Dict[str, Any]) -> ToolResult:
        """Обработчик инструмента run_tests."""
        import subprocess
        import sys

        test_pattern = arguments.get("test_pattern", "test_*.py")
        verbose = arguments.get("verbose", False)

        try:
            # Запуск pytest
            cmd = [sys.executable, "-m", "pytest"]
            if verbose:
                cmd.append("-v")
            cmd.extend(["-k", test_pattern])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd="."
            )

            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"

            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Exit code: {result.returncode}\n{output}"
                }]
            )

        except Exception as e:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Failed to run tests: {str(e)}"
                }],
                is_error=True
            )

    async def _handle_code_check(self, arguments: Dict[str, Any]) -> ToolResult:
        """Обработчик инструмента code_check."""
        import subprocess
        import sys
        from pathlib import Path

        file_path = arguments.get("file_path")
        check_type = arguments.get("check_type", "all")

        if not file_path:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "file_path is required"
                }],
                is_error=True
            )

        file_path = Path(file_path)
        if not file_path.exists():
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"File not found: {file_path}"
                }],
                is_error=True
            )

        results = []

        try:
            if check_type in ["lint", "all"]:
                # Запуск flake8 для линтинга
                result = subprocess.run(
                    [sys.executable, "-m", "flake8", str(file_path)],
                    capture_output=True,
                    text=True
                )
                results.append(f"Flake8 result:\n{result.stdout}{result.stderr}")

            if check_type in ["type_check", "all"]:
                # Запуск mypy для проверки типов
                result = subprocess.run(
                    [sys.executable, "-m", "mypy", str(file_path)],
                    capture_output=True,
                    text=True
                )
                results.append(f"MyPy result:\n{result.stdout}{result.stderr}")

            if check_type in ["security", "all"]:
                # Запуск bandit для проверки безопасности
                result = subprocess.run(
                    [sys.executable, "-m", "bandit", "-r", str(file_path)],
                    capture_output=True,
                    text=True
                )
                results.append(f"Bandit result:\n{result.stdout}{result.stderr}")

            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "\n\n".join(results)
                }]
            )

        except Exception as e:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Failed to check code: {str(e)}"
                }],
                is_error=True
            )

    async def _handle_build_project(self, arguments: Dict[str, Any]) -> ToolResult:
        """Обработчик инструмента build_project."""
        import subprocess
        import sys

        build_type = arguments.get("build_type", "development")
        clean = arguments.get("clean", False)

        try:
            commands = []

            if clean:
                # Очистка
                commands.append([sys.executable, "-m", "pip", "uninstall", "-y", "code-agent"])

            # Установка зависимостей
            commands.append([sys.executable, "-m", "pip", "install", "-e", "."])

            # Сборка
            if build_type == "production":
                commands.append([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
                commands.append([sys.executable, "setup.py", "bdist_wheel"])
            elif build_type == "test":
                commands.append([sys.executable, "-m", "pip", "install", "-e", ".[test]"])

            results = []
            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd="."
                )
                results.append(f"Command: {' '.join(cmd)}\nExit code: {result.returncode}")
                if result.stdout:
                    results.append(f"STDOUT:\n{result.stdout}")
                if result.stderr:
                    results.append(f"STDERR:\n{result.stderr}")

            return ToolResult(
                content=[{
                    "type": "text",
                    "text": "\n\n".join(results)
                }]
            )

        except Exception as e:
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Failed to build project: {str(e)}"
                }],
                is_error=True
            )