"""
Интеграционные тесты для MCP сервера.

Проверяет полную интеграцию MCP протокола с сервером.
"""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp.server import MCPServer
from src.config_loader import ConfigLoader


class TestMCPIntegration:
    """Интеграционные тесты MCP сервера."""

    @pytest.fixture
    async def mcp_server(self):
        """Фикстура для MCP сервера."""
        config_loader = ConfigLoader()
        server = MCPServer(config_loader)
        yield server
        # Очистка после тестов
        await server.cleanup() if hasattr(server, 'cleanup') else None

    @pytest.mark.asyncio
    async def test_mcp_initialize(self, mcp_server):
        """Тест инициализации MCP соединения."""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "resources": {"subscribe": True},
                "tools": {"listChanged": True},
                "prompts": {"listChanged": True}
            },
            "clientInfo": {
                "name": "Test Client",
                "version": "1.0.0"
            }
        }

        result = await mcp_server.handle_initialize(params, "test_conn")

        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "Code Agent MCP Server"

    @pytest.mark.asyncio
    async def test_resources_list(self, mcp_server):
        """Тест получения списка ресурсов."""
        result = await mcp_server.handle_resources_list({}, "test_conn")

        assert "resources" in result
        assert isinstance(result["resources"], list)

        # Проверяем структуру ресурсов
        if result["resources"]:
            resource = result["resources"][0]
            required_fields = ["uri", "name", "description", "mimeType"]
            for field in required_fields:
                assert field in resource

    @pytest.mark.asyncio
    async def test_resources_read_existing_file(self, mcp_server):
        """Тест чтения существующего файла через ресурсы."""
        # Создаем тестовый файл
        test_file = Path("test_readme.md")
        test_content = "# Test README\n\nThis is a test file for MCP integration."
        test_file.write_text(test_content)

        try:
            uri = f"file://{test_file.absolute()}"
            result = await mcp_server.handle_resources_read({"uri": uri}, "test_conn")

            assert "contents" in result
            assert len(result["contents"]) == 1
            content = result["contents"][0]
            assert "text" in content or "blob" in content
            assert content.get("mimeType") == "text/markdown"

        finally:
            test_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_resources_read_nonexistent_file(self, mcp_server):
        """Тест чтения несуществующего файла."""
        uri = "file://nonexistent_file.txt"

        with pytest.raises(FileNotFoundError):
            await mcp_server.handle_resources_read({"uri": uri}, "test_conn")

    @pytest.mark.asyncio
    async def test_tools_list(self, mcp_server):
        """Тест получения списка инструментов."""
        result = await mcp_server.handle_tools_list({}, "test_conn")

        assert "tools" in result
        assert isinstance(result["tools"], list)

        # Проверяем что есть инструменты
        assert len(result["tools"]) > 0

        # Проверяем структуру инструментов
        tool = result["tools"][0]
        required_fields = ["name", "description", "inputSchema"]
        for field in required_fields:
            assert field in tool

    @pytest.mark.asyncio
    async def test_tools_call_run_tests(self, mcp_server):
        """Тест вызова инструмента run_tests."""
        # Этот тест может быть медленным, поэтому проверяем только структуру
        result = await mcp_server.handle_tools_call({
            "name": "run_tests",
            "arguments": {"test_pattern": "test_nonexistent_*.py"}
        }, "test_conn")

        assert "content" in result
        assert "isError" in result
        assert isinstance(result["content"], list)

    @pytest.mark.asyncio
    async def test_tools_call_code_check(self, mcp_server):
        """Тест вызова инструмента code_check."""
        # Создаем тестовый файл
        test_file = Path("test_code.py")
        test_content = '''
def test_function():
    """A simple test function."""
    return "test"
'''
        test_file.write_text(test_content)

        try:
            result = await mcp_server.handle_tools_call({
                "name": "code_check",
                "arguments": {
                    "file_path": str(test_file),
                    "check_type": "lint"
                }
            }, "test_conn")

            assert "content" in result
            assert "isError" in result
            assert isinstance(result["content"], list)

        finally:
            test_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_prompts_list(self, mcp_server):
        """Тест получения списка промптов."""
        result = await mcp_server.handle_prompts_list({}, "test_conn")

        assert "prompts" in result
        assert isinstance(result["prompts"], list)

        # Проверяем что есть промпты
        assert len(result["prompts"]) > 0

        # Проверяем структуру промптов
        prompt = result["prompts"][0]
        required_fields = ["name", "description"]
        for field in required_fields:
            assert field in prompt

    @pytest.mark.asyncio
    async def test_prompts_get_code_analysis(self, mcp_server):
        """Тест получения промпта code_analysis."""
        result = await mcp_server.handle_prompts_get({
            "name": "code_analysis",
            "arguments": {
                "code": "def hello(): return 'world'",
                "language": "python"
            }
        }, "test_conn")

        assert "description" in result
        assert "messages" in result
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) > 0

        # Проверяем структуру сообщения
        message = result["messages"][0]
        assert "role" in message
        assert "content" in message

    @pytest.mark.asyncio
    async def test_prompts_get_nonexistent(self, mcp_server):
        """Тест получения несуществующего промпта."""
        with pytest.raises(ValueError, match="not found"):
            await mcp_server.handle_prompts_get({
                "name": "nonexistent_prompt"
            }, "test_conn")

    @pytest.mark.asyncio
    async def test_mcp_request_handling(self, mcp_server):
        """Тест обработки полного MCP запроса."""
        # Мокаем WebSocket для тестирования
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_text = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Тестовый запрос инициализации
        init_request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "Test", "version": "1.0.0"}
            }
        }

        mock_ws.receive_text.side_effect = [
            json.dumps(init_request),
            Exception("Connection closed")  # Для выхода из цикла
        ]

        # Запускаем обработку в фоне (но не ждем завершения)
        task = asyncio.create_task(self._mock_websocket_handler(mcp_server, mock_ws))

        # Даем немного времени на обработку
        await asyncio.sleep(0.1)

        # Проверяем что был отправлен ответ
        assert mock_ws.send_json.called

        # Отменяем задачу
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _mock_websocket_handler(self, server, ws):
        """Мок обработчик WebSocket для тестирования."""
        await ws.accept()

        try:
            while True:
                data = await ws.receive_text()
                request_data = json.loads(data)

                # Имитируем обработку запроса
                if request_data.get("method") == "initialize":
                    response = await server.handle_initialize(
                        request_data.get("params", {}),
                        "test_conn"
                    )
                    await ws.send_json({
                        "jsonrpc": "2.0",
                        "id": request_data["id"],
                        "result": response
                    })

        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        """Тест обработки ошибок."""
        # Тест вызова несуществующего метода
        with pytest.raises(Exception):  # Должен быть HTTPException или подобный
            await mcp_server.handle_request({
                "id": "test",
                "method": "nonexistent_method",
                "params": {}
            }, "test_conn")

        # Тест вызова tools/call без имени
        with pytest.raises(ValueError, match="Tool name is required"):
            await mcp_server.handle_tools_call({}, "test_conn")

        # Тест вызова prompts/get без имени
        with pytest.raises(ValueError, match="Prompt name is required"):
            await mcp_server.handle_prompts_get({}, "test_conn")


def run_integration_tests():
    """Запуск интеграционных тестов MCP."""
    print("\n" + "="*70)
    print("ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ MCP СЕРВЕРА")
    print("="*70 + "\n")

    # Запускаем pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])


if __name__ == "__main__":
    run_integration_tests()