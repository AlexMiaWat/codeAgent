"""
Core types and enumerations for the Code Agent system.

This module contains fundamental type definitions used throughout the system,
including task types, execution states, and other core enumerations.
"""

from enum import Enum
from typing import List, Dict, Optional, Set
import re


class TaskType(Enum):
    """
    Enumeration of task types for categorization and prioritization.

    This enum defines the standard task categories used in the Code Agent system
    for organizing, filtering, and managing different types of development tasks.
    """

    CODE = "code"
    """Development tasks: new features, bug fixes, implementation"""

    DOCS = "docs"
    """Documentation tasks: writing, updating, or maintaining documentation"""

    REFACTOR = "refactor"
    """Refactoring tasks: code improvements, restructuring, optimization"""

    TEST = "test"
    """Testing tasks: writing tests, test execution, test maintenance"""

    RELEASE = "release"
    """Release tasks: versioning, packaging, deployment preparation"""

    DEVOPS = "devops"
    """DevOps tasks: infrastructure, CI/CD, deployment, monitoring"""

    @classmethod
    def from_string(cls, value: str) -> Optional['TaskType']:
        """
        Create TaskType from string value.

        Args:
            value: String representation of task type

        Returns:
            TaskType enum value or None if invalid
        """
        if not value:
            return None
        try:
            return cls(value.lower())
        except ValueError:
            return None

    @classmethod
    def auto_detect(cls, text: str) -> Optional['TaskType']:
        """
        Automatically detect task type from task text using keyword analysis.

        This method analyzes the task description to determine the most likely
        task type based on keywords and patterns in the text.

        Args:
            text: Task description text

        Returns:
            Detected TaskType or None if cannot determine
        """
        text_lower = text.lower()

        # Define keyword patterns for each task type (more specific patterns first)
        patterns = {
            cls.DEVOPS: [
                # DevOps keywords (most specific)
                r'\b(docker|kubernetes|terraform|ansible|jenkins|gitlab.ci|github.actions)\b',
                r'\b(infrastructure|infra|deployment|ci.cd|pipeline|automation)\b',
                r'\b(monitoring|logging|alerting|security|backup|scaling)\b',
                r'\b(server|environment|cluster|container|orchestration)\b'
            ],
            cls.TEST: [
                # Testing keywords
                r'\b(unittest|pytest|selenium|junit|testng|cypress)\b',
                r'\b(test|spec|fixture|mock|assert|coverage)\b',
                r'\b(verify|validate|check|unit.*test|integration.*test)\b',
                r'\b(write.*test|add.*test|create.*test|implement.*test)\b',
                r'\b(unit.*test|test.*unit|tests.*unit)\b',
                r'\b(test.*for|tests.*for)\b'
            ],
            cls.RELEASE: [
                # Release keywords
                r'\b(release|version|tag|changelog|publish|distribute)\b',
                r'\b(package|build.*release|deploy.*production)\b',
                r'\b(staging|production|live.*deploy)\b'
            ],
            cls.REFACTOR: [
                # Refactoring keywords
                r'\b(refactor|restructure|optimize|improve|clean|cleanup)\b',
                r'\b(duplicate|redundant|simplify|extract)\b',
                r'\b(architecture|design.*pattern|code.*quality)\b',
                r'\b(extract.*common|remove.*duplicate)\b'
            ],
            cls.DOCS: [
                # Documentation keywords
                r'\b(documentation|readme|guide|manual|wiki)\b',
                r'\b(doc|api.*doc|swagger|openapi|javadoc)\b',
                r'\b(comment|describe|explain|tutorial|how.*to)\b',
                r'\b(document|update.*doc|write.*doc)\b'
            ],
            cls.CODE: [
                # Development keywords (most general, checked last)
                r'\b(implement|develop|code|feature|functionality)\b',
                r'\b(add.*feature|new.*component|create.*module)\b',
                r'\b(fix.*bug|resolve.*issue|bugfix|hotfix)\b',
                r'\b(api|endpoint|interface|method|class|algorithm)\b',
                r'\b(integration|connect|integrate.*with)\b'
            ]
        }

        # Check patterns in priority order (most specific types first)
        priority_order = [cls.DEVOPS, cls.TEST, cls.RELEASE, cls.REFACTOR, cls.DOCS, cls.CODE]

        for task_type in priority_order:
            for pattern in patterns[task_type]:
                if re.search(pattern, text_lower):
                    return task_type

        return None

    @property
    def display_name(self) -> str:
        """
        Get human-readable display name for the task type.

        Returns:
            Localized display name
        """
        names = {
            self.CODE: "Разработка",
            self.DOCS: "Документация",
            self.REFACTOR: "Рефакторинг",
            self.TEST: "Тестирование",
            self.RELEASE: "Релиз",
            self.DEVOPS: "DevOps"
        }
        return names.get(self, self.value)

    @property
    def priority(self) -> int:
        """
        Get priority level for task ordering (lower number = higher priority).

        Returns:
            Priority level (1-6)
        """
        priorities = {
            self.CODE: 1,      # Highest priority
            self.TEST: 2,
            self.REFACTOR: 3,
            self.DOCS: 4,
            self.RELEASE: 5,
            self.DEVOPS: 6      # Lowest priority
        }
        return priorities.get(self, 99)

    @classmethod
    def get_all_types(cls) -> List['TaskType']:
        """
        Get all available task types.

        Returns:
            List of all TaskType values
        """
        return list(cls)

    @classmethod
    def get_types_by_priority(cls) -> List['TaskType']:
        """
        Get task types ordered by priority (highest first).

        Returns:
            List of TaskType values ordered by priority
        """
        return sorted(cls.get_all_types(), key=lambda t: t.priority)

    def __str__(self) -> str:
        """String representation of the task type."""
        return self.value

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"TaskType.{self.name}"


# Additional type definitions for future use
class ExecutionState(Enum):
    """Enumeration of execution states for tasks and operations."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComponentState(Enum):
    """Enumeration of component lifecycle states."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"