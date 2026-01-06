"""
Browser manager module for the Instagram auto signup system.

This module provides functionality for creating and managing browser instances
with proxy and user agent rotation.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import WebDriverException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

from .proxy_pool_manager import ProxyPoolManager, ProxyConfig
from .user_agent_rotator import UserAgentRotator, UserAgentInfo
from ..core.config import config_manager

logger = logging.getLogger(__name__)


@dataclass
class BrowserInstance:
    """Browser instance data class."""
    driver: Any
    proxy_config: Optional[ProxyConfig] = None
    user_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    page_loads: int = 0
    errors: int = 0
    is_healthy: bool = True


@dataclass
class BrowserConfig:
    """Browser configuration data class."""
    browser_type: str = "chrome"
    headless: bool = True
    window_size: Tuple[int, int] = (1920, 1080)
    page_load_timeout: int = 30
    implicit_wait: int = 10
    disable_images: bool = True
    disable_notifications: bool = True
    disable_extensions: bool = True
    disable_infobars: bool = True
    disable_gpu: bool = True
    disable_dev_shm_usage: bool = True
    errors: int = 0
    is_healthy: bool = True


class BrowserManager:
    """Manager for browser instances."""
    
    def __init__(self, proxy_manager: ProxyPoolManager, user_agent_rotator: UserAgentRotator):
        """
        Initialize the browser manager.
        
        Args:
            proxy_manager: Proxy pool manager instance
            user_agent_rotator: User agent rotator instance
        """
        self.proxy_manager = proxy_manager
        self.user_agent_rotator = user_agent_rotator
        self.browser_instances: List[BrowserInstance] = []
        self.config = BrowserConfig()
        
        # WebDriver paths (will be set during initialization)
        self.chrome_driver_path = None
        self.firefox_driver_path = None
        self.edge_driver_path = None
    
    async def initialize(self) -> bool:
        """Initialize the browser manager."""
        logger.info("Initializing browser manager...")
        
        # Load configuration
        from ..core.config import config_manager
        system_config = config_manager.get_config()
        
        # Update browser config from system config
        if hasattr(system_config, 'browser_type'):
            self.config.browser_type = system_config.browser_type
        if hasattr(system_config, 'headless'):
            self.config.headless = system_config.headless
        if hasattr(system_config, 'window_size'):
            self.config.window_size = tuple(system_config.window_size)
        if hasattr(system_config, 'page_load_timeout'):
            self.config.page_load_timeout = system_config.page_load_timeout
        if hasattr(system_config, 'implicit_wait'):
            self.config.implicit_wait = system_config.implicit_wait
        if hasattr(system_config, 'disable_images'):
            self.config.disable_images = system_config.disable_images
        
        # Initialize WebDriver managers
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.firefox import GeckoDriverManager
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            
            # Download and cache drivers
            if self.config.browser_type == "chrome":
                self.chrome_driver_path = ChromeDriverManager().install()
                logger.info(f"Chrome driver installed at: {self.chrome_driver_path}")
            elif self.config.browser_type == "firefox":
                self.firefox_driver_path = GeckoDriverManager().install()
                logger.info(f"Firefox driver installed at: {self.firefox_driver_path}")
            elif self.config.browser_type == "edge":
                self.edge_driver_path = EdgeChromiumDriverManager().install()
                logger.info(f"Edge driver installed at: {self.edge_driver_path}")
            
        except Exception as e:
            logger.warning(f"WebDriver manager error: {e}")
            logger.info("Will attempt to use system-installed drivers")
        
        logger.info("Browser manager initialized successfully")
        return True
    
    async def cleanup(self) -> None:
        """Clean up all browser instances."""
        logger.info("Cleaning up browser instances...")
        
        for instance in self.browser_instances:
            try:
                instance.driver.quit()
                logger.info("Browser instance closed")
            except Exception as e:
                logger.error(f"Error closing browser instance: {e}")
        
        self.browser_instances.clear()
    
    async def create_browser_instance(
        self, 
        proxy_config: Optional[ProxyConfig] = None,
        user_agent: Optional[str] = None
    ) -> Optional[BrowserInstance]:
        """
        Create a new browser instance.
        
        Args:
            proxy_config: Proxy configuration to use
            user_agent: User agent string to use
            
        Returns:
            BrowserInstance if successful, None otherwise
        """
        try:
            # Get proxy - try proxy_config first, then proxy_manager
            if proxy_config is None:
                proxy_config = self.proxy_manager.get_proxy()
            
            # Get user agent
            if user_agent is None:
                user_agent_info = self.user_agent_rotator.get_user_agent()
                user_agent = user_agent_info.user_agent if user_agent_info else None
            
            # Create browser options
            if self.config.browser_type == "chrome":
                driver = await self._create_chrome_driver(proxy_config, user_agent)
            elif self.config.browser_type == "firefox":
                driver = await self._create_firefox_driver(proxy_config, user_agent)
            elif self.config.browser_type == "edge":
                driver = await self._create_edge_driver(proxy_config, user_agent)
            else:
                logger.error(f"Unsupported browser type: {self.config.browser_type}")
                return None
            
            if driver is None:
                return None
            
            # Configure driver
            driver.set_page_load_timeout(self.config.page_load_timeout)
            driver.implicitly_wait(self.config.implicit_wait)
            
            # Set window size
            driver.set_window_size(*self.config.window_size)
            
            # Create browser instance - return driver directly for compatibility
            self.browser_instances.append(BrowserInstance(
                driver=driver,
                proxy_config=proxy_config,
                user_agent=user_agent
            ))
            
            logger.info(f"Browser instance created with {self.config.browser_type}")
            return self.browser_instances[-1]
            
        except Exception as e:
            logger.error(f"Failed to create browser instance: {e}")
            return None
    
    async def _create_chrome_driver(
        self, 
        proxy_config: Optional[ProxyConfig], 
        user_agent: Optional[str]
    ) -> Optional[webdriver.Chrome]:
        """Create Chrome driver instance with strong anti-detection."""
        try:
            options = ChromeOptions()
            
            # Anti-detection options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-browser-side-navigation")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            
            # Headless mode
            if self.config.headless:
                options.add_argument("--headless=new")
            
            # Window size
            options.add_argument(f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}")
            
            # User agent
            if user_agent:
                options.add_argument(f"--user-agent={user_agent}")
            else:
                options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Proxy
            if proxy_config:
                if hasattr(proxy_config, 'url'):
                    options.add_argument(f"--proxy-server={proxy_config.url}")
                elif isinstance(proxy_config, dict):
                    options.add_argument(f"--proxy-server={proxy_config.get('url', '')}")
            
            # Disable automation flags
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Disable images for speed
            if self.config.disable_images:
                prefs = {
                    "profile.managed_default_content_settings.images": 2,
                    "profile.default_content_setting_values.notifications": 2,
                    "credentials_enable_service": False,
                    "profile.password_manager_enabled": False
                }
                options.add_experimental_option("prefs", prefs)
            
            # Create service
            service = None
            if self.chrome_driver_path:
                service = ChromeService(self.chrome_driver_path)
            
            # Create driver
            driver = webdriver.Chrome(service=service, options=options)
            
            # Anti-detection scripts
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": driver.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
            })
            
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """)
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            return None
    
    async def _create_firefox_driver(
        self, 
        proxy_config: Optional[ProxyConfig], 
        user_agent: Optional[str]
    ) -> Optional[webdriver.Firefox]:
        """Create Firefox driver instance."""
        try:
            options = FirefoxOptions()
            
            # Basic options
            if self.config.headless:
                options.add_argument("--headless")
            
            # Set user agent
            if user_agent:
                options.set_preference("general.useragent.override", user_agent)
            
            # Disable images if configured
            if self.config.disable_images:
                options.set_preference("permissions.default.image", 2)
            
            # Set proxy
            if proxy_config:
                options.set_preference("network.proxy.type", 1)
                options.set_preference("network.proxy.http", proxy_config.ip)
                options.set_preference("network.proxy.http_port", proxy_config.port)
                options.set_preference("network.proxy.ssl", proxy_config.ip)
                options.set_preference("network.proxy.ssl_port", proxy_config.port)
            
            # Create service
            service = None
            if self.firefox_driver_path:
                service = FirefoxService(self.firefox_driver_path)
            
            # Create driver
            driver = webdriver.Firefox(service=service, options=options)
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create Firefox driver: {e}")
            return None
    
    async def _create_edge_driver(
        self, 
        proxy_config: Optional[ProxyConfig], 
        user_agent: Optional[str]
    ) -> Optional[webdriver.Edge]:
        """Create Edge driver instance."""
        try:
            options = EdgeOptions()
            
            # Basic options
            if self.config.headless:
                options.add_argument("--headless")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            # Set user agent
            if user_agent:
                options.add_argument(f"--user-agent={user_agent}")
            
            # Set proxy
            if proxy_config:
                options.add_argument(f"--proxy-server={proxy_config.url}")
            
            # Disable images if configured
            if self.config.disable_images:
                prefs = {"profile.managed_default_content_settings.images": 2}
                options.add_experimental_option("prefs", prefs)
            
            # Create service
            service = None
            if self.edge_driver_path:
                service = EdgeService(self.edge_driver_path)
            
            # Create driver
            driver = webdriver.Edge(service=service, options=options)
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create Edge driver: {e}")
            return None
    
    async def close_browser_instance(self, instance: BrowserInstance) -> bool:
        """
        Close a browser instance.
        
        Args:
            instance: Browser instance to close
            
        Returns:
            True if successful, False otherwise
        """
        try:
            instance.driver.quit()
            
            if instance in self.browser_instances:
                self.browser_instances.remove(instance)
            
            logger.info("Browser instance closed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close browser instance: {e}")
            return False
    
    def get_browser_stats(self) -> Dict[str, Any]:
        """
        Get browser statistics.
        
        Returns:
            Dictionary with browser statistics
        """
        total_instances = len(self.browser_instances)
        healthy_instances = len([i for i in self.browser_instances if i.is_healthy])
        
        total_page_loads = sum(i.page_loads for i in self.browser_instances)
        total_errors = sum(i.errors for i in self.browser_instances)
        
        return {
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "total_page_loads": total_page_loads,
            "total_errors": total_errors,
            "browser_type": self.config.browser_type
        }