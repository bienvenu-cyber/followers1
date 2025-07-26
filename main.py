#!/usr/bin/env python3
"""
Instagram Auto Signup System - Main Entry Point

This is the main entry point for the Instagram auto signup system.
It handles system initialization, configuration validation, and startup.
"""

import asyncio
import sys
import os
import signal
import logging
from pathlib import Path
from typing import Optional

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.main_controller import MainController
from src.core.config import ConfigManager
from src.core.statistics_manager import StatisticsManager
from src.core.performance_optimizer import PerformanceOptimizer
from src.services.account_creator import AccountCreator
from src.managers.browser_manager import BrowserManager
from src.managers.proxy_pool_manager import ProxyPoolManager
from src.managers.user_agent_rotator import UserAgentRotator
from src.services.email_service_handler import EmailServiceHandler
from src.services.anti_detection_module import AntiDetectionModule
from src.services.element_selector import ElementSelector
from src.services.browser_error_handler import BrowserErrorHandler
from src.services.verification_code_extractor import VerificationCodeExtractor


class InstagramAutoSignupSystem:
    """Main system class for Instagram auto signup."""
    
    def __init__(self):
        """Initialize the system."""
        self.logger = None
        self.config_manager = None
        self.main_controller = None
        self.components = {}
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self) -> bool:
        """Initialize the system and all components."""
        try:
            # Setup logging first
            self._setup_logging()
            self.logger.info("Starting Instagram Auto Signup System initialization...")
            
            # Initialize configuration
            if not await self._initialize_configuration():
                return False
            
            # Validate configuration
            if not await self._validate_configuration():
                return False
            
            # Initialize all components
            if not await self._initialize_components():
                return False
            
            # Initialize main controller
            if not await self._initialize_main_controller():
                return False
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            self.logger.info("System initialization completed successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"System initialization failed: {e}")
            else:
                print(f"System initialization failed: {e}")
            return False
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/instagram_auto_signup.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logging system initialized")
    
    async def _initialize_configuration(self) -> bool:
        """Initialize configuration manager."""
        try:
            self.logger.info("Initializing configuration manager...")
            self.config_manager = ConfigManager()
            await self.config_manager.initialize()
            self.logger.info("Configuration manager initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration manager: {e}")
            return False
    
    async def _validate_configuration(self) -> bool:
        """Validate system configuration."""
        try:
            self.logger.info("Validating system configuration...")
            
            # Check required configuration values
            required_configs = [
                "creation_interval",
                "max_concurrent_creations",
                "browser_type",
                "email_services",
                "proxies"
            ]
            
            config = self.config_manager.get_config()
            missing_configs = []
            
            for required_config in required_configs:
                if not hasattr(config, required_config) or getattr(config, required_config) is None:
                    missing_configs.append(required_config)
            
            if missing_configs:
                self.logger.error(f"Missing required configuration values: {missing_configs}")
                return False
            
            # Validate specific configuration values
            if config.creation_interval <= 0:
                self.logger.error("creation_interval must be greater than 0")
                return False
            
            if config.max_concurrent_creations <= 0:
                self.logger.error("max_concurrent_creations must be greater than 0")
                return False
            
            if not config.email_services:
                self.logger.error("At least one email service must be configured")
                return False
            
            if not config.proxies:
                self.logger.warning("No proxies configured - system will use direct connection")
            
            # Validate file paths
            required_files = [
                "config/system_config.json",
                "config/bots_credentials.json"
            ]
            
            for file_path in required_files:
                if not os.path.exists(file_path):
                    self.logger.error(f"Required file not found: {file_path}")
                    return False
            
            self.logger.info("Configuration validation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def _initialize_components(self) -> bool:
        """Initialize all system components."""
        try:
            self.logger.info("Initializing system components...")
            
            # Initialize proxy pool manager
            self.logger.info("Initializing proxy pool manager...")
            proxy_manager = ProxyPoolManager()
            await proxy_manager.initialize()
            self.components["proxy_manager"] = proxy_manager
            
            # Initialize user agent rotator
            self.logger.info("Initializing user agent rotator...")
            user_agent_rotator = UserAgentRotator()
            await user_agent_rotator.initialize()
            self.components["user_agent_rotator"] = user_agent_rotator
            
            # Initialize browser manager
            self.logger.info("Initializing browser manager...")
            browser_manager = BrowserManager(proxy_manager, user_agent_rotator)
            await browser_manager.initialize()
            self.components["browser_manager"] = browser_manager
            
            # Initialize email service handler
            self.logger.info("Initializing email service handler...")
            email_service = EmailServiceHandler()
            await email_service.initialize()
            self.components["email_service"] = email_service
            
            # Initialize anti-detection module
            self.logger.info("Initializing anti-detection module...")
            anti_detection = AntiDetectionModule()
            await anti_detection.initialize()
            self.components["anti_detection"] = anti_detection
            
            # Initialize element selector
            self.logger.info("Initializing element selector...")
            element_selector = ElementSelector()
            await element_selector.initialize()
            self.components["element_selector"] = element_selector
            
            # Initialize browser error handler
            self.logger.info("Initializing browser error handler...")
            error_handler = BrowserErrorHandler()
            await error_handler.initialize()
            self.components["error_handler"] = error_handler
            
            # Initialize verification code extractor
            self.logger.info("Initializing verification code extractor...")
            verification_extractor = VerificationCodeExtractor()
            await verification_extractor.initialize()
            self.components["verification_extractor"] = verification_extractor
            
            # Initialize account creator
            self.logger.info("Initializing account creator...")
            account_creator = AccountCreator(
                browser_manager=browser_manager,
                email_service=email_service,
                anti_detection=anti_detection,
                element_selector=element_selector,
                error_handler=error_handler,
                config_manager=self.config_manager,
                verification_extractor=verification_extractor
            )
            await account_creator.initialize()
            self.components["account_creator"] = account_creator
            
            # Initialize statistics manager
            self.logger.info("Initializing statistics manager...")
            stats_manager = StatisticsManager()
            await stats_manager.initialize()
            self.components["stats_manager"] = stats_manager
            
            # Initialize performance optimizer
            self.logger.info("Initializing performance optimizer...")
            performance_optimizer = PerformanceOptimizer()
            await performance_optimizer.initialize()
            self.components["performance_optimizer"] = performance_optimizer
            
            self.logger.info("All system components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            return False
    
    async def _initialize_main_controller(self) -> bool:
        """Initialize the main controller."""
        try:
            self.logger.info("Initializing main controller...")
            self.main_controller = MainController(self.components["account_creator"])
            
            if await self.main_controller.initialize_services():
                self.logger.info("Main controller initialized successfully")
                return True
            else:
                self.logger.error("Main controller initialization failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Main controller initialization failed: {e}")
            return False
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Run the system."""
        try:
            self.logger.info("Starting Instagram Auto Signup System...")
            
            # Start the main controller
            self.main_controller.start_continuous_creation()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f"System runtime error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the system gracefully."""
        try:
            self.logger.info("Shutting down Instagram Auto Signup System...")
            
            # Stop main controller
            if self.main_controller:
                await self.main_controller.shutdown()
            
            # Cleanup components
            for name, component in self.components.items():
                try:
                    if hasattr(component, 'cleanup'):
                        await component.cleanup()
                    self.logger.info(f"Component {name} cleaned up successfully")
                except Exception as e:
                    self.logger.error(f"Error cleaning up component {name}: {e}")
            
            self.logger.info("System shutdown completed")
            self.shutdown_event.set()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point."""
    system = InstagramAutoSignupSystem()
    
    # Initialize system
    if not await system.initialize():
        print("System initialization failed. Exiting.")
        sys.exit(1)
    
    # Run system
    try:
        await system.run()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run the main function
    asyncio.run(main())