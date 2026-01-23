#!/usr/bin/env python3
"""
Интеграционные тесты для многоуровневой верификации в ServerCore

Тестирует полную интеграцию MultiLevelVerificationManager с ServerCore:
- Pre-execution, in-execution, post-execution верификация
- Передача реальных данных в систему верификации
- Обработка результатов верификации и принятие решений
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Добавляем src в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.server_core import ServerCore
from src.verification.verification_manager import MultiLevelVerificationManager
from src.verification.interfaces import IMultiLevelVerificationManager
from src.quality.models.quality_result import (
    VerificationResult, MultiLevelVerificationResult, VerificationLevel,
    QualityGateResult, QualityResult, QualityStatus, QualityCheckType
)
from src.todo_manager import TodoItem
from src.core.types import TaskType


class MockVerificationManager(IMultiLevelVerificationManager):
    """Mock реализация для тестирования"""

    def __init__(self, pre_score=0.8, in_score=0.9, post_score=0.85, ai_score=0.7):
        self.pre_score = pre_score
        self.in_score = in_score
        self.post_score = post_score
        self.ai_score = ai_score
        self.calls = []

    async def run_verification_pipeline(self, task_id: str, context=None):
        self.calls.append(('pipeline', task_id, context))
        return MultiLevelVerificationResult(task_id=task_id)

    async def run_pre_execution_checks(self, task_id: str, context=None):
        self.calls.append(('pre_execution', task_id, context))
        quality_result = QualityGateResult(
            gate_name="pre_execution_test",
            results=[QualityResult(
                check_type=QualityCheckType.COVERAGE,
                status=QualityStatus.PASSED,
                score=self.pre_score,
                message="Pre-execution check passed"
            )]
        )
        return VerificationResult(
            task_id=task_id,
            verification_level=VerificationLevel.PRE_EXECUTION,
            quality_result=quality_result
        )

    async def run_in_execution_monitoring(self, task_id: str, context=None):
        self.calls.append(('in_execution', task_id, context))
        quality_result = QualityGateResult(
            gate_name="in_execution_test",
            results=[QualityResult(
                check_type=QualityCheckType.PROGRESS,
                status=QualityStatus.PASSED,
                score=self.in_score,
                message="In-execution monitoring passed"
            )]
        )
        return VerificationResult(
            task_id=task_id,
            verification_level=VerificationLevel.IN_EXECUTION,
            quality_result=quality_result
        )

    async def run_post_execution_validation(self, task_id: str, execution_result=None, context=None):
        self.calls.append(('post_execution', task_id, execution_result, context))
        quality_result = QualityGateResult(
            gate_name="post_execution_test",
            results=[QualityResult(
                check_type=QualityCheckType.OUTPUT_VALIDATION,
                status=QualityStatus.PASSED,
                score=self.post_score,
                message="Post-execution validation passed"
            )]
        )
        return VerificationResult(
            task_id=task_id,
            verification_level=VerificationLevel.POST_EXECUTION,
            quality_result=quality_result
        )

    async def run_ai_validation(self, task_id: str, analysis_data=None, context=None):
        self.calls.append(('ai_validation', task_id, analysis_data, context))
        quality_result = QualityGateResult(
            gate_name="ai_validation_test",
            results=[QualityResult(
                check_type=QualityCheckType.CODE_QUALITY_AI,
                status=QualityStatus.PASSED,
                score=self.ai_score,
                message="AI validation passed"
            )]
        )
        return VerificationResult(
            task_id=task_id,
            verification_level=VerificationLevel.AI_VALIDATION,
            quality_result=quality_result
        )

    async def run_cross_validation(self, verification_results=None, context=None):
        self.calls.append(('cross_validation', verification_results, context))
        quality_result = QualityGateResult(
            gate_name="cross_validation_test",
            results=[QualityResult(
                check_type=QualityCheckType.CONSISTENCY_CHECK,
                status=QualityStatus.PASSED,
                score=0.9,
                message="Cross-validation passed"
            )]
        )
        return VerificationResult(
            task_id="cross_validation",
            verification_level=VerificationLevel.CROSS_VALIDATION,
            quality_result=quality_result
        )


class TestVerificationIntegration:
    """Интеграционные тесты верификации в ServerCore"""

    @pytest.fixture
    def mock_components(self):
        """Создание mock компонентов для тестирования"""
        todo_manager = MagicMock()
        todo_manager.get_pending_tasks.return_value = []
        todo_manager.get_all_tasks.return_value = []

        checkpoint_manager = MagicMock()
        checkpoint_manager.get_completed_tasks.return_value = []
        checkpoint_manager.increment_iteration.return_value = None

        status_manager = MagicMock()
        server_logger = MagicMock()

        task_executor = MagicMock(return_value=True)  # Синхронный mock
        revision_executor = MagicMock(return_value=True)
        todo_generator = MagicMock(return_value=True)

        return {
            'todo_manager': todo_manager,
            'checkpoint_manager': checkpoint_manager,
            'status_manager': status_manager,
            'server_logger': server_logger,
            'task_executor': task_executor,
            'revision_executor': revision_executor,
            'todo_generator': todo_generator
        }

    @pytest.fixture
    def server_config(self):
        """Базовая конфигурация сервера"""
        return {
            'quality_gates': {'enabled': False},
            'verification': {
                'levels': {
                    'pre_execution': {'enabled': True, 'weight': 0.2, 'required_score': 0.7},
                    'in_execution': {'enabled': True, 'weight': 0.3, 'required_score': 0.8},
                    'post_execution': {'enabled': True, 'weight': 0.3, 'required_score': 0.75},
                    'ai_validation': {'enabled': True, 'weight': 0.2, 'required_score': 0.6}
                },
                'overall_threshold': 0.7
            }
        }

    @pytest.mark.asyncio
    async def test_full_verification_pipeline_integration(self, mock_components, server_config):
        """Тест полной интеграции пайплайна верификации"""
        # Создаем ServerCore с mock verification manager
        verification_manager = MockVerificationManager(
            pre_score=0.8, in_score=0.9, post_score=0.85, ai_score=0.7
        )

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        # Создаем тестовую задачу
        todo_item = TodoItem(
            text="Implement user authentication",
            category="code",
            id="test_task_001",
            task_type=TaskType.CODE
        )

        # Выполняем задачу с верификацией
        success, verification_result = await server.execute_single_task(todo_item, 1, 1)

        # Проверяем результаты
        assert success is True
        assert verification_result['task_id'] == 'test_task_001'
        assert verification_result['verification_passed'] is True
        assert 'pre_execution' in verification_result['levels_executed']
        assert 'in_execution' in verification_result['levels_executed']
        assert 'post_execution' in verification_result['levels_executed']
        assert 'ai_validation' in verification_result['levels_executed']

        # Проверяем что все уровни верификации были вызваны
        calls = verification_manager.calls
        assert len(calls) >= 4  # Минимум 4 уровня верификации

        # Проверяем вызовы
        call_types = [call[0] for call in calls]
        assert 'pre_execution' in call_types
        assert 'in_execution' in call_types
        assert 'post_execution' in call_types
        assert 'ai_validation' in call_types

    @pytest.mark.asyncio
    async def test_verification_decision_making(self, mock_components, server_config):
        """Тест принятия решений на основе верификации"""
        # Тест с низким скором pre-execution (должен заблокироваться)
        verification_manager = MockVerificationManager(
            pre_score=0.5,  # Ниже порога 0.7
            in_score=0.9,
            post_score=0.85,
            ai_score=0.7
        )

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        todo_item = TodoItem(
            text="Fix critical bug",
            category="code",
            id="test_task_002",
            task_type=TaskType.CODE
        )

        success, verification_result = await server.execute_single_task(todo_item, 1, 1)

        # Задача должна быть заблокирована из-за низкого скора pre-execution
        assert success is False
        assert verification_result['verification_passed'] is False
        assert 'pre_execution_threshold_not_met' in verification_result['decisions']

    @pytest.mark.asyncio
    async def test_data_passing_to_verification(self, mock_components, server_config):
        """Тест передачи реальных данных в систему верификации"""
        verification_manager = MockVerificationManager()

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        # Создаем задачу с дополнительными данными
        todo_item = TodoItem(
            text="Refactor user service class",
            category="refactor",
            id="test_task_003",
            task_type=TaskType.REFACTOR
        )
        # Добавляем mock code changes
        todo_item.code_changes = {
            'files_modified': ['src/user_service.py'],
            'lines_added': 25,
            'lines_removed': 10,
            'complexity_delta': -5
        }

        success, verification_result = await server.execute_single_task(todo_item, 1, 1)

        # Проверяем что данные были переданы в AI валидацию
        ai_calls = [call for call in verification_manager.calls if call[0] == 'ai_validation']
        assert len(ai_calls) == 1

        call_type, task_id, analysis_data, context = ai_calls[0]
        assert analysis_data['task_description'] == todo_item.text
        assert analysis_data['task_type'] == todo_item.category
        assert 'code_changes' in analysis_data
        assert analysis_data['code_changes']['files_modified'] == ['src/user_service.py']

    @pytest.mark.asyncio
    async def test_verification_with_execution_failure(self, mock_components, server_config):
        """Тест верификации при неудачном выполнении задачи"""
        verification_manager = MockVerificationManager()

        # Настраиваем task_executor на возврат False (неудачное выполнение)
        mock_components['task_executor'].return_value = False

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        todo_item = TodoItem(
            text="Deploy to production",
            category="release",
            id="test_task_004",
            task_type=TaskType.RELEASE
        )

        success, verification_result = await server.execute_single_task(todo_item, 1, 1)

        # Задача должна провалиться
        assert success is False
        assert verification_result['execution_result']['success'] is False

        # Но верификация все равно должна выполниться
        assert len(verification_result['levels_executed']) >= 3  # pre, in, post
        assert verification_result['verification_passed'] is True  # Верификация успешна, но выполнение провалено

    @pytest.mark.asyncio
    async def test_batch_execution_with_verification(self, mock_components, server_config):
        """Тест пакетного выполнения с верификацией"""
        verification_manager = MockVerificationManager()

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        # Создаем несколько задач
        tasks = [
            TodoItem(text="Task 1", category="code", id="task_001", task_type=TaskType.CODE),
            TodoItem(text="Task 2", category="test", id="task_002", task_type=TaskType.TEST),
            TodoItem(text="Task 3", category="docs", id="task_003", task_type=TaskType.DOCS)
        ]

        # Выполняем пакет задач
        await server.execute_tasks_batch(tasks, iteration=1)

        # Проверяем что верификация была вызвана для всех задач
        verification_calls = verification_manager.calls
        task_ids_called = set()

        for call in verification_calls:
            if len(call) >= 2:
                task_ids_called.add(call[1])

        # Должны быть вызовы для всех трех задач
        assert "task_001" in task_ids_called
        assert "task_002" in task_ids_called
        assert "task_003" in task_ids_called

    @pytest.mark.asyncio
    async def test_verification_manager_getters(self, mock_components, server_config):
        """Тест getter методов для verification manager"""
        verification_manager = MockVerificationManager()

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        # Тестируем getter
        vm = server.get_verification_manager()
        assert vm is verification_manager
        assert isinstance(vm, IMultiLevelVerificationManager)

    @pytest.mark.asyncio
    async def test_verification_configuration(self, mock_components, server_config):
        """Тест конфигурации верификации"""
        verification_manager = MultiLevelVerificationManager()

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        # Тестируем конфигурацию
        new_config = {
            'levels': {
                'pre_execution': {'enabled': False},  # Отключаем pre-execution
                'ai_validation': {'enabled': False}   # Отключаем AI validation
            },
            'overall_threshold': 0.8
        }

        server.configure_verification(new_config)

        # Проверяем что конфигурация применилась
        assert verification_manager.overall_threshold == 0.8

    @pytest.mark.asyncio
    async def test_verification_error_handling(self, mock_components, server_config):
        """Тест обработки ошибок в верификации"""
        class FailingVerificationManager(MockVerificationManager):
            async def run_pre_execution_checks(self, task_id: str, context=None):
                raise Exception("Pre-execution check failed")

        verification_manager = FailingVerificationManager()

        server = ServerCore(
            **mock_components,
            config=server_config,
            project_dir=Path("/tmp/test"),
            verification_manager=verification_manager
        )

        todo_item = TodoItem(
            text="Test error handling",
            category="test",
            id="error_task_001",
            task_type=TaskType.TEST
        )

        success, verification_result = await server.execute_single_task(todo_item, 1, 1)

        # Задача должна провалиться из-за ошибки верификации
        assert success is False
        assert verification_result['verification_passed'] is False
        assert 'execution_error' in verification_result['decisions']
        assert 'error' in verification_result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])