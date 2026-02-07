"""Reporter that saves quality gate results to a file."""
import json
from src.quality.interfaces.iquality_reporter import IQualityReporter

class FileReporter(IQualityReporter):
    def __init__(self, filepath: str = "quality_report.json"):
        self.filepath = filepath

    def report(self, results: dict):
        with open(self.filepath, "w") as f:
            json.dump(results, f, indent=4)
        print(f"Quality Gate report saved to {self.filepath}")
