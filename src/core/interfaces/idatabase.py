"""
Interface for Database component.

This interface defines the contract for database operations in the Code Agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .imanager import IManager


class IDatabase(IManager, ABC):
    """
    Interface for database operations.

    This interface defines methods for:
    - Connecting to database
    - Executing queries
    - Managing transactions
    - Data persistence and retrieval
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the database.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close database connection.

        Returns:
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a database query.

        Args:
            query: SQL query string
            params: Optional parameters for the query

        Returns:
            List of result rows as dictionaries
        """
        pass

    @abstractmethod
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute an update/insert/delete query.

        Args:
            query: SQL query string
            params: Optional parameters for the query

        Returns:
            Number of affected rows
        """
        pass

    @abstractmethod
    def begin_transaction(self) -> bool:
        """
        Begin a database transaction.

        Returns:
            True if transaction started successfully, False otherwise
        """
        pass

    @abstractmethod
    def commit_transaction(self) -> bool:
        """
        Commit the current transaction.

        Returns:
            True if transaction committed successfully, False otherwise
        """
        pass

    @abstractmethod
    def rollback_transaction(self) -> bool:
        """
        Rollback the current transaction.

        Returns:
            True if transaction rolled back successfully, False otherwise
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if database connection is active.

        Returns:
            True if connected, False otherwise
        """
        pass