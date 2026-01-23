"""
Static tests for core types and data structures

This module contains static tests that verify type definitions,
enum values, and data structure integrity without requiring
runtime instantiation.
"""

import pytest
from pathlib import Path
from datetime import datetime

from src.core.types import (
    ErrorSeverity, TaskStatus, ComponentStatus,
    ServerConfig, TaskResult, MetricsData,
    ErrorInfo, ComponentHealth, TaskId
)


class TestEnums:
    """Test enum definitions and values"""

    def test_error_severity_values(self):
        """Test ErrorSeverity enum has expected values"""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

        # Test all values are unique
        values = [e.value for e in ErrorSeverity]
        assert len(values) == len(set(values))

    def test_task_status_values(self):
        """Test TaskStatus enum has expected values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

        # Test all values are unique
        values = [e.value for e in TaskStatus]
        assert len(values) == len(set(values))

    def test_component_status_values(self):
        """Test ComponentStatus enum has expected values"""
        assert ComponentStatus.INITIALIZING.value == "initializing"
        assert ComponentStatus.READY.value == "ready"
        assert ComponentStatus.RUNNING.value == "running"
        assert ComponentStatus.STOPPING.value == "stopping"
        assert ComponentStatus.ERROR.value == "error"
        assert ComponentStatus.DISABLED.value == "disabled"

        # Test all values are unique
        values = [e.value for e in ComponentStatus]
        assert len(values) == len(set(values))


class TestDataClasses:
    """Test dataclass definitions and default values"""

    def test_server_config_creation(self):
        """Test ServerConfig can be created with minimal parameters"""
        project_dir = Path("/tmp/project")
        docs_dir = Path("/tmp/docs")
        status_file = Path("/tmp/status.json")

        config = ServerConfig(
            project_dir=project_dir,
            docs_dir=docs_dir,
            status_file=status_file
        )

        assert config.project_dir == project_dir
        assert config.docs_dir == docs_dir
        assert config.status_file == status_file
        assert config.check_interval == 60
        assert config.http_port == 3456
        assert config.http_enabled is True

    def test_task_result_creation(self):
        """Test TaskResult can be created"""
        result = TaskResult(
            task_id="test_task_123",
            status=TaskStatus.COMPLETED,
            success=True,
            message="Task completed successfully",
            execution_time=1.5,
            cursor_used=False
        )

        assert result.task_id == "test_task_123"
        assert result.status == TaskStatus.COMPLETED
        assert result.success is True
        assert result.execution_time == 1.5
        assert isinstance(result.timestamp, datetime)
        assert result.error_message is None

    def test_metrics_data_creation(self):
        """Test MetricsData can be created"""
        metrics = MetricsData(
            component_name="test_component",
            timestamp=datetime.now(),
            metrics={"cpu_usage": 85.5, "memory_mb": 256},
            tags={"env": "test", "version": "1.0"}
        )

        assert metrics.component_name == "test_component"
        assert isinstance(metrics.timestamp, datetime)
        assert metrics.metrics["cpu_usage"] == 85.5
        assert metrics.tags["env"] == "test"

    def test_error_info_creation(self):
        """Test ErrorInfo can be created"""
        error = ErrorInfo(
            severity=ErrorSeverity.HIGH,
            message="Test error message",
            component="test_component",
            error_code="TEST_001",
            context={"user_id": "123", "action": "save"}
        )

        assert error.severity == ErrorSeverity.HIGH
        assert error.message == "Test error message"
        assert error.component == "test_component"
        assert error.error_code == "TEST_001"
        assert isinstance(error.timestamp, datetime)

    def test_component_health_creation(self):
        """Test ComponentHealth can be created"""
        from src.core.types import ComponentHealth

        health = ComponentHealth(
            component_name="test_component",
            status=ComponentStatus.RUNNING,
            last_check=datetime.now(),
            message="Component is healthy",
            metrics={"uptime": 3600},
            errors=[]
        )

        assert health.component_name == "test_component"
        assert health.status == ComponentStatus.RUNNING
        assert health.message == "Component is healthy"
        assert health.metrics["uptime"] == 3600
        assert health.errors == []


class TestTypeDefinitions:
    """Test type definitions and imports"""

    def test_all_types_importable(self):
        """Test all types can be imported without errors"""
        # This test ensures no import errors in the types module
        from src.core import types

        # Check that all expected classes are available
        assert hasattr(types, 'ErrorSeverity')
        assert hasattr(types, 'TaskStatus')
        assert hasattr(types, 'ComponentStatus')
        assert hasattr(types, 'ServerConfig')
        assert hasattr(types, 'TaskResult')
        assert hasattr(types, 'MetricsData')
        assert hasattr(types, 'ErrorInfo')
        assert hasattr(types, 'ComponentHealth')
        assert hasattr(types, 'TaskId')

    def test_enum_inheritance(self):
        """Test enums inherit from Enum correctly"""
        from enum import Enum

        assert isinstance(ErrorSeverity.LOW, Enum)
        assert isinstance(TaskStatus.PENDING, Enum)
        assert isinstance(ComponentStatus.READY, Enum)

    def test_dataclass_fields(self):
        """Test dataclasses have expected fields"""
        from dataclasses import fields

        # Test ServerConfig fields
        config_fields = [f.name for f in fields(ServerConfig)]
        expected_config_fields = [
            'project_dir', 'docs_dir', 'status_file', 'check_interval',
            'task_delay', 'max_iterations', 'http_port', 'http_enabled',
            'auto_reload', 'reload_on_py_changes', 'cursor_interface_type',
            'auto_todo_enabled', 'max_todo_generations', 'session_tracker_file',
            'checkpoint_file'
        ]
        for field_name in expected_config_fields:
            assert field_name in config_fields

        # Test TaskResult fields
        result_fields = [f.name for f in fields(TaskResult)]
        expected_result_fields = [
            'task_id', 'status', 'success', 'message', 'execution_time',
            'cursor_used', 'error_message', 'output_files', 'metadata', 'timestamp'
        ]
        for field_name in expected_result_fields:
            assert field_name in result_fields