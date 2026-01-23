"""
Integration tests for core + quality systems interaction

This module contains integration tests that verify the interaction
between core components (DI container, server core) and quality gates system.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from src.core.di_container import DependencyInjectionContainer
from src.core.server_core import ServerCore
from src.quality.quality_gate_manager import QualityGateManager
from src.quality.reporters import ConsoleReporter, FileReporter
from src.todo_manager import TodoItem


class TestDIQualityIntegration:
    """Integration tests for DI container and quality gates"""

    @pytest.fixture
    def di_container(self):
        """Create DI container with quality gates"""
        container = DependencyInjectionContainer()

        # Register quality components
        container.register_singleton(QualityGateManager, QualityGateManager)
        container.register_singleton(ConsoleReporter, ConsoleReporter)
        container.register_singleton(FileReporter, FileReporter)

        return container

    def test_di_container_quality_registration(self, di_container):
        """Test DI container can register and resolve quality components"""
        # Resolve quality gate manager
        qg_manager = di_container.resolve(QualityGateManager)
        assert isinstance(qg_manager, QualityGateManager)

        # Resolve reporters
        console_reporter = di_container.resolve(ConsoleReporter)
        assert isinstance(console_reporter, ConsoleReporter)

        file_reporter = di_container.resolve(FileReporter)
        assert isinstance(file_reporter, FileReporter)

    def test_quality_components_configuration_via_di(self, di_container):
        """Test quality components can be configured through DI"""
        qg_manager = di_container.resolve(QualityGateManager)

        config = {
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 70.0}
            }
        }

        qg_manager.configure(config)
        assert qg_manager._config == config

    def test_di_quality_lifetime_management(self, di_container):
        """Test DI container manages quality component lifetimes"""
        # Resolve singleton multiple times
        qg1 = di_container.resolve(QualityGateManager)
        qg2 = di_container.resolve(QualityGateManager)

        # Should be same instance (singleton)
        assert qg1 is qg2

        # Configure one, check the other
        qg1.configure({'enabled': True})
        assert qg2._config['enabled'] == True


class TestServerCoreQualityIntegration:
    """Integration tests for ServerCore and Quality Gates"""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for ServerCore"""
        return {
            'todo_manager': Mock(),
            'checkpoint_manager': Mock(),
            'status_manager': Mock(),
            'logger': Mock(),
            'task_executor': AsyncMock(return_value=True),
            'revision_executor': AsyncMock(return_value=True),
            'todo_generator': AsyncMock(return_value=True)
        }

    @pytest.fixture
    def quality_gate_manager(self):
        """Create configured QualityGateManager"""
        manager = QualityGateManager()
        manager.configure({
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 80.0},
                'complexity': {'enabled': True, 'max_complexity': 10}
            }
        })
        return manager

    @pytest.fixture
    def server_core_with_quality(self, mock_components, quality_gate_manager):
        """Create ServerCore with quality gates enabled"""
        config = {
            'quality_gates': {
                'enabled': True,
                'strict_mode': False
            }
        }

        server = ServerCore(
            todo_manager=mock_components['todo_manager'],
            checkpoint_manager=mock_components['checkpoint_manager'],
            status_manager=mock_components['status_manager'],
            server_logger=mock_components['logger'],
            task_executor=mock_components['task_executor'],
            revision_executor=mock_components['revision_executor'],
            todo_generator=mock_components['todo_generator'],
            config=config,
            project_dir=Path.cwd(),
            quality_gate_manager=quality_gate_manager,
            task_delay=0
        )
        return server

    @pytest.mark.asyncio
    async def test_server_core_quality_gates_enabled(self, server_core_with_quality):
        """Test ServerCore properly enables quality gates"""
        server = server_core_with_quality

        assert server._is_quality_gates_enabled() == True
        assert server._quality_gate_manager is not None

    @pytest.mark.asyncio
    async def test_server_core_quality_gates_execution_success(self, server_core_with_quality, mock_components, quality_gate_manager):
        """Test successful quality gates allow task execution"""
        from src.quality.models.quality_result import QualityGateResult, QualityResult, QualityStatus, QualityCheckType

        # Mock successful quality check
        successful_result = QualityGateResult("test")
        successful_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.9
        ))

        with Mock() as mock_run_gates:
            mock_run_gates.return_value = successful_result
            quality_gate_manager.run_all_gates = mock_run_gates

            with Mock() as mock_should_block:
                mock_should_block.return_value = False
                quality_gate_manager.should_block_execution = mock_should_block

                # Create test task
                todo_item = TodoItem(
                    text="Integration test task",
                    category="test",
                    id="integration_test_001"
                )

                # Execute task
                result = await server_core_with_quality.execute_single_task(todo_item, 1, 1)

                # Should succeed
                assert result == True
                mock_components['task_executor'].assert_called_once()

    @pytest.mark.asyncio
    async def test_server_core_quality_gates_execution_blocked(self, server_core_with_quality, mock_components, quality_gate_manager):
        """Test failed quality gates block task execution"""
        from src.quality.models.quality_result import QualityGateResult, QualityResult, QualityStatus, QualityCheckType
        from src.core.server_core import QualityGateException

        # Mock failed quality check
        failed_result = QualityGateResult("test")
        failed_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.FAILED,
            score=0.3
        ))

        with Mock() as mock_run_gates:
            mock_run_gates.return_value = failed_result
            quality_gate_manager.run_all_gates = mock_run_gates

            with Mock() as mock_should_block:
                mock_should_block.return_value = True
                quality_gate_manager.should_block_execution = mock_should_block

                # Enable strict mode
                server_core_with_quality.config['quality_gates']['strict_mode'] = True

                # Create test task
                todo_item = TodoItem(
                    text="Integration test task",
                    category="test",
                    id="integration_test_002"
                )

                # Execute task - should raise exception
                with pytest.raises(QualityGateException):
                    await server_core_with_quality.execute_single_task(todo_item, 1, 1)

                # Task executor should not be called
                mock_components['task_executor'].assert_not_called()

    @pytest.mark.asyncio
    async def test_server_core_quality_gates_disabled(self, server_core_with_quality, mock_components):
        """Test disabled quality gates allow execution without checks"""
        # Disable quality gates
        server_core_with_quality.config['quality_gates']['enabled'] = False

        # Create test task
        todo_item = TodoItem(
            text="Integration test task",
            category="test",
            id="integration_test_003"
        )

        # Execute task
        result = await server_core_with_quality.execute_single_task(todo_item, 1, 1)

        # Should succeed without quality checks
        assert result == True
        mock_components['task_executor'].assert_called_once()


class TestDIQualityServerIntegration:
    """Integration tests for full DI + Quality + Server pipeline"""

    @pytest.fixture
    def full_di_container(self):
        """Create full DI container with all components"""
        container = DependencyInjectionContainer()

        # Register core components
        container.register_singleton(QualityGateManager, QualityGateManager)

        # Register reporters
        container.register_singleton(ConsoleReporter, ConsoleReporter)
        container.register_singleton(FileReporter, FileReporter)

        # Register mock managers
        container.register_singleton('todo_manager', Mock())
        container.register_singleton('checkpoint_manager', Mock())
        container.register_singleton('status_manager', Mock())
        container.register_singleton('logger', Mock())
        container.register_singleton('task_executor', AsyncMock(return_value=True))
        container.register_singleton('revision_executor', AsyncMock(return_value=True))
        container.register_singleton('todo_generator', AsyncMock(return_value=True))

        return container

    def test_di_container_full_registration(self, full_di_container):
        """Test DI container can register all required components"""
        # Resolve all components
        qg_manager = full_di_container.resolve(QualityGateManager)
        console_reporter = full_di_container.resolve(ConsoleReporter)
        file_reporter = full_di_container.resolve(FileReporter)

        todo_manager = full_di_container.resolve('todo_manager')
        checkpoint_manager = full_di_container.resolve('checkpoint_manager')
        status_manager = full_di_container.resolve('status_manager')
        logger = full_di_container.resolve('logger')

        assert qg_manager is not None
        assert console_reporter is not None
        assert file_reporter is not None
        assert todo_manager is not None
        assert checkpoint_manager is not None
        assert status_manager is not None
        assert logger is not None

    def test_di_quality_configuration_chain(self, full_di_container):
        """Test configuration flows through DI-resolved components"""
        qg_manager = full_di_container.resolve(QualityGateManager)
        console_reporter = full_di_container.resolve(ConsoleReporter)

        # Configure quality manager
        qg_config = {
            'enabled': True,
            'strict_mode': True,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 85.0},
                'complexity': {'enabled': True, 'max_complexity': 8}
            }
        }
        qg_manager.configure(qg_config)

        # Configure reporter
        reporter_config = {'verbose': True}
        console_reporter.configure(reporter_config)

        # Verify configurations
        assert qg_manager._config == qg_config
        assert console_reporter is not None  # Configuration stored internally

    @pytest.mark.asyncio
    async def test_full_integration_pipeline(self, full_di_container):
        """Test full integration pipeline from DI to task execution"""
        # Resolve all components
        qg_manager = full_di_container.resolve(QualityGateManager)
        console_reporter = full_di_container.resolve(ConsoleReporter)
        todo_manager = full_di_container.resolve('todo_manager')
        checkpoint_manager = full_di_container.resolve('checkpoint_manager')
        status_manager = full_di_container.resolve('status_manager')
        logger = full_di_container.resolve('logger')
        task_executor = full_di_container.resolve('task_executor')
        revision_executor = full_di_container.resolve('revision_executor')
        todo_generator = full_di_container.resolve('todo_generator')

        # Configure quality gates
        qg_manager.configure({
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 70.0}
            }
        })

        # Create server core with DI-resolved components
        config = {
            'quality_gates': {
                'enabled': True,
                'strict_mode': False
            }
        }

        server = ServerCore(
            todo_manager=todo_manager,
            checkpoint_manager=checkpoint_manager,
            status_manager=status_manager,
            server_logger=logger,
            task_executor=task_executor,
            revision_executor=revision_executor,
            todo_generator=todo_generator,
            config=config,
            project_dir=Path.cwd(),
            quality_gate_manager=qg_manager,
            task_delay=0
        )

        # Create test task
        todo_item = TodoItem(
            text="Full integration test",
            category="integration",
            id="full_integration_test_001"
        )

        # Execute task (should work with mocks)
        result = await server.execute_single_task(todo_item, 1, 1)

        # Verify the pipeline worked
        assert result == True
        task_executor.assert_called_once_with(todo_item, task_number=1, total_tasks=1)


class TestQualityReportingIntegration:
    """Integration tests for quality reporting pipeline"""

    @pytest.fixture
    def quality_reporting_setup(self):
        """Setup quality gates with reporting"""
        qg_manager = QualityGateManager()
        console_reporter = ConsoleReporter()
        file_reporter = FileReporter()

        # Configure quality manager
        qg_manager.configure({
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 75.0},
                'complexity': {'enabled': True, 'max_complexity': 12}
            }
        })

        return {
            'manager': qg_manager,
            'console_reporter': console_reporter,
            'file_reporter': file_reporter
        }

    def test_quality_reporting_chain(self, quality_reporting_setup):
        """Test quality results flow through reporting chain"""
        setup = quality_reporting_setup
        manager = setup['manager']
        console_reporter = setup['console_reporter']
        file_reporter = setup['file_reporter']

        # Create test context
        context = {
            'project_path': '/tmp/test_project',
            'task_type': 'development',
            'files': ['test.py']
        }

        # Run quality gates
        result = manager.run_all_gates(context)

        # Report results
        console_reporter.report(result)

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name

        try:
            file_reporter.configure({'output_file': temp_file})
            file_reporter.report(result)

            # Verify file reporting worked
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert len(content) > 0

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_quality_reporting_error_handling(self, quality_reporting_setup):
        """Test error handling in quality reporting"""
        setup = quality_reporting_setup
        file_reporter = setup['file_reporter']

        # Try to report without configuration (should handle gracefully)
        result = Mock()
        result.get_overall_status.return_value = "PASSED"

        # Should not raise exception even without proper config
        file_reporter.report(result)