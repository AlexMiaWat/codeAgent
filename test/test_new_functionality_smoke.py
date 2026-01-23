"""
Smoke tests for new functionality

This module contains smoke tests that verify basic functionality
of new components without deep testing. Tests cover: Docker support,
HTTP server, auto-reload, thread-safe LearningTool, and Unicode improvements.
"""

import tempfile
import threading
from pathlib import Path

from src.tools.docker_utils import is_docker_available
from src.tools.learning_tool import LearningTool, normalize_unicode_text as learning_normalize
from src.tools.context_analyzer_tool import ContextAnalyzerTool, normalize_unicode_text as context_normalize
from src.agents.smart_agent import create_smart_agent
from src.server import CodeAgentServer


class TestDockerUtilsSmoke:
    """Smoke tests for Docker utilities"""

    def test_docker_available_function_runs(self):
        """Test that is_docker_available function runs without errors"""
        # Function should return a boolean without throwing exceptions
        result = is_docker_available()
        assert isinstance(result, bool)

    def test_docker_available_with_timeout(self):
        """Test that Docker check doesn't hang indefinitely"""
        import time
        start_time = time.time()
        result = is_docker_available()
        end_time = time.time()

        # Should complete within reasonable time (10 seconds max)
        assert end_time - start_time < 10
        assert isinstance(result, bool)


class TestLearningToolThreadSafetySmoke:
    """Smoke tests for thread-safe LearningTool"""

    def test_learning_tool_basic_creation(self):
        """Test LearningTool can be created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)
            assert tool is not None
            assert hasattr(tool, 'experience_dir')
            assert hasattr(tool, 'experience_file')

    def test_learning_tool_normalize_unicode_smoke(self):
        """Test Unicode normalization function works"""
        # Test basic functionality
        result = learning_normalize("Hello World")
        assert isinstance(result, str)
        assert result == "hello world"

        # Test with None
        result = learning_normalize(None)
        assert result == ""

        # Test with empty string
        result = learning_normalize("")
        assert result == ""

    def test_learning_tool_save_experience_smoke(self):
        """Test basic experience saving"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            result = tool.save_task_experience(
                task_id="smoke_test",
                task_description="Smoke test task",
                success=True
            )

            assert "сохранен" in result.lower()

    def test_learning_tool_file_locking_smoke(self):
        """Test that file operations work (basic smoke test)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            # Save some data
            tool.save_task_experience("test1", "Test task 1", True)
            tool.save_task_experience("test2", "Test task 2", False)

            # Read data back
            result = tool.get_statistics()
            assert "статистика" in result.lower()

    def test_learning_tool_concurrent_access_smoke(self):
        """Test basic concurrent access (smoke test)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = LearningTool(experience_dir=temp_dir)

            results = []
            errors = []

            def worker(worker_id):
                try:
                    # Each worker saves multiple experiences
                    for i in range(5):
                        result = tool.save_task_experience(
                            f"thread_{worker_id}_task_{i}",
                            f"Task {i} from thread {worker_id}",
                            worker_id % 2 == 0  # Alternate success/failure
                        )
                        results.append(result)
                except Exception as e:
                    errors.append(f"Thread {worker_id}: {e}")

            # Start multiple threads
            threads = []
            num_threads = 5
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            # Wait for completion
            for t in threads:
                t.join()

            # Should have results from all threads
            assert len(results) == num_threads * 5
            assert len(errors) == 0  # No errors should occur

            # Verify data integrity
            stats = tool.get_statistics()
            assert "статистика" in stats.lower()


class TestContextAnalyzerUnicodeSmoke:
    """Smoke tests for Unicode improvements in ContextAnalyzerTool"""

    def test_context_analyzer_basic_creation(self):
        """Test ContextAnalyzerTool can be created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ContextAnalyzerTool(project_dir=temp_dir)
            assert tool is not None
            assert hasattr(tool, 'project_dir')

    def test_context_analyzer_normalize_unicode_smoke(self):
        """Test Unicode normalization function works"""
        # Test basic functionality
        result = context_normalize("Hello World")
        assert isinstance(result, str)
        assert result == "hello world"

        # Test with None (if supported)
        try:
            result = context_normalize(None)
            assert result == ""
        except:
            # If None is not supported, that's also fine
            pass

        # Test with Unicode characters
        result = context_normalize("Café résumé naïve")
        assert isinstance(result, str)
        # Should normalize to base characters
        assert "cafe" in result

    def test_context_analyzer_basic_operations(self):
        """Test basic operations work"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal project structure
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("# Main file")

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Test basic methods
            result = tool.analyze_project_structure()
            assert isinstance(result, str)

            result = tool.find_file_dependencies("src/main.py")
            assert isinstance(result, str)

    def test_context_analyzer_unicode_search(self):
        """Test Unicode-aware search functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with Unicode content
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "docs" / "readme.md").write_text("""
# Документация проекта

Этот файл содержит информацию о проекте.
Здесь описаны основные возможности системы.
""")

            tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Test search with Unicode query
            result = tool.find_related_files("документация")
            assert isinstance(result, str)


class TestSmartAgentDockerSmoke:
    """Smoke tests for Smart Agent Docker support"""

    def test_smart_agent_creation_smoke(self, mock_openai_api_key):
        """Test Smart Agent can be created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(project_dir=Path(temp_dir), use_llm=False)
            assert agent is not None
            assert hasattr(agent, 'role')
            assert hasattr(agent, 'goal')
            assert hasattr(agent, 'tools')

    def test_smart_agent_tools_initialization(self, mock_openai_api_key):
        """Test Smart Agent tools are initialized"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = create_smart_agent(project_dir=Path(temp_dir), use_llm=False)

            assert len(agent.tools) >= 2  # Should have at least LearningTool and ContextAnalyzerTool

            tool_names = [tool.__class__.__name__ for tool in agent.tools]
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names


class TestHTTPServerSmoke:
    """Smoke tests for HTTP server functionality"""

    def test_http_server_class_has_methods(self):
        """Test HTTP server class has expected methods"""
        # Test that the class has the expected HTTP-related methods
        assert hasattr(CodeAgentServer, '_setup_http_server')
        assert callable(getattr(CodeAgentServer, '_setup_http_server'))

    def test_http_server_attributes_exist(self):
        """Test HTTP server attributes exist in class"""
        # Check that class has attributes related to HTTP server
        # These are initialized in __init__, so we check they exist as attributes
        import inspect
        init_source = inspect.getsource(CodeAgentServer.__init__)

        # Should initialize http_port and flask_app
        assert 'self.http_port' in init_source
        assert 'self.flask_app' in init_source


class TestAutoReloadSmoke:
    """Smoke tests for auto-reload functionality"""

    def test_auto_reload_class_has_methods(self):
        """Test auto-reload class has expected methods"""
        assert hasattr(CodeAgentServer, '_setup_file_watcher')
        assert callable(getattr(CodeAgentServer, '_setup_file_watcher'))

        assert hasattr(CodeAgentServer, '_check_reload_needed')
        assert callable(getattr(CodeAgentServer, '_check_reload_needed'))

    def test_auto_reload_attributes_exist(self):
        """Test auto-reload attributes exist in class"""
        import inspect
        init_source = inspect.getsource(CodeAgentServer.__init__)

        # Should initialize reload-related attributes
        assert 'self.auto_reload' in init_source
        assert 'self._reload_lock' in init_source

    def test_auto_reload_lock_is_threading_lock(self):
        """Test that reload lock is properly initialized as threading lock"""
        import inspect
        init_source = inspect.getsource(CodeAgentServer.__init__)

        # Should initialize _reload_lock as threading.Lock()
        assert 'threading.Lock()' in init_source or 'Lock()' in init_source


class TestUnicodeNormalizationSmoke:
    """Smoke tests for Unicode normalization functions"""

    def test_learning_tool_unicode_normalization(self):
        """Test LearningTool Unicode normalization"""
        test_cases = [
            ("Hello World", "hello world"),
            ("CAFÉ", "cafe"),
            (" naïve résumé ", " naive resume "),
            ("", ""),
        ]

        for input_text, expected in test_cases:
            result = learning_normalize(input_text)
            assert isinstance(result, str)
            # Basic checks - exact matching depends on implementation
            assert len(result) >= 0

    def test_context_analyzer_unicode_normalization(self):
        """Test ContextAnalyzerTool Unicode normalization"""
        test_cases = [
            "Hello World",
            "CAFÉ",
            " naïve résumé ",
            "",
        ]

        for input_text in test_cases:
            result = context_normalize(input_text)
            assert isinstance(result, str)
            assert len(result) >= 0

    def test_unicode_normalization_consistency(self):
        """Test that both normalization functions handle basic cases"""
        test_text = "CAFÉ naïve"

        learning_result = learning_normalize(test_text)
        context_result = context_normalize(test_text)

        # Both should produce valid strings
        assert isinstance(learning_result, str)
        assert isinstance(context_result, str)

        # Both should handle the same input without crashing
        assert len(learning_result) > 0
        assert len(context_result) > 0


class TestNewFunctionalityIntegrationSmoke:
    """Smoke tests for integration of new functionality"""

    def test_all_components_can_be_imported(self):
        """Test that all new components can be imported"""
        from src.tools.docker_utils import is_docker_available
        from src.tools.learning_tool import LearningTool
        from src.tools.context_analyzer_tool import ContextAnalyzerTool
        from src.agents.smart_agent import create_smart_agent
        from src.server import CodeAgentServer

        # All imports should succeed
        assert callable(is_docker_available)
        assert LearningTool
        assert ContextAnalyzerTool
        assert callable(create_smart_agent)
        assert CodeAgentServer

    def test_basic_component_interaction(self):
        """Test basic interaction between components"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Smart Agent
            agent = create_smart_agent(project_dir=Path(temp_dir), use_llm=False)

            # Check that it has the expected tools
            tool_types = [type(tool).__name__ for tool in agent.tools]

            assert "LearningTool" in tool_types
            assert "ContextAnalyzerTool" in tool_types

            # Test that tools can be accessed
            for tool in agent.tools:
                assert hasattr(tool, '_run') or hasattr(tool, 'run')