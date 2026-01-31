"""Пользовательские инструменты для Code Agent"""

from .learning_tool import LearningTool
from .context_analyzer_tool import ContextAnalyzerTool
from .docker_utils import is_docker_available

# MCP инструменты (импортируются для регистрации в CrewAI)
try:
    from .mcp_tool import (
        search_project_files, read_project_file, get_project_structure,
        list_project_resources, call_mcp_tool, get_server_metrics,
        analyze_code_context
    )
    MCP_TOOLS_AVAILABLE = True
    __all__.extend([
        "search_project_files", "read_project_file", "get_project_structure",
        "list_project_resources", "call_mcp_tool", "get_server_metrics",
        "analyze_code_context", "MCP_TOOLS_AVAILABLE"
    ])
except ImportError:
    MCP_TOOLS_AVAILABLE = False

__all__ = ["LearningTool", "ContextAnalyzerTool", "is_docker_available", "MCP_TOOLS_AVAILABLE"]
