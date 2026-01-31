"""
Дымовые тесты для системы верификации

Проверяют базовую работоспособность:
- Компоненты верификации могут быть созданы
- Базовые методы выполняются без исключений
- Компоненты правильно взаимодействуют
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import asyncio
from typing import Dict, Any, Optional

from src.verification.verification_manager import MultiLevelVerificationManager
from src.verification.execution_monitor import ExecutionMonitor
from src.verification.llm_validator import LLMValidator
from src.quality.models.quality_result import (
    VerificationResult, MultiLevelVerificationResult, VerificationLevel,
    QualityGateResult, QualityResult, QualityCheckType, QualityStatus
)


class TestMultiLevelVerificationManagerSmoke:
    """Дымовые тесты для MultiLevelVerificationManager"""

    def test_manager_creation(self):
        """Проверяет создание MultiLevelVerificationManager"""
        manager = MultiLevelVerificationManager()

        assert manager is not None
        assert hasattr(manager, 'quality_gate_manager')
        assert hasattr(manager, 'execution_monitor')
        assert hasattr(manager, 'llm_validator')

    def test_manager_creation_with_config(self):
        """Проверяет создание менеджера с конфигурацией"""
        config = {
            'verification': {
                'levels': {
                    VerificationLevel.PRE_EXECUTION: {
                        'enabled': True,
                        'weight': 0.3,
                        'required_score': 0.8
                    }
                },
                'quality_gates': {},
                'execution_monitor': {},
                'llm_validator': {}
            }
        }

        manager = MultiLevelVerificationManager(config)

        assert manager.config == config
        assert hasattr(manager, 'level_configs')

    @patch('src.verification.verification_manager.QualityGateManager')
    @patch('src.verification.verification_manager.ExecutionMonitor')
    @patch('src.verification.verification_manager.LLMValidator')
    def test_manager_run_verification_pipeline(self, mock_llm_validator, mock_execution_monitor, mock_quality_gate):
        """Проверяет запуск пайплайна верификации"""
        # Настраиваем моки
        mock_quality_gate_instance = Mock()
        mock_quality_gate_instance.run_quality_checks = AsyncMock(return_value=[])
        mock_quality_gate.return_value = mock_quality_gate_instance

        mock_execution_monitor_instance = Mock()
        mock_execution_monitor_instance.start_monitoring = AsyncMock()
        mock_execution_monitor_instance.stop_monitoring = AsyncMock(return_value={'execution_time': 1.0})
        mock_execution_monitor.return_value = mock_execution_monitor_instance

        mock_llm_validator_instance = Mock()
        mock_llm_validator_instance.validate_code_quality = AsyncMock(return_value=VerificationResult(
            level=VerificationLevel.AI_VALIDATION,
            passed=True,
            score=0.9
        ))
        mock_llm_validator.return_value = mock_llm_validator_instance

        manager = MultiLevelVerificationManager()

        async def test():
            result = await manager.run_verification_pipeline("test_task_123")

            assert result is not None
            assert isinstance(result, MultiLevelVerificationResult)
            assert result.task_id == "test_task_123"

        asyncio.run(test())

    @patch('src.verification.verification_manager.QualityGateManager')
    @patch('src.verification.verification_manager.ExecutionMonitor')
    @patch('src.verification.verification_manager.LLMValidator')
    def test_manager_run_pre_execution_checks(self, mock_llm_validator, mock_execution_monitor, mock_quality_gate):
        """Проверяет pre-execution проверки"""
        # Настраиваем моки
        mock_quality_gate_instance = Mock()
        mock_quality_gate_instance.run_quality_checks = AsyncMock(return_value=[
            QualityResult(
                check_type=QualityCheckType.COVERAGE,
                check_name="Coverage Check",
                passed=True,
                score=0.85
            )
        ])
        mock_quality_gate.return_value = mock_quality_gate_instance

        manager = MultiLevelVerificationManager()

        async def test():
            result = await manager.run_pre_execution_checks("test_task_123")

            assert result is not None
            assert isinstance(result, VerificationResult)
            assert result.level == VerificationLevel.PRE_EXECUTION

        asyncio.run(test())

    @patch('src.verification.verification_manager.QualityGateManager')
    @patch('src.verification.verification_manager.ExecutionMonitor')
    @patch('src.verification.verification_manager.LLMValidator')
    def test_manager_run_post_execution_validation(self, mock_llm_validator, mock_execution_monitor, mock_quality_gate):
        """Проверяет post-execution валидацию"""
        # Настраиваем моки
        mock_llm_validator_instance = Mock()
        mock_llm_validator_instance.validate_task_compliance = AsyncMock(return_value=VerificationResult(
            level=VerificationLevel.POST_EXECUTION,
            passed=True,
            score=0.88
        ))
        mock_llm_validator.return_value = mock_llm_validator_instance

        manager = MultiLevelVerificationManager()

        execution_result = {"status": "completed", "output": "test output"}

        async def test():
            result = await manager.run_post_execution_validation("test_task_123", execution_result)

            assert result is not None
            assert isinstance(result, VerificationResult)
            assert result.level == VerificationLevel.POST_EXECUTION

        asyncio.run(test())

    @patch('src.verification.verification_manager.QualityGateManager')
    @patch('src.verification.verification_manager.ExecutionMonitor')
    @patch('src.verification.verification_manager.LLMValidator')
    def test_manager_run_ai_validation(self, mock_llm_validator, mock_execution_monitor, mock_quality_gate):
        """Проверяет AI валидацию"""
        # Настраиваем моки
        mock_llm_validator_instance = Mock()
        mock_llm_validator_instance.validate_code_quality = AsyncMock(return_value=VerificationResult(
            level=VerificationLevel.AI_VALIDATION,
            passed=True,
            score=0.92
        ))
        mock_llm_validator.return_value = mock_llm_validator_instance

        manager = MultiLevelVerificationManager()

        analysis_data = {"code": "def test(): pass", "task": "write function"}

        async def test():
            result = await manager.run_ai_validation("test_task_123", analysis_data)

            assert result is not None
            assert isinstance(result, VerificationResult)
            assert result.level == VerificationLevel.AI_VALIDATION

        asyncio.run(test())


class TestExecutionMonitorSmoke:
    """Дымовые тесты для ExecutionMonitor"""

    def test_monitor_creation(self):
        """Проверяет создание ExecutionMonitor"""
        monitor = ExecutionMonitor()

        assert monitor is not None
        assert hasattr(monitor, '_active_monitors')
        assert hasattr(monitor, '_health_checks')

    def test_monitor_creation_with_config(self):
        """Проверяет создание монитора с конфигурацией"""
        config = {
            'health_check_interval': 30,
            'max_execution_time': 3600,
            'progress_tracking_enabled': True
        }

        monitor = ExecutionMonitor(config)

        assert monitor.config == config

    def test_monitor_start_monitoring(self):
        """Проверяет начало мониторинга"""
        monitor = ExecutionMonitor()

        async def test():
            await monitor.start_monitoring("test_task_123", {"context": "test"})

            # Проверяем, что задача добавлена в активные
            assert "test_task_123" in monitor._active_monitors

        asyncio.run(test())

    def test_monitor_update_progress(self):
        """Проверяет обновление прогресса"""
        monitor = ExecutionMonitor()

        async def test():
            # Сначала запускаем мониторинг
            await monitor.start_monitoring("test_task_123")

            # Обновляем прогресс
            progress_data = {"progress": 50, "status": "running"}
            await monitor.update_progress("test_task_123", progress_data)

            # Проверяем, что данные сохранены
            assert "test_task_123" in monitor._progress_data

        asyncio.run(test())

    def test_monitor_check_execution_health(self):
        """Проверяет проверку здоровья выполнения"""
        monitor = ExecutionMonitor()

        async def test():
            # Сначала запускаем мониторинг
            await monitor.start_monitoring("test_task_123")

            # Проверяем здоровье
            health = await monitor.check_execution_health("test_task_123")

            assert health is not None
            assert isinstance(health, dict)

        asyncio.run(test())

    def test_monitor_stop_monitoring(self):
        """Проверяет остановку мониторинга"""
        monitor = ExecutionMonitor()

        async def test():
            # Запускаем и останавливаем мониторинг
            await monitor.start_monitoring("test_task_123")
            metrics = await monitor.stop_monitoring("test_task_123")

            assert metrics is not None
            assert isinstance(metrics, dict)
            # Проверяем, что задача удалена из активных
            assert "test_task_123" not in monitor._active_monitors

        asyncio.run(test())

    def test_monitor_multiple_tasks(self):
        """Проверяет мониторинг нескольких задач"""
        monitor = ExecutionMonitor()

        async def test():
            # Запускаем несколько задач
            await monitor.start_monitoring("task_1")
            await monitor.start_monitoring("task_2")
            await monitor.start_monitoring("task_3")

            assert len(monitor._active_monitors) == 3

            # Останавливаем одну задачу
            await monitor.stop_monitoring("task_2")

            assert len(monitor._active_monitors) == 2
            assert "task_1" in monitor._active_monitors
            assert "task_3" in monitor._active_monitors
            assert "task_2" not in monitor._active_monitors

        asyncio.run(test())


class TestLLMValidatorSmoke:
    """Дымовые тесты для LLMValidator"""

    @patch('src.verification.llm_validator.LLMValidator._get_llm_client')
    def test_validator_creation(self, mock_get_client):
        """Проверяет создание LLMValidator"""
        mock_get_client.return_value = Mock()

        validator = LLMValidator()

        assert validator is not None
        assert hasattr(validator, 'llm_client')

    @patch('src.verification.llm_validator.LLMValidator._get_llm_client')
    def test_validator_creation_with_config(self, mock_get_client):
        """Проверяет создание валидатора с конфигурацией"""
        mock_get_client.return_value = Mock()

        config = {
            'model_name': 'gpt-4',
            'temperature': 0.3,
            'max_tokens': 1000
        }

        validator = LLMValidator(config=config)

        assert validator.config == config

    @patch('src.verification.llm_validator.LLMValidator._get_llm_client')
    def test_validator_validate_code_quality(self, mock_get_client):
        """Проверяет валидацию качества кода"""
        mock_client = Mock()
        mock_client.generate = AsyncMock(return_value=Mock(content='{"score": 0.85, "issues": []}'))
        mock_get_client.return_value = mock_client

        validator = LLMValidator()

        code_changes = {"file": "test.py", "changes": "def test(): pass"}

        async def test():
            result = await validator.validate_code_quality(code_changes)

            assert result is not None
            assert isinstance(result, VerificationResult)
            assert result.level == VerificationLevel.AI_VALIDATION

        asyncio.run(test())

    @patch('src.verification.llm_validator.LLMValidator._get_llm_client')
    def test_validator_validate_task_compliance(self, mock_get_client):
        """Проверяет валидацию соответствия задаче"""
        mock_client = Mock()
        mock_client.generate = AsyncMock(return_value=Mock(content='{"score": 0.9, "compliant": true}'))
        mock_get_client.return_value = mock_client

        validator = LLMValidator()

        task_description = "Write a function to calculate sum"
        execution_result = {"code": "def sum(a, b): return a + b"}

        async def test():
            result = await validator.validate_task_compliance(task_description, execution_result)

            assert result is not None
            assert isinstance(result, VerificationResult)
            assert result.level == VerificationLevel.POST_EXECUTION

        asyncio.run(test())

    @patch('src.verification.llm_validator.LLMValidator._get_llm_client')
    def test_validator_generate_improvement_suggestions(self, mock_get_client):
        """Проверяет генерацию предложений по улучшению"""
        mock_client = Mock()
        mock_client.generate = AsyncMock(return_value=Mock(content='["Add docstrings", "Improve error handling"]'))
        mock_get_client.return_value = mock_client

        validator = LLMValidator()

        analysis_data = {"code": "def test(): pass", "issues": ["no docstring"]}

        async def test():
            suggestions = await validator.generate_improvement_suggestions(analysis_data)

            assert suggestions is not None
            assert isinstance(suggestions, list)

        asyncio.run(test())

    @patch('src.verification.llm_validator.LLMValidator._get_llm_client')
    def test_validator_error_handling(self, mock_get_client):
        """Проверяет обработку ошибок"""
        mock_client = Mock()
        mock_client.generate = AsyncMock(side_effect=Exception("LLM error"))
        mock_get_client.return_value = mock_client

        validator = LLMValidator()

        code_changes = {"file": "test.py", "changes": "invalid code"}

        async def test():
            # Должен вернуть результат с failed=True вместо исключения
            result = await validator.validate_code_quality(code_changes)

            assert result is not None
            assert isinstance(result, VerificationResult)
            assert result.passed == False

        asyncio.run(test())


class TestVerificationIntegrationSmoke:
    """Дымовые тесты интеграции компонентов верификации"""

    @patch('src.verification.verification_manager.QualityGateManager')
    @patch('src.verification.verification_manager.ExecutionMonitor')
    @patch('src.verification.verification_manager.LLMValidator')
    def test_full_verification_workflow(self, mock_llm_validator, mock_execution_monitor, mock_quality_gate):
        """Проверяет полный workflow верификации"""

        # Настраиваем моки для полного workflow
        mock_quality_gate_instance = Mock()
        mock_quality_gate_instance.run_quality_checks = AsyncMock(return_value=[
            QualityResult(check_type=QualityCheckType.COVERAGE, check_name="Coverage", passed=True, score=0.9)
        ])
        mock_quality_gate.return_value = mock_quality_gate_instance

        mock_execution_monitor_instance = Mock()
        mock_execution_monitor_instance.start_monitoring = AsyncMock()
        mock_execution_monitor_instance.check_execution_health = AsyncMock(return_value={"status": "healthy"})
        mock_execution_monitor_instance.stop_monitoring = AsyncMock(return_value={"execution_time": 2.0})
        mock_execution_monitor.return_value = mock_execution_monitor_instance

        mock_llm_validator_instance = Mock()
        mock_llm_validator_instance.validate_code_quality = AsyncMock(return_value=VerificationResult(
            level=VerificationLevel.AI_VALIDATION, passed=True, score=0.95
        ))
        mock_llm_validator_instance.validate_task_compliance = AsyncMock(return_value=VerificationResult(
            level=VerificationLevel.POST_EXECUTION, passed=True, score=0.88
        ))
        mock_llm_validator.return_value = mock_llm_validator_instance

        manager = MultiLevelVerificationManager()

        async def test():
            # 1. Pre-execution проверки
            pre_result = await manager.run_pre_execution_checks("workflow_task")
            assert pre_result.passed == True

            # 2. In-execution мониторинг
            in_result = await manager.run_in_execution_monitoring("workflow_task")
            assert in_result.passed == True

            # 3. Post-execution валидация
            execution_result = {"status": "completed", "output": "success"}
            post_result = await manager.run_post_execution_validation("workflow_task", execution_result)
            assert post_result.passed == True

            # 4. AI валидация
            ai_result = await manager.run_ai_validation("workflow_task", {"analysis": "data"})
            assert ai_result.passed == True

            # 5. Полный пайплайн
            full_result = await manager.run_verification_pipeline("workflow_task")
            assert full_result.overall_passed == True
            assert full_result.task_id == "workflow_task"

        asyncio.run(test())

    def test_verification_error_recovery(self):
        """Проверяет восстановление после ошибок"""
        manager = MultiLevelVerificationManager()

        async def test():
            # Тестируем с несуществующей задачей - должно работать без исключений
            try:
                result = await manager.run_pre_execution_checks("nonexistent_task")
                # Даже если задача не существует, должен вернуться результат
                assert isinstance(result, VerificationResult)
            except Exception as e:
                # Если исключение, оно должно быть обработано
                pytest.fail(f"Unexpected exception: {e}")

        asyncio.run(test())