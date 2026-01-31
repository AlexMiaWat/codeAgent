"""
Статические тесты для Quality Gates framework

Тестирует:
- Интерфейсы Quality Gates
- QualityGateManager
- Различные чекеры качества
- Структуры данных результатов
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.quality.quality_gate_manager import QualityGateManager
from src.quality.interfaces.iquality_gate import IQualityGate
from src.quality.interfaces.iquality_checker import IQualityChecker
from src.quality.interfaces.iquality_gate_manager import IQualityGateManager
from src.quality.interfaces.iquality_reporter import IQualityReporter
from src.quality.models.quality_result import (
    QualityResult, QualityGateResult, QualityStatus, QualityCheckType
)
from src.quality.checkers import (
    CoverageChecker, ComplexityChecker, SecurityChecker, StyleChecker,
    TaskTypeChecker, DependencyChecker, ResourceChecker, ProgressChecker
)


class TestQualityInterfaces:
    """Тесты для интерфейсов Quality Gates"""

    def test_i_quality_gate_interface(self):
        """Проверяет интерфейс IQualityGate"""
        # Проверяем properties
        assert hasattr(IQualityGate, 'name')
        assert hasattr(IQualityGate, 'check_type')
        assert hasattr(IQualityGate, 'enabled')

        # Проверяем методы
        interface_methods = [
            'configure', 'run_checks', 'get_required_score',
            'is_strict_mode', 'get_configuration_schema'
        ]

        for method in interface_methods:
            assert hasattr(IQualityGate, method)

        # Проверяем, что методы являются абстрактными
        import inspect
        for method_name in interface_methods:
            method = getattr(IQualityGate, method_name)
            assert hasattr(method, '__isabstractmethod__')
            assert method.__isabstractmethod__

    def test_i_quality_checker_interface(self):
        """Проверяет интерфейс IQualityChecker"""
        # Проверяем properties
        assert hasattr(IQualityChecker, 'name')
        assert hasattr(IQualityChecker, 'check_type')
        assert hasattr(IQualityChecker, 'description')

        # Проверяем методы
        interface_methods = [
            'configure', 'check', 'get_default_threshold',
            'is_configurable', 'get_supported_file_types', 'validate_configuration'
        ]

        for method in interface_methods:
            assert hasattr(IQualityChecker, method)

        # Проверяем, что методы являются абстрактными
        import inspect
        for method_name in interface_methods:
            method = getattr(IQualityChecker, method_name)
            assert hasattr(method, '__isabstractmethod__')
            assert method.__isabstractmethod__

    def test_i_quality_gate_manager_interface(self):
        """Проверяет интерфейс IQualityGateManager"""
        interface_methods = [
            'run_quality_checks', 'get_enabled_gates', 'configure_gate',
            'get_quality_report', 'is_quality_gate_passed'
        ]

        for method in interface_methods:
            assert hasattr(IQualityGateManager, method)

    def test_i_quality_reporter_interface(self):
        """Проверяет интерфейс IQualityReporter"""
        interface_methods = [
            'generate_report', 'export_report', 'get_summary'
        ]

        for method in interface_methods:
            assert hasattr(IQualityReporter, method)


class TestQualityDataStructures:
    """Тесты для структур данных Quality Gates"""

    def test_quality_result_creation(self):
        """Тестирует создание QualityResult"""
        result = QualityResult(
            check_type=QualityCheckType.COVERAGE,
            check_name="Code Coverage Check",
            passed=True,
            score=0.85,
            details="Coverage is above threshold",
            metadata={"covered_lines": 85, "total_lines": 100},
            recommendations=["Consider adding more tests for edge cases"],
            timestamp=datetime.now()
        )

        assert result.check_type == QualityCheckType.COVERAGE
        assert result.check_name == "Code Coverage Check"
        assert result.passed == True
        assert result.score == 0.85
        assert result.details == "Coverage is above threshold"
        assert result.metadata == {"covered_lines": 85, "total_lines": 100}
        assert len(result.recommendations) == 1
        assert isinstance(result.timestamp, datetime)

    def test_quality_result_defaults(self):
        """Тестирует значения по умолчанию для QualityResult"""
        result = QualityResult(
            check_type=QualityCheckType.COMPLEXITY,
            check_name="Complexity Check",
            passed=False
        )

        assert result.score == 0.0
        assert result.details is None
        assert result.metadata == {}
        assert result.recommendations == []
        assert result.issues == []

    def test_quality_gate_result_creation(self):
        """Тестирует создание QualityGateResult"""
        coverage_result = QualityResult(
            check_type=QualityCheckType.COVERAGE,
            check_name="Coverage",
            passed=True,
            score=0.9
        )

        complexity_result = QualityResult(
            check_type=QualityCheckType.COMPLEXITY,
            check_name="Complexity",
            passed=True,
            score=0.8
        )

        gate_result = QualityGateResult(
            gate_name="Code Quality Gate",
            check_type=QualityCheckType.COVERAGE,  # Это поле может быть устаревшим
            passed=True,
            overall_score=0.85,
            results=[coverage_result, complexity_result],
            execution_time=2.5,
            metadata={"total_checks": 2, "passed_checks": 2}
        )

        assert gate_result.gate_name == "Code Quality Gate"
        assert gate_result.passed == True
        assert gate_result.overall_score == 0.85
        assert len(gate_result.results) == 2
        assert gate_result.execution_time == 2.5

    def test_quality_status_enum(self):
        """Тестирует перечисление QualityStatus"""
        expected_statuses = {'PASSED', 'FAILED', 'WARNING', 'ERROR', 'SKIPPED'}

        actual_statuses = {status.name for status in QualityStatus}
        assert actual_statuses == expected_statuses

        # Проверяем значения
        assert QualityStatus.PASSED.value == "passed"
        assert QualityStatus.FAILED.value == "failed"
        assert QualityStatus.WARNING.value == "warning"

    def test_quality_check_type_enum(self):
        """Тестирует перечисление QualityCheckType"""
        expected_types = {
            'COVERAGE', 'COMPLEXITY', 'SECURITY', 'STYLE',
            'TASK_TYPE', 'DEPENDENCY', 'RESOURCE', 'PROGRESS'
        }

        actual_types = {check_type.name for check_type in QualityCheckType}
        assert actual_types == expected_types

        # Проверяем значения
        assert QualityCheckType.COVERAGE.value == "coverage"
        assert QualityCheckType.COMPLEXITY.value == "complexity"
        assert QualityCheckType.SECURITY.value == "security"


class TestQualityGateManagerStatic:
    """Статические тесты для QualityGateManager"""

    def test_manager_implements_interface(self):
        """Проверяет, что QualityGateManager реализует интерфейс"""
        assert issubclass(QualityGateManager, IQualityGateManager)

    def test_manager_initialization(self):
        """Тестирует инициализацию QualityGateManager"""
        config = {
            QualityCheckType.COVERAGE: {
                'enabled': True,
                'threshold': 0.8,
                'strict': False
            },
            QualityCheckType.COMPLEXITY: {
                'enabled': True,
                'threshold': 0.7,
                'max_complexity': 10
            }
        }

        manager = QualityGateManager(config)

        assert manager._config == config
        assert hasattr(manager, '_checkers')
        assert hasattr(manager, '_enabled_gates')
        assert hasattr(manager, '_gate_configs')

    def test_manager_default_initialization(self):
        """Тестирует инициализацию с конфигурацией по умолчанию"""
        manager = QualityGateManager()

        assert manager._config == {}
        assert isinstance(manager._checkers, dict)
        assert isinstance(manager._enabled_gates, dict)
        assert isinstance(manager._gate_configs, dict)

    def test_manager_checker_initialization(self):
        """Проверяет инициализацию чекеров"""
        manager = QualityGateManager()

        # Проверяем, что все чекеры инициализированы
        expected_checkers = {
            QualityCheckType.COVERAGE: CoverageChecker,
            QualityCheckType.COMPLEXITY: ComplexityChecker,
            QualityCheckType.SECURITY: SecurityChecker,
            QualityCheckType.STYLE: StyleChecker,
            QualityCheckType.TASK_TYPE: TaskTypeChecker,
            QualityCheckType.DEPENDENCY: DependencyChecker,
            QualityCheckType.RESOURCE: ResourceChecker,
            QualityCheckType.PROGRESS: ProgressChecker
        }

        for check_type, checker_class in expected_checkers.items():
            assert check_type in manager._checkers
            assert isinstance(manager._checkers[check_type], checker_class)

    def test_manager_method_signatures(self):
        """Проверяет сигнатуры методов"""
        import inspect

        manager = QualityGateManager()

        # Проверяем основные методы
        methods_to_check = [
            'run_quality_checks',
            'get_enabled_gates',
            'configure_gate',
            'get_quality_report',
            'is_quality_gate_passed'
        ]

        for method_name in methods_to_check:
            method = getattr(manager, method_name)
            assert asyncio.iscoroutinefunction(method)

    def test_manager_configuration_setup(self):
        """Тестирует настройку конфигурации"""
        config = {
            QualityCheckType.COVERAGE: {
                'enabled': True,
                'threshold': 0.85
            }
        }

        manager = QualityGateManager(config)

        # Проверяем, что настройки применились
        assert QualityCheckType.COVERAGE in manager._enabled_gates
        assert manager._enabled_gates[QualityCheckType.COVERAGE] == True


class TestQualityCheckersStatic:
    """Статические тесты для чекеров качества"""

    def test_coverage_checker_interface(self):
        """Проверяет, что CoverageChecker реализует интерфейс"""
        assert issubclass(CoverageChecker, IQualityChecker)

    def test_coverage_checker_initialization(self):
        """Тестирует инициализацию CoverageChecker"""
        checker = CoverageChecker()

        assert checker.name == "CoverageChecker"
        assert checker.check_type == QualityCheckType.COVERAGE
        assert checker.description is not None

    def test_coverage_checker_methods(self):
        """Проверяет методы CoverageChecker"""
        checker = CoverageChecker()

        # Проверяем основные методы
        assert hasattr(checker, 'configure')
        assert hasattr(checker, 'check')
        assert asyncio.iscoroutinefunction(checker.check)

        # Проверяем properties
        assert hasattr(checker, 'name')
        assert hasattr(checker, 'check_type')
        assert hasattr(checker, 'description')

    def test_complexity_checker_interface(self):
        """Проверяет, что ComplexityChecker реализует интерфейс"""
        assert issubclass(ComplexityChecker, IQualityChecker)

    def test_security_checker_interface(self):
        """Проверяет, что SecurityChecker реализует интерфейс"""
        assert issubclass(SecurityChecker, IQualityChecker)

    def test_style_checker_interface(self):
        """Проверяет, что StyleChecker реализует интерфейс"""
        assert issubclass(StyleChecker, IQualityChecker)

    def test_task_type_checker_interface(self):
        """Проверяет, что TaskTypeChecker реализует интерфейс"""
        assert issubclass(TaskTypeChecker, IQualityChecker)

    def test_dependency_checker_interface(self):
        """Проверяет, что DependencyChecker реализует интерфейс"""
        assert issubclass(DependencyChecker, IQualityChecker)

    def test_resource_checker_interface(self):
        """Проверяет, что ResourceChecker реализует интерфейс"""
        assert issubclass(ResourceChecker, IQualityChecker)

    def test_progress_checker_interface(self):
        """Проверяет, что ProgressChecker реализует интерфейс"""
        assert issubclass(ProgressChecker, IQualityChecker)

    @pytest.mark.parametrize("checker_class,expected_name", [
        (CoverageChecker, "CoverageChecker"),
        (ComplexityChecker, "ComplexityChecker"),
        (SecurityChecker, "SecurityChecker"),
        (StyleChecker, "StyleChecker"),
        (TaskTypeChecker, "TaskTypeChecker"),
        (DependencyChecker, "DependencyChecker"),
        (ResourceChecker, "ResourceChecker"),
        (ProgressChecker, "ProgressChecker"),
    ])
    def test_checker_names(self, checker_class, expected_name):
        """Тестирует имена чекеров"""
        checker = checker_class()
        assert checker.name == expected_name

    @pytest.mark.parametrize("checker_class,expected_type", [
        (CoverageChecker, QualityCheckType.COVERAGE),
        (ComplexityChecker, QualityCheckType.COMPLEXITY),
        (SecurityChecker, QualityCheckType.SECURITY),
        (StyleChecker, QualityCheckType.STYLE),
        (TaskTypeChecker, QualityCheckType.TASK_TYPE),
        (DependencyChecker, QualityCheckType.DEPENDENCY),
        (ResourceChecker, QualityCheckType.RESOURCE),
        (ProgressChecker, QualityCheckType.PROGRESS),
    ])
    def test_checker_types(self, checker_class, expected_type):
        """Тестирует типы чекеров"""
        checker = checker_class()
        assert checker.check_type == expected_type

    def test_checker_default_thresholds(self):
        """Тестирует пороги по умолчанию для чекеров"""
        checkers = [
            CoverageChecker(),
            ComplexityChecker(),
            SecurityChecker(),
            StyleChecker(),
            TaskTypeChecker(),
            DependencyChecker(),
            ResourceChecker(),
            ProgressChecker()
        ]

        for checker in checkers:
            threshold = checker.get_default_threshold()
            assert isinstance(threshold, float)
            assert 0.0 <= threshold <= 1.0

    def test_checker_supported_file_types(self):
        """Тестирует поддерживаемые типы файлов"""
        checkers = [
            CoverageChecker(),
            ComplexityChecker(),
            SecurityChecker(),
            StyleChecker(),
            TaskTypeChecker(),
            DependencyChecker(),
            ResourceChecker(),
            ProgressChecker()
        ]

        for checker in checkers:
            file_types = checker.get_supported_file_types()
            assert isinstance(file_types, list)
            # Большинство чекеров должны поддерживать Python файлы
            assert '.py' in file_types or len(file_types) == 0  # некоторые чекеры могут быть универсальными