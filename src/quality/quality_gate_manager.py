"""Central manager for quality gates."""
from typing import List, Dict, Any
from src.quality.interfaces.iquality_gate_manager import IQualityGateManager
from src.quality.interfaces.iquality_gate import IQualityGate
from src.quality.interfaces.iquality_checker import IQualityChecker
from src.quality.interfaces.iquality_reporter import IQualityReporter
from src.quality.models.quality_result import QualityResult

class QualityGate(IQualityGate):
    """Represents a single quality gate composed of multiple checkers."""
    def __init__(self, name: str, checkers: List[IQualityChecker]):
        self.name = name
        self.checkers = checkers
        self.results: List[QualityResult] = []

    def run(self) -> bool:
        """Runs all checkers within this gate and aggregates results."""
        gate_passed = True
        self.results = []
        for checker in self.checkers:
            try:
                checker_result_data = checker.check()
                status = checker_result_data.get("status", "error")
                metrics = {k: v for k, v in checker_result_data.items() if k != "status"}
                result = QualityResult(
                    checker_name=checker.__class__.__name__,
                    status=status,
                    metrics=metrics
                )
                if status != "pass":
                    gate_passed = False
            except Exception as e:
                result = QualityResult(
                    checker_name=checker.__class__.__name__,
                    status="error",
                    metrics={},
                    details=f"An error occurred: {e}"
                )
                gate_passed = False
            self.results.append(result)
        return gate_passed

class QualityGateManager(IQualityGateManager):
    """Manages the execution and reporting of multiple quality gates."""
    def __init__(self, reporters: List[IQualityReporter] = None):
        self.gates: Dict[str, IQualityGate] = {}
        self.reporters = reporters if reporters is not None else []
        self.overall_results: Dict[str, List[QualityResult]] = {}

    def add_gate(self, gate: IQualityGate):
        """Adds a quality gate to the manager."""
        if not isinstance(gate, IQualityGate):
            raise TypeError("Gate must implement IQualityGate interface.")
        self.gates[gate.name] = gate

    def run_gates(self) -> bool:
        """Runs all registered quality gates and generates a report."""
        overall_status = True
        self.overall_results = {}

        for gate_name, gate in self.gates.items():
            print(f"Running Quality Gate: {gate_name}...")
            gate_passed = gate.run()
            self.overall_results[gate_name] = gate.results
            if not gate_passed:
                overall_status = False
            print(f"Quality Gate '{gate_name}' status: {'PASSED' if gate_passed else 'FAILED'}")

        self._generate_report()
        return overall_status

    def _generate_report(self):
        """Generates reports using all registered reporters."""
        report_data = {
            gate_name: [res.__dict__ for res in results]
            for gate_name, results in self.overall_results.items()
        }
        for reporter in self.reporters:
            reporter.report(report_data)
