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