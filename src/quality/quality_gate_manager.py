from typing import List, Dict, Any, Optional
from src.quality.interfaces.iquality_gate_manager import IQualityGateManager
from src.quality.interfaces.iquality_gate import IQualityGate
from src.quality.interfaces.iquality_checker import IQualityChecker
from src.quality.interfaces.iquality_reporter import IQualityReporter
from src.quality.models.quality_result import QualityResult, QualityCheckType, QualityStatus, QualityGateResult

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
                raw_status = checker_result_data.get("status", "error")
                
                status = QualityStatus.PASSED if raw_status == "pass" else \
                         (QualityStatus.FAILED if raw_status == "fail" else QualityStatus.ERROR)
                
                message = checker_result_data.get("message", f"Check {checker.__class__.__name__} {raw_status}")
                score = checker_result_data.get("score", 1.0 if status == QualityStatus.PASSED else 0.0)
                threshold = checker_result_data.get("threshold", 0.7)
                
                result = QualityResult(
                    check_type=QualityCheckType.STATIC_ANALYSIS, # Defaulting for now
                    status=status,
                    message=message,
                    score=score,
                    threshold=threshold,
                    details=checker_result_data
                )
                if status == QualityStatus.FAILED or status == QualityStatus.ERROR:
                    gate_passed = False
            except Exception as e:
                result = QualityResult(
                    check_type=QualityCheckType.STATIC_ANALYSIS, # Defaulting for now
                    status=QualityStatus.ERROR,
                    message=f"An error occurred during {checker.__class__.__name__} check: {e}",
                    score=0.0,
                    threshold=0.7,
                    details={}
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

    async def run_specific_gates(self, check_types: List[QualityCheckType], context: Dict[str, Any]) -> QualityGateResult:
        """Runs a subset of quality gates based on specified check types."""
        specific_results: List[QualityResult] = []
        overall_specific_status = QualityStatus.PASSED
        
        # Placeholder: In a real scenario, you'd map check_types to actual checkers/gates
        # For now, we'll simulate results for the requested check types
        for check_type in check_types:
            # Simulate a successful check for demonstration
            status = QualityStatus.PASSED
            message = f"{check_type.value} check passed (simulated)"
            score = 1.0
            
            if check_type == QualityCheckType.STATIC_ANALYSIS and context.get("simulate_static_fail", False):
                status = QualityStatus.FAILED
                message = f"{check_type.value} check failed (simulated)"
                score = 0.0
                overall_specific_status = QualityStatus.FAILED
            elif check_type == QualityCheckType.CODE_QUALITY_AI and context.get("simulate_ai_warning", False):
                status = QualityStatus.WARNING
                message = f"{check_type.value} check generated warnings (simulated)"
                score = 0.6
                if overall_specific_status == QualityStatus.PASSED:
                    overall_specific_status = QualityStatus.WARNING

            specific_results.append(
                QualityResult(
                    check_type=check_type,
                    status=status,
                    message=message,
                    score=score,
                    threshold=0.7,
                    details={'context_info': context}
                )
            )

        gate_result = QualityGateResult(
            gate_name="specific_checks",
            results=specific_results
        )
        gate_result.overall_status = overall_specific_status
        gate_result.summary_message = f"Specific checks completed with {overall_specific_status.value} status."
        return gate_result

    def _generate_report(self):
        """Generates reports using all registered reporters."""
        report_data = {
            gate_name: [res.__dict__ for res in results]
            for gate_name, results in self.overall_results.items()
        }
        for reporter in self.reporters:
            reporter.report(report_data)
