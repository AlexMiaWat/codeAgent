"""
Tests for new interfaces: IServer, IAgent, ITaskManager

This module contains tests for the newly implemented interfaces
to ensure they follow the correct patterns and can be used in DI.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.core.interfaces import IServer, IAgent, ITaskManager, TaskExecutionState
from src.core.mock_implementations import MockServer, MockAgentManager, MockTaskManager
from src.todo_manager import TodoItem


class TestIServerInterface:
    """Tests for IServer interface"""

    def test_mock_server_creation(self):
        """Test MockServer can be created and implements IServer"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            config = {"test": "config"}

            server = MockServer(project_dir=project_dir, config=config)
            assert server is not None
            assert isinstance(server, IServer)
            assert server.project_dir == project_dir
            assert server.config == config

    def test_mock_server_lifecycle(self):
        """Test MockServer lifecycle methods"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = MockServer(project_dir=Path(temp_dir))

            # Initial state
            assert not server.is_running()
            assert server.is_healthy()

            # Start server
            assert server.start()
            assert server.is_running()

            # Stop server
            assert server.stop()
            assert not server.is_running()

            # Restart server
            assert server.restart()
            assert server.is_running()

    def test_mock_server_status(self):
        """Test MockServer status methods"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = MockServer(project_dir=Path(temp_dir), config={"test": True})

            status = server.get_server_status()
            assert isinstance(status, dict)
            assert "running" in status
            assert "project_dir" in status
            assert "config" in status

            metrics = server.get_metrics()
            assert isinstance(metrics, dict)

    def test_mock_server_task_operations(self):
        """Test MockServer task-related methods"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = MockServer(project_dir=Path(temp_dir))

            # Test task execution
            assert server.execute_task("test_task_id")

            # Test task lists
            pending = server.get_pending_tasks()
            assert isinstance(pending, list)

            active = server.get_active_tasks()
            assert isinstance(active, list)

    def test_mock_server_component_status(self):
        """Test MockServer component status methods"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = MockServer(project_dir=Path(temp_dir))

            # Test component status
            status = server.get_component_status("test_component")
            assert isinstance(status, dict)
            assert "component" in status

            # Test config reload
            assert server.reload_configuration()


class TestIAgentInterface:
    """Tests for IAgent interface"""

    def test_mock_agent_manager_creation(self):
        """Test MockAgentManager can be created and implements IAgent"""
        config = {"test": "config"}
        agent_manager = MockAgentManager(config=config)

        assert agent_manager is not None
        assert isinstance(agent_manager, IAgent)
        assert agent_manager.config == config

    def test_mock_agent_manager_agent_operations(self):
        """Test MockAgentManager agent CRUD operations"""
        agent_manager = MockAgentManager()

        # Test available agents
        available = agent_manager.get_available_agents()
        assert isinstance(available, list)
        assert len(available) > 0

        # Test agent creation
        agent_id = agent_manager.create_agent("executor", {"verbose": True})
        assert agent_id is not None
        assert isinstance(agent_id, str)

        # Test getting agent
        agent = agent_manager.get_agent(agent_id)
        assert agent is not None
        assert agent["type"] == "executor"

        # Test active agents
        active = agent_manager.get_active_agents()
        assert agent_id in active

        # Test agent removal
        assert agent_manager.remove_agent(agent_id)
        assert agent_id not in agent_manager.get_active_agents()

    def test_mock_agent_manager_configuration(self):
        """Test MockAgentManager configuration methods"""
        agent_manager = MockAgentManager()

        # Create agent
        agent_id = agent_manager.create_agent("smart")

        # Test configuration update
        new_config = {"max_iter": 25, "memory": 100}
        assert agent_manager.configure_agent(agent_id, new_config)

        # Verify configuration
        status = agent_manager.get_agent_status(agent_id)
        assert status["config"]["max_iter"] == 25

    def test_mock_agent_manager_execution(self):
        """Test MockAgentManager task execution"""
        agent_manager = MockAgentManager()

        # Create agent
        agent_id = agent_manager.create_agent("executor")

        # Test task execution
        result = agent_manager.execute_with_agent(
            agent_id,
            "Test task description",
            {"context": "test"}
        )

        assert isinstance(result, dict)
        assert result["agent_id"] == agent_id
        assert result["status"] == "completed"

    def test_mock_agent_manager_validation(self):
        """Test MockAgentManager validation methods"""
        agent_manager = MockAgentManager()

        # Test config validation
        assert agent_manager.validate_agent_config("executor", {"valid": True})

        # Test agent types info
        info = agent_manager.get_agent_types_info()
        assert isinstance(info, dict)
        assert "executor" in info


class TestITaskManagerInterface:
    """Tests for ITaskManager interface"""

    def test_mock_task_manager_creation(self):
        """Test MockTaskManager can be created and implements ITaskManager"""
        config = {"test": "config"}
        task_manager = MockTaskManager(config=config)

        assert task_manager is not None
        assert isinstance(task_manager, ITaskManager)
        assert task_manager.config == config

    def test_mock_task_manager_execution_lifecycle(self):
        """Test MockTaskManager execution lifecycle"""
        task_manager = MockTaskManager()

        # Create mock task
        mock_task = Mock(spec=TodoItem)
        mock_task.text = "Test task"
        mock_task.id = "test_task_1"

        # Test execution initialization
        execution_id = task_manager.initialize_task_execution(mock_task)
        assert execution_id is not None
        assert isinstance(execution_id, str)

        # Test execution status
        status = task_manager.get_execution_status(execution_id)
        assert isinstance(status, dict)
        assert status["state"] == TaskExecutionState.INITIALIZING

        # Test task step execution
        step_result = task_manager.execute_task_step(execution_id, {"step": 1})
        assert isinstance(step_result, dict)

        # Test progress monitoring
        progress = task_manager.monitor_task_progress(execution_id)
        assert isinstance(progress, dict)

        # Test finalization
        assert task_manager.finalize_task_execution(execution_id)

    def test_mock_task_manager_error_handling(self):
        """Test MockTaskManager error handling"""
        task_manager = MockTaskManager()

        # Create execution
        mock_task = Mock(spec=TodoItem)
        execution_id = task_manager.initialize_task_execution(mock_task)

        # Test failure handling
        test_error = ValueError("Test error")
        result = task_manager.handle_task_failure(execution_id, test_error)
        assert isinstance(result, dict)

        # Test cancellation
        assert task_manager.cancel_task_execution(execution_id)

    def test_mock_task_manager_history_and_metrics(self):
        """Test MockTaskManager history and metrics"""
        task_manager = MockTaskManager()

        # Create some executions
        mock_task = Mock(spec=TodoItem)
        for i in range(3):
            execution_id = task_manager.initialize_task_execution(mock_task)
            if i < 2:
                task_manager.finalize_task_execution(execution_id)

        # Test active executions
        active = task_manager.get_active_executions()
        assert isinstance(active, list)

        # Test execution history
        history = task_manager.get_execution_history()
        assert isinstance(history, list)
        assert len(history) >= 3

        # Test metrics
        metrics = task_manager.get_execution_metrics()
        assert isinstance(metrics, dict)
        assert "total_executions" in metrics

    def test_mock_task_manager_retry_and_validation(self):
        """Test MockTaskManager retry and validation"""
        task_manager = MockTaskManager()

        # Create execution
        mock_task = Mock(spec=TodoItem)
        execution_id = task_manager.initialize_task_execution(mock_task)

        # Test validation
        validation = task_manager.validate_execution_requirements(execution_id)
        assert isinstance(validation, dict)
        assert validation["valid"]

        # Test retry
        new_execution_id = task_manager.retry_execution(execution_id)
        assert new_execution_id != execution_id


class TestTaskExecutionState:
    """Tests for TaskExecutionState enum"""

    def test_execution_states_exist(self):
        """Test all execution states are defined"""
        states = [
            TaskExecutionState.PENDING,
            TaskExecutionState.INITIALIZING,
            TaskExecutionState.EXECUTING,
            TaskExecutionState.MONITORING,
            TaskExecutionState.COMPLETED,
            TaskExecutionState.FAILED,
            TaskExecutionState.CANCELLED
        ]

        assert len(states) == 7
        for state in states:
            assert isinstance(state, TaskExecutionState)

    def test_execution_state_values(self):
        """Test execution state string values"""
        assert TaskExecutionState.PENDING.value == "pending"
        assert TaskExecutionState.COMPLETED.value == "completed"
        assert TaskExecutionState.FAILED.value == "failed"


class TestInterfacesIntegration:
    """Integration tests for new interfaces with DI container"""

    def test_interfaces_in_di_container(self):
        """Test new interfaces can be registered and resolved in DI container"""
        from src.core.di_container import create_default_container

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            config = {}
            status_file = project_dir / "status.md"

            # Create container with new interfaces
            container = create_default_container(project_dir, config, status_file)

            # Test IServer resolution
            server = container.resolve(IServer)
            assert server is not None
            assert isinstance(server, IServer)

            # Test IAgent resolution
            agent_manager = container.resolve(IAgent)
            assert agent_manager is not None
            assert isinstance(agent_manager, IAgent)

            # Test ITaskManager resolution
            task_manager = container.resolve(ITaskManager)
            assert task_manager is not None
            assert isinstance(task_manager, ITaskManager)

    def test_interface_health_checks(self):
        """Test all new interfaces implement health checks"""
        from src.core.di_container import create_default_container

        with tempfile.TemporaryDirectory() as temp_dir:
            container = create_default_container(
                Path(temp_dir),
                {},
                Path(temp_dir) / "status.md"
            )

            # Test IServer health
            server = container.resolve(IServer)
            assert server.is_healthy()

            # Test IAgent health
            agent_manager = container.resolve(IAgent)
            assert agent_manager.is_healthy()

            # Test ITaskManager health
            task_manager = container.resolve(ITaskManager)
            assert task_manager.is_healthy()