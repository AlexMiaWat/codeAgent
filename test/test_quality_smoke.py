"""
Smoke tests for Quality Gates system

This module contains smoke tests that verify basic functionality
of quality gates components can be instantiated and basic operations work.
"""


from src.quality.quality_gate_manager import QualityGateManager
from src.quality.checkers import (
    CoverageChecker, ComplexityChecker, SecurityChecker, StyleChecker,
    TaskTypeChecker, DependencyChecker, ResourceChecker, ProgressChecker
)
from src.quality.reporters import ConsoleReporter, FileReporter
from src.quality.models.quality_result import (
    QualityStatus, QualityCheckType, QualityResult, QualityGateResult
)


class TestQualityGateManagerSmoke:
    """Smoke tests for QualityGateManager"""

    def test_quality_gate_manager_creation(self):
        """Test QualityGateManager can be created"""
        manager = QualityGateManager()
        assert manager is not None
        assert hasattr(manager, '_config')
        assert hasattr(manager, '_checkers')

    def test_quality_gate_manager_configuration(self):
        """Test QualityGateManager configuration"""
        manager = QualityGateManager()

        config = {
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 80.0},
                'complexity': {'enabled': True, 'max_complexity': 10}
            }
        }

        manager.configure(config)

        assert manager._config == config

    def test_quality_gate_manager_basic_run(self):
        """Test basic quality gates run"""
        manager = QualityGateManager()

        config = {
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 50.0}
            }
        }
        manager.configure(config)

        # Mock context
        context = {
            'project_path': '/tmp/test',
            'task_type': 'test'
        }

        # Run gates (should not fail even if no actual checking)
        result = manager.run_all_gates(context)

        assert isinstance(result, QualityGateResult)
        assert result.gate_name is not None

    def test_should_block_execution_logic(self):
        """Test should_block_execution logic"""
        manager = QualityGateManager()

        # Test with no results
        assert not manager.should_block_execution()

        # Test with passing result
        passing_result = QualityGateResult("test")
        passing_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.9
        ))

        assert not manager.should_block_execution(passing_result)

        # Test with failing result in strict mode
        manager._config = {'strict_mode': True}
        failing_result = QualityGateResult("test")
        failing_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.FAILED,
            score=0.3
        ))

        assert manager.should_block_execution(failing_result)


class TestQualityCheckersSmoke:
    """Smoke tests for quality checkers"""

    def test_coverage_checker_creation(self):
        """Test CoverageChecker can be created"""
        checker = CoverageChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.COVERAGE

    def test_complexity_checker_creation(self):
        """Test ComplexityChecker can be created"""
        checker = ComplexityChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.COMPLEXITY

    def test_security_checker_creation(self):
        """Test SecurityChecker can be created"""
        checker = SecurityChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.SECURITY

    def test_style_checker_creation(self):
        """Test StyleChecker can be created"""
        checker = StyleChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.STYLE

    def test_task_type_checker_creation(self):
        """Test TaskTypeChecker can be created"""
        checker = TaskTypeChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.TASK_TYPE

    def test_dependency_checker_creation(self):
        """Test DependencyChecker can be created"""
        checker = DependencyChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.DEPENDENCY

    def test_resource_checker_creation(self):
        """Test ResourceChecker can be created"""
        checker = ResourceChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.RESOURCE

    def test_progress_checker_creation(self):
        """Test ProgressChecker can be created"""
        checker = ProgressChecker()
        assert checker is not None
        assert checker.get_check_type() == QualityCheckType.PROGRESS

    def test_checker_configure(self):
        """Test checker configuration"""
        checker = CoverageChecker()

        config = {'min_coverage': 75.0}
        checker.configure(config)

        # Should not raise exception
        assert checker is not None

    def test_checker_basic_check(self):
        """Test basic checker check method"""
        checker = CoverageChecker()

        context = {
            'project_path': '/tmp/test',
            'files': []
        }

        # Should return a result (may be failed due to no files)
        result = checker.check(context)

        assert isinstance(result, QualityResult)
        assert result.check_type == QualityCheckType.COVERAGE

    def test_all_checkers_have_unique_types(self):
        """Test all checkers have unique check types"""
        checkers = [
            CoverageChecker(), ComplexityChecker(), SecurityChecker(), StyleChecker(),
            TaskTypeChecker(), DependencyChecker(), ResourceChecker(), ProgressChecker()
        ]

        check_types = [checker.get_check_type() for checker in checkers]
        assert len(check_types) == len(set(check_types))  # All unique


class TestQualityReportersSmoke:
    """Smoke tests for quality reporters"""

    def test_console_reporter_creation(self):
        """Test ConsoleReporter can be created"""
        reporter = ConsoleReporter()
        assert reporter is not None

    def test_file_reporter_creation(self):
        """Test FileReporter can be created"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            reporter = FileReporter()
            reporter.configure({'output_file': temp_file})
            assert reporter is not None
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_console_reporter_report(self):
        """Test ConsoleReporter report method"""
        reporter = ConsoleReporter()

        # Create a test result
        result = QualityGateResult("test_gate")
        result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.85
        ))

        # Should not raise exception
        reporter.report(result)

    def test_file_reporter_report(self):
        """Test FileReporter report method"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name

        try:
            reporter = FileReporter()
            reporter.configure({'output_file': temp_file})

            # Create a test result
            result = QualityGateResult("test_gate")
            result.add_result(QualityResult(
                check_type=QualityCheckType.COVERAGE,
                status=QualityStatus.PASSED,
                score=0.85
            ))

            # Should not raise exception
            reporter.report(result)

            # Check file was written
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert len(content) > 0

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_reporter_configure(self):
        """Test reporter configuration"""
        reporter = ConsoleReporter()

        config = {'verbose': True}
        reporter.configure(config)

        # Should not raise exception
        assert reporter is not None


class TestQualityModelsSmoke:
    """Smoke tests for quality models"""

    def test_quality_result_creation(self):
        """Test QualityResult can be created"""
        result = QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.85,
            message="Coverage is good",
            details={'covered_lines': 85, 'total_lines': 100}
        )

        assert result.check_type == QualityCheckType.COVERAGE
        assert result.status == QualityStatus.PASSED
        assert result.score == 0.85
        assert result.message == "Coverage is good"
        assert result.details == {'covered_lines': 85, 'total_lines': 100}

    def test_quality_gate_result_creation(self):
        """Test QualityGateResult can be created"""
        result = QualityGateResult("test_gate")

        assert result.gate_name == "test_gate"
        assert len(result.results) == 0
        assert result.timestamp is not None

    def test_quality_gate_result_add_result(self):
        """Test adding results to QualityGateResult"""
        gate_result = QualityGateResult("test_gate")

        check_result = QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.85
        )

        gate_result.add_result(check_result)

        assert len(gate_result.results) == 1
        assert gate_result.results[0] == check_result

    def test_quality_gate_result_overall_status(self):
        """Test overall status calculation"""
        gate_result = QualityGateResult("test_gate")

        # Add passing result
        gate_result.add_result(QualityResult(
            check_type=QualityCheckType.COVERAGE,
            status=QualityStatus.PASSED,
            score=0.85
        ))

        # Should be passed
        assert gate_result.get_overall_status() == QualityStatus.PASSED

        # Add failing result
        gate_result.add_result(QualityResult(
            check_type=QualityCheckType.COMPLEXITY,
            status=QualityStatus.FAILED,
            score=15.0
        ))

        # Should be failed
        assert gate_result.get_overall_status() == QualityStatus.FAILED

        # Add warning result
        gate_result.add_result(QualityResult(
            check_type=QualityCheckType.STYLE,
            status=QualityStatus.WARNING,
            score=0.7
        ))

        # Should still be failed (failed takes precedence)
        assert gate_result.get_overall_status() == QualityStatus.FAILED


class TestQualityIntegrationSmoke:
    """Smoke tests for quality system integration"""

    def test_full_quality_pipeline(self):
        """Test full quality pipeline"""
        # Create manager
        manager = QualityGateManager()

        # Configure
        config = {
            'enabled': True,
            'strict_mode': False,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 50.0},
                'complexity': {'enabled': True, 'max_complexity': 20}
            }
        }
        manager.configure(config)

        # Create context
        context = {
            'project_path': '/tmp/test',
            'task_type': 'development',
            'files': []
        }

        # Run quality gates
        result = manager.run_all_gates(context)

        # Should return a result
        assert isinstance(result, QualityGateResult)
        assert len(result.results) >= 0  # May be 0 if no checks actually run

        # Test blocking logic
        should_block = manager.should_block_execution(result)
        assert isinstance(should_block, bool)

        # Test reporting
        console_reporter = ConsoleReporter()
        console_reporter.report(result)  # Should not raise

    def test_quality_gates_with_different_configs(self):
        """Test quality gates with different configurations"""
        manager = QualityGateManager()

        # Test with minimal config
        minimal_config = {'enabled': False}
        manager.configure(minimal_config)

        context = {'project_path': '/tmp/test'}
        result = manager.run_all_gates(context)

        assert isinstance(result, QualityGateResult)

        # Test with full config
        full_config = {
            'enabled': True,
            'strict_mode': True,
            'gates': {
                'coverage': {'enabled': True, 'min_coverage': 80.0},
                'complexity': {'enabled': True, 'max_complexity': 10},
                'security': {'enabled': True},
                'style': {'enabled': True}
            }
        }
        manager.configure(full_config)

        result = manager.run_all_gates(context)
        assert isinstance(result, QualityGateResult)