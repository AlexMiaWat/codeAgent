"""
Base interface for all managers in the Code Agent system.

This interface defines the common contract that all manager components
must implement, ensuring consistency and testability.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IManager(ABC):
    """
    Base interface for all manager components.

    All managers should implement this interface to ensure:
    - Consistent initialization patterns
    - Standardized error handling
    - Common configuration approach
    - Testability through dependency injection
    """

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the manager is in a healthy state and can perform operations.

        Returns:
            True if manager is healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the manager.

        Returns:
            Dictionary containing status information
        """
        pass

    @abstractmethod
    def dispose(self) -> None:
        """
        Clean up resources used by the manager.

        This method should be called when the manager is no longer needed
        to ensure proper resource cleanup.
        """
        pass