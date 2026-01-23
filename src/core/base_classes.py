"""
Base classes for Code Agent components.

This module provides abstract base classes with common functionality
shared across different manager implementations.
"""

from abc import ABC
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseManager(ABC):
    """
    Base class for all managers providing common functionality.

    This class implements common patterns used across all manager types:
    - Health checking
    - Status reporting
    - Resource cleanup
    - Basic configuration handling
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize base manager.

        Args:
            config: Configuration dictionary for the manager
        """
        self.config = config or {}
        self._start_time = datetime.now()
        self._healthy = True
        self._status_info = {}

    def is_healthy(self) -> bool:
        """
        Check if the manager is in a healthy state.

        Returns:
            True if manager is healthy, False otherwise
        """
        try:
            # Basic health check - can be overridden by subclasses
            return self._healthy and self._perform_health_check()
        except Exception as e:
            logger.warning(f"Health check failed for {self.__class__.__name__}: {e}")
            return False

    def _perform_health_check(self) -> bool:
        """
        Perform manager-specific health check.

        This method can be overridden by subclasses to implement
        custom health checking logic.

        Returns:
            True if healthy, False otherwise
        """
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the manager.

        Returns:
            Dictionary containing status information
        """
        return {
            "manager_type": self.__class__.__name__,
            "healthy": self.is_healthy(),
            "start_time": self._start_time.isoformat(),
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "config": self._get_config_status(),
            **self._status_info
        }

    def _get_config_status(self) -> Dict[str, Any]:
        """
        Get configuration status information.

        Returns:
            Dictionary with configuration status
        """
        return {
            "config_keys": list(self.config.keys()) if self.config else [],
            "has_config": bool(self.config)
        }

    def dispose(self) -> None:
        """
        Clean up resources used by the manager.

        This method should be called when the manager is no longer needed
        to ensure proper resource cleanup.
        """
        try:
            self._healthy = False
            self._cleanup_resources()
            logger.info(f"Disposed {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error disposing {self.__class__.__name__}: {e}")

    def _cleanup_resources(self) -> None:
        """
        Clean up manager-specific resources.

        This method can be overridden by subclasses to implement
        custom resource cleanup logic.
        """
        pass

    def update_status_info(self, key: str, value: Any) -> None:
        """
        Update status information.

        Args:
            key: Status key to update
            value: New value for the key
        """
        self._status_info[key] = value

    def set_healthy(self, healthy: bool) -> None:
        """
        Set the health status of the manager.

        Args:
            healthy: New health status
        """
        self._healthy = healthy


class ConfigurableManager(BaseManager):
    """
    Base class for managers that support configuration reloading.

    This class extends BaseManager with configuration management capabilities.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._config_version = 1

    def reload_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Reload manager configuration.

        Args:
            new_config: New configuration to apply

        Returns:
            True if configuration reloaded successfully, False otherwise
        """
        try:
            old_config = self.config.copy()
            self.config.update(new_config)
            self._config_version += 1

            # Allow subclasses to react to config changes
            if not self._validate_config():
                # Rollback on validation failure
                self.config = old_config
                self._config_version -= 1
                logger.error(f"Configuration validation failed for {self.__class__.__name__}")
                return False

            self._apply_config_changes()
            logger.info(f"Configuration reloaded for {self.__class__.__name__}")
            return True

        except Exception as e:
            logger.error(f"Failed to reload config for {self.__class__.__name__}: {e}")
            return False

    def _validate_config(self) -> bool:
        """
        Validate new configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def _apply_config_changes(self) -> None:
        """
        Apply configuration changes.

        This method can be overridden by subclasses to react to
        configuration changes.
        """
        pass

    def get_config_version(self) -> int:
        """
        Get current configuration version.

        Returns:
            Configuration version number
        """
        return self._config_version


class MetricsManager(BaseManager):
    """
    Base class for managers that collect and report metrics.

    This class extends BaseManager with metrics collection capabilities.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._metrics = {}
        self._metrics_enabled = self.config.get('metrics_enabled', True)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.

        Returns:
            Dictionary containing current metrics
        """
        if not self._metrics_enabled:
            return {"metrics_enabled": False}

        return {
            "metrics_enabled": True,
            "timestamp": datetime.now().isoformat(),
            **self._metrics
        }

    def update_metric(self, key: str, value: Any) -> None:
        """
        Update a metric value.

        Args:
            key: Metric key
            value: New metric value
        """
        if self._metrics_enabled:
            self._metrics[key] = value

    def increment_metric(self, key: str, amount: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            key: Metric key
            amount: Amount to increment by (default: 1)
        """
        if self._metrics_enabled:
            current = self._metrics.get(key, 0)
            self._metrics[key] = current + amount

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()

    def _cleanup_resources(self) -> None:
        """Clean up metrics resources."""
        super()._cleanup_resources()
        self.reset_metrics()