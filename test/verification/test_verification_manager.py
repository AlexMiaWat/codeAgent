"""
Тесты для MultiLevelVerificationManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.verification.verification_manager import MultiLevelVerificationManager
from src.quality.models.quality_result import VerificationLevel, QualityStatus


@pytest.mark.asyncio
async def test_verification_manager_initialization():
    """Тест инициализации Verification Manager"""
    config = {
        'verification': {
            'levels': {
                VerificationLevel.PRE_EXECUTION: {
                    'enabled': True,
                    'weight': 0.2,
                    'required_score': 0.7
                },
                VerificationLevel.IN_EXECUTION: {
                    'enabled': True,
                    'weight': 0.3,
                    'required_score': 0.8
                }
            }
        }
    }

    manager = MultiLevelVerificationManager(config)

    assert manager.overall_threshold == 0.7
    assert VerificationLevel.PRE_EXECUTION in manager.level_configs
    assert manager.level_configs[VerificationLevel.PRE_EXECUTION]['enabled'] is True


@pytest.mark.asyncio
async def test_pre_execution_checks():
    """Тест выполнения pre-execution проверок"""
    manager = MultiLevelVerificationManager()

    # Mock quality gate manager
    manager.quality_gate_manager.run_specific_gates = AsyncMock()
    mock_gate_result = MagicMock()
    mock_gate_result.results = []
    manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

    result = await manager.run_pre_execution_checks("test_task_123")

    assert result.task_id == "test_task_123"
    assert result.verification_level == VerificationLevel.PRE_EXECUTION
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_in_execution_monitoring():
    """Тест мониторинга выполнения"""
    manager = MultiLevelVerificationManager()

    # Mock execution monitor
    manager.execution_monitor.start_monitoring = AsyncMock()
    manager.execution_monitor.check_execution_health = AsyncMock(return_value={
        'healthy': True,
        'issues': []
    })

    result = await manager.run_in_execution_monitoring("test_task_123")

    assert result.task_id == "test_task_123"
    assert result.verification_level == VerificationLevel.IN_EXECUTION
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_cross_validation():
    """Тест кросс-валидации"""
    manager = MultiLevelVerificationManager()

    # Mock verification results
    mock_pre_result = MagicMock()
    mock_pre_result.overall_score = 0.8
    mock_pre_result.quality_result.has_errors.return_value = False

    mock_post_result = MagicMock()
    mock_post_result.overall_score = 0.75
    mock_post_result.quality_result.has_errors.return_value = False

    verification_results = {
        'pre_execution': mock_pre_result,
        'post_execution': mock_post_result
    }

    result = await manager.run_cross_validation(verification_results)

    assert result.verification_level == VerificationLevel.CROSS_VALIDATION
    assert result.execution_time >= 0


def test_level_enabled_check():
    """Тест проверки включенности уровней"""
    config = {
        'verification': {
            'levels': {
                VerificationLevel.PRE_EXECUTION: {'enabled': True},
                VerificationLevel.AI_VALIDATION: {'enabled': False}
            }
        }
    }

    manager = MultiLevelVerificationManager(config)

    assert manager._is_level_enabled(VerificationLevel.PRE_EXECUTION) is True
    assert manager._is_level_enabled(VerificationLevel.AI_VALIDATION) is False


@pytest.mark.asyncio
async def test_post_execution_validation():
    """Тест post-execution валидации"""
    manager = MultiLevelVerificationManager()

    # Mock quality gate manager
    manager.quality_gate_manager.run_specific_gates = AsyncMock()
    mock_gate_result = MagicMock()
    mock_gate_result.results = []
    manager.quality_gate_manager.run_specific_gates.return_value = mock_gate_result

    execution_result = {'status': 'completed', 'files_changed': 5}

    result = await manager.run_post_execution_validation("test_task", execution_result)

    assert result.task_id == "test_task"
    assert result.verification_level == VerificationLevel.POST_EXECUTION
    assert result.execution_time >= 0
    assert result.metadata['execution_result_keys'] == list(execution_result.keys())


@pytest.mark.asyncio
async def test_ai_validation():
    """Тест AI валидации"""
    manager = MultiLevelVerificationManager()

    # Mock LLM validator
    manager.llm_validator.validate_code_quality = AsyncMock()
    manager.llm_validator.validate_logic_correctness = AsyncMock()
    manager.llm_validator.validate_task_compliance = AsyncMock()

    # Mock responses
    mock_ai_result1 = MagicMock()
    mock_ai_result1.quality_result.results = []
    mock_ai_result1.overall_score = 0.8

    mock_ai_result2 = MagicMock()
    mock_ai_result2.quality_result.results = []
    mock_ai_result2.overall_score = 0.7

    manager.llm_validator.validate_code_quality.return_value = mock_ai_result1
    manager.llm_validator.validate_logic_correctness.return_value = mock_ai_result2

    analysis_data = {
        'code_changes': [{'file': 'test.py'}],
        'task_description': 'Test task'
    }

    result = await manager.run_ai_validation("test_task", analysis_data)

    assert result.task_id == "test_task"
    assert result.verification_level == VerificationLevel.AI_VALIDATION
    assert result.execution_time >= 0
    assert result.metadata['ai_validations_run'] == 2
    assert result.metadata['valid_results'] == 2


@pytest.mark.asyncio
async def test_verification_pipeline_full():
    """Тест полного пайплайна верификации"""
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

    # Mock AI validation
    manager.llm_validator.validate_code_quality = AsyncMock()
    mock_ai_result = MagicMock()
    mock_ai_result.quality_result.results = []
    mock_ai_result.overall_score = 0.8
    manager.llm_validator.validate_code_quality.return_value = mock_ai_result

    # Run full pipeline
    result = await manager.run_verification_pipeline("test_task_123")

    assert result.task_id == "test_task_123"
    assert result.execution_time >= 0
    assert result.is_successful is True  # Should be successful with all mocks passing
    assert len(result.results_by_level) == 5  # All levels should be executed

    # Check that task was removed from active verifications
    assert "test_task_123" not in manager.active_verifications


@pytest.mark.asyncio
async def test_verification_pipeline_with_failures():
    """Тест пайплайна верификации с провалами"""
    manager = MultiLevelVerificationManager()

    # Mock dependencies to fail
    manager.quality_gate_manager.run_specific_gates = AsyncMock(side_effect=Exception("Gate failed"))

    # Should still complete without crashing
    result = await manager.run_verification_pipeline("test_task_fail")

    assert result.task_id == "test_task_fail"
    assert result.execution_time >= 0
    assert result.is_successful is False  # Should fail due to errors


@pytest.mark.asyncio
async def test_cross_validation_with_discrepancies():
    """Тест кросс-валидации с расхождениями"""
    manager = MultiLevelVerificationManager()

    # Mock verification results with discrepancies
    mock_pre_result = MagicMock()
    mock_pre_result.overall_score = 0.9
    mock_pre_result.quality_result.has_errors.return_value = False

    mock_post_result = MagicMock()
    mock_post_result.overall_score = 0.6  # Significant discrepancy
    mock_post_result.quality_result.has_errors.return_value = False

    mock_ai_result = MagicMock()
    mock_ai_result.overall_score = 0.8

    verification_results = {
        VerificationLevel.PRE_EXECUTION.value: mock_pre_result,
        VerificationLevel.POST_EXECUTION.value: mock_post_result,
        VerificationLevel.AI_VALIDATION.value: mock_ai_result
    }

    result = await manager.run_cross_validation(verification_results)

    assert result.verification_level == VerificationLevel.CROSS_VALIDATION
    assert result.execution_time >= 0
    assert 'issues' in result.quality_result.details
    assert len(result.quality_result.details['issues']) > 0


def test_level_config_defaults():
    """Тест конфигурации уровней по умолчанию"""
    manager = MultiLevelVerificationManager()

    # Check default configs
    assert VerificationLevel.PRE_EXECUTION in manager.level_configs
    assert VerificationLevel.IN_EXECUTION in manager.level_configs
    assert VerificationLevel.POST_EXECUTION in manager.level_configs
    assert VerificationLevel.AI_VALIDATION in manager.level_configs
    assert VerificationLevel.CROSS_VALIDATION in manager.level_configs

    # Check default values
    pre_config = manager.level_configs[VerificationLevel.PRE_EXECUTION]
    assert pre_config['enabled'] is True
    assert pre_config['weight'] == 0.2
    assert pre_config['required_score'] == 0.7


def test_active_verifications_management():
    """Тест управления активными верификациями"""
    manager = MultiLevelVerificationManager()

    # Initially empty
    assert len(manager.get_active_verifications()) == 0

    # Add active verification manually (simulating pipeline start)
    from src.quality.models.quality_result import MultiLevelVerificationResult
    verification_result = MultiLevelVerificationResult(task_id="test_task")
    manager.active_verifications["test_task"] = verification_result

    # Should be in active list
    assert "test_task" in manager.get_active_verifications()

    # Should get status
    status = manager.get_verification_status("test_task")
    assert status is not None
    assert status['task_id'] == "test_task"
    assert status['current_score'] == verification_result.overall_score


def test_cross_validation_score_calculation():
    """Тест расчета скора кросс-валидации"""
    manager = MultiLevelVerificationManager()

    # Mock multi-level result
    mock_result = MagicMock()
    mock_result.results_by_level = {}

    # Empty results
    score = manager._calculate_cross_validation_score(mock_result)
    assert score == 0.5

    # Add some results
    mock_level_result1 = MagicMock()
    mock_level_result1.overall_score = 0.8

    mock_level_result2 = MagicMock()
    mock_level_result2.overall_score = 0.9

    mock_result.results_by_level = {
        'level1': mock_level_result1,
        'level2': mock_level_result2
    }

    score = manager._calculate_cross_validation_score(mock_result)
    assert 0.0 <= score <= 1.0

    # Test with identical scores (perfect consistency)
    mock_level_result1.overall_score = 0.8
    mock_level_result2.overall_score = 0.8

    score = manager._calculate_cross_validation_score(mock_result)
    assert score == 1.0  # Perfect consistency

    # Test with large discrepancies
    mock_level_result1.overall_score = 0.9
    mock_level_result2.overall_score = 0.1

    score = manager._calculate_cross_validation_score(mock_result)
    assert score < 0.5  # Low consistency score


def test_error_result_creation():
    """Тест создания результатов ошибок"""
    from datetime import datetime
    manager = MultiLevelVerificationManager()

    start_time = datetime.now()
    error_result = manager._create_error_verification_result(
        "test_task", VerificationLevel.PRE_EXECUTION, "Test error", start_time
    )

    assert error_result.task_id == "test_task"
    assert error_result.verification_level == VerificationLevel.PRE_EXECUTION
    assert error_result.execution_time >= 0
    assert error_result.quality_result.results[0].status.name == 'ERROR'
    assert "Test error" in error_result.quality_result.results[0].message