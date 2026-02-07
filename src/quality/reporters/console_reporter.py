"""Reporter that prints quality gate results to the console."""
from src.quality.interfaces.iquality_reporter import IQualityReporter

class ConsoleReporter(IQualityReporter):
    def report(self, results: dict):
        print("Quality Gate Report:")
        for gate_name, result in results.items():
            print(f"- {gate_name}: {result['status']}")
