"""
Interface for Logger component.

This interface defines the contract for logging functionality in the Code Agent system.
It ensures consistent logging across all components with proper abstraction.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path


class ILogger(ABC):
    """
    Interface for logging operations.

    This interface defines methods for:
    - Different log levels (info, warning, error, debug)
    - Structured logging
    - Task-specific logging
    - Server-level logging
    """

    @abstractmethod
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the logger.

        Args:
            config: Optional configuration for the logger
        """
        pass

    @abstractmethod
    def log_info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an informational message.

        Args:
            message: The message to log
            extra: Optional extra data to include in the log
        """
        pass

    @abstractmethod
    def log_warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a warning message.

        Args:
            message: The warning message to log
            extra: Optional extra data to include in the log
        """
        pass

    @abstractmethod
    def log_error(self, message: str, exception: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error message.

        Args:
            message: The error message to log
            exception: Optional exception that caused the error
            extra: Optional extra data to include in the log
        """
        pass

    @abstractmethod
    def log_debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a debug message.

        Args:
            message: The debug message to log
            extra: Optional extra data to include in the log
        """
        pass

    @abstractmethod
    def create_task_logger(self, task_id: str, task_name: str) -> 'ITaskLogger':
        """
        Create a task-specific logger.

        Args:
            task_id: Unique identifier for the task
            task_name: Name of the task

        Returns:
            Task-specific logger instance
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the logger and clean up resources.
        """
        pass


class ITaskLogger(ABC):
    """
    Interface for task-specific logging operations.

    This interface defines methods for logging task execution details,
    phases, instructions, and results.
    """

    @abstractmethod
    def set_phase(self, phase: str, stage: Optional[int] = None, instruction_num: Optional[int] = None) -> None:
        """
        Set the current execution phase of the task.

        Args:
            phase: Current phase of task execution
            stage: Optional stage number
            instruction_num: Optional instruction number
        """
        pass

    @abstractmethod
    def log_instruction(self, instruction_num: int, instruction_text: str, task_type: str) -> None:
        """
        Log a generated instruction.

        Args:
            instruction_num: Number of the instruction
            instruction_text: Text of the instruction
            task_type: Type of the task
        """
        pass

    @abstractmethod
    def log_cursor_response(self, response: Dict[str, Any], brief: bool = True) -> None:
        """
        Log response from Cursor.

        Args:
            response: Response data from Cursor
            brief: Whether to log brief or detailed version
        """
        pass

    @abstractmethod
    def log_result_received(self, file_path: str, wait_time: float, content_preview: str = "", execution_time: Optional[float] = None) -> None:
        """
        Log that a result was received.

        Args:
            file_path: Path to the result file
            wait_time: Time spent waiting for result
            content_preview: Preview of the content
            execution_time: Total execution time
        """
        pass

    @abstractmethod
    def log_completion(self, success: bool, summary: str = "") -> None:
        """
        Log task completion.

        Args:
            success: Whether the task completed successfully
            summary: Optional summary of the task execution
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the task logger.
        """
        pass