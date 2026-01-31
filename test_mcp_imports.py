#!/usr/bin/env python3
"""
Тест импортов MCP компонентов.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_mcp_imports():
    """Тестирование импортов MCP."""
    try:
        print("Testing MCP imports...")

        # Тест базовых импортов
        from mcp.auth import AuthManager
        print("✓ AuthManager imported")

        from mcp.cache import CacheManager
        print("✓ CacheManager imported")

        from mcp.metrics import MetricsManager
        print("✓ MetricsManager imported")

        from mcp.resources import ResourceManager
        print("✓ ResourceManager imported")

        from mcp.tools import ToolsManager
        print("✓ ToolsManager imported")

        from mcp.prompts import PromptsManager
        print("✓ PromptsManager imported")

        # Тест основного сервера
        from mcp.server import MCPServer
        print("✓ MCPServer imported")

        # Тест server.py
        import server
        print(f"✓ server.py imported, MCP_AVAILABLE: {server.MCP_AVAILABLE}")

        print("\n🎉 All MCP imports successful!")
        return True

    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mcp_imports()
    sys.exit(0 if success else 1)