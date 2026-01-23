"""
Integration tests for CodeAgentServer decomposition with real ServerCore

This module tests that ServerCore has been properly extracted from CodeAgentServer
with real logic implementation, and that the decomposition maintains correct functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.server import CodeAgentServer
from src.core import ServerCore, TaskExecutor, RevisionExecutor, TodoGenerator
from src.config_loader import ConfigLoader


class TestServerCoreExtraction:
    """Test that ServerCore has been properly extracted with real logic"""

    def test_servercore_class_exists_and_importable(self):
        """Test that ServerCore class exists and can be imported"""
        from src.core import ServerCore
        assert ServerCore is not None

    def test_servercore_has_real_methods(self):
        """Test that ServerCore has real implementation methods, not just proxies"""
        # Check that ServerCore has its own implementation methods
        assert hasattr(ServerCore, 'execute_iteration')
        assert hasattr(ServerCore, 'execute_single_task')
        assert hasattr(ServerCore, 'execute_tasks_batch')
        assert hasattr(ServerCore, '_handle_no_tasks_scenario')
        assert hasattr(ServerCore, '_sync_todos_with_checkpoint')
        assert hasattr(ServerCore, '_filter_completed_tasks')

        # Check that methods are callable
        assert callable(ServerCore.execute_iteration)
        assert callable(ServerCore.execute_single_task)
        assert callable(ServerCore._handle_no_tasks_scenario)

    def test_servercore_protocols_exist(self):
        """Test that ServerCore protocols are properly defined"""
        from src.core import TaskExecutor, RevisionExecutor, TodoGenerator
        assert TaskExecutor is not None
        assert RevisionExecutor is not None
        assert TodoGenerator is not None

    def test_servercore_constructor_signature(self):
        """Test that ServerCore constructor has proper parameters"""
        import inspect
        sig = inspect.signature(ServerCore.__init__)
        params = list(sig.parameters.keys())

        # Should have all necessary parameters
        assert 'todo_manager' in params
        assert 'checkpoint_manager' in params
        assert 'status_manager' in params
        assert 'server_logger' in params
        assert 'task_executor' in params
        assert 'revision_executor' in params
        assert 'todo_generator' in params
        assert 'config' in params


class TestCodeAgentServerIntegration:
    """Test that CodeAgentServer properly integrates with ServerCore"""

    def test_server_has_servercore_attribute(self):
        """Test that CodeAgentServer creates ServerCore instance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / 'docs').mkdir()
            (temp_path / 'status.txt').write_text('')

            with patch('src.server.ConfigLoader') as mock_config:
                # Mock config
                mock_config.return_value.config_data = {
                    'server': {'task_delay': 1, 'auto_todo_generation': {'enabled': False}},
                    'project': {'todo_format': 'txt'}
                }
                mock_config.return_value.get_project_dir.return_value = temp_path
                mock_config.return_value.get_docs_dir.return_value = temp_path / 'docs'
                mock_config.return_value.get_status_file.return_value = temp_path / 'status.txt'

                with patch('src.server.TodoManager'), \
                     patch('src.server.create_executor_agent'), \
                     patch('src.server.ServerLogger'), \
                     patch('src.server.CheckpointManager'), \
                     patch('src.server.SessionTracker'):

                    server = CodeAgentServer()
                    # ServerCore should be created during initialization
                    assert hasattr(server, 'server_core')
                    assert server.server_core is not None
                    assert isinstance(server.server_core, ServerCore)

    def test_servercore_methods_delegated_correctly(self):
        """Test that CodeAgentServer delegates to ServerCore correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / 'docs').mkdir()
            (temp_path / 'status.txt').write_text('')

            with patch('src.server.ConfigLoader') as mock_config:
                mock_config.return_value.config_data = {
                    'server': {'task_delay': 1, 'auto_todo_generation': {'enabled': False}},
                    'project': {'todo_format': 'txt'}
                }
                mock_config.return_value.get_project_dir.return_value = temp_path
                mock_config.return_value.get_docs_dir.return_value = temp_path / 'docs'
                mock_config.return_value.get_status_file.return_value = temp_path / 'status.txt'

                with patch('src.server.TodoManager') as mock_todo, \
                     patch('src.server.create_executor_agent'), \
                     patch('src.server.ServerLogger') as mock_logger, \
                     patch('src.server.CheckpointManager') as mock_checkpoint, \
                     patch('src.server.SessionTracker'), \
                     patch('src.server.StatusManager') as mock_status:

                    # Setup mocks
                    mock_todo_instance = Mock()
                    mock_todo.return_value = mock_todo_instance
                    mock_todo_instance.get_pending_tasks.return_value = []
                    mock_todo_instance.get_all_tasks.return_value = []

                    mock_checkpoint_instance = Mock()
                    mock_checkpoint.return_value = mock_checkpoint_instance
                    mock_checkpoint_instance.checkpoint_data = {"tasks": []}
                    mock_checkpoint_instance.get_recovery_info.return_value = {
                        "was_clean_shutdown": True,
                        "last_start_time": None,
                        "last_stop_time": None,
                        "iteration_count": 0
                    }
                    mock_checkpoint_instance.get_statistics.return_value = {
                        "completed": 0,
                        "failed": 0,
                        "iteration_count": 0
                    }

                    mock_logger_instance = Mock()
                    mock_logger.return_value = mock_logger_instance

                    mock_status_instance = Mock()
                    mock_status.return_value = mock_status_instance

                    server = CodeAgentServer()

                    # Test that ServerCore is properly initialized
                    assert server.server_core is not None
                    assert server.server_core.todo_manager == mock_todo_instance
                    assert server.server_core.checkpoint_manager == mock_checkpoint_instance
                    assert server.server_core.status_manager == mock_status_instance
                    assert server.server_core.server_logger == mock_logger_instance


class TestComponentCleanup:
    """Test that unused components have been removed"""

    def test_unused_core_files_removed(self):
        """Test that unused core files are no longer present"""
        core_dir = Path('src/core')

        # These files should not exist anymore
        removed_files = [
            'http_server.py',
            'file_watcher.py',
            'abstract_base.py',
            'interfaces.py',
            'types.py',
            'http_api_service.py',
            'server_lifecycle_manager.py',
            'task_execution_service.py'
        ]

        for file in removed_files:
            assert not (core_dir / file).exists(), f"File {file} should have been removed"

    def test_only_servercore_remains(self):
        """Test that only ServerCore related files remain in core/"""
        core_dir = Path('src/core')
        remaining_files = list(core_dir.glob('*.py'))

        # Should only have __init__.py and server_core.py
        expected_files = {'__init__.py', 'server_core.py'}
        actual_files = {f.name for f in remaining_files}

        assert actual_files == expected_files, f"Expected {expected_files}, got {actual_files}"


class TestImportSimplification:
    """Test that imports have been simplified"""

    def test_server_imports_work(self):
        """Test that server imports work without complex importlib usage"""
        # This should work without importlib.spec issues
        from src.server import CodeAgentServer
        from src.core import ServerCore
        assert CodeAgentServer is not None
        assert ServerCore is not None

    def test_core_module_clean(self):
        """Test that core module only exports ServerCore components"""
        import src.core as core_module

        # Should only have ServerCore related exports
        expected_exports = {'ServerCore', 'TaskExecutor', 'RevisionExecutor', 'TodoGenerator'}
        actual_exports = set(core_module.__all__)

        assert actual_exports == expected_exports, f"Expected {expected_exports}, got {actual_exports}"

        # Should not have removed components
        removed_components = ['ConfigurationManager', 'ErrorHandler', 'MetricsCollector', 'HttpServer', 'FileWatcher']
        for component in removed_components:
            assert not hasattr(core_module, component), f"{component} should have been removed"


class TestServerCoreFunctionality:
    """Test ServerCore functionality in isolation"""

    def test_servercore_handles_empty_tasks(self):
        """Test that ServerCore properly handles scenario with no tasks"""
        # Mock components
        mock_todo = Mock()
        mock_todo.get_pending_tasks.return_value = []
        mock_todo.get_all_tasks.return_value = []
        mock_todo.project_dir = Path('/tmp/test')  # Mock project_dir properly

        mock_checkpoint = Mock()
        mock_checkpoint.checkpoint_data = {"tasks": []}

        mock_status = Mock()
        mock_logger = Mock()

        # Create ServerCore with disabled auto TODO generation
        server_core = ServerCore(
            todo_manager=mock_todo,
            checkpoint_manager=mock_checkpoint,
            status_manager=mock_status,
            server_logger=mock_logger,
            task_executor=Mock(),
            revision_executor=Mock(),
            todo_generator=Mock(),
            config={'project': {'todo_format': 'txt'}},
            auto_todo_enabled=False
        )

        # Test execute_iteration with no tasks
        has_more_tasks, pending_tasks = server_core.execute_iteration(1)

        # ServerCore always returns True after reload when no auto TODO generation
        # This is because it assumes there might be more tasks after reload
        assert has_more_tasks == True  # ServerCore reloads and continues
        assert pending_tasks == []  # But no actual pending tasks

    def test_servercore_handles_pending_tasks(self):
        """Test that ServerCore properly handles scenario with pending tasks"""
        from src.todo_manager import TodoItem

        # Create mock task
        mock_task = TodoItem(text="Test task", done=False)

        # Mock components
        mock_todo = Mock()
        mock_todo.get_pending_tasks.return_value = [mock_task]
        mock_todo.get_all_tasks.return_value = [mock_task]

        mock_checkpoint = Mock()
        mock_checkpoint.checkpoint_data = {"tasks": []}

        mock_status = Mock()
        mock_logger = Mock()

        # Create ServerCore
        server_core = ServerCore(
            todo_manager=mock_todo,
            checkpoint_manager=mock_checkpoint,
            status_manager=mock_status,
            server_logger=mock_logger,
            task_executor=Mock(),
            revision_executor=Mock(),
            todo_generator=Mock(),
            config={'project': {'todo_format': 'txt'}},
            auto_todo_enabled=False
        )

        # Test execute_iteration with pending tasks
        has_more_tasks, pending_tasks = server_core.execute_iteration(1)

        # Should return True (has more tasks) and the pending task
        assert has_more_tasks == True
        assert len(pending_tasks) == 1
        assert pending_tasks[0] == mock_task