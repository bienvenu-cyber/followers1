"""
Configuration change event system for dynamic application of configuration changes.
"""

from typing import Dict, Any, Callable, List
from enum import Enum
from dataclasses import dataclass
import threading
from .logging_config import get_logger

logger = get_logger(__name__)


class ConfigChangeType(Enum):
    """Types of configuration changes."""
    VALUE_UPDATED = "value_updated"
    MULTIPLE_VALUES_UPDATED = "multiple_values_updated"
    CONFIG_RELOADED = "config_reloaded"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class ConfigChangeEvent:
    """Configuration change event data."""
    change_type: ConfigChangeType
    key: str = None
    old_value: Any = None
    new_value: Any = None
    changes: Dict[str, Any] = None
    error: Exception = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()


class ConfigEventDispatcher:
    """Event dispatcher for configuration changes."""
    
    def __init__(self):
        self._listeners: Dict[ConfigChangeType, List[Callable[[ConfigChangeEvent], None]]] = {}
        self._global_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        self._lock = threading.RLock()
    
    def add_listener(self, event_type: ConfigChangeType, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Add a listener for specific configuration change events."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(callback)
            logger.debug(f"Added listener for {event_type.value}: {callback.__name__}")
    
    def add_global_listener(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Add a global listener that receives all configuration change events."""
        with self._lock:
            self._global_listeners.append(callback)
            logger.debug(f"Added global listener: {callback.__name__}")
    
    def remove_listener(self, event_type: ConfigChangeType, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Remove a specific event listener."""
        with self._lock:
            if event_type in self._listeners and callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)
                logger.debug(f"Removed listener for {event_type.value}: {callback.__name__}")
    
    def remove_global_listener(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Remove a global event listener."""
        with self._lock:
            if callback in self._global_listeners:
                self._global_listeners.remove(callback)
                logger.debug(f"Removed global listener: {callback.__name__}")
    
    def dispatch_event(self, event: ConfigChangeEvent) -> None:
        """Dispatch a configuration change event to all relevant listeners."""
        with self._lock:
            # Notify specific event type listeners
            if event.change_type in self._listeners:
                for callback in self._listeners[event.change_type]:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in config event listener {callback.__name__}: {e}")
            
            # Notify global listeners
            for callback in self._global_listeners:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in global config event listener {callback.__name__}: {e}")
    
    def clear_listeners(self) -> None:
        """Clear all event listeners."""
        with self._lock:
            self._listeners.clear()
            self._global_listeners.clear()
            logger.debug("Cleared all configuration event listeners")


# Global event dispatcher instance
config_event_dispatcher = ConfigEventDispatcher()


def add_config_change_listener(event_type: ConfigChangeType, callback: Callable[[ConfigChangeEvent], None]) -> None:
    """Add a configuration change listener."""
    config_event_dispatcher.add_listener(event_type, callback)


def add_global_config_listener(callback: Callable[[ConfigChangeEvent], None]) -> None:
    """Add a global configuration change listener."""
    config_event_dispatcher.add_global_listener(callback)


def remove_config_change_listener(event_type: ConfigChangeType, callback: Callable[[ConfigChangeEvent], None]) -> None:
    """Remove a configuration change listener."""
    config_event_dispatcher.remove_listener(event_type, callback)


def remove_global_config_listener(callback: Callable[[ConfigChangeEvent], None]) -> None:
    """Remove a global configuration change listener."""
    config_event_dispatcher.remove_global_listener(callback)