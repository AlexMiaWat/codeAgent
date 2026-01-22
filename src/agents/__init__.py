"""Агенты CrewAI для Code Agent"""

from .executor_agent import create_executor_agent
from .smart_agent import create_smart_agent

__all__ = ['create_executor_agent', 'create_smart_agent']
