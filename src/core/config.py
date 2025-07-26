"""
Configuration management module for the Instagram auto signup system.

This module handles loading, validating, and applying configuration settings.
It also provides hot-reload capability for configuration changes.
"""

import os
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    validate = None
    ValidationError = Exception


# Configure logger
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


@dataclass
class SystemConfig:
    """System configuration data class."""
    creation_interval: int = 300
    max_concurrent_creations: int = 1
    retry_attempts: int = 3
    proxy_rotation_frequency: int = 10
    email_service_timeout: int = 120
    human_behavior_variance: float = 0.3
    performance_optimization_enabled: bool = True
    log_level: str = "INFO"
    browser_timeout: int = 30
    page_load_timeout: int = 20
    implicit_wait: int = 10
    min_typing_delay: float = 0.1
    max_typing_delay: float = 0.5
    min_action_delay: float = 1.0
    max_action_delay: float = 3.0
    email_check_interval: int = 10
    max_email_wait_time: int = 120
    proxy_timeout: int = 10
    proxy_validation_timeout: int = 5
    browser_type: str = "chrome"
    headless: bool = True
    window_size: tuple = (1920, 1080)
    disable_images: bool = True
    email_services: List[Dict[str, Any]] = None
    proxies: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default lists."""
        if self.email_services is None:
            self.email_services = []
        if self.proxies is None:
            self.proxies = []


class ConfigEventDispatcher:
    """Dispatches configuration change events to registered callbacks."""
    
    def __init__(self):
        """Initialize the event dispatcher."""
        self._callbacks = []
    
    def register_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """Register a callback for configuration changes."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def dispatch(self, config: SystemConfig) -> None:
        """Dispatch configuration change event to all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(config)
            except Exception as e:
                logger.error(f"Error in configuration change callback: {e}")


class ConfigFileHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """File system event handler for configuration file changes."""
    
    def __init__(self, config_manager):
        """Initialize the file handler."""
        self.config_manager = config_manager
        self.last_modified = 0
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path == str(self.config_manager.config_file):
            # Avoid duplicate events
            current_time = os.path.getmtime(event.src_path)
            if current_time > self.last_modified:
                self.last_modified = current_time
                logger.info(f"Configuration file changed: {event.src_path}")
                self.config_manager.reload_config()


class ConfigManager:
    """Configuration manager for the Instagram auto signup system."""
    
    # Configuration schema for validation
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "creation_interval": {"type": "integer", "minimum": 60, "maximum": 3600},
            "max_concurrent_creations": {"type": "integer", "minimum": 1, "maximum": 10},
            "retry_attempts": {"type": "integer", "minimum": 1, "maximum": 10},
            "proxy_rotation_frequency": {"type": "integer", "minimum": 1, "maximum": 100},
            "email_service_timeout": {"type": "integer", "minimum": 30, "maximum": 300},
            "human_behavior_variance": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "performance_optimization_enabled": {"type": "boolean"},
            "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
            "browser_timeout": {"type": "integer", "minimum": 10, "maximum": 120},
            "page_load_timeout": {"type": "integer", "minimum": 5, "maximum": 60},
            "implicit_wait": {"type": "integer", "minimum": 1, "maximum": 30},
            "min_typing_delay": {"type": "number", "minimum": 0.01, "maximum": 1.0},
            "max_typing_delay": {"type": "number", "minimum": 0.1, "maximum": 2.0},
            "min_action_delay": {"type": "number", "minimum": 0.5, "maximum": 5.0},
            "max_action_delay": {"type": "number", "minimum": 1.0, "maximum": 10.0},
            "email_check_interval": {"type": "integer", "minimum": 5, "maximum": 60},
            "max_email_wait_time": {"type": "integer", "minimum": 60, "maximum": 600},
            "proxy_timeout": {"type": "integer", "minimum": 5, "maximum": 60},
            "proxy_validation_timeout": {"type": "integer", "minimum": 3, "maximum": 30},
            "browser_type": {"type": "string", "enum": ["chrome", "firefox", "edge"]},
            "headless": {"type": "boolean"},
            "window_size": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2
            },
            "disable_images": {"type": "boolean"},
            "email_services": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "priority": {"type": "integer", "minimum": 1}
                    },
                    "required": ["name"]
                }
            },
            "proxies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ip": {"type": "string"},
                        "port": {"type": "integer"},
                        "type": {"type": "string", "enum": ["http", "https", "socks4", "socks5"]},
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["ip", "port"]
                }
            }
        },
        "required": ["creation_interval", "max_concurrent_creations", "retry_attempts"],
        "additionalProperties": False
    }
    
    def __init__(self, config_file: str = "config/system_config.json"):
        self.config_file = Path(config_file)
        self.config = SystemConfig()
        self._change_callbacks: List[Callable[[SystemConfig], None]] = []
        self._file_observer: Optional[Observer] = None
        self._file_handler: Optional[ConfigFileHandler] = None
        self._lock = threading.RLock()
        self._hot_reload_enabled = False
        self._event_dispatcher = ConfigEventDispatcher()
        
        self._ensure_config_directory()
    
    async def initialize(self) -> bool:
        """Initialize the configuration manager."""
        try:
            logger.info("Initializing configuration manager...")
            
            # Load configuration
            if not await self.load_config():
                return False
            
            # Enable hot-reload if available
            self.enable_hot_reload()
            
            logger.info("Configuration manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize configuration manager: {e}")
            return False
    
    def _ensure_config_directory(self) -> None:
        """Ensure configuration directory exists."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _validate_config_data(self, config_data: Dict[str, Any]) -> None:
        """Validate configuration data against schema."""
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not available - skipping schema validation")
            return
            
        try:
            # Make sure we're validating a dictionary, not a SystemConfig object
            if not isinstance(config_data, dict):
                config_data = asdict(config_data)
                
            validate(instance=config_data, schema=self.CONFIG_SCHEMA)
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e.message}")
    
    def _handle_file_change(self) -> None:
        """Handle configuration file changes."""
        try:
            with self._lock:
                old_config = self.config
                self.load_config_sync()
                
                # Notify callbacks of configuration change
                self._event_dispatcher.dispatch(self.config)
                
                logger.info("Configuration reloaded due to file change")
        except Exception as e:
            logger.error(f"Error handling configuration file change: {e}")
    
    async def load_config(self) -> bool:
        """Load configuration from file."""
        try:
            with self._lock:
                return self.load_config_sync()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def load_config_sync(self) -> bool:
        """Load configuration from file (synchronous version)."""
        try:
            if not self.config_file.exists():
                logger.warning(f"Configuration file not found: {self.config_file}")
                self._create_default_config()
            
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Validate configuration
            self._validate_config_data(config_data)
            
            # Update configuration
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            logger.info(f"Configuration loaded from {self.config_file}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return False
        except ConfigurationError as e:
            logger.error(str(e))
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def _create_default_config(self) -> None:
        """Create default configuration file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self.config), f, indent=2)
            
            logger.info(f"Created default configuration file: {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to create default configuration file: {e}")
    
    def get_config(self) -> SystemConfig:
        """Get current configuration."""
        with self._lock:
            return self.config
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update configuration with new values."""
        try:
            with self._lock:
                # Update configuration
                for key, value in new_config.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
                
                # Save to file
                with open(self.config_file, 'w') as f:
                    json.dump(asdict(self.config), f, indent=2)
                
                # Notify callbacks of configuration change
                self._event_dispatcher.dispatch(self.config)
                
                logger.info("Configuration updated")
                return True
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False
    
    def update_config_value(self, key: str, value: Any) -> bool:
        """Update a single configuration value."""
        return self.update_config({key: value})
    
    def register_change_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """Register a callback for configuration changes."""
        self._event_dispatcher.register_callback(callback)
    
    def unregister_change_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """Unregister a callback."""
        self._event_dispatcher.unregister_callback(callback)
    
    def reload_config(self) -> bool:
        """Reload configuration from file."""
        try:
            with self._lock:
                old_config = self.config
                if self.load_config_sync():
                    # Notify callbacks of configuration change
                    self._event_dispatcher.dispatch(self.config)
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False
    
    def enable_hot_reload(self) -> None:
        """Enable hot-reload functionality with file watching."""
        if self._hot_reload_enabled:
            return
        
        if not WATCHDOG_AVAILABLE:
            logger.warning("Watchdog not available - hot-reload disabled")
            return
        
        try:
            self._file_handler = ConfigFileHandler(self)
            self._file_observer = Observer()
            self._file_observer.schedule(
                self._file_handler,
                str(self.config_file.parent),
                recursive=False
            )
            self._file_observer.start()
            self._hot_reload_enabled = True
            logger.info("Hot-reload enabled for configuration file")
            
        except Exception as e:
            logger.error(f"Failed to enable hot-reload: {e}")
            raise ConfigurationError(f"Failed to enable hot-reload: {e}")
    
    def disable_hot_reload(self) -> None:
        """Disable hot-reload functionality."""
        if not self._hot_reload_enabled:
            return
        
        try:
            if self._file_observer:
                self._file_observer.stop()
                self._file_observer.join()
                self._file_observer = None
            
            self._file_handler = None
            self._hot_reload_enabled = False
            logger.info("Hot-reload disabled for configuration file")
            
        except Exception as e:
            logger.error(f"Error disabling hot-reload: {e}")
    

# Global configuration manager instance
config_manager = ConfigManager()