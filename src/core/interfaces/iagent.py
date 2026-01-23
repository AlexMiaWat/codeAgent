"""
Interface for Agent component.

This interface defines the contract for managing CrewAI agents in the Code Agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from .imanager import IManager

if TYPE_CHECKING:
    from crewai import Agent


class IAgent(IManager, ABC):
    """
    Interface for agent management in the Code Agent system.

    This interface defines methods for:
    - Creating and configuring CrewAI agents
    - Managing agent lifecycle
    - Executing tasks through agents
    - Monitoring agent status and performance
    """

    @abstractmethod
    def create_agent(
        self,
        agent_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a new agent of specified type.

        Args:
            agent_type: Type of agent to create (e.g., 'executor', 'smart', 'custom')
            config: Configuration parameters for the agent

        Returns:
            Unique agent ID if created successfully, None otherwise
        """
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional['Agent']:
        """
        Get a CrewAI agent instance by ID.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            CrewAI Agent instance if found, None otherwise
        """
        pass

    @abstractmethod
    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent and clean up its resources.

        Args:
            agent_id: Unique identifier of the agent to remove

        Returns:
            True if agent was removed successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_available_agents(self) -> List[str]:
        """
        Get list of available agent types that can be created.

        Returns:
            List of available agent type names
        """
        pass

    @abstractmethod
    def get_active_agents(self) -> List[str]:
        """
        Get list of currently active agent IDs.

        Returns:
            List of active agent IDs
        """
        pass

    @abstractmethod
    def configure_agent(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """
        Update configuration of an existing agent.

        Args:
            agent_id: Unique identifier of the agent
            config: New configuration parameters

        Returns:
            True if configuration updated successfully, False otherwise
        """
        pass

    @abstractmethod
    def execute_with_agent(
        self,
        agent_id: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task using specified agent.

        Args:
            agent_id: Unique identifier of the agent to use
            task_description: Description of the task to execute
            context: Additional context for task execution

        Returns:
            Dictionary containing execution result with status and output
        """
        pass

    @abstractmethod
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get status and information about a specific agent.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            Dictionary containing agent status, configuration, and performance metrics
        """
        pass

    @abstractmethod
    def validate_agent_config(self, agent_type: str, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for a specific agent type.

        Args:
            agent_type: Type of agent to validate config for
            config: Configuration to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_agent_types_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all supported agent types.

        Returns:
            Dictionary mapping agent types to their descriptions and capabilities
        """
        pass