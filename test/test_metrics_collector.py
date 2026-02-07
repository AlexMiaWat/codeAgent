import pytest
import datetime
from src.monitoring.metrics_collector import MetricsCollector, TaskMetric, MetricsReport

def test_track_task_execution():
    collector = MetricsCollector()
    collector.track_task_execution("task_1", 10.5, True)
    collector.track_task_execution("task_2", 5.0, False)

    assert len(collector._task_metrics) == 2
    assert collector._task_metrics[0].task_id == "task_1"
    assert collector._task_metrics[0].duration == 10.5
    assert collector._task_metrics[0].success is True
    assert isinstance(collector._task_metrics[0].timestamp, datetime.datetime)

def test_generate_report():
    collector = MetricsCollector()
    collector.track_task_execution("task_1", 10.0, True)
    collector.track_task_execution("task_2", 20.0, False)
    collector.track_task_execution("task_3", 15.0, True)

    report = collector.generate_report()

    assert report.total_tasks == 3
    assert report.successful_tasks == 2
    assert report.failed_tasks == 1
    assert report.avg_duration == pytest.approx((10.0 + 20.0 + 15.0) / 3)
    assert len(report.detailed_metrics) == 3

def test_reset_metrics():
    collector = MetricsCollector()
    collector.track_task_execution("task_1", 10.0, True)
    assert len(collector._task_metrics) == 1
    collector.reset_metrics()
    assert len(collector._task_metrics) == 0
    report = collector.generate_report()
    assert report.total_tasks == 0
    assert report.avg_duration == 0.0
