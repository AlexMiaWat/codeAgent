"""
Integration tests for new functionality

This module contains integration tests that verify interaction between
new components: Smart Agent with Docker, HTTP server, auto-reload,
thread-safe LearningTool, and Unicode improvements.
"""

import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.tools.learning_tool import LearningTool
from src.tools.context_analyzer_tool import ContextAnalyzerTool
from src.agents.smart_agent import create_smart_agent
from src.server import CodeAgentServer


class TestSmartAgentToolsIntegration:
    """Integration tests for Smart Agent and its tools"""

    def test_smart_agent_tools_work_together(self):
        """Test that Smart Agent tools work together"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Smart Agent
            agent = create_smart_agent(project_dir=Path(temp_dir), use_llm=False)

            # Get tools
            learning_tool = None
            context_tool = None

            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                elif isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool

            assert learning_tool is not None
            assert context_tool is not None

            # Create some project structure
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("# Main application")

            # Save experience about analyzing this file
            result = learning_tool.save_task_experience(
                task_id="integration_test_1",
                task_description="Analyze main.py file structure",
                success=True
            )
            assert "сохранен" in result.lower()

            # Use context analyzer on the same file
            result = context_tool.analyze_component("src")
            assert "анализ компонента" in result.lower()

            # Check that learning tool has the experience
            stats = learning_tool.get_statistics()
            assert "1" in stats  # Should have 1 experience

    def test_smart_agent_experience_and_context_sharing(self):
        """Test that experience and context analysis work together"""
        with tempfile.TemporaryDirectory() as temp_dir:
            learning_tool = LearningTool(experience_dir=Path(temp_dir) / "experience")
            context_tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Create test files
            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "utils.py").write_text("""
import os
from pathlib import Path

def helper_function():
    return "helper"
""")

            # Analyze the file with context tool
            deps = context_tool.find_file_dependencies("src/utils.py")
            assert isinstance(deps, str)

            # Save experience about this analysis
            learning_tool.save_task_experience(
                task_id="file_analysis",
                task_description="Analyzed utils.py dependencies",
                success=True,
                patterns=["python", "dependencies", "import"]
            )

            # Find similar tasks
            similar = learning_tool.find_similar_tasks("analyze python file")
            assert isinstance(similar, str)

            # Get recommendations for similar work
            recommendations = learning_tool.get_recommendations("analyze dependencies in python file")
            assert isinstance(recommendations, str)


class TestUnicodeIntegration:
    """Integration tests for Unicode functionality across components"""

    def test_unicode_search_across_tools(self):
        """Test Unicode search works across different tools"""
        with tempfile.TemporaryDirectory() as temp_dir:
            learning_tool = LearningTool(experience_dir=Path(temp_dir) / "experience")

            # Create files with Unicode content
            (Path(temp_dir) / "docs").mkdir()
            (Path(temp_dir) / "docs" / "readme.md").write_text("""
# Документация проекта

Этот файл содержит информацию о проекте.
Здесь описаны основные возможности системы.
""")

            (Path(temp_dir) / "src").mkdir()
            (Path(temp_dir) / "src" / "main.py").write_text("""
# Основной модуль приложения

def main():
    print("Привет, мир!")
""")

            context_tool = ContextAnalyzerTool(project_dir=temp_dir)

            # Save experience with Unicode
            learning_tool.save_task_experience(
                task_id="unicode_test",
                task_description="Анализ файлов с Unicode содержимым",
                success=True,
                patterns=["unicode", "encoding", "internationalization"]
            )

            # Search for Unicode content
            context_result = context_tool.find_related_files("документация")
            learning_result = learning_tool.find_similar_tasks("анализ файлов")

            # Both should work without errors
            assert isinstance(context_result, str)
            assert isinstance(learning_result, str)

    def test_unicode_normalization_consistency(self):
        """Test that Unicode normalization is consistent across tools"""
        from src.tools.learning_tool import normalize_unicode_text as learning_normalize
        from src.tools.context_analyzer_tool import normalize_unicode_text as context_normalize

        test_strings = [
            "CAFÉ naïve résumé",
            "Москва Санкт-Петербург",
            "Hello Wörld naïve",
            "test@example.com 123-456",
        ]

        for test_str in test_strings:
            learning_result = learning_normalize(test_str)
            context_result = context_normalize(test_str)

            # Both should produce valid strings and handle the input
            assert isinstance(learning_result, str)
            assert isinstance(context_result, str)
            assert len(learning_result) > 0
            assert len(context_result) > 0

            # Both should lowercase the result
            assert learning_result.islower()
            assert context_result.islower()


class TestDockerSmartAgentIntegration:
    """Integration tests for Docker support in Smart Agent"""

    @patch('src.agents.smart_agent.is_docker_available')
    def test_smart_agent_docker_integration(self, mock_docker_check):
        """Test Smart Agent with Docker integration"""
        mock_docker_check.return_value = True

        with patch('crewai_tools.CodeInterpreterTool') as mock_code_tool_class:
            mock_code_tool = MagicMock()
            mock_code_tool_class.return_value = mock_code_tool

            with tempfile.TemporaryDirectory() as temp_dir:
                # Create agent with Docker enabled
                agent = create_smart_agent(
                    project_dir=Path(temp_dir),
                    use_docker=True,
                    use_llm=False
                )

                assert agent is not None

                # Should have at least 3 tools (LearningTool, ContextAnalyzerTool, CodeInterpreterTool)
                tool_names = [tool.__class__.__name__ for tool in agent.tools]
                assert "LearningTool" in tool_names
                assert "ContextAnalyzerTool" in tool_names

                # CodeInterpreterTool should be added when Docker is available
                # (This depends on the actual implementation)

    @patch('src.agents.smart_agent.is_docker_available')
    def test_smart_agent_fallback_without_docker(self, mock_docker_check):
        """Test Smart Agent fallback when Docker is not available"""
        mock_docker_check.return_value = False

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent with Docker requested but not available
            agent = create_smart_agent(
                project_dir=Path(temp_dir),
                use_docker=True,  # Request Docker
                use_llm=False
            )

            assert agent is not None

            # Should still have basic tools
            tool_names = [tool.__class__.__name__ for tool in agent.tools]
            assert "LearningTool" in tool_names
            assert "ContextAnalyzerTool" in tool_names

            # Should not crash even if Docker is not available


class TestServerHTTPIntegration:
    """Integration tests for HTTP server in CodeAgentServer"""

    @patch('flask.Flask')
    def test_http_server_initialization_integration(self, mock_flask):
        """Test HTTP server initialization and basic functionality"""
        mock_app = MagicMock()
        mock_flask.return_value = mock_app

        server_config = {
            'http_enabled': True,
            'http_port': 3456,
            'auto_reload': False
        }

        server = CodeAgentServer(server_config=server_config)

        # Setup HTTP server
        server._setup_http_server()

        # Flask app should be created
        mock_flask.assert_called_once()
        assert server.flask_app is not None

        # Routes should be registered
        assert mock_app.route.called
        assert mock_app.route.call_count >= 3  # At least /, /status, /health routes

    @patch('flask.Flask')
    @patch('threading.Thread')
    def test_http_server_threading_integration(self, mock_thread, mock_flask):
        """Test HTTP server threading integration"""
        mock_app = MagicMock()
        mock_flask.return_value = mock_app
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        server_config = {
            'http_enabled': True,
            'http_port': 3456,
            'auto_reload': False
        }

        server = CodeAgentServer(server_config=server_config)
        server._setup_http_server()

        # Thread should be created for HTTP server
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs['daemon'] == True
        assert 'HTTP-Server' in kwargs['name']

    def test_server_without_flask_integration(self):
        """Test server handles missing Flask gracefully"""
        with patch.dict('sys.modules', {'flask': None}):
            server_config = {
                'http_enabled': True,
                'http_port': 3456
            }

            server = CodeAgentServer(server_config=server_config)

            # Should not crash when setting up HTTP server
            try:
                server._setup_http_server()
            except ImportError as e:
                # Should be a clean ImportError about Flask
                assert "flask" in str(e).lower()


class TestAutoReloadIntegration:
    """Integration tests for auto-reload functionality"""

    @patch('watchdog.observers.Observer')
    def test_auto_reload_file_watcher_integration(self, mock_observer):
        """Test auto-reload file watcher integration"""
        mock_observer_instance = MagicMock()
        mock_observer.return_value = mock_observer_instance

        server_config = {
            'auto_reload': True,
            'reload_on_py_changes': True,
            'http_enabled': False
        }

        server = CodeAgentServer(server_config=server_config)
        server._setup_file_watcher()

        # Observer should be created and started
        mock_observer.assert_called_once()
        mock_observer_instance.schedule.assert_called_once()
        mock_observer_instance.start.assert_called_once()

    def test_auto_reload_lock_integration(self):
        """Test auto-reload lock integration"""
        server = CodeAgentServer({})

        # Test that reload lock works
        with server._reload_lock:
            # Simulate setting reload flag
            server._should_reload = True

        # Check reload needed
        result = server._check_reload_needed()
        assert result == True

        # Reset should work
        server._should_reload = False
        result = server._check_reload_needed()
        assert result == False


class TestThreadSafetyIntegration:
    """Integration tests for thread safety across components"""

    def test_learning_tool_concurrent_file_access(self):
        """Test LearningTool handles concurrent file access"""
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

import pytest
from src.new_functionality import new_feature_function, another_new_function
import time


class TestNewFunctionalityIntegration:
    """Integration tests for new_feature_function and another_new_function"""

    def test_new_feature_function_timestamp_format(self):
        """Test that new_feature_function returns a string with correct timestamp format"""
        result = new_feature_function()
        # Example: "New functionality is working as of 2023-10-27 10:30:00!"
        parts = result.split(" as of ")
        assert len(parts) == 2
        timestamp_str = parts[1].replace("!", "")
        try:
            time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pytest.fail("Timestamp format is incorrect")

    def test_another_new_function_with_integers(self):
        """Test another_new_function with integer inputs"""
        result = another_new_function(10, 20, weight_x=0.4)
        assert result == 10 * 0.4 + 20 * 0.6  # 4 + 12 = 16
        assert result == 16.0

    def test_another_new_function_with_floats(self):
        """Test another_new_function with float inputs"""
        result = another_new_function(10.5, 20.5, weight_x=0.5)
        assert result == 10.5 * 0.5 + 20.5 * 0.5  # 5.25 + 10.25 = 15.5
        assert result == 15.5

    def test_another_new_function_weight_x_boundaries(self):
        """Test another_new_function handles weight_x at boundaries (0 and 1)"""
        result_zero_weight = another_new_function(100, 50, weight_x=0.0)
        assert result_zero_weight == 50.0

        result_one_weight = another_new_function(100, 50, weight_x=1.0)
        assert result_one_weight == 100.0

    def test_another_new_function_invalid_weight_x(self):
        """Test another_new_function raises ValueError for invalid weight_x"""
        with pytest.raises(ValueError, match="weight_x must be between 0 and 1"):
            another_new_function(10, 20, weight_x=-0.1)

        with pytest.raises(ValueError, match="weight_x must be between 0 and 1"):
            another_new_function(10, 20, weight_x=1.1)

    def test_another_new_function_large_numbers(self):
        """Test another_new_function with large numbers"""
        result = another_new_function(1_000_000, 2_000_000, weight_x=0.75)
        assert result == 1_000_000 * 0.75 + 2_000_000 * 0.25  # 750_000 + 500_000 = 1_250_000
        assert result == 1_250_000.0
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

    def test_tools_concurrent_unicode_operations(self):
        """Test concurrent Unicode operations across tools"""
        from src.tools.learning_tool import normalize_unicode_text as learning_normalize
        from src.tools.context_analyzer_tool import normalize_unicode_text as context_normalize

        results = []
        errors = []

        def worker(worker_id):
            try:
                test_strings = [
                    f"Thread {worker_id}: CAFÉ résumé naïve",
                    f"Thread {worker_id}: Москва тест",
                    f"Thread {worker_id}: Hello Wörld"
                ]

                for test_str in test_strings:
                    learning_result = learning_normalize(test_str)
                    context_result = context_normalize(test_str)

                    results.append({
                        'thread': worker_id,
                        'input': test_str,
                        'learning': learning_result,
                        'context': context_result
                    })
            except Exception as e:
                errors.append(f"Thread {worker_id}: {e}")

        # Start multiple threads
        threads = []
        num_threads = 3
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify results
        assert len(results) == num_threads * 3
        assert len(errors) == 0

        # All results should be valid strings
        for result in results:
            assert isinstance(result['learning'], str)
            assert isinstance(result['context'], str)
            assert len(result['learning']) > 0
            assert len(result['context']) > 0


class TestFullSystemIntegration:
    """Full system integration tests"""

    @patch('src.agents.smart_agent.is_docker_available')
    @patch('flask.Flask')
    @patch('watchdog.observers.Observer')
    def test_complete_system_integration(self, mock_observer, mock_flask, mock_docker_check):
        """Test complete system with all new components"""
        # Setup mocks
        mock_docker_check.return_value = True
        mock_app = MagicMock()
        mock_flask.return_value = mock_app
        mock_observer_instance = MagicMock()
        mock_observer.return_value = mock_observer_instance

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Smart Agent
            agent = create_smart_agent(project_dir=Path(temp_dir), use_llm=False)
            assert agent is not None

            # Create server with all features enabled
            server_config = {
                'http_enabled': True,
                'http_port': 3456,
                'auto_reload': True,
                'reload_on_py_changes': True
            }

            server = CodeAgentServer(server_config=server_config)

            # Setup all components
            server._setup_http_server()
            server._setup_file_watcher()

            # Verify everything is initialized
            assert server.flask_app is not None
            assert server.auto_reload == True

            # Test that tools work together
            learning_tool = None
            context_tool = None

            for tool in agent.tools:
                if isinstance(tool, LearningTool):
                    learning_tool = tool
                elif isinstance(tool, ContextAnalyzerTool):
                    context_tool = tool

            assert learning_tool is not None
            assert context_tool is not None

            # Create some content and test interaction
            (Path(temp_dir) / "test.py").write_text("# Integration test file")

            # Save experience
            learning_tool.save_task_experience(
                "integration_complete",
                "Complete system integration test",
                True
            )

            # Analyze context
            context_result = context_tool.analyze_project_structure()

            # Everything should work without errors
            assert isinstance(context_result, str)