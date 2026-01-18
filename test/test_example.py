"""
Example test file demonstrating test structure and fixtures usage.

This file serves as a template for writing new tests.
"""

import pytest
from pathlib import Path


class TestProjectSetup:
    """Tests for project setup and initialization."""
    
    def test_project_root_exists(self, project_root_path):
        """Test that project root directory exists."""
        assert project_root_path.exists()
        assert project_root_path.is_dir()
    
    def test_src_directory_exists(self, project_root_path):
        """Test that src directory exists."""
        src_dir = project_root_path / "src"
        assert src_dir.exists()
        assert src_dir.is_dir()
    
    def test_config_directory_exists(self, project_root_path):
        """Test that config directory exists."""
        config_dir = project_root_path / "config"
        assert config_dir.exists()
        assert config_dir.is_dir()


class TestTempProjectDir:
    """Tests using temporary project directory."""
    
    def test_temp_project_structure(self, temp_project_dir):
        """Test that temporary project has correct structure."""
        assert temp_project_dir.exists()
        assert (temp_project_dir / "docs").exists()
        assert (temp_project_dir / "src").exists()
        assert (temp_project_dir / "todo.txt").exists()
    
    def test_temp_project_todo_content(self, temp_project_dir):
        """Test that temporary project has TODO content."""
        todo_file = temp_project_dir / "todo.txt"
        content = todo_file.read_text()
        assert "Test task" in content
        assert "Another task" in content


class TestMockFixtures:
    """Tests demonstrating mock fixtures usage."""
    
    def test_mock_config_structure(self, mock_config):
        """Test that mock config has correct structure."""
        assert "project" in mock_config
        assert "agent" in mock_config
        assert "server" in mock_config
        assert mock_config["project"]["base_dir"] is not None
    
    def test_mock_cursor_cli(self, mock_cursor_cli):
        """Test mock Cursor CLI interface."""
        result = mock_cursor_cli.execute("test command")
        assert result["status"] == "success"
        assert mock_cursor_cli.is_available()
    
    def test_mock_llm_manager(self, mock_llm_manager):
        """Test mock LLM manager."""
        response = mock_llm_manager.generate("test prompt")
        assert response is not None
        assert isinstance(response, str)
        assert mock_llm_manager.is_available()
    
    def test_mock_todo_manager(self, mock_todo_manager):
        """Test mock TODO manager."""
        task = mock_todo_manager.get_next_task()
        assert task is not None
        assert "id" in task
        assert "title" in task
        assert task["status"] == "pending"


@pytest.mark.unit
class TestSampleContent:
    """Tests for sample content fixtures."""
    
    def test_sample_todo_content(self, sample_todo_content):
        """Test sample TODO content."""
        assert "Инициализировать проект" in sample_todo_content
        assert "Настроить окружение" in sample_todo_content
    
    def test_sample_status_content(self, sample_status_content):
        """Test sample status content."""
        assert "Code Agent Project Status" in sample_status_content
        assert "Инструкция 1" in sample_status_content
    
    def test_sample_cursor_report(self, sample_cursor_report):
        """Test sample Cursor report."""
        assert "Cursor Execution Report" in sample_cursor_report
        assert "Status: Completed" in sample_cursor_report


@pytest.mark.parametrize("task_id,expected_title", [
    (1, "Task 1"),
    (2, "Task 2"),
])
def test_parametrized_example(task_id, expected_title, mock_todo_manager):
    """Example of parametrized test."""
    tasks = mock_todo_manager.get_all_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    assert task is not None
    assert task["title"] == expected_title


@pytest.mark.slow
def test_slow_operation():
    """Example of a slow test that should be skipped by default."""
    import time
    time.sleep(0.1)  # Simulate slow operation
    assert True


@pytest.mark.integration
def test_integration_example(temp_project_dir, mock_cursor_cli, mock_todo_manager):
    """Example of an integration test using multiple fixtures."""
    # Get task from TODO manager
    task = mock_todo_manager.get_next_task()
    assert task is not None
    
    # Execute task with Cursor CLI
    result = mock_cursor_cli.execute(f"Execute task: {task['title']}")
    assert result["status"] == "success"
    
    # Mark task as complete
    assert mock_todo_manager.mark_complete(task["id"])


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
