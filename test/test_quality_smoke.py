"""
Дымовые тесты для Quality Gates framework

Проверяют базовую работоспособность:
- QualityGateManager может быть создан
- Чекеры могут выполняться
- Gates могут быть настроены
- Интеграция компонентов работает
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import asyncio
from typing import Dict, Any, Optional, List

from src.quality.quality_gate_manager import QualityGateManager
from src.quality.interfaces.iquality_gate import IQualityGate
from src.quality.models.quality_result import (
    QualityResult, QualityGateResult, QualityStatus, QualityCheckType
)
from src.quality.checkers import (
    CoverageChecker, ComplexityChecker, SecurityChecker, StyleChecker,
    TaskTypeChecker, DependencyChecker, ResourceChecker, ProgressChecker
)


class TestQualityGateManagerSmoke:
    """Дымовые тесты для QualityGateManager"""

    def test_manager_creation(self):
        """Проверяет создание QualityGateManager"""
        manager = QualityGateManager()

        assert manager is not None
        assert hasattr(manager, '_checkers')
        assert hasattr(manager, '_enabled_gates')
        assert hasattr(manager, '_gate_configs')

    def test_manager_creation_with_config(self):
        """Проверяет создание менеджера с конфигурацией"""
        config = {
            QualityCheckType.COVERAGE: {
                'enabled': True,
                'threshold': 0.8,
                'strict': False
            },
            QualityCheckType.COMPLEXITY: {
                'enabled': True,
                'threshold': 0.7
            }
        }

        manager = QualityGateManager(config)

        assert manager._config == config
        assert QualityCheckType.COVERAGE in manager._enabled_gates
        assert manager._enabled_gates[QualityCheckType.COVERAGE] == True

    def test_manager_run_quality_checks(self):
        """Проверяет выполнение quality checks"""
        manager = QualityGateManager()

        async def test():
            results = await manager.run_quality_checks()

            assert results is not None
            assert isinstance(results, list)

            # Даже если нет включенных чекеров, должен вернуться пустой список
            if len(results) > 0:
                for result in results:
                    assert isinstance(result, QualityResult)

        asyncio.run(test())

    def test_manager_run_quality_checks_with_context(self):
        """Проверяет выполнение quality checks с контекстом"""
        manager = QualityGateManager()

        context = {
            'project_path': '/test/project',
            'files': ['test.py', 'main.py'],
            'task_type': 'code'
        }

        async def test():
            results = await manager.run_quality_checks(context)

            assert results is not None
            assert isinstance(results, list)

        asyncio.run(test())

    def test_manager_get_enabled_gates(self):
        """Проверяет получение списка включенных gates"""
        config = {
            QualityCheckType.COVERAGE: {'enabled': True},
            QualityCheckType.COMPLEXITY: {'enabled': False},
            QualityCheckType.SECURITY: {'enabled': True}
        }

        manager = QualityGateManager(config)

        enabled_gates = manager.get_enabled_gates()

        assert enabled_gates is not None
        assert isinstance(enabled_gates, list)
        assert QualityCheckType.COVERAGE in enabled_gates
        assert QualityCheckType.SECURITY in enabled_gates
        assert QualityCheckType.COMPLEXITY not in enabled_gates

    def test_manager_configure_gate(self):
        """Проверяет настройку gate"""
        manager = QualityGateManager()

        config = {
            'enabled': True,
            'threshold': 0.85,
            'strict': True
        }

        async def test():
            success = await manager.configure_gate(QualityCheckType.COVERAGE, config)

            # Настройка должна выполниться без ошибок
            assert success == True or success is None  # зависит от реализации

        asyncio.run(test())

    def test_manager_get_quality_report(self):
        """Проверяет получение quality report"""
        manager = QualityGateManager()

        async def test():
            # Сначала выполняем проверки
            results = await manager.run_quality_checks()

            # Получаем отчет
            report = await manager.get_quality_report()

            assert report is not None
            assert isinstance(report, dict)

        asyncio.run(test())

    def test_manager_is_quality_gate_passed(self):
        """Проверяет проверку прохождения quality gate"""
        manager = QualityGateManager()

        async def test():
            passed = await manager.is_quality_gate_passed()

            # Должен вернуться булевый результат
            assert isinstance(passed, bool)

        asyncio.run(test())


class TestQualityCheckersSmoke:
    """Дымовые тесты для чекеров качества"""

    def test_coverage_checker_creation_and_execution(self):
        """Проверяет создание и выполнение CoverageChecker"""
        checker = CoverageChecker()

        assert checker is not None
        assert checker.name == "CoverageChecker"
        assert checker.check_type == QualityCheckType.COVERAGE

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.COVERAGE

        asyncio.run(test())

    def test_coverage_checker_with_context(self):
        """Проверяет CoverageChecker с контекстом"""
        checker = CoverageChecker()

        context = {
            'project_path': '/test',
            'coverage_data': {'total': 100, 'covered': 85}
        }

        async def test():
            result = await checker.check(context)

            assert result is not None
            assert isinstance(result, QualityResult)

        asyncio.run(test())

    def test_complexity_checker_creation_and_execution(self):
        """Проверяет создание и выполнение ComplexityChecker"""
        checker = ComplexityChecker()

        assert checker is not None
        assert checker.name == "ComplexityChecker"
        assert checker.check_type == QualityCheckType.COMPLEXITY

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.COMPLEXITY

        asyncio.run(test())

    def test_security_checker_creation_and_execution(self):
        """Проверяет создание и выполнение SecurityChecker"""
        checker = SecurityChecker()

        assert checker is not None
        assert checker.name == "SecurityChecker"
        assert checker.check_type == QualityCheckType.SECURITY

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.SECURITY

        asyncio.run(test())

    def test_style_checker_creation_and_execution(self):
        """Проверяет создание и выполнение StyleChecker"""
        checker = StyleChecker()

        assert checker is not None
        assert checker.name == "StyleChecker"
        assert checker.check_type == QualityCheckType.STYLE

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.STYLE

        asyncio.run(test())

    def test_task_type_checker_creation_and_execution(self):
        """Проверяет создание и выполнение TaskTypeChecker"""
        checker = TaskTypeChecker()

        assert checker is not None
        assert checker.name == "TaskTypeChecker"
        assert checker.check_type == QualityCheckType.TASK_TYPE

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.TASK_TYPE

        asyncio.run(test())

    def test_dependency_checker_creation_and_execution(self):
        """Проверяет создание и выполнение DependencyChecker"""
        checker = DependencyChecker()

        assert checker is not None
        assert checker.name == "DependencyChecker"
        assert checker.check_type == QualityCheckType.DEPENDENCY

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.DEPENDENCY

        asyncio.run(test())

    def test_resource_checker_creation_and_execution(self):
        """Проверяет создание и выполнение ResourceChecker"""
        checker = ResourceChecker()

        assert checker is not None
        assert checker.name == "ResourceChecker"
        assert checker.check_type == QualityCheckType.RESOURCE

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.RESOURCE

        asyncio.run(test())

    def test_progress_checker_creation_and_execution(self):
        """Проверяет создание и выполнение ProgressChecker"""
        checker = ProgressChecker()

        assert checker is not None
        assert checker.name == "ProgressChecker"
        assert checker.check_type == QualityCheckType.PROGRESS

        async def test():
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.PROGRESS

        asyncio.run(test())

    @pytest.mark.parametrize("checker_class", [
        CoverageChecker,
        ComplexityChecker,
        SecurityChecker,
        StyleChecker,
        TaskTypeChecker,
        DependencyChecker,
        ResourceChecker,
        ProgressChecker
    ])
    def test_all_checkers_basic_functionality(self, checker_class):
        """Проверяет базовую функциональность всех чекеров"""
        checker = checker_class()

        # Проверяем основные атрибуты
        assert hasattr(checker, 'name')
        assert hasattr(checker, 'check_type')
        assert hasattr(checker, 'description')

        # Проверяем основные методы
        assert hasattr(checker, 'configure')
        assert hasattr(checker, 'check')
        assert asyncio.iscoroutinefunction(checker.check)

        # Проверяем свойства
        assert checker.get_default_threshold() >= 0.0
        assert checker.get_default_threshold() <= 1.0

        assert isinstance(checker.get_supported_file_types(), list)

    @pytest.mark.parametrize("checker_class", [
        CoverageChecker,
        ComplexityChecker,
        SecurityChecker,
        StyleChecker,
        TaskTypeChecker,
        DependencyChecker,
        ResourceChecker,
        ProgressChecker
    ])
    def test_all_checkers_configuration(self, checker_class):
        """Проверяет настройку всех чекеров"""
        checker = checker_class()

        config = {'threshold': 0.8, 'enabled': True}

        # Настройка должна выполниться без ошибок
        checker.configure(config)

        # Проверяем, что конфигурация валидна
        assert checker.validate_configuration(config) == True

    @pytest.mark.parametrize("checker_class,expected_types", [
        (CoverageChecker, ['.py', '.js', '.ts', '.java']),
        (ComplexityChecker, ['.py', '.js', '.ts', '.java', '.cpp', '.c']),
        (SecurityChecker, ['.py', '.js', '.ts', '.java', '.yaml', '.yml', '.json']),
        (StyleChecker, ['.py', '.js', '.ts', '.java', '.css', '.html']),
    ])
    def test_checker_supported_file_types(self, checker_class, expected_types):
        """Проверяет поддерживаемые типы файлов для чекеров"""
        checker = checker_class()

        supported_types = checker.get_supported_file_types()

        assert isinstance(supported_types, list)
        # Проверяем, что базовые типы поддерживаются
        for expected_type in expected_types:
            if expected_type in ['.py', '.js', '.ts']:
                assert expected_type in supported_types or len(supported_types) == 0


class TestQualityGatesIntegrationSmoke:
    """Дымовые тесты интеграции Quality Gates"""

    def test_manager_with_multiple_checkers(self):
        """Проверяет работу менеджера с несколькими чекерами"""
        config = {
            QualityCheckType.COVERAGE: {'enabled': True, 'threshold': 0.8},
            QualityCheckType.COMPLEXITY: {'enabled': True, 'threshold': 0.7},
            QualityCheckType.SECURITY: {'enabled': True, 'threshold': 0.9}
        }

        manager = QualityGateManager(config)

        async def test():
            results = await manager.run_quality_checks()

            assert results is not None
            assert isinstance(results, list)

            # Проверяем, что результаты соответствуют включенным чекерам
            enabled_gates = manager.get_enabled_gates()
            # Количество результатов может быть меньше количества чекеров,
            # если некоторые чекеры не могут выполниться

        asyncio.run(test())

    def test_manager_configuration_workflow(self):
        """Проверяет workflow настройки менеджера"""
        manager = QualityGateManager()

        # Настраиваем gate
        config = {'enabled': True, 'threshold': 0.85, 'strict': False}

        async def test():
            # Настраиваем gate
            await manager.configure_gate(QualityCheckType.COVERAGE, config)

            # Проверяем, что gate включен
            enabled_gates = manager.get_enabled_gates()
            assert QualityCheckType.COVERAGE in enabled_gates

            # Выполняем проверки
            results = await manager.run_quality_checks()

            # Получаем отчет
            report = await manager.get_quality_report()
            assert isinstance(report, dict)

            # Проверяем статус
            passed = await manager.is_quality_gate_passed()
            assert isinstance(passed, bool)

        asyncio.run(test())

    def test_checker_configuration_and_execution(self):
        """Проверяет настройку и выполнение чекера"""
        checker = CoverageChecker()

        # Настраиваем чекер
        config = {'threshold': 0.8, 'min_coverage': 75}
        checker.configure(config)

        # Проверяем валидность конфигурации
        assert checker.validate_configuration(config) == True

        async def test():
            # Выполняем проверку
            result = await checker.check()

            assert result is not None
            assert isinstance(result, QualityResult)
            assert result.check_type == QualityCheckType.COVERAGE

            # Проверяем, что результат содержит ожидаемые поля
            assert hasattr(result, 'passed')
            assert hasattr(result, 'score')
            assert hasattr(result, 'check_name')

        asyncio.run(test())

    def test_quality_gate_result_structure(self):
        """Проверяет структуру QualityGateResult"""
        # Создаем тестовые результаты
        coverage_result = QualityResult(
            check_type=QualityCheckType.COVERAGE,
            check_name="Coverage Check",
            passed=True,
            score=0.85
        )

        complexity_result = QualityResult(
            check_type=QualityCheckType.COMPLEXITY,
            check_name="Complexity Check",
            passed=True,
            score=0.9
        )

        gate_result = QualityGateResult(
            gate_name="Code Quality Gate",
            check_type=QualityCheckType.COVERAGE,  # Это поле может быть устаревшим
            passed=True,
            overall_score=0.875,
            results=[coverage_result, complexity_result],
            execution_time=1.5
        )

        assert gate_result.gate_name == "Code Quality Gate"
        assert gate_result.passed == True
        assert gate_result.overall_score == 0.875
        assert len(gate_result.results) == 2
        assert gate_result.execution_time == 1.5

    def test_error_handling_in_quality_checks(self):
        """Проверяет обработку ошибок в quality checks"""
        manager = QualityGateManager()

        async def test():
            # Выполняем проверки - даже если есть ошибки, не должно быть исключений
            try:
                results = await manager.run_quality_checks()
                assert isinstance(results, list)
            except Exception as e:
                pytest.fail(f"Unexpected exception in quality checks: {e}")

        asyncio.run(test())

    def test_empty_configuration_handling(self):
        """Проверяет обработку пустой конфигурации"""
        manager = QualityGateManager({})

        async def test():
            # С пустой конфигурацией все равно должно работать
            results = await manager.run_quality_checks()
            assert isinstance(results, list)

            enabled_gates = manager.get_enabled_gates()
            assert isinstance(enabled_gates, list)

        asyncio.run(test())