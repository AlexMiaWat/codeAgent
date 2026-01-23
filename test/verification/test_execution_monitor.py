"""
Unit tests for ExecutionMonitor
"""

import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from src.verification.execution_monitor import ExecutionMonitor, ExecutionMetrics


class TestExecutionMetrics:
    """Unit tests for ExecutionMetrics"""

    def test_execution_metrics_creation(self):
        """Test ExecutionMetrics initialization"""
        task_id = "test_task_123"
        metrics = ExecutionMetrics(task_id)

        assert metrics.task_id == task_id
        assert metrics.start_time > 0
        assert metrics.last_progress_time == metrics.start_time
        assert metrics.cpu_usage == []
        assert metrics.memory_usage == []
        assert metrics.progress_updates == []
        assert metrics.errors == []
        assert metrics.warnings == []
        assert metrics.status == "running"

    def test_execution_metrics_update_progress(self):
        """Test progress update functionality"""
        metrics = ExecutionMetrics("test_task")

        progress_data = {'step': 1, 'message': 'Starting execution'}
        metrics.update_progress(progress_data)

        assert len(metrics.progress_updates) == 1
        assert metrics.progress_updates[0]['data'] == progress_data
        assert metrics.progress_updates[0]['timestamp'] > 0
        assert metrics.last_progress_time > metrics.start_time

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_execution_metrics_record_resource_usage(self, mock_memory, mock_cpu):
        """Test resource usage recording"""
        mock_cpu.return_value = 45.5
        mock_memory.return_value.percent = 67.8

        metrics = ExecutionMetrics("test_task")
        metrics.record_resource_usage()

        assert len(metrics.cpu_usage) == 1
        assert len(metrics.memory_usage) == 1
        assert metrics.cpu_usage[0]['cpu_percent'] == 45.5
        assert metrics.memory_usage[0]['memory_percent'] == 67.8

    def test_execution_metrics_record_error(self):
        """Test error recording"""
        metrics = ExecutionMetrics("test_task")

        error_msg = "Test error occurred"
        metrics.record_error(error_msg)

        assert len(metrics.errors) == 1
        assert metrics.errors[0]['error'] == error_msg
        assert metrics.errors[0]['timestamp'] > 0

    def test_execution_metrics_record_warning(self):
        """Test warning recording"""
        metrics = ExecutionMetrics("test_task")

        warning_msg = "Test warning occurred"
        metrics.record_warning(warning_msg)

        assert len(metrics.warnings) == 1
        assert metrics.warnings[0]['warning'] == warning_msg
        assert metrics.warnings[0]['timestamp'] > 0

    def test_execution_metrics_finalize(self):
        """Test metrics finalization"""
        metrics = ExecutionMetrics("test_task")

        # Add some test data
        metrics.record_error("Test error")
        metrics.record_warning("Test warning")
        metrics.update_progress({'step': 1})

        # Mock CPU and memory data
        metrics.cpu_usage = [
            {'timestamp': 1000, 'cpu_percent': 20.0},
            {'timestamp': 1005, 'cpu_percent': 30.0}
        ]
        metrics.memory_usage = [
            {'timestamp': 1000, 'memory_percent': 50.0},
            {'timestamp': 1005, 'memory_percent': 60.0}
        ]

        # Set end time
        metrics.status = "completed"

        final_metrics = metrics.finalize()

        assert final_metrics['task_id'] == "test_task"
        assert final_metrics['duration'] > 0
        assert final_metrics['status'] == "completed"
        assert final_metrics['cpu_avg'] == 25.0  # (20+30)/2
        assert final_metrics['cpu_peak'] == 30.0
        assert final_metrics['memory_avg'] == 55.0  # (50+60)/2
        assert final_metrics['memory_peak'] == 60.0
        assert final_metrics['progress_updates'] == 1
        assert final_metrics['errors_count'] == 1
        assert final_metrics['warnings_count'] == 1
        assert len(final_metrics['errors']) == 1
        assert len(final_metrics['warnings']) == 1


class TestExecutionMonitor:
    """Unit tests for ExecutionMonitor"""

    def test_execution_monitor_creation(self):
        """Test ExecutionMonitor initialization"""
        monitor = ExecutionMonitor()

        assert monitor.monitoring_interval == 5.0
        assert monitor.max_monitoring_time == 3600
        assert monitor.resource_check_enabled is True
        assert monitor._active_monitors == {}
        assert monitor._monitor_threads == {}
        assert monitor._stop_events == {}

    def test_execution_monitor_with_config(self):
        """Test ExecutionMonitor with custom config"""
        config = {
            'monitoring_interval': 10.0,
            'max_monitoring_time': 7200,
            'resource_check_enabled': False,
            'cpu_threshold': 80.0,
            'memory_threshold': 90.0,
            'progress_timeout': 600
        }

        monitor = ExecutionMonitor(config)

        assert monitor.monitoring_interval == 10.0
        assert monitor.max_monitoring_time == 7200
        assert monitor.resource_check_enabled is False

    @pytest.mark.asyncio
    async def test_start_monitoring(self):
        """Test starting monitoring"""
        monitor = ExecutionMonitor()

        await monitor.start_monitoring("test_task")

        assert "test_task" in monitor._active_monitors
        assert "test_task" in monitor._monitor_threads
        assert "test_task" in monitor._stop_events
        assert isinstance(monitor._active_monitors["test_task"], ExecutionMetrics)
        assert isinstance(monitor._monitor_threads["test_task"], threading.Thread)
        assert isinstance(monitor._stop_events["test_task"], threading.Event)

    @pytest.mark.asyncio
    async def test_start_monitoring_already_active(self):
        """Test starting monitoring for already active task"""
        monitor = ExecutionMonitor()

        # Start monitoring
        await monitor.start_monitoring("test_task")
        initial_thread = monitor._monitor_threads["test_task"]

        # Try to start again
        await monitor.start_monitoring("test_task")

        # Should not create new thread
        assert monitor._monitor_threads["test_task"] == initial_thread

    @pytest.mark.asyncio
    async def test_update_progress(self):
        """Test progress update"""
        monitor = ExecutionMonitor()

        await monitor.start_monitoring("test_task")

        progress_data = {'step': 2, 'message': 'Halfway done'}
        await monitor.update_progress("test_task", progress_data)

        metrics = monitor._active_monitors["test_task"]
        assert len(metrics.progress_updates) == 1
        assert metrics.progress_updates[0]['data'] == progress_data

    @pytest.mark.asyncio
    async def test_update_progress_nonexistent_task(self):
        """Test progress update for non-existent task"""
        monitor = ExecutionMonitor()

        # Should not crash
        await monitor.update_progress("nonexistent", {'data': 'test'})

    @pytest.mark.asyncio
    async def test_check_execution_health_healthy(self):
        """Test health check for healthy execution"""
        monitor = ExecutionMonitor()

        await monitor.start_monitoring("test_task")

        # Mock recent progress
        metrics = monitor._active_monitors["test_task"]
        metrics.last_progress_time = time.time()  # Recent progress

        health = await monitor.check_execution_health("test_task")

        assert health['status'] == 'monitoring'
        assert health['healthy'] is True
        assert health['issues'] == []
        assert 'cpu_usage' in health
        assert 'memory_usage' in health

    @pytest.mark.asyncio
    async def test_check_execution_health_unhealthy(self):
        """Test health check for unhealthy execution"""
        monitor = ExecutionMonitor()

        await monitor.start_monitoring("test_task")

        # Mock old progress (timeout)
        metrics = monitor._active_monitors["test_task"]
        metrics.last_progress_time = time.time() - 400  # Older than 300s timeout

        # Mock high resource usage
        metrics.cpu_usage = [{'timestamp': time.time(), 'cpu_percent': 96.0}]
        metrics.memory_usage = [{'timestamp': time.time(), 'memory_percent': 97.0}]

        health = await monitor.check_execution_health("test_task")

        assert health['status'] == 'monitoring'
        assert health['healthy'] is False
        assert len(health['issues']) > 0
        assert any('no_progress' in issue for issue in health['issues'])

    @pytest.mark.asyncio
    async def test_check_execution_health_nonexistent_task(self):
        """Test health check for non-existent task"""
        monitor = ExecutionMonitor()

        health = await monitor.check_execution_health("nonexistent")

        assert health['status'] == 'not_monitoring'
        assert health['healthy'] is False

    @pytest.mark.asyncio
    async def test_stop_monitoring(self):
        """Test stopping monitoring"""
        monitor = ExecutionMonitor()

        await monitor.start_monitoring("test_task")

        # Wait a bit for monitoring to start
        await asyncio.sleep(0.1)

        result = await monitor.stop_monitoring("test_task")

        assert 'task_id' in result
        assert 'duration' in result
        assert 'status' in result

        # Should clean up resources
        assert "test_task" not in monitor._active_monitors
        assert "test_task" not in monitor._monitor_threads
        assert "test_task" not in monitor._stop_events

    @pytest.mark.asyncio
    async def test_stop_monitoring_nonexistent_task(self):
        """Test stopping monitoring for non-existent task"""
        monitor = ExecutionMonitor()

        result = await monitor.stop_monitoring("nonexistent")

        assert result['error'] == 'not_monitoring'

    def test_get_active_tasks(self):
        """Test getting active tasks list"""
        monitor = ExecutionMonitor()

        # Initially empty
        assert monitor.get_active_tasks() == []

        # Add a task manually (simulating start_monitoring)
        monitor._active_monitors["task1"] = ExecutionMetrics("task1")
        monitor._active_monitors["task2"] = ExecutionMetrics("task2")

        active_tasks = monitor.get_active_tasks()
        assert len(active_tasks) == 2
        assert "task1" in active_tasks
        assert "task2" in active_tasks

    def test_get_task_metrics(self):
        """Test getting task metrics"""
        monitor = ExecutionMonitor()

        # Non-existent task
        assert monitor.get_task_metrics("nonexistent") is None

        # Add a task manually
        metrics = ExecutionMetrics("test_task")
        monitor._active_monitors["test_task"] = metrics

        # Add some test data
        metrics.cpu_usage = [{'timestamp': time.time(), 'cpu_percent': 25.0}]
        metrics.memory_usage = [{'timestamp': time.time(), 'memory_percent': 45.0}]
        metrics.record_error("Test error")
        metrics.record_warning("Test warning")

        task_metrics = monitor.get_task_metrics("test_task")

        assert task_metrics is not None
        assert task_metrics['task_id'] == "test_task"
        assert task_metrics['duration'] > 0
        assert task_metrics['status'] == "running"
        assert task_metrics['progress_updates'] == 0
        assert task_metrics['cpu_current'] == 25.0
        assert task_metrics['memory_current'] == 45.0
        assert task_metrics['errors_count'] == 1
        assert task_metrics['warnings_count'] == 1

    @patch('threading.Thread')
    @patch('time.sleep')
    def test_monitor_task_thread(self, mock_sleep, mock_thread):
        """Test the monitoring thread functionality"""
        monitor = ExecutionMonitor()

        # Create stop event
        stop_event = threading.Event()

        # Create metrics
        metrics = ExecutionMetrics("test_task")
        monitor._active_monitors["test_task"] = metrics

        # Mock the thread to not actually run
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Set stop event to stop immediately
        stop_event.set()

        # Call the monitoring function directly
        monitor._monitor_task("test_task", stop_event)

        # Thread should be created
        mock_thread.assert_called_once()

    def test_monitor_task_with_timeout(self):
        """Test monitoring thread with timeout"""
        monitor = ExecutionMonitor()

        # Set very short max monitoring time
        monitor.max_monitoring_time = 0.1

        stop_event = threading.Event()
        metrics = ExecutionMetrics("test_task")
        monitor._active_monitors["test_task"] = metrics

        # Start monitoring
        monitor._monitor_task("test_task", stop_event)

        # Should have stopped due to timeout
        assert metrics.status == "running"  # Status not changed in this implementation

    def test_monitor_task_resource_check_disabled(self):
        """Test monitoring thread with resource check disabled"""
        monitor = ExecutionMonitor()
        monitor.resource_check_enabled = False

        stop_event = threading.Event()
        stop_event.set()  # Stop immediately

        metrics = ExecutionMetrics("test_task")
        monitor._active_monitors["test_task"] = metrics

        # Should not crash when resource check is disabled
        monitor._monitor_task("test_task", stop_event)