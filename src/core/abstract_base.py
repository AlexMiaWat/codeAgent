"""
Abstract base classes for Code Agent components.

This module provides abstract base classes that define common interfaces
and functionality for components in the Code Agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    """Status enumeration for component lifecycle."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    DISABLED = "disabled"
    ERROR = "error"


class ServerConfig:
    """Configuration class for server components."""

    def __init__(self, **kwargs):
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 3456)
        self.debug = kwargs.get('debug', False)
        self.max_workers = kwargs.get('max_workers', 4)
        self.timeout = kwargs.get('timeout', 30)


class ComponentHealth:
    """Health status representation for components."""

    def __init__(self, status: str = "unknown", message: str = "", details: Optional[Dict[str, Any]] = None):
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status in ["healthy", "ok", "ready"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert health status to dictionary."""
        return {
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class IServerComponent(ABC):
    """Interface for server components."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the component."""
        pass

    @abstractmethod
    def start(self) -> bool:
        """Start the component."""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Stop the component."""
        pass

    @abstractmethod
    def get_status(self) -> ComponentStatus:
        """Get current component status."""
        pass

    @abstractmethod
    def get_health(self) -> ComponentHealth:
        """Get component health information."""
        pass


class IConfigurable(ABC):
    """Interface for configurable components."""

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the component with given configuration."""
        pass

    @abstractmethod
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration."""
        pass

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration."""
        pass


class IMetricsCollector(ABC):
    """Interface for metrics collection."""

    @abstractmethod
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics."""
        pass

    @abstractmethod
    def get_metric(self, name: str) -> Any:
        """Get specific metric by name."""
        pass

    @abstractmethod
    def reset_metrics(self) -> bool:
        """Reset all metrics."""
        pass


class BaseComponent(IServerComponent):
    """
    Base component class providing common functionality.

    This class implements the basic lifecycle management and health checking
    that all components should support.
    """

    def __init__(self, component_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base component.

        Args:
            component_name: Name of the component
            config: Optional configuration dictionary
        """
        self.component_name = component_name
        self._config = config or {}
        self._status = ComponentStatus.INITIALIZING
        self._start_time = None
        self._health_checks = []

    def initialize(self) -> bool:
        """
        Initialize the component.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._status = ComponentStatus.READY
            logger.info(f"Component {self.component_name} initialized successfully")
            return True
        except Exception as e:
            self._status = ComponentStatus.ERROR
            logger.error(f"Failed to initialize component {self.component_name}: {e}")
            return False

    def start(self) -> bool:
        """
        Start the component.

        Returns:
            True if start successful, False otherwise
        """
        try:
            if self._status != ComponentStatus.READY:
                logger.warning(f"Component {self.component_name} not ready for start")
                return False

            self._status = ComponentStatus.RUNNING
            self._start_time = datetime.now()
            logger.info(f"Component {self.component_name} started successfully")
            return True
        except Exception as e:
            self._status = ComponentStatus.ERROR
            logger.error(f"Failed to start component {self.component_name}: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop the component.

        Returns:
            True if stop successful, False otherwise
        """
        try:
            self._status = ComponentStatus.DISABLED
            logger.info(f"Component {self.component_name} stopped successfully")
            return True
        except Exception as e:
            self._status = ComponentStatus.ERROR
            logger.error(f"Failed to stop component {self.component_name}: {e}")
            return False

    def get_status(self) -> ComponentStatus:
        """Get current component status."""
        return self._status

    def get_health(self) -> ComponentHealth:
        """
        Get component health information.

        Returns:
            ComponentHealth object with current health status
        """
        try:
            if self._status == ComponentStatus.RUNNING:
                health_status = "healthy"
                message = "Component is running normally"
            elif self._status == ComponentStatus.READY:
                health_status = "ready"
                message = "Component is ready to start"
            elif self._status == ComponentStatus.ERROR:
                health_status = "unhealthy"
                message = "Component is in error state"
            else:
                health_status = "unknown"
                message = f"Component status: {self._status.value}"

            details = {
                "component_name": self.component_name,
                "status": self._status.value,
                "start_time": self._start_time.isoformat() if self._start_time else None,
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds() if self._start_time else None
            }

            return ComponentHealth(health_status, message, details)

        except Exception as e:
            return ComponentHealth("error", f"Health check failed: {e}")


class ConfigurableComponent(BaseComponent, IConfigurable):
    """
    Base component with configuration support.

    This class extends BaseComponent with configuration management capabilities.
    """

    def __init__(self, component_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize configurable component.

        Args:
            component_name: Name of the component
            config: Optional configuration dictionary
        """
        super().__init__(component_name, config)
        self._configuration = config or {}

    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the component.

        Args:
            config: Configuration dictionary

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            if self.validate_configuration(config):
                self._configuration.update(config)
                logger.info(f"Component {self.component_name} configured successfully")
                return True
            else:
                logger.error(f"Invalid configuration for component {self.component_name}")
                return False
        except Exception as e:
            logger.error(f"Configuration failed for component {self.component_name}: {e}")
            return False

    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._configuration.copy()

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        # Basic validation - can be overridden by subclasses
        if not isinstance(config, dict):
            return False
        return True


class MetricsEnabledComponent(BaseComponent, IMetricsCollector):
    """
    Base component with metrics collection support.

    This class extends BaseComponent with metrics collection capabilities.
    """

    def __init__(self, component_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics-enabled component.

        Args:
            component_name: Name of the component
            config: Optional configuration dictionary
        """
        super().__init__(component_name, config)
        self._metrics = {}
        self._metrics_start_time = datetime.now()

    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect current metrics.

        Returns:
            Dictionary of current metrics
        """
        base_metrics = {
            "component_name": self.component_name,
            "status": self._status.value,
            "uptime_seconds": (datetime.now() - self._metrics_start_time).total_seconds(),
            "health_status": self.get_health().status
        }

        # Merge with component-specific metrics
        all_metrics = base_metrics.copy()
        all_metrics.update(self._metrics)

        return all_metrics

    def get_metric(self, name: str) -> Any:
        """
        Get specific metric by name.

        Args:
            name: Name of the metric

        Returns:
            Metric value or None if not found
        """
        return self._metrics.get(name)

    def reset_metrics(self) -> bool:
        """
        Reset all metrics.

        Returns:
            True if reset successful, False otherwise
        """
        try:
            self._metrics.clear()
            self._metrics_start_time = datetime.now()
            logger.info(f"Metrics reset for component {self.component_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset metrics for component {self.component_name}: {e}")
            return False

    def _set_metric(self, name: str, value: Any) -> None:
        """Set a metric value (protected method for subclasses)."""
        self._metrics[name] = value