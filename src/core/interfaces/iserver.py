"""
Interface for Server component.

This interface defines the contract for managing the Code Agent server lifecycle,
coordinating components, and handling requests.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

from .imanager import IManager


class IServer(IManager, ABC):
    """
    Interface for server management in the Code Agent system.

    This interface defines methods for:
    - Managing server lifecycle (start, stop, restart)
    - Coordinating component interactions
    - Handling task execution requests
    - Providing server status and metrics
    - Managing configuration and health checks
    """

    @abstractmethod
    def start(self) -> bool:
        """
        Start the server and all its components.

        Returns:
            True if server started successfully, False otherwise
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the server and clean up resources.

        Returns:
            True if server stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def restart(self) -> bool:
        """
        Restart the server.

        Returns:
            True if server restarted successfully, False otherwise
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the server is currently running.

        Returns:
            True if server is running, False otherwise
        """
        pass

    @abstractmethod
    def get_server_status(self) -> Dict[str, Any]:
        """
        Get comprehensive server status information.

        Returns:
            Dictionary containing server status, component states, metrics, etc.
        """
        pass

    @abstractmethod
    def execute_task(self, task_id: str) -> bool:
        """
        Execute a specific task by ID.

        Args:
            task_id: Unique identifier of the task to execute

        Returns:
            True if task execution was initiated successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        Get list of pending tasks waiting for execution.

        Returns:
            List of pending task dictionaries with metadata
        """
        pass

    @abstractmethod
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get list of currently active/executing tasks.

        Returns:
            List of active task dictionaries with progress information
        """
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get server performance metrics.

        Returns:
            Dictionary containing performance metrics (execution times, success rates, etc.)
        """
        pass

    @abstractmethod
    def reload_configuration(self) -> bool:
        """
        Reload server configuration without restart.

        Returns:
            True if configuration reloaded successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_component_status(self, component_name: str) -> Dict[str, Any]:
        """
        Get status of a specific server component.

        Args:
            component_name: Name of the component to check

        Returns:
            Dictionary containing component status information
        """
        pass