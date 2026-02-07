
class MetricsCollector:
    def __init__(self):
        self.metrics = []

    def track_task_execution(self, task: str, duration: float, success: bool):
        """Отслеживание выполнения задачи"""
        metric = {"task": task, "duration": duration, "success": success}
        self.metrics.append(metric)
        print(f"Tracked task execution: {metric}")
        
    def generate_report(self) -> dict:
        """Генерация отчета с метриками"""
        print("Generating metrics report...")
        # Placeholder for actual report generation logic
        successful_tasks = [m for m in self.metrics if m['success']]
        failed_tasks = [m for m in self.metrics if not m['success']]
        return {
            "total_tasks": len(self.metrics),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "average_duration": sum([m['duration'] for m in self.metrics]) / len(self.metrics) if self.metrics else 0
        }
