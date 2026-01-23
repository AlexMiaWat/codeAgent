"""
Static tests for Quality Gates system

This module contains static tests that verify quality gates
definitions, interfaces, and method implementations without
requiring runtime instantiation.
"""

import inspect
from abc import ABC
from typing import get_type_hints

from src.quality.interfaces import (
    IQualityChecker, IQualityGateManager, IQualityReporter, IQualityGate
)
from src.quality.quality_gate_manager import QualityGateManager
from src.quality.checkers import (
    CoverageChecker, ComplexityChecker, SecurityChecker, StyleChecker,
    TaskTypeChecker, DependencyChecker, ResourceChecker, ProgressChecker
)
from src.quality.reporters import ConsoleReporter, FileReporter
from src.quality.models.quality_result import (
    QualityStatus, QualityCheckType, QualityResult, QualityGateResult
)


class TestQualityInterfacesStatic:
    """Static tests for quality interfaces"""

    def test_i_quality_checker_is_abstract(self):
        """Test IQualityChecker is abstract base class"""
        assert issubclass(IQualityChecker, ABC)

    def test_i_quality_gate_manager_is_abstract(self):
        """Test IQualityGateManager is abstract base class"""
        assert issubclass(IQualityGateManager, ABC)

    def test_i_quality_reporter_is_abstract(self):
        """Test IQualityReporter is abstract base class"""
        assert issubclass(IQualityReporter, ABC)

    def test_i_quality_gate_is_abstract(self):
        """Test IQualityGate is abstract base class"""
        assert issubclass(IQualityGate, ABC)

    def test_i_quality_checker_methods(self):
        """Test IQualityChecker has expected abstract methods"""
        methods = [name for name, _ in inspect.getmembers(
            IQualityChecker, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['check', 'get_check_type', 'configure']
        for method in expected_methods:
            assert method in methods, f"IQualityChecker missing {method}"

    def test_i_quality_gate_manager_methods(self):
        """Test IQualityGateManager has expected methods"""
        methods = [name for name, _ in inspect.getmembers(
            IQualityGateManager, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['configure', 'run_all_gates', 'should_block_execution', 'get_gate_results']
        for method in expected_methods:
            assert method in methods, f"IQualityGateManager missing {method}"

    def test_i_quality_reporter_methods(self):
        """Test IQualityReporter has expected methods"""
        methods = [name for name, _ in inspect.getmembers(
            IQualityReporter, predicate=inspect.isfunction) if not name.startswith('_')]

        expected_methods = ['report', 'configure']
        for method in expected_methods:
            assert method in methods, f"IQualityReporter missing {method}"


class TestQualityGateManagerStatic:
    """Static tests for QualityGateManager"""

    def test_quality_gate_manager_inherits_from_interface(self):
        """Test QualityGateManager implements IQualityGateManager"""
        assert issubclass(QualityGateManager, IQualityGateManager)
        assert issubclass(QualityGateManager, ABC)

    def test_quality_gate_manager_methods_exist(self):
        """Test QualityGateManager has expected methods"""
        expected_methods = [
            'configure', 'run_all_gates', 'should_block_execution', 'get_gate_results',
            '_setup_default_configuration', '_run_single_gate', '_aggregate_results',
            '_should_block_based_on_results', '_get_gate_config', '_is_gate_enabled'
        ]
        for method in expected_methods:
            assert hasattr(QualityGateManager, method)
            assert callable(getattr(QualityGateManager, method))

    def test_quality_gate_manager_init_signature(self):
        """Test QualityGateManager.__init__ signature"""
        init_sig = inspect.signature(QualityGateManager.__init__)
        assert 'config' in init_sig.parameters


class TestQualityCheckersStatic:
    """Static tests for quality checkers"""

    def test_coverage_checker_inherits_from_interface(self):
        """Test CoverageChecker implements IQualityChecker"""
        assert issubclass(CoverageChecker, IQualityChecker)
        assert issubclass(CoverageChecker, ABC)

    def test_complexity_checker_inherits_from_interface(self):
        """Test ComplexityChecker implements IQualityChecker"""
        assert issubclass(ComplexityChecker, IQualityChecker)
        assert issubclass(ComplexityChecker, ABC)

    def test_security_checker_inherits_from_interface(self):
        """Test SecurityChecker implements IQualityChecker"""
        assert issubclass(SecurityChecker, IQualityChecker)
        assert issubclass(SecurityChecker, ABC)

    def test_style_checker_inherits_from_interface(self):
        """Test StyleChecker implements IQualityChecker"""
        assert issubclass(StyleChecker, IQualityChecker)
        assert issubclass(StyleChecker, ABC)

    def test_task_type_checker_inherits_from_interface(self):
        """Test TaskTypeChecker implements IQualityChecker"""
        assert issubclass(TaskTypeChecker, IQualityChecker)
        assert issubclass(TaskTypeChecker, ABC)

    def test_dependency_checker_inherits_from_interface(self):
        """Test DependencyChecker implements IQualityChecker"""
        assert issubclass(DependencyChecker, IQualityChecker)
        assert issubclass(DependencyChecker, ABC)

    def test_resource_checker_inherits_from_interface(self):
        """Test ResourceChecker implements IQualityChecker"""
        assert issubclass(ResourceChecker, IQualityChecker)
        assert issubclass(ResourceChecker, ABC)

    def test_progress_checker_inherits_from_interface(self):
        """Test ProgressChecker implements IQualityChecker"""
        assert issubclass(ProgressChecker, IQualityChecker)
        assert issubclass(ProgressChecker, ABC)

    def test_all_checkers_have_required_methods(self):
        """Test all checkers have required methods"""
        checkers = [
            CoverageChecker, ComplexityChecker, SecurityChecker, StyleChecker,
            TaskTypeChecker, DependencyChecker, ResourceChecker, ProgressChecker
        ]

        required_methods = ['check', 'get_check_type', 'configure']

        for checker_class in checkers:
            for method in required_methods:
                assert hasattr(checker_class, method), f"{checker_class.__name__} missing {method}"
                assert callable(getattr(checker_class, method)), f"{checker_class.__name__}.{method} not callable"


class TestQualityReportersStatic:
    """Static tests for quality reporters"""

    def test_console_reporter_inherits_from_interface(self):
        """Test ConsoleReporter implements IQualityReporter"""
        assert issubclass(ConsoleReporter, IQualityReporter)
        assert issubclass(ConsoleReporter, ABC)

    def test_file_reporter_inherits_from_interface(self):
        """Test FileReporter implements IQualityReporter"""
        assert issubclass(FileReporter, IQualityReporter)
        assert issubclass(FileReporter, ABC)

    def test_reporters_have_required_methods(self):
        """Test reporters have required methods"""
        reporters = [ConsoleReporter, FileReporter]
        required_methods = ['report', 'configure']

        for reporter_class in reporters:
            for method in required_methods:
                assert hasattr(reporter_class, method), f"{reporter_class.__name__} missing {method}"
                assert callable(getattr(reporter_class, method)), f"{reporter_class.__name__}.{method} not callable"


class TestQualityModelsStatic:
    """Static tests for quality models"""

    def test_quality_status_enum_values(self):
        """Test QualityStatus enum has expected values"""
        assert QualityStatus.PASSED.value == "passed"
        assert QualityStatus.FAILED.value == "failed"
        assert QualityStatus.WARNING.value == "warning"
        assert QualityStatus.ERROR.value == "error"

    def test_quality_check_type_enum_values(self):
        """Test QualityCheckType enum has expected values"""
        expected_types = [
            "coverage", "complexity", "security", "style", "task_type",
            "dependency", "resource", "progress"
        ]
        for check_type in expected_types:
            assert hasattr(QualityCheckType, check_type.upper())
            assert getattr(QualityCheckType, check_type.upper()).value == check_type

    def test_quality_result_init_signature(self):
        """Test QualityResult.__init__ signature"""
        init_sig = inspect.signature(QualityResult.__init__)
        expected_params = ['check_type', 'status', 'score', 'message', 'details']
        for param in expected_params:
            assert param in init_sig.parameters

    def test_quality_gate_result_init_signature(self):
        """Test QualityGateResult.__init__ signature"""
        init_sig = inspect.signature(QualityGateResult.__init__)
        expected_params = ['gate_name', 'timestamp', 'results']
        for param in expected_params:
            assert param in init_sig.parameters


class TestMethodSignatures:
    """Test method signatures"""

    def test_quality_gate_manager_configure_signature(self):
        """Test QualityGateManager.configure signature"""
        sig = inspect.signature(QualityGateManager.configure)
        assert 'config' in sig.parameters

    def test_quality_gate_manager_run_all_gates_signature(self):
        """Test QualityGateManager.run_all_gates signature"""
        sig = inspect.signature(QualityGateManager.run_all_gates)
        assert 'context' in sig.parameters

    def test_checker_check_signature(self):
        """Test checker check method signature"""
        sig = inspect.signature(CoverageChecker.check)
        assert 'context' in sig.parameters

    def test_checker_configure_signature(self):
        """Test checker configure method signature"""
        sig = inspect.signature(CoverageChecker.configure)
        assert 'config' in sig.parameters

    def test_reporter_report_signature(self):
        """Test reporter report method signature"""
        sig = inspect.signature(ConsoleReporter.report)
        assert 'result' in sig.parameters


class TestTypeHints:
    """Test type hints"""

    def test_quality_gate_manager_type_hints(self):
        """Test QualityGateManager methods have type hints"""
        methods_to_check = ['configure', 'run_all_gates', 'should_block_execution']

        for method_name in methods_to_check:
            method = getattr(QualityGateManager, method_name)
            hints = get_type_hints(method)
            assert hints, f"{method_name} should have type hints"

    def test_checker_type_hints(self):
        """Test checker methods have type hints"""
        methods_to_check = ['check', 'configure', 'get_check_type']

        for method_name in methods_to_check:
            method = getattr(CoverageChecker, method_name)
            hints = get_type_hints(method)
            assert hints, f"{method_name} should have type hints"


class TestClassHierarchy:
    """Test class hierarchy"""

    def test_no_multiple_inheritance_conflicts(self):
        """Test that class hierarchies don't have conflicts"""
        classes_to_check = [
            QualityGateManager, CoverageChecker, ComplexityChecker,
            SecurityChecker, ConsoleReporter, FileReporter
        ]

        for cls in classes_to_check:
            mro = cls.__mro__
            # Should not have duplicates in MRO
            assert len(mro) == len(set(mro)), f"{cls.__name__} has MRO conflicts"