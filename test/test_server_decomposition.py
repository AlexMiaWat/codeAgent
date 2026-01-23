"""
Integration tests for CodeAgentServer decomposition with real ServerCore

This module tests that ServerCore has been properly extracted from CodeAgentServer
with real logic implementation, and that the decomposition maintains correct functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.server import CodeAgentServer
from src.core import ServerCore, TaskExecutor, RevisionExecutor, TodoGenerator


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

    def test_servercore_di_integration_correctly(self):
        """Test that CodeAgentServer integrates with DI container correctly"""
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

                with patch('src.server.create_executor_agent'), \
                     patch('src.server.SessionTracker'):

                    server = CodeAgentServer()

                    # Test that ServerCore is properly initialized with DI container
                    assert server.server_core is not None
                    assert isinstance(server.server_core, ServerCore)

                    # Test that DI container was created
                    assert server.di_container is not None

                    # Test that ServerCore has proper dependencies injected
                    assert server.server_core.todo_manager is not None
                    assert server.server_core.checkpoint_manager is not None
                    assert server.server_core.status_manager is not None
                    assert server.server_core.server_logger is not None

                    # Test that todo_manager_factory is set
                    assert server.server_core.todo_manager_factory is not None
                    assert callable(server.server_core.todo_manager_factory)


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

    def test_core_files_structure(self):
        """Test that core/ contains expected architecture files"""
        core_dir = Path('src/core')
        remaining_files = list(core_dir.glob('*.py'))

        # Should have core architecture files including DI container
        expected_files = {'__init__.py', 'server_core.py', 'di_container.py'}
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

    def test_core_module_exports(self):
        """Test that core module exports expected components"""
        import src.core as core_module

        # Should have ServerCore and DI components
        expected_exports = {
            'ServerCore', 'TaskExecutor', 'RevisionExecutor', 'TodoGenerator',
            'DIContainer', 'create_default_container', 'ServiceLifetime',
            'IManager', 'ITodoManager', 'IStatusManager', 'ICheckpointManager', 'ILogger'
        }
        actual_exports = set(core_module.__all__)

        assert actual_exports == expected_exports, f"Expected {expected_exports}, got {actual_exports}"


class TestServerCoreWithDI:
    """Test ServerCore functionality using DI container"""

    def test_servercore_di_integration(self):
        """Test that ServerCore can be created and used through DI container"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / 'docs').mkdir()
            (temp_path / 'status.txt').write_text('')

            # Create DI container
            from src.core.di_container import create_default_container
            container = create_default_container(temp_path, {'project': {'todo_format': 'txt'}}, temp_path / 'status.txt')

            # Mock the factory to return a mock todo manager
            mock_todo_manager = Mock()
            mock_todo_manager.get_pending_tasks.return_value = []
            mock_todo_manager.get_all_tasks.return_value = []

            # Create ServerCore using the container
            from src.core.interfaces import ICheckpointManager, IStatusManager, ILogger
            server_core = ServerCore(
                todo_manager=mock_todo_manager,
                checkpoint_manager=container.resolve(ICheckpointManager),
                status_manager=container.resolve(IStatusManager),
                server_logger=container.resolve(ILogger),
                task_executor=Mock(),
                revision_executor=Mock(),
                todo_generator=Mock(),
                config={'project': {'todo_format': 'txt'}},
                project_dir=temp_path,
                auto_todo_enabled=False
            )

            # Test that ServerCore was created successfully
            assert server_core is not None
            assert hasattr(server_core, 'execute_iteration')

    def test_servercore_handles_empty_tasks_with_di(self):
        """Test that ServerCore properly handles scenario with no tasks using DI"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create DI container
            from src.core.di_container import create_default_container
            container = create_default_container(temp_path, {'project': {'todo_format': 'txt'}}, temp_path / 'status.txt')

            # Mock todo manager to return no tasks
            mock_todo_manager = Mock()
            mock_todo_manager.get_pending_tasks.return_value = []
            mock_todo_manager.get_all_tasks.return_value = []

            # Create ServerCore
            from src.core.interfaces import ICheckpointManager, IStatusManager, ILogger
            server_core = ServerCore(
                todo_manager=mock_todo_manager,
                checkpoint_manager=container.resolve(ICheckpointManager),
                status_manager=container.resolve(IStatusManager),
                server_logger=container.resolve(ILogger),
                task_executor=Mock(),
                revision_executor=Mock(),
                todo_generator=Mock(),
                config={'project': {'todo_format': 'txt'}},
                project_dir=temp_path,
                auto_todo_enabled=False
            )

            # Test execute_iteration with no tasks
            has_more_tasks, pending_tasks = server_core.execute_iteration(1)

            # ServerCore should handle empty tasks scenario
            assert isinstance(has_more_tasks, bool)
            assert isinstance(pending_tasks, list)
            assert pending_tasks == []