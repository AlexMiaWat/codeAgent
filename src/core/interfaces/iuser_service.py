"""
Interface for User Service component.

This interface defines the contract for user management operations in the Code Agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from .imanager import IManager


class IUserService(IManager, ABC):
    """
    Interface for user service operations.

    This interface defines methods for:
    - User authentication and authorization
    - User profile management
    - Session management
    - User preferences
    """

    @abstractmethod
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with username and password.

        Args:
            username: User's username
            password: User's password

        Returns:
            User data dictionary if authentication successful, None otherwise
        """
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by user ID.

        Args:
            user_id: Unique user identifier

        Returns:
            User data dictionary if user found, None otherwise
        """
        pass

    @abstractmethod
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new user.

        Args:
            user_data: User information for creation

        Returns:
            User ID if creation successful, None otherwise
        """
        pass

    @abstractmethod
    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """
        Update user information.

        Args:
            user_id: Unique user identifier
            user_data: Updated user information

        Returns:
            True if update successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: Unique user identifier

        Returns:
            True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences.

        Args:
            user_id: Unique user identifier

        Returns:
            Dictionary containing user preferences
        """
        pass

    @abstractmethod
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences.

        Args:
            user_id: Unique user identifier
            preferences: Updated preferences

        Returns:
            True if update successful, False otherwise
        """
        pass

    @abstractmethod
    def list_users(self, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[Dict[str, Any]]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of user data dictionaries
        """
        pass