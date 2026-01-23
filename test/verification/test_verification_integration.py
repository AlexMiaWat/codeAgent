"""
Integration tests for verification system

This module contains integration tests that verify the complete
verification pipeline and interactions between components.
"""

import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

from src.verification.verification_manager import MultiLevelVerificationManager
from src.verification.execution_monitor import ExecutionMonitor
from src.verification.llm_validator import LLMValidator
from src.quality.models.quality_result import VerificationLevel, QualityStatus


class TestVerificationPipelineIntegration:
    """Integration tests for the complete verification pipeline"""

    @pytest.fixture
    async def setup_verification_pipeline(self):
        """Setup complete verification pipeline with mocked dependencies"""
        # Create components
        manager = MultiLevelVerificationManager()

        # Mock quality gate manager to return successful results
        manager.quality_gate_manager.run_specific_gates = AsyncMock()
        mock_gate_result = MagicMock()
        mock_gate_result.results = [
            MagicMock(status=QualityStatus.PASSED, score=0.9, check_type=MagicMock()),
            MagicMock(status=QualityStatus.PASSED, score=0.85, check_type=MagicMock())
        ]
        mock_gate_result.has_errors.return_value = False
        manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

        # Mock execution monitor
        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': True,
            'issues': [],
            'cpu_usage': 45.0,
            'memory_usage': 60.0
        })

        # Mock LLM validator
        manager.llm_validator.validate_code_quality = AsyncMock()
        manager.llm_validator.validate_logic_correctness = AsyncMock()
        manager.llm_validator.validate_task_compliance = AsyncMock()

        # Create mock AI validation results
        ai_result = MagicMock()
        ai_result.quality_result.results = [MagicMock(status=QualityStatus.PASSED, score=0.8)]
        ai_result.overall_score = 0.8

        manager.llm_validator.validate_code_quality.return_value = ai_result
        manager.llm_validator.validate_logic_correctness.return_value = ai_result
        manager.llm_validator.validate_task_compliance.return_value = ai_result

        return manager

    @pytest.mark.asyncio
    async def test_full_verification_pipeline_success(self, setup_verification_pipeline):
        """Test complete verification pipeline with all levels passing"""
        manager = setup_verification_pipeline

        # Run full verification pipeline
        result = await manager.run_verification_pipeline("integration_test_task_001")

        # Verify overall result
        assert result.task_id == "integration_test_task_001"
        assert result.is_successful is True
        assert result.execution_time >= 0
        assert result.overall_score > 0

        # Verify all verification levels were executed
        assert len(result.results_by_level) == 5  # All 5 levels
        assert VerificationLevel.PRE_EXECUTION in result.results_by_level
        assert VerificationLevel.IN_EXECUTION in result.results_by_level
        assert VerificationLevel.POST_EXECUTION in result.results_by_level
        assert VerificationLevel.AI_VALIDATION in result.results_by_level
        assert VerificationLevel.CROSS_VALIDATION in result.results_by_level

        # Verify cross-validation score was calculated
        assert result.cross_validation_score >= 0.0

        # Verify cleanup - task should be removed from active verifications
        assert "integration_test_task_001" not in manager.active_verifications

    @pytest.mark.asyncio
    async def test_verification_pipeline_with_pre_execution_failure(self, setup_verification_pipeline):
        """Test pipeline with pre-execution level failure"""
        manager = setup_verification_pipeline

        # Make pre-execution checks fail
        failed_gate_result = MagicMock()
        failed_gate_result.results = [MagicMock(status=QualityStatus.FAILED, score=0.3)]
        failed_gate_result.has_errors.return_value = True

        # Return failed result only for pre-execution
        call_count = 0
        async def mock_run_specific_gates(checks, context):
            nonlocal call_count
            call_count += 1
            if 'pre_execution' in str(checks).lower() or call_count == 1:
                return failed_gate_result
            else:
                return MagicMock(results=[], has_errors=lambda: False)

        manager.quality_gate_manager.run_specific_gates = mock_run_specific_gates

        result = await manager.run_verification_pipeline("failed_pre_execution_task")

        # Pipeline should complete but with lower success score
        assert result.task_id == "failed_pre_execution_task"
        assert result.execution_time >= 0

        # Pre-execution should have failed
        pre_result = result.results_by_level.get(VerificationLevel.PRE_EXECUTION)
        assert pre_result is not None
        assert pre_result.quality_result.results[0].status == QualityStatus.FAILED

    @pytest.mark.asyncio
    async def test_verification_pipeline_with_execution_monitoring_issues(self, setup_verification_pipeline):
        """Test pipeline with execution monitoring issues"""
        manager = setup_verification_pipeline

        # Make execution monitoring report issues
        manager.execution_monitor.check_execution_health.return_value = {
            'healthy': False,
            'issues': ['high_cpu_usage_95.0%', 'no_progress_for_350s'],
            'cpu_usage': 95.0,
            'memory_usage': 80.0
        }

        result = await manager.run_verification_pipeline("monitoring_issues_task")

        # Should complete but in-execution should show warnings/issues
        assert result.task_id == "monitoring_issues_task"
        assert result.execution_time >= 0

        in_execution_result = result.results_by_level.get(VerificationLevel.IN_EXECUTION)
        assert in_execution_result is not None

        # Should have some issues recorded
        health_data = in_execution_result.metadata.get('health_status', {})
        assert not health_data.get('healthy', True)

    @pytest.mark.asyncio
    async def test_verification_pipeline_with_ai_validation_failure(self, setup_verification_pipeline):
        """Test pipeline with AI validation failures"""
        manager = setup_verification_pipeline

        # Make AI validation fail
        failed_ai_result = MagicMock()
        failed_ai_result.quality_result.results = [MagicMock(status=QualityStatus.ERROR, score=0.0)]
        failed_ai_result.overall_score = 0.0

        manager.llm_validator.validate_code_quality = AsyncMock(return_value=failed_ai_result)

        result = await manager.run_verification_pipeline("ai_failure_task")

        # Should complete but AI validation should fail
        ai_result = result.results_by_level.get(VerificationLevel.AI_VALIDATION)
        assert ai_result is not None
        assert ai_result.quality_result.results[0].status == QualityStatus.ERROR

    @pytest.mark.asyncio
    async def test_concurrent_verification_pipelines(self, setup_verification_pipeline):
        """Test running multiple verification pipelines concurrently"""
        manager = setup_verification_pipeline

        # Run multiple pipelines concurrently
        tasks = []
        for i in range(3):
            task_id = f"concurrent_task_{i}"
            tasks.append(manager.run_verification_pipeline(task_id))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed with: {result}"
            assert result.task_id == f"concurrent_task_{i}"
            assert result.is_successful is True

    @pytest.mark.asyncio
    async def test_verification_with_real_execution_monitor(self):
        """Test verification pipeline with real execution monitor integration"""
        manager = MultiLevelVerificationManager()

        # Use real execution monitor but mock other components
        manager.quality_gate_manager.run_specific_gates = AsyncMock()
        mock_gate_result = MagicMock()
        mock_gate_result.results = []
        mock_gate_result.has_errors.return_value = False
        manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

        manager.llm_validator.validate_code_quality = AsyncMock()
        ai_result = MagicMock()
        ai_result.quality_result.results = [MagicMock(status=QualityStatus.PASSED, score=0.8)]
        ai_result.overall_score = 0.8
        manager.llm_validator.validate_code_quality.return_value = ai_result

        # Run pipeline - execution monitor should work normally
        result = await manager.run_verification_pipeline("real_monitor_task")

        assert result.task_id == "real_monitor_task"
        assert VerificationLevel.IN_EXECUTION in result.results_by_level

        # Check that execution monitor was actually used
        in_execution_result = result.results_by_level[VerificationLevel.IN_EXECUTION]
        assert 'monitoring_active' in in_execution_result.metadata

    @pytest.mark.asyncio
    async def test_verification_with_different_configurations(self):
        """Test verification pipeline with different configuration settings"""

        # Test with custom configuration
        config = {
            'verification': {
                'overall_threshold': 0.9,
                'levels': {
                    VerificationLevel.PRE_EXECUTION: {
                        'enabled': True,
                        'weight': 0.4,
                        'required_score': 0.8
                    },
                    VerificationLevel.IN_EXECUTION: {
                        'enabled': True,
                        'weight': 0.4,
                        'required_score': 0.9
                    },
                    VerificationLevel.POST_EXECUTION: {
                        'enabled': True,
                        'weight': 0.2,
                        'required_score': 0.85
                    },
                    VerificationLevel.AI_VALIDATION: {
                        'enabled': False,  # Disable AI validation
                        'weight': 0.0,
                        'required_score': 0.0
                    }
                }
            }
        }

        manager = MultiLevelVerificationManager(config)

        # Mock dependencies
        manager.quality_gate_manager.run_specific_gates = AsyncMock()
        mock_gate_result = MagicMock()
        mock_gate_result.results = [MagicMock(status=QualityStatus.PASSED, score=0.95)]
        mock_gate_result.has_errors.return_value = False
        manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': True, 'issues': []
        })

        # AI validation should be disabled
        result = await manager.run_verification_pipeline("custom_config_task")

        assert result.task_id == "custom_config_task"
        assert manager.overall_threshold == 0.9

        # AI validation should not be in results
        assert VerificationLevel.AI_VALIDATION not in result.results_by_level

        # But other levels should be present
        assert VerificationLevel.PRE_EXECUTION in result.results_by_level
        assert VerificationLevel.IN_EXECUTION in result.results_by_level
        assert VerificationLevel.POST_EXECUTION in result.results_by_level

    @pytest.mark.asyncio
    async def test_verification_pipeline_error_recovery(self):
        """Test that pipeline continues despite individual level failures"""
        manager = MultiLevelVerificationManager()

        # Mock dependencies with mixed success/failure
        call_count = 0
        async def mock_quality_gates(checks, context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Pre-execution
                failed_result = MagicMock()
                failed_result.results = [MagicMock(status=QualityStatus.FAILED, score=0.2)]
                failed_result.has_errors.return_value = True
                return failed_result
            else:  # Post-execution
                success_result = MagicMock()
                success_result.results = [MagicMock(status=QualityStatus.PASSED, score=0.9)]
                success_result.has_errors.return_value = False
                return success_result

        manager.quality_gate_manager.run_specific_gates = mock_quality_gates

        # Execution monitor succeeds
        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': True, 'issues': []
        })

        # AI validation fails
        manager.llm_validator.validate_code_quality = AsyncMock(side_effect=Exception("AI service down"))

        # Pipeline should complete despite failures
        result = await manager.run_verification_pipeline("error_recovery_task")

        assert result.task_id == "error_recovery_task"
        assert result.execution_time >= 0

        # Should have results for all levels, some with errors
        assert len(result.results_by_level) == 5

        # Pre-execution should have failed
        pre_result = result.results_by_level[VerificationLevel.PRE_EXECUTION]
        assert pre_result.quality_result.results[0].status == QualityStatus.FAILED

        # AI validation should have error
        ai_result = result.results_by_level[VerificationLevel.AI_VALIDATION]
        assert ai_result.quality_result.results[0].status == QualityStatus.ERROR

    @pytest.mark.asyncio
    async def test_verification_status_tracking(self):
        """Test that verification status is properly tracked"""
        manager = MultiLevelVerificationManager()

        # Mock dependencies for successful run
        manager.quality_gate_manager.run_specific_gates = AsyncMock()
        mock_gate_result = MagicMock()
        mock_gate_result.results = []
        manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': True, 'issues': []
        })

        # Run pipeline
        result = await manager.run_verification_pipeline("status_tracking_task")

        # Check that we can get status during execution (would need to be tested differently)
        # For now, just verify the result has proper status
        assert result.is_successful is True
        assert result.overall_score >= 0.7  # Above threshold

    @pytest.mark.asyncio
    async def test_verification_component_interaction(self):
        """Test interactions between verification components"""
        manager = MultiLevelVerificationManager()

        # Test that components can be accessed and interact
        assert hasattr(manager, 'execution_monitor')
        assert hasattr(manager, 'llm_validator')
        assert hasattr(manager, 'quality_gate_manager')

        # Test that execution monitor can be used independently
        await manager.execution_monitor.start_monitoring("component_test_task")
        health = await manager.execution_monitor.check_execution_health("component_test_task")
        assert 'healthy' in health

        # Clean up
        await manager.execution_monitor.stop_monitoring("component_test_task")

        # Test that LLM validator can be used independently
        suggestions = await manager.llm_validator.generate_improvement_suggestions({
            'issues': ['test issue']
        })
        assert isinstance(suggestions, list)


class TestVerificationEndToEndScenarios:
    """End-to-end scenario tests for verification system"""

    @pytest.mark.asyncio
    async def test_code_development_verification_scenario(self):
        """Test complete verification scenario for code development task"""
        manager = MultiLevelVerificationManager()

        # Mock all components for a realistic code development scenario
        manager.quality_gate_manager.run_specific_gates = AsyncMock()

        # Pre-execution: Good code quality checks pass
        pre_gate_result = MagicMock()
        pre_gate_result.results = [
            MagicMock(status=QualityStatus.PASSED, score=0.9, check_type=MagicMock(value='coverage')),
            MagicMock(status=QualityStatus.PASSED, score=0.85, check_type=MagicMock(value='style'))
        ]
        pre_gate_result.has_errors.return_value = False

        # Post-execution: Code changes validated successfully
        post_gate_result = MagicMock()
        post_gate_result.results = [
            MagicMock(status=QualityStatus.PASSED, score=0.95, check_type=MagicMock(value='output_validation'))
        ]
        post_gate_result.has_errors.return_value = False

        # Alternate between pre and post execution results
        call_count = 0
        async def mock_gates(checks, context):
            nonlocal call_count
            call_count += 1
            if 'DEPENDENCY' in str(checks) or 'TASK_TYPE' in str(checks):
                return pre_gate_result
            else:
                return post_gate_result

        manager.quality_gate_manager.run_specific_gates = mock_gates

        # Execution monitoring: Healthy execution
        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': True,
            'issues': [],
            'cpu_usage': 35.0,
            'memory_usage': 45.0,
            'time_since_progress': 45  # Recent progress
        })

        # AI validation: Good code quality and task compliance
        ai_code_result = MagicMock()
        ai_code_result.quality_result.results = [MagicMock(status=QualityStatus.PASSED, score=0.88)]
        ai_code_result.overall_score = 0.88

        ai_compliance_result = MagicMock()
        ai_compliance_result.quality_result.results = [MagicMock(status=QualityStatus.PASSED, score=0.92)]
        ai_compliance_result.overall_score = 0.92

        manager.llm_validator.validate_code_quality = AsyncMock(return_value=ai_code_result)
        manager.llm_validator.validate_task_compliance = AsyncMock(return_value=ai_compliance_result)

        # Run verification for code development task
        result = await manager.run_verification_pipeline("code_dev_task_001")

        # Verify successful completion
        assert result.is_successful is True
        assert result.overall_score >= 0.8  # High score expected

        # Verify all levels contributed positively
        scores = [r.overall_score or 0 for r in result.results_by_level.values()]
        assert all(score >= 0.8 for score in scores if score > 0)

    @pytest.mark.asyncio
    async def test_problematic_execution_verification_scenario(self):
        """Test verification scenario with problematic execution"""
        manager = MultiLevelVerificationManager()

        # Setup mocks to simulate problematic execution
        manager.quality_gate_manager.run_specific_gates = AsyncMock()

        # Pre-execution has warnings
        pre_result = MagicMock()
        pre_result.results = [MagicMock(status=QualityStatus.WARNING, score=0.7)]
        pre_result.has_errors.return_value = False

        # Post-execution has issues
        post_result = MagicMock()
        post_result.results = [MagicMock(status=QualityStatus.FAILED, score=0.4)]
        post_result.has_errors.return_value = True

        call_count = 0
        async def mock_gates(checks, context):
            nonlocal call_count
            call_count += 1
            return pre_result if 'pre' in str(context).lower() else post_result

        manager.quality_gate_manager.run_specific_gates = mock_gates

        # Execution monitoring shows problems
        manager.execution_monitor.start_monitoring = AsyncMock()
        manager.execution_monitor.check_execution_health = AsyncMock(return_value={
            'healthy': False,
            'issues': ['high_cpu_usage_90.0%', 'no_progress_for_400s'],
            'cpu_usage': 90.0,
            'memory_usage': 85.0
        })

        # AI validation finds issues
        ai_result = MagicMock()
        ai_result.quality_result.results = [MagicMock(status=QualityStatus.WARNING, score=0.6)]
        ai_result.overall_score = 0.6

        manager.llm_validator.validate_code_quality = AsyncMock(return_value=ai_result)

        # Run verification
        result = await manager.run_verification_pipeline("problematic_task_001")

        # Should complete but with lower success score
        assert result.execution_time >= 0

        # Should have multiple issues identified
        post_exec = result.results_by_level.get(VerificationLevel.POST_EXECUTION)
        assert post_exec.quality_result.results[0].status == QualityStatus.FAILED

        in_exec = result.results_by_level.get(VerificationLevel.IN_EXECUTION)
        health_status = in_exec.metadata.get('health_status', {})
        assert not health_status.get('healthy', True)

        # Overall score should be lower
        assert result.overall_score < 0.8