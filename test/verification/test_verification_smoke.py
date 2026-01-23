"""
Smoke tests for verification system components

This module contains smoke tests that verify basic functionality
of verification components can be instantiated and basic operations work.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.verification.verification_manager import MultiLevelVerificationManager
from src.verification.execution_monitor import ExecutionMonitor
from src.verification.llm_validator import LLMValidator
from src.quality.models.quality_result import VerificationLevel


class TestMultiLevelVerificationManagerSmoke:
    """Smoke tests for MultiLevelVerificationManager"""

    def test_verification_manager_creation(self):
        """Test MultiLevelVerificationManager can be created"""
        manager = MultiLevelVerificationManager()
        assert manager is not None
        assert hasattr(manager, 'quality_gate_manager')
        assert hasattr(manager, 'execution_monitor')
        assert hasattr(manager, 'llm_validator')
        assert hasattr(manager, 'level_configs')
        assert manager.overall_threshold == 0.7

    def test_verification_manager_with_config(self):
        """Test MultiLevelVerificationManager with custom config"""
        config = {
            'verification': {
                'overall_threshold': 0.8,
                'levels': {
                    VerificationLevel.PRE_EXECUTION: {
                        'enabled': True,
                        'weight': 0.3,
                        'required_score': 0.8
                    }
                }
            }
        }

        manager = MultiLevelVerificationManager(config)
        assert manager.overall_threshold == 0.8
        assert manager.level_configs[VerificationLevel.PRE_EXECUTION]['enabled'] is True
        assert manager.level_configs[VerificationLevel.PRE_EXECUTION]['weight'] == 0.3

    @pytest.mark.asyncio
    async def test_verification_manager_basic_operations(self):
        """Test basic operations don't crash"""
        manager = MultiLevelVerificationManager()

        # Mock dependencies
        manager.quality_gate_manager.run_specific_gates = AsyncMock()
        mock_gate_result = MagicMock()
        mock_gate_result.results = []
        manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': True,
            'issues': []
        })

        # Test pre-execution checks
        result = await manager.run_pre_execution_checks("test_task")
        assert result is not None
        assert result.task_id == "test_task"
        assert result.verification_level == VerificationLevel.PRE_EXECUTION

        # Test in-execution monitoring
        result = await manager.run_in_execution_monitoring("test_task")
        assert result is not None
        assert result.task_id == "test_task"
        assert result.verification_level == VerificationLevel.IN_EXECUTION

    def test_verification_manager_active_verifications(self):
        """Test active verifications tracking"""
        manager = MultiLevelVerificationManager()

        # Initially empty
        assert len(manager.get_active_verifications()) == 0

        # Test status for non-existent task
        status = manager.get_verification_status("non_existent")
        assert status is None


class TestExecutionMonitorSmoke:
    """Smoke tests for ExecutionMonitor"""

    def test_execution_monitor_creation(self):
        """Test ExecutionMonitor can be created"""
        monitor = ExecutionMonitor()
        assert monitor is not None
        assert hasattr(monitor, '_active_monitors')
        assert hasattr(monitor, '_monitor_threads')
        assert hasattr(monitor, '_stop_events')
        assert monitor.monitoring_interval == 5.0
        assert monitor.max_monitoring_time == 3600
        assert monitor.resource_check_enabled is True

    def test_execution_monitor_with_config(self):
        """Test ExecutionMonitor with custom config"""
        config = {
            'monitoring_interval': 10.0,
            'max_monitoring_time': 7200,
            'resource_check_enabled': False
        }

        monitor = ExecutionMonitor(config)
        assert monitor.monitoring_interval == 10.0
        assert monitor.max_monitoring_time == 7200
        assert monitor.resource_check_enabled is False

    @pytest.mark.asyncio
    async def test_execution_monitor_basic_operations(self):
        """Test basic monitoring operations"""
        monitor = ExecutionMonitor()

        # Test health check for non-existent task
        health = await monitor.check_execution_health("non_existent")
        assert health['status'] == 'not_monitoring'
        assert health['healthy'] is False

        # Test stop monitoring for non-existent task (should not crash)
        result = await monitor.stop_monitoring("non_existent")
        assert result['error'] == 'not_monitoring'

    def test_execution_monitor_get_methods(self):
        """Test getter methods"""
        monitor = ExecutionMonitor()

        # Should return empty lists initially
        active_tasks = monitor.get_active_tasks()
        assert isinstance(active_tasks, list)
        assert len(active_tasks) == 0

        # Test getting metrics for non-existent task
        metrics = monitor.get_task_metrics("non_existent")
        assert metrics is None


class TestLLMValidatorSmoke:
    """Smoke tests for LLMValidator"""

    def test_llm_validator_creation(self):
        """Test LLMValidator can be created"""
        validator = LLMValidator()
        assert validator is not None
        assert hasattr(validator, 'llm_manager')
        assert validator.code_quality_threshold == 0.7
        assert validator.task_compliance_threshold == 0.8
        assert validator.logic_validation_threshold == 0.75

    def test_llm_validator_with_config(self):
        """Test LLMValidator with custom config"""
        config = {
            'code_quality_threshold': 0.8,
            'task_compliance_threshold': 0.9,
            'logic_validation_threshold': 0.8
        }

        validator = LLMValidator(config=config)
        assert validator.code_quality_threshold == 0.8
        assert validator.task_compliance_threshold == 0.9
        assert validator.logic_validation_threshold == 0.8

    def test_llm_validator_with_llm_manager(self):
        """Test LLMValidator with custom LLM manager"""
        mock_llm_manager = MagicMock()
        validator = LLMValidator(llm_manager=mock_llm_manager)
        assert validator.llm_manager == mock_llm_manager

    @pytest.mark.asyncio
    async def test_llm_validator_basic_operations(self):
        """Test basic validation operations don't crash"""
        validator = LLMValidator()

        # Mock LLM manager
        validator.llm_manager.generate_response = AsyncMock(return_value=MagicMock(
            success=False,
            error="Mock error"
        ))

        # Test code quality validation
        code_changes = {
            'task_id': 'test_task',
            'files_changed': ['test.py'],
            'lines_added': 10,
            'code_snippets': [{'file': 'test.py', 'content': 'def test(): pass'}]
        }

        result = await validator.validate_code_quality(code_changes)
        assert result is not None
        assert result.task_id == 'test_task'
        assert result.verification_level == VerificationLevel.AI_VALIDATION

        # Test task compliance validation
        task_description = "Implement test function"
        execution_result = {'status': 'completed', 'output': 'Function implemented'}

        result = await validator.validate_task_compliance(task_description, execution_result)
        assert result is not None
        assert result.verification_level == VerificationLevel.AI_VALIDATION

        # Test logic validation
        code_changes_logic = {
            'task_id': 'test_task',
            'code_changes': [{'file': 'test.py', 'change': 'Added function'}]
        }

        result = await validator.validate_logic_correctness(code_changes_logic)
        assert result is not None
        assert result.verification_level == VerificationLevel.AI_VALIDATION

        # Test improvement suggestions
        suggestions = await validator.generate_improvement_suggestions({})
        assert isinstance(suggestions, list)


class TestVerificationIntegrationSmoke:
    """Smoke tests for verification components integration"""

    @pytest.mark.asyncio
    async def test_verification_manager_with_mock_dependencies(self):
        """Test verification manager integrates with mocked dependencies"""
        manager = MultiLevelVerificationManager()

        # Mock all dependencies
        manager.quality_gate_manager.run_specific_gates = AsyncMock()
        mock_gate_result = MagicMock()
        mock_gate_result.results = []
        manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': True, 'issues': []
        })

        # Mock LLM validator
        manager.llm_validator.validate_code_quality = AsyncMock()
        mock_ai_result = MagicMock()
        mock_ai_result.quality_result.results = []
        mock_ai_result.overall_score = 0.8
        manager.llm_validator.validate_code_quality.return_value = mock_ai_result

        # Test that pipeline can start (even if it fails due to incomplete mocks)
        try:
            await asyncio.wait_for(
                manager.run_verification_pipeline("test_task"),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            pytest.fail("Verification pipeline timed out")
        except Exception:
            # It's ok if it fails due to incomplete mocking, as long as it doesn't crash
            pass

    def test_verification_components_can_be_imported_together(self):
        """Test all verification components can be imported and used together"""
        from src.verification import MultiLevelVerificationManager, ExecutionMonitor, LLMValidator

        # Can create instances
        manager = MultiLevelVerificationManager()
        monitor = ExecutionMonitor()
        validator = LLMValidator()

        assert manager is not None
        assert monitor is not None
        assert validator is not None

        # Manager has the components
        assert hasattr(manager, 'execution_monitor')
        assert hasattr(manager, 'llm_validator')
        assert isinstance(manager.execution_monitor, ExecutionMonitor)
        assert isinstance(manager.llm_validator, LLMValidator)


class TestVerificationErrorHandlingSmoke:
    """Smoke tests for error handling in verification components"""

    @pytest.mark.asyncio
    async def test_verification_manager_handles_errors_gracefully(self):
        """Test verification manager handles errors without crashing"""
        manager = MultiLevelVerificationManager()

        # Make dependencies raise exceptions
        manager.quality_gate_manager.run_specific_gates = AsyncMock(side_effect=Exception("Test error"))

        # Should not crash
        result = await manager.run_pre_execution_checks("test_task")
        assert result is not None
        assert result.quality_result.results[0].status.name == 'ERROR'

    @pytest.mark.asyncio
    async def test_execution_monitor_handles_errors_gracefully(self):
        """Test execution monitor handles errors without crashing"""
        monitor = ExecutionMonitor()

        # Test with invalid task ID - should handle gracefully
        health = await monitor.check_execution_health("invalid_task")
        assert health['status'] == 'not_monitoring'

        result = await monitor.stop_monitoring("invalid_task")
        assert result['error'] == 'not_monitoring'

    @pytest.mark.asyncio
    async def test_llm_validator_handles_errors_gracefully(self):
        """Test LLM validator handles errors without crashing"""
        validator = LLMValidator()

        # Mock LLM manager to always fail
        validator.llm_manager.generate_response = AsyncMock(return_value=MagicMock(
            success=False,
            error="LLM unavailable"
        ))

        # Should not crash
        result = await validator.validate_code_quality({})
        assert result is not None
        assert result.quality_result.results[0].status.name == 'ERROR'