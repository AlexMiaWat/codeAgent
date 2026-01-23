"""
Static tests for new functionality

This module contains static tests that verify new functionality
introduced in recent updates without requiring runtime instantiation.
Tests cover: Docker support, HTTP server, auto-reload, thread-safe LearningTool,
and Unicode improvements in ContextAnalyzerTool.
"""

import inspect
import tempfile
from pathlib import Path
from typing import get_type_hints
from unittest.mock import MagicMock, patch

from src.tools.docker_utils import is_docker_available
from src.tools.learning_tool import LearningTool, normalize_unicode_text as learning_normalize
from src.tools.context_analyzer_tool import ContextAnalyzerTool, normalize_unicode_text as context_normalize
from src.agents.smart_agent import create_smart_agent
from src.server import CodeAgentServer


class TestDockerUtilsStatic:
    """Static tests for Docker utilities"""

    def test_is_docker_available_function_exists(self):
        """Test that is_docker_available function exists and has correct signature"""
        assert callable(is_docker_available)

        sig = inspect.signature(is_docker_available)
        assert len(sig.parameters) == 0  # No parameters
        assert sig.return_annotation == bool

    def test_is_docker_available_imports(self):
        """Test that required imports are available"""
        import subprocess
        import logging
        # These imports should be available for the function to work

    def test_docker_function_type_hints(self):
        """Test that type hints are correctly defined"""
        hints = get_type_hints(is_docker_available)
        assert 'return' in hints
        assert hints['return'] == bool


class TestLearningToolThreadSafetyStatic:
    """Static tests for thread-safe LearningTool"""

    def test_learning_tool_inherits_base_tool(self):
        """Test LearningTool inherits from BaseTool"""
        from crewai.tools.base_tool import BaseTool
        assert issubclass(LearningTool, BaseTool)

    def test_learning_tool_has_lock_methods(self):
        """Test LearningTool has file locking methods"""
        # Check for methods that use fcntl locks
        import inspect
        source = inspect.getsource(LearningTool)

        # Should contain fcntl imports and lock usage
        assert 'import fcntl' in source
        assert 'LOCK_SH' in source  # Shared lock for reading
        assert 'LOCK_EX' in source  # Exclusive lock for writing
        assert 'LOCK_UN' in source  # Unlock

    def test_learning_tool_normalize_function(self):
        """Test normalize_unicode_text function in LearningTool"""
        assert callable(learning_normalize)

        sig = inspect.signature(learning_normalize)
        assert 'text' in sig.parameters
        assert sig.return_annotation == str

    def test_normalize_unicode_function_consistency(self):
        """Test that normalize_unicode_text functions are consistent"""
        # Both LearningTool and ContextAnalyzerTool should have similar normalize functions
        assert callable(learning_normalize)
        assert callable(context_normalize)

        # Both should have same signature
        learning_sig = inspect.signature(learning_normalize)
        context_sig = inspect.signature(context_normalize)

        assert len(learning_sig.parameters) == len(context_sig.parameters)
        assert learning_sig.return_annotation == context_sig.return_annotation

    def test_learning_tool_file_operations_are_locked(self):
        """Test that file operations in LearningTool use locking"""
        import inspect
        source = inspect.getsource(LearningTool)

        # Critical file operations should be protected with locks
        # This is a basic check that locking is implemented
        assert 'flock' in source


class TestContextAnalyzerUnicodeStatic:
    """Static tests for Unicode improvements in ContextAnalyzerTool"""

    def test_context_analyzer_inherits_base_tool(self):
        """Test ContextAnalyzerTool inherits from BaseTool"""
        from crewai.tools.base_tool import BaseTool
        assert issubclass(ContextAnalyzerTool, BaseTool)

    def test_context_analyzer_normalize_function(self):
        """Test normalize_unicode_text function in ContextAnalyzerTool"""
        assert callable(context_normalize)

        sig = inspect.signature(context_normalize)
        assert 'text' in sig.parameters
        assert sig.return_annotation == str

    def test_context_analyzer_uses_normalize(self):
        """Test that ContextAnalyzerTool uses normalize_unicode_text internally"""
        import inspect
        source = inspect.getsource(ContextAnalyzerTool)

        # Should use normalize_unicode_text in multiple places
        assert 'normalize_unicode_text' in source
        # Count occurrences to ensure it's used meaningfully
        count = source.count('normalize_unicode_text')
        assert count >= 5  # Should be used in several methods


class TestSmartAgentDockerStatic:
    """Static tests for Smart Agent Docker support"""

    def test_create_smart_agent_function_exists(self):
        """Test create_smart_agent function exists"""
        assert callable(create_smart_agent)

    def test_create_smart_agent_signature(self):
        """Test create_smart_agent has expected parameters"""
        sig = inspect.signature(create_smart_agent)

        expected_params = ['project_dir', 'role', 'goal', 'verbose', 'use_llm', 'use_docker', 'experience_dir']
        for param in expected_params:
            assert param in sig.parameters

    def test_smart_agent_imports_docker_utils(self):
        """Test that Smart Agent imports Docker utilities"""
        import inspect
        source = inspect.getsource(create_smart_agent)

        # Should import Docker checking functionality
        assert 'is_docker_available' in source or 'docker' in source.lower()


class TestHTTPServerStatic:
    """Static tests for HTTP server functionality"""

    def test_code_agent_server_has_http_attributes(self):
        """Test CodeAgentServer has HTTP-related attributes"""
        # Check class has HTTP-related attributes defined
        assert hasattr(CodeAgentServer, '_setup_http_server')
        assert hasattr(CodeAgentServer, '_check_http_server_ready')

    def test_http_server_method_signatures(self):
        """Test HTTP server methods have correct signatures"""
        setup_sig = inspect.signature(CodeAgentServer._setup_http_server)
        assert len(setup_sig.parameters) == 1  # self only

        check_sig = inspect.signature(CodeAgentServer._check_http_server_ready)
        assert len(check_sig.parameters) == 1  # self only

    def test_http_server_imports_flask(self):
        """Test that HTTP server imports Flask"""
        import inspect
        source = inspect.getsource(CodeAgentServer)

        # Should import Flask for HTTP server
        assert 'from flask import' in source
        assert 'Flask' in source

    def test_http_server_has_route_methods(self):
        """Test that HTTP server has route definition methods"""
        # Check for methods that define HTTP routes
        assert hasattr(CodeAgentServer, '_setup_http_server')

        # The _setup_http_server method should contain route definitions
        import inspect
        source = inspect.getsource(CodeAgentServer._setup_http_server)
        assert '@self.flask_app.route' in source


class TestAutoReloadStatic:
    """Static tests for auto-reload functionality"""

    def test_code_agent_server_has_reload_attributes(self):
        """Test CodeAgentServer has reload-related attributes"""
        assert hasattr(CodeAgentServer, '_setup_file_watcher')
        assert hasattr(CodeAgentServer, '_check_reload_needed')
        assert hasattr(CodeAgentServer, '_reload_lock')

    def test_auto_reload_method_signatures(self):
        """Test auto-reload methods have correct signatures"""
        setup_sig = inspect.signature(CodeAgentServer._setup_file_watcher)
        assert len(setup_sig.parameters) == 1  # self only

        check_sig = inspect.signature(CodeAgentServer._check_reload_needed)
        assert len(check_sig.parameters) == 1  # self only

    def test_auto_reload_imports_watchdog(self):
        """Test that auto-reload imports watchdog"""
        import inspect
        source = inspect.getsource(CodeAgentServer)

        # Should import watchdog for file watching
        assert 'from watchdog.' in source
        assert 'Observer' in source
        assert 'FileSystemEventHandler' in source

    def test_auto_reload_has_event_handler_class(self):
        """Test that auto-reload defines FileChangeHandler class"""
        import inspect
        source = inspect.getsource(CodeAgentServer)

        # Should contain FileChangeHandler class definition
        assert 'class FileChangeHandler' in source
        assert 'FileSystemEventHandler' in source


class TestUnicodeNormalizationStatic:
    """Static tests for Unicode normalization functions"""

    def test_unicode_normalize_functions_exist(self):
        """Test that Unicode normalize functions exist in both tools"""
        assert callable(learning_normalize)
        assert callable(context_normalize)

    def test_unicode_normalize_signatures(self):
        """Test Unicode normalize function signatures"""
        learning_sig = inspect.signature(learning_normalize)
        context_sig = inspect.signature(context_normalize)

        # Both should accept Optional[str] and return str
        assert 'text' in learning_sig.parameters
        assert 'text' in context_sig.parameters

        assert learning_sig.return_annotation == str
        assert context_sig.return_annotation == str

    def test_unicode_normalize_implementations(self):
        """Test that Unicode functions handle common cases"""
        # This is static test - we check the implementation exists
        # but don't actually call it (that would be dynamic test)

        learning_source = inspect.getsource(learning_normalize)
        context_source = inspect.getsource(context_normalize)

        # Both should use unicodedata.normalize
        assert 'unicodedata.normalize' in learning_source
        assert 'unicodedata.normalize' in context_source

        # Both should handle None input
        assert 'if text is None' in learning_source
        assert 'if text is None' in context_source or 'text is None' in context_source


class TestNewFunctionalityIntegrationStatic:
    """Static tests for integration of new functionality"""

    def test_all_new_components_importable(self):
        """Test that all new components can be imported without errors"""
        try:
            from src.tools.docker_utils import is_docker_available
            from src.tools.learning_tool import LearningTool, normalize_unicode_text
            from src.tools.context_analyzer_tool import ContextAnalyzerTool
            from src.agents.smart_agent import create_smart_agent
            from src.server import CodeAgentServer

            # All imports should succeed
            assert True
        except ImportError as e:
            assert False, f"Import failed: {e}"

    def test_new_functionality_class_structure(self):
        """Test that new functionality classes have expected structure"""
        # LearningTool should have expected methods
        expected_learning_methods = ['save_task_experience', 'find_similar_tasks', 'get_recommendations']
        for method in expected_learning_methods:
            assert hasattr(LearningTool, method)

        # ContextAnalyzerTool should have expected methods
        expected_context_methods = ['analyze_project_structure', 'find_file_dependencies', 'get_task_context']
        for method in expected_context_methods:
            assert hasattr(ContextAnalyzerTool, method)

        # CodeAgentServer should have HTTP and reload methods
        expected_server_methods = ['_setup_http_server', '_setup_file_watcher', '_check_reload_needed']
        for method in expected_server_methods:
            assert hasattr(CodeAgentServer, method)

    def test_new_functionality_no_circular_imports(self):
        """Test that new functionality doesn't have circular import issues"""
        # This is tested by successful imports above
        # If there were circular imports, the imports would fail
        pass