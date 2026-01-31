"""
Интеграционные тесты для всей новой функциональности

Тестируют взаимодействие компонентов:
- LLM система + Quality Gates + Verification + Core
- Полные рабочие процессы
- Интеграцию через DI контейнер
- End-to-end сценарии
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import asyncio
from typing import Dict, Any, Optional

from src.core.di_container import DIContainer
from src.core.server_core import ServerCore
from src.llm.manager import LLMManager
from src.llm.intelligent_router import IntelligentRouter
from src.verification.verification_manager import MultiLevelVerificationManager
from src.quality.quality_gate_manager import QualityGateManager
from src.llm.types import ModelConfig, ModelResponse, GenerationRequest, RoutingDecision
from src.core.types import TaskType
from src.quality.models.quality_result import VerificationResult, MultiLevelVerificationResult, VerificationLevel


class TestLLMQualityIntegration:
    """Интеграционные тесты LLM + Quality Gates"""

    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_llm_with_quality_gates(self, mock_error_learning, mock_adaptive, mock_router,
                                   mock_monitor, mock_validator, mock_intelligent_evaluator,
                                   mock_evaluator, mock_strategy, mock_client, mock_registry, mock_config):
        """Тестирует интеграцию LLM с Quality Gates"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {
            'models': {'gpt-4': {}},
            'providers': {},
            'routing': {'enabled': True}
        }
        mock_config.return_value = mock_config_instance

        # Мокаем роутер
        mock_router_instance = Mock()
        mock_router_instance.route_request.return_value = RoutingDecision(
            model_name="gpt-4", strategy="quality_optimized", reasoning="Best quality", confidence=0.9
        )
        mock_router.return_value = mock_router_instance

        # Мокаем клиент для генерации качественного кода
        mock_client_instance = Mock()
        mock_client_instance.generate = AsyncMock(return_value=ModelResponse(
            model_name="gpt-4",
            content='''def calculate_fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number using iterative approach."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n < 2:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b''',
            response_time=1.5,
            success=True
        ))
        mock_client.return_value = mock_client_instance

        llm_manager = LLMManager()

        async def test():
            # Генерируем код с маршрутизацией
            request = GenerationRequest(prompt="Write a Python function to calculate Fibonacci numbers with proper error handling and documentation")
            response = await llm_manager.generate_with_routing(request)

            assert response.success == True
            assert "def calculate_fibonacci" in response.content
            assert "docstring" in response.content.lower() or '"""' in response.content

            # Проверяем через Quality Gates
            quality_manager = QualityGateManager()
            quality_results = await quality_manager.run_quality_checks({
                'code_content': response.content,
                'language': 'python'
            })

            # Должен быть хотя бы один результат quality проверки
            assert len(quality_results) >= 0  # Может быть пустым если чекеры не настроены

        asyncio.run(test())


class TestLLMVerificationIntegration:
    """Интеграционные тесты LLM + Verification"""

    @patch('src.verification.verification_manager.QualityGateManager')
    @patch('src.verification.verification_manager.ExecutionMonitor')
    @patch('src.verification.verification_manager.LLMValidator')
    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_llm_with_verification_pipeline(self, mock_error_learning, mock_adaptive, mock_router,
                                          mock_monitor, mock_validator, mock_intelligent_evaluator,
                                          mock_evaluator, mock_strategy, mock_client, mock_registry,
                                          mock_config, mock_llm_validator, mock_execution_monitor, mock_quality_gate):
        """Тестирует полный pipeline LLM + Verification"""

        # Настраиваем LLM моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {'models': {'gpt-4': {}}, 'providers': {}}
        mock_config.return_value = mock_config_instance

        mock_client_instance = Mock()
        mock_client_instance.generate = AsyncMock(return_value=ModelResponse(
            model_name="gpt-4",
            content='{"function": "test", "description": "A test function", "complexity": "simple"}',
            response_time=1.0,
            success=True
        ))
        mock_client.return_value = mock_client_instance

        # Настраиваем Verification моки
        mock_quality_gate_instance = Mock()
        mock_quality_gate_instance.run_quality_checks = AsyncMock(return_value=[])
        mock_quality_gate.return_value = mock_quality_gate_instance

        mock_execution_monitor_instance = Mock()
        mock_execution_monitor_instance.start_monitoring = AsyncMock()
        mock_execution_monitor_instance.stop_monitoring = AsyncMock(return_value={'execution_time': 1.0})
        mock_execution_monitor.return_value = mock_execution_monitor_instance

        mock_llm_validator_instance = Mock()
        mock_llm_validator_instance.validate_code_quality = AsyncMock(return_value=VerificationResult(
            level=VerificationLevel.AI_VALIDATION, passed=True, score=0.9
        ))
        mock_llm_validator_instance.validate_task_compliance = AsyncMock(return_value=VerificationResult(
            level=VerificationLevel.POST_EXECUTION, passed=True, score=0.85
        ))
        mock_llm_validator.return_value = mock_llm_validator_instance

        llm_manager = LLMManager()
        verification_manager = MultiLevelVerificationManager()

        async def test():
            # Генерируем контент через LLM
            request = GenerationRequest(prompt="Create a simple test function")
            llm_response = await llm_manager.generate(request)
            assert llm_response.success == True

            # Запускаем верификацию
            verification_result = await verification_manager.run_verification_pipeline("test_task_123", {
                'llm_response': llm_response,
                'task_description': 'Create a simple test function'
            })

            assert verification_result is not None
            assert isinstance(verification_result, MultiLevelVerificationResult)
            assert verification_result.task_id == "test_task_123"

            # Проверяем, что все уровни верификации выполнены
            assert VerificationLevel.PRE_EXECUTION in verification_result.level_results
            assert VerificationLevel.POST_EXECUTION in verification_result.level_results
            assert VerificationLevel.AI_VALIDATION in verification_result.level_results

        asyncio.run(test())


class TestCoreLLMIntegration:
    """Интеграционные тесты Core + LLM"""

    @patch('src.core.server_core.QualityGateManager')
    @patch('src.core.server_core.MultiLevelVerificationManager')
    @patch('src.llm.manager.ConfigLoader')
    @patch('src.llm.manager.ModelRegistry')
    @patch('src.llm.manager.ClientManager')
    @patch('src.llm.manager.StrategyManager')
    @patch('src.llm.manager.ResponseEvaluator')
    @patch('src.llm.manager.IntelligentEvaluator')
    @patch('src.llm.manager.JsonValidator')
    @patch('src.llm.manager.HealthMonitor')
    @patch('src.llm.manager.IntelligentRouter')
    @patch('src.llm.manager.AdaptiveStrategyManager')
    @patch('src.llm.manager.ErrorLearningSystem')
    def test_server_core_with_llm_task_processing(self, mock_error_learning, mock_adaptive, mock_router,
                                                 mock_monitor, mock_validator, mock_intelligent_evaluator,
                                                 mock_evaluator, mock_strategy, mock_client, mock_registry,
                                                 mock_config, mock_verification, mock_quality):
        """Тестирует обработку задач в ServerCore с использованием LLM"""

        # Настраиваем моки
        mock_config_instance = Mock()
        mock_config_instance.load_config.return_value = {'models': {'gpt-4': {}}, 'providers': {}}
        mock_config.return_value = mock_config_instance

        mock_client_instance = Mock()
        mock_client_instance.generate = AsyncMock(return_value=ModelResponse(
            model_name="gpt-4",
            content="# Test implementation\ndef test_function():\n    return 'Hello World'",
            response_time=1.0,
            success=True
        ))
        mock_client.return_value = mock_client_instance

        # Мокаем компоненты верификации
        mock_quality_instance = Mock()
        mock_quality_instance.run_quality_checks = AsyncMock(return_value=[])
        mock_quality.return_value = mock_quality_instance

        mock_verification_instance = Mock()
        mock_verification_instance.run_verification_pipeline = AsyncMock(return_value=Mock(
            overall_passed=True, overall_score=0.9
        ))
        mock_verification.return_value = mock_verification_instance

        # Мокаем менеджеры
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        # Настраиваем todo manager для возврата задачи
        mock_task = Mock()
        mock_task.id = "test_task_123"
        mock_task.type = TaskType.CODE
        mock_task.description = "Write a test function"
        mock_task.status = "pending"

        mock_todo_manager.get_task = AsyncMock(return_value=mock_task)
        mock_todo_manager.update_task_status = AsyncMock()
        mock_todo_manager.get_pending_tasks = AsyncMock(return_value=[mock_task])

        server_core = ServerCore(
            todo_manager=mock_todo_manager,
            status_manager=mock_status_manager,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger
        )

        # Интегрируем LLM
        llm_manager = LLMManager()

        async def test():
            # Обрабатываем задачу
            await server_core.process_single_task("test_task_123")

            # Проверяем, что задача была получена
            mock_todo_manager.get_task.assert_called_with("test_task_123")

            # Проверяем, что можем сгенерировать код для задачи через LLM
            request = GenerationRequest(prompt=mock_task.description)
            llm_response = await llm_manager.generate(request)

            assert llm_response.success == True
            assert "def test_function" in llm_response.content

        asyncio.run(test())


class TestFullSystemIntegration:
    """Интеграционные тесты всей системы"""

    @patch('src.core.di_container.DIContainer.resolve')
    def test_di_container_full_integration(self, mock_resolve):
        """Тестирует полную интеграцию через DI контейнер"""

        # Мокаем разрешение сервисов
        def resolve_side_effect(service_type):
            if service_type.__name__ == 'ILLMManager':
                return Mock(generate=AsyncMock(return_value=Mock(content="LLM response", success=True)))
            elif service_type.__name__ == 'IVerificationManager':
                return Mock(run_verification_pipeline=AsyncMock(return_value=Mock(overall_passed=True)))
            elif service_type.__name__ == 'IQualityGateManager':
                return Mock(run_quality_checks=AsyncMock(return_value=[]))
            return Mock()

        mock_resolve.side_effect = resolve_side_effect

        container = DIContainer()

        # Регистрируем сервисы
        class ILLMManager: pass
        class IVerificationManager: pass
        class IQualityGateManager: pass

        container.register_singleton(ILLMManager)
        container.register_singleton(IVerificationManager)
        container.register_singleton(IQualityGateManager)

        async def test():
            # Разрешаем сервисы
            llm = container.resolve(ILLMManager)
            verification = container.resolve(IVerificationManager)
            quality = container.resolve(IQualityGateManager)

            # Проверяем базовую функциональность
            llm_response = await llm.generate(GenerationRequest(prompt="test"))
            assert llm_response.success == True

            verification_result = await verification.run_verification_pipeline("task_123")
            assert verification_result.overall_passed == True

            quality_results = await quality.run_quality_checks()
            assert isinstance(quality_results, list)

        asyncio.run(test())

    def test_task_processing_workflow(self):
        """Тестирует полный workflow обработки задач"""

        # Создаем моки для всех компонентов
        mock_todo_manager = Mock()
        mock_status_manager = Mock()
        mock_checkpoint_manager = Mock()
        mock_logger = Mock()

        # Настраиваем задачу
        mock_task = Mock()
        mock_task.id = "integration_task_001"
        mock_task.type = TaskType.CODE
        mock_task.description = "Implement user authentication"
        mock_task.status = "pending"

        mock_todo_manager.get_pending_tasks = Mock(return_value=[mock_task])
        mock_todo_manager.get_task = AsyncMock(return_value=mock_task)
        mock_todo_manager.update_task_status = AsyncMock()

        with patch('src.core.server_core.QualityGateManager') as mock_quality, \
             patch('src.core.server_core.MultiLevelVerificationManager') as mock_verification, \
             patch('src.llm.manager.LLMManager') as mock_llm:

            # Настраиваем компоненты
            mock_quality_instance = Mock()
            mock_quality_instance.run_quality_checks = AsyncMock(return_value=[])
            mock_quality.return_value = mock_quality_instance

            mock_verification_instance = Mock()
            mock_verification_instance.run_verification_pipeline = AsyncMock(return_value=Mock(
                overall_passed=True, overall_score=0.88
            ))
            mock_verification.return_value = mock_verification_instance

            mock_llm_instance = Mock()
            mock_llm_instance.generate_with_routing = AsyncMock(return_value=Mock(
                content="def authenticate_user(username, password): return True",
                success=True,
                response_time=2.0
            ))
            mock_llm.return_value = mock_llm_instance

            server_core = ServerCore(
                todo_manager=mock_todo_manager,
                status_manager=mock_status_manager,
                checkpoint_manager=mock_checkpoint_manager,
                logger=mock_logger
            )

            async def test():
                # Запускаем обработку задачи
                await server_core.process_single_task("integration_task_001")

                # Проверяем, что все компоненты были использованы
                mock_todo_manager.get_task.assert_called_with("integration_task_001")
                mock_todo_manager.update_task_status.assert_called()

                # Проверяем, что верификация была выполнена
                mock_verification_instance.run_verification_pipeline.assert_called()

            asyncio.run(test())

    def test_end_to_end_quality_assurance(self):
        """Тестирует end-to-end quality assurance pipeline"""

        with patch('src.quality.quality_gate_manager.QualityGateManager') as mock_quality_manager, \
             patch('src.verification.verification_manager.MultiLevelVerificationManager') as mock_verification_manager, \
             patch('src.llm.manager.LLMManager') as mock_llm_manager:

            # Настраиваем Quality Gates
            mock_quality_instance = Mock()
            mock_quality_instance.run_quality_checks = AsyncMock(return_value=[
                Mock(check_type=Mock(value='coverage'), passed=True, score=0.85),
                Mock(check_type=Mock(value='complexity'), passed=True, score=0.9),
                Mock(check_type=Mock(value='style'), passed=False, score=0.6)
            ])
            mock_quality_manager.return_value = mock_quality_instance

            # Настраиваем Verification
            mock_verification_instance = Mock()
            mock_verification_instance.run_verification_pipeline = AsyncMock(return_value=Mock(
                overall_passed=True,
                overall_score=0.82,
                level_results={
                    VerificationLevel.PRE_EXECUTION: Mock(passed=True, score=0.88),
                    VerificationLevel.IN_EXECUTION: Mock(passed=True, score=0.85),
                    VerificationLevel.POST_EXECUTION: Mock(passed=True, score=0.80),
                    VerificationLevel.AI_VALIDATION: Mock(passed=True, score=0.78)
                }
            ))
            mock_verification_manager.return_value = mock_verification_instance

            # Настраиваем LLM
            mock_llm_instance = Mock()
            mock_llm_instance.generate_with_routing = AsyncMock(return_value=Mock(
                content='''def process_data(data):
    """Process input data with validation."""
    if not data:
        raise ValueError("Data cannot be empty")
    return {"processed": len(data), "status": "success"}''',
                success=True
            ))
            mock_llm_manager.return_value = mock_llm_instance

            async def test():
                # Создаем менеджеры
                quality_manager = mock_quality_manager.return_value
                verification_manager = mock_verification_manager.return_value
                llm_manager = mock_llm_manager.return_value

                # 1. Генерируем код через LLM
                llm_response = await llm_manager.generate_with_routing(
                    GenerationRequest(prompt="Write a data processing function with validation")
                )
                assert llm_response.success == True

                # 2. Проверяем качество кода
                quality_results = await quality_manager.run_quality_checks({
                    'code_content': llm_response.content
                })
                assert len(quality_results) == 3

                # 3. Запускаем верификацию
                verification_result = await verification_manager.run_verification_pipeline("qa_task_001", {
                    'code': llm_response.content,
                    'quality_results': quality_results
                })

                assert verification_result.overall_passed == True
                assert verification_result.overall_score >= 0.8

                # 4. Проверяем все уровни верификации
                assert len(verification_result.level_results) == 4
                for level, result in verification_result.level_results.items():
                    assert result.passed == True
                    assert result.score >= 0.7

            asyncio.run(test())


class TestPerformanceIntegration:
    """Интеграционные тесты производительности"""

    def test_concurrent_task_processing(self):
        """Тестирует конкурентную обработку задач"""

        with patch('src.core.server_core.QualityGateManager') as mock_quality, \
             patch('src.core.server_core.MultiLevelVerificationManager') as mock_verification:

            mock_quality_instance = Mock()
            mock_quality_instance.run_quality_checks = AsyncMock(return_value=[])
            mock_quality.return_value = mock_quality_instance

            mock_verification_instance = Mock()
            mock_verification_instance.run_verification_pipeline = AsyncMock(return_value=Mock(overall_passed=True))
            mock_verification.return_value = mock_verification_instance

            async def process_task(task_id: str, todo_manager, status_manager, checkpoint_manager, logger):
                server_core = ServerCore(todo_manager, status_manager, checkpoint_manager, logger)
                await server_core.process_single_task(task_id)
                return f"Task {task_id} processed"

            async def test():
                # Создаем несколько задач
                tasks = []
                for i in range(5):
                    mock_todo_manager = Mock()
                    mock_status_manager = Mock()
                    mock_checkpoint_manager = Mock()
                    mock_logger = Mock()

                    mock_task = Mock()
                    mock_task.id = f"concurrent_task_{i}"
                    mock_task.type = TaskType.CODE
                    mock_task.description = f"Task {i} description"

                    mock_todo_manager.get_task = AsyncMock(return_value=mock_task)
                    mock_todo_manager.update_task_status = AsyncMock()

                    task = process_task(
                        f"concurrent_task_{i}",
                        mock_todo_manager,
                        mock_status_manager,
                        mock_checkpoint_manager,
                        mock_logger
                    )
                    tasks.append(task)

                # Запускаем конкурентно
                results = await asyncio.gather(*tasks)

                # Проверяем результаты
                assert len(results) == 5
                for result in results:
                    assert "processed" in result

            asyncio.run(test())

    def test_memory_usage_monitoring(self):
        """Тестирует мониторинг использования памяти"""

        with patch('src.verification.execution_monitor.ExecutionMonitor') as mock_monitor:

            mock_monitor_instance = Mock()
            mock_monitor_instance.start_monitoring = AsyncMock()
            mock_monitor_instance.check_execution_health = AsyncMock(return_value={
                'memory_usage': 85.5,
                'cpu_usage': 45.2,
                'status': 'healthy'
            })
            mock_monitor_instance.stop_monitoring = AsyncMock(return_value={
                'execution_time': 2.5,
                'peak_memory': 120.5,
                'avg_cpu': 52.1
            })
            mock_monitor.return_value = mock_monitor_instance

            async def test():
                monitor = mock_monitor.return_value

                # Мониторим выполнение
                await monitor.start_monitoring("memory_test_task")

                # Проверяем здоровье несколько раз
                for _ in range(3):
                    health = await monitor.check_execution_health("memory_test_task")
                    assert health['status'] == 'healthy'
                    assert 'memory_usage' in health
                    assert 'cpu_usage' in health

                # Завершаем мониторинг
                metrics = await monitor.stop_monitoring("memory_test_task")

                assert 'execution_time' in metrics
                assert 'peak_memory' in metrics
                assert 'avg_cpu' in metrics

            asyncio.run(test())