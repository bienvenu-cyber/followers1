"""
System initialization module for the Instagram auto signup system.

This module handles the initialization sequence, configuration validation,
and component setup for the entire system.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.core.config import ConfigManager


@dataclass
class InitializationResult:
    """Result of system initialization."""
    success: bool
    message: str
    failed_components: List[str] = None
    warnings: List[str] = None


class SystemInitializer:
    """Handles system initialization and validation."""
    
    def __init__(self):
        """Initialize the system initializer."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = None
        
    async def initialize_system(self) -> InitializationResult:
        """Initialize the entire system."""
        try:
            self.logger.info("Starting system initialization...")
            
            # Step 1: Validate environment
            env_result = self._validate_environment()
            if not env_result.success:
                return env_result
            
            # Step 2: Initialize configuration
            config_result = await self._initialize_configuration()
            if not config_result.success:
                return config_result
            
            # Step 3: Validate configuration
            validation_result = await self._validate_configuration()
            if not validation_result.success:
                return validation_result
            
            # Step 4: Create required directories
            dir_result = self._create_required_directories()
            if not dir_result.success:
                return dir_result
            
            # Step 5: Validate dependencies
            deps_result = self._validate_dependencies()
            if not deps_result.success:
                return deps_result
            
            self.logger.info("System initialization completed successfully")
            return InitializationResult(
                success=True,
                message="System initialized successfully",
                warnings=[]
            )
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return InitializationResult(
                success=False,
                message=f"System initialization failed: {e}"
            )
    
    def _validate_environment(self) -> InitializationResult:
        """Validate the system environment."""
        try:
            self.logger.info("Validating system environment...")
            
            warnings = []
            
            # Check Python version
            import sys
            if sys.version_info < (3, 8):
                return InitializationResult(
                    success=False,
                    message="Python 3.8 or higher is required"
                )
            
            # Check required directories exist
            required_dirs = ["config", "logs", "src"]
            missing_dirs = []
            
            for dir_name in required_dirs:
                if not os.path.exists(dir_name):
                    missing_dirs.append(dir_name)
            
            if missing_dirs:
                return InitializationResult(
                    success=False,
                    message=f"Required directories missing: {missing_dirs}"
                )
            
            # Check disk space
            try:
                import shutil
                total, used, free = shutil.disk_usage(".")
                free_gb = free // (1024**3)
                
                if free_gb < 1:
                    warnings.append(f"Low disk space: {free_gb}GB available")
                elif free_gb < 5:
                    warnings.append(f"Limited disk space: {free_gb}GB available")
            except Exception as e:
                warnings.append(f"Could not check disk space: {e}")
            
            # Check memory
            try:
                import psutil
                memory = psutil.virtual_memory()
                available_gb = memory.available // (1024**3)
                
                if available_gb < 1:
                    warnings.append(f"Low memory: {available_gb}GB available")
                elif available_gb < 2:
                    warnings.append(f"Limited memory: {available_gb}GB available")
            except ImportError:
                warnings.append("psutil not available - cannot check memory")
            except Exception as e:
                warnings.append(f"Could not check memory: {e}")
            
            self.logger.info("Environment validation completed")
            return InitializationResult(
                success=True,
                message="Environment validation passed",
                warnings=warnings
            )
            
        except Exception as e:
            return InitializationResult(
                success=False,
                message=f"Environment validation failed: {e}"
            )
    
    async def _initialize_configuration(self) -> InitializationResult:
        """Initialize configuration manager."""
        try:
            self.logger.info("Initializing configuration...")
            
            self.config_manager = ConfigManager()
            success = await self.config_manager.initialize()
            
            if not success:
                return InitializationResult(
                    success=False,
                    message="Configuration initialization failed"
                )
            
            self.logger.info("Configuration initialized successfully")
            return InitializationResult(
                success=True,
                message="Configuration initialized successfully"
            )
            
        except Exception as e:
            return InitializationResult(
                success=False,
                message=f"Configuration initialization failed: {e}"
            )
    
    async def _validate_configuration(self) -> InitializationResult:
        """Validate system configuration."""
        try:
            self.logger.info("Validating configuration...")
            
            config = self.config_manager.get_config()
            warnings = []
            
            # Required configuration keys
            required_keys = [
                "creation_interval",
                "max_concurrent_creations",
                "browser_type",
                "email_services",
                "proxies"
            ]
            
            missing_keys = []
            for key in required_keys:
                if not hasattr(config, key) or getattr(config, key) is None:
                    missing_keys.append(key)
            
            if missing_keys:
                return InitializationResult(
                    success=False,
                    message=f"Missing required configuration keys: {missing_keys}"
                )
            
            # Validate specific values
            if hasattr(config, "creation_interval") and config.creation_interval <= 0:
                return InitializationResult(
                    success=False,
                    message="creation_interval must be greater than 0"
                )
            
            if hasattr(config, "max_concurrent_creations") and config.max_concurrent_creations <= 0:
                return InitializationResult(
                    success=False,
                    message="max_concurrent_creations must be greater than 0"
                )
            
            if hasattr(config, "browser_type") and config.browser_type not in ["chrome", "firefox", "edge"]:
                return InitializationResult(
                    success=False,
                    message=f"Unsupported browser type: {config.browser_type}"
                )
            
            if hasattr(config, "email_services") and not config.email_services:
                return InitializationResult(
                    success=False,
                    message="At least one email service must be configured"
                )
            
            if hasattr(config, "proxies") and not config.proxies:
                warnings.append("No proxies configured - system will use direct connection")
            
            # Validate email services configuration
            if hasattr(config, "email_services"):
                for service in config.email_services:
                    if "name" not in service:
                        return InitializationResult(
                            success=False,
                            message="Email service missing 'name' field"
                        )
                    if "priority" not in service:
                        warnings.append(f"Email service '{service['name']}' missing priority - using default")
            
            # Validate proxy configuration
            if hasattr(config, "proxies"):
                for i, proxy in enumerate(config.proxies):
                    if "ip" not in proxy or "port" not in proxy:
                        return InitializationResult(
                            success=False,
                            message=f"Proxy {i} missing required fields (ip, port)"
                        )
                    
                    if proxy.get("type", "http") not in ["http", "https", "socks4", "socks5"]:
                        warnings.append(f"Proxy {i} has unsupported type: {proxy.get('type')}")
            
            # Check file permissions
            config_files = [
                "config/system_config.json",
                "config/bots_credentials.json"
            ]
            
            for file_path in config_files:
                if not os.path.exists(file_path):
                    return InitializationResult(
                        success=False,
                        message=f"Required configuration file not found: {file_path}"
                    )
                
                if not os.access(file_path, os.R_OK):
                    return InitializationResult(
                        success=False,
                        message=f"Cannot read configuration file: {file_path}"
                    )
                
                if not os.access(file_path, os.W_OK):
                    warnings.append(f"Configuration file is read-only: {file_path}")
            
            self.logger.info("Configuration validation completed")
            return InitializationResult(
                success=True,
                message="Configuration validation passed",
                warnings=warnings
            )
            
        except Exception as e:
            return InitializationResult(
                success=False,
                message=f"Configuration validation failed: {e}"
            )
    
    def _create_required_directories(self) -> InitializationResult:
        """Create required directories."""
        try:
            self.logger.info("Creating required directories...")
            
            required_dirs = [
                "logs",
                "temp",
                "screenshots",
                "data"
            ]
            
            created_dirs = []
            for dir_name in required_dirs:
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name, exist_ok=True)
                    created_dirs.append(dir_name)
            
            if created_dirs:
                self.logger.info(f"Created directories: {created_dirs}")
            
            return InitializationResult(
                success=True,
                message="Required directories created successfully"
            )
            
        except Exception as e:
            return InitializationResult(
                success=False,
                message=f"Failed to create required directories: {e}"
            )
    
    def _validate_dependencies(self) -> InitializationResult:
        """Validate system dependencies."""
        try:
            self.logger.info("Validating dependencies...")
            
            # Required Python packages
            required_packages = [
                "selenium",
                "requests",
                "asyncio",
                "aiohttp",
                "psutil"
            ]
            
            missing_packages = []
            warnings = []
            
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)
            
            if missing_packages:
                return InitializationResult(
                    success=False,
                    message=f"Missing required packages: {missing_packages}"
                )
            
            # Check Selenium WebDriver availability
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                
                # Try to create a Chrome options object (doesn't require Chrome to be installed)
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                
            except ImportError:
                return InitializationResult(
                    success=False,
                    message="Selenium WebDriver not available"
                )
            except Exception as e:
                warnings.append(f"WebDriver setup warning: {e}")
            
            # Check browser availability
            config = self.config_manager.get_config()
            browser_type = getattr(config, "browser_type", "chrome")
            
            if browser_type == "chrome":
                try:
                    from selenium.webdriver.chrome.service import Service
                    # This doesn't actually start Chrome, just checks if the module is available
                except ImportError:
                    warnings.append("Chrome WebDriver not available")
            elif browser_type == "firefox":
                try:
                    from selenium.webdriver.firefox.service import Service
                except ImportError:
                    warnings.append("Firefox WebDriver not available")
            elif browser_type == "edge":
                try:
                    from selenium.webdriver.edge.service import Service
                except ImportError:
                    warnings.append("Edge WebDriver not available")
            
            self.logger.info("Dependency validation completed")
            return InitializationResult(
                success=True,
                message="Dependency validation passed",
                warnings=warnings
            )
            
        except Exception as e:
            return InitializationResult(
                success=False,
                message=f"Dependency validation failed: {e}"
            )


# Global system initializer instance
system_initializer = SystemInitializer()