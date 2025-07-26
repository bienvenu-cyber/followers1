"""
User agent rotator module for the Instagram auto signup system.

This module provides functionality for managing and rotating user agents
to avoid detection.
"""

import logging
import random
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class BrowserType(Enum):
    """Browser types for user agents."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"
    OPERA = "opera"


class DeviceType(Enum):
    """Device types for user agents."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


@dataclass
class UserAgentInfo:
    """User agent information data class."""
    user_agent: str
    browser_type: BrowserType
    device_type: DeviceType
    version: str
    os: str
    last_used: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    is_active: bool = True
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total


class UserAgentRotator(ResourceManager):
    """Manager for user agent rotation."""
    
    def __init__(self):
        """Initialize the user agent rotator."""
        super().__init__("UserAgentRotator")
        self.user_agents: List[UserAgentInfo] = []
        self.current_index = 0
        self.blacklisted_agents = set()
        
        # Default user agents
        self._add_default_user_agents()
    
    def _add_default_user_agents(self) -> None:
        """Add default user agents."""
        default_agents = [
            # Chrome on Windows
            UserAgentInfo(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                browser_type=BrowserType.CHROME,
                device_type=DeviceType.DESKTOP,
                version="91.0.4472.124",
                os="Windows 10"
            ),
            # Chrome on macOS
            UserAgentInfo(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                browser_type=BrowserType.CHROME,
                device_type=DeviceType.DESKTOP,
                version="91.0.4472.114",
                os="macOS 10.15.7"
            ),
            # Firefox on Windows
            UserAgentInfo(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                browser_type=BrowserType.FIREFOX,
                device_type=DeviceType.DESKTOP,
                version="89.0",
                os="Windows 10"
            ),
            # Safari on macOS
            UserAgentInfo(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                browser_type=BrowserType.SAFARI,
                device_type=DeviceType.DESKTOP,
                version="14.1.1",
                os="macOS 10.15.7"
            ),
            # Edge on Windows
            UserAgentInfo(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
                browser_type=BrowserType.EDGE,
                device_type=DeviceType.DESKTOP,
                version="91.0.864.59",
                os="Windows 10"
            ),
            # Chrome on Android
            UserAgentInfo(
                user_agent="Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
                browser_type=BrowserType.CHROME,
                device_type=DeviceType.MOBILE,
                version="91.0.4472.120",
                os="Android 11"
            )
        ]
        
        self.user_agents.extend(default_agents)
    
    async def initialize(self) -> bool:
        """Initialize the user agent rotator."""
        logger.info("Initializing user agent rotator...")
        
        # Try to load additional user agents from fake-useragent if available
        try:
            from fake_useragent import UserAgent
            ua = UserAgent()
            
            # Add some random user agents
            for browser_type in ["chrome", "firefox", "safari", "edge", "opera"]:
                for _ in range(3):
                    try:
                        user_agent = getattr(ua, browser_type)
                        
                        # Determine device type based on user agent string
                        device_type = DeviceType.DESKTOP
                        if "Mobile" in user_agent:
                            device_type = DeviceType.MOBILE
                        elif "Tablet" in user_agent:
                            device_type = DeviceType.TABLET
                        
                        # Determine OS
                        os = "Unknown"
                        if "Windows" in user_agent:
                            os = "Windows"
                        elif "Macintosh" in user_agent:
                            os = "macOS"
                        elif "Linux" in user_agent:
                            os = "Linux"
                        elif "Android" in user_agent:
                            os = "Android"
                        elif "iOS" in user_agent:
                            os = "iOS"
                        
                        # Extract version (simplified)
                        version = "Unknown"
                        if browser_type.capitalize() in user_agent:
                            parts = user_agent.split(browser_type.capitalize() + "/")
                            if len(parts) > 1:
                                version = parts[1].split(" ")[0]
                        
                        # Add to user agents list
                        self.user_agents.append(UserAgentInfo(
                            user_agent=user_agent,
                            browser_type=BrowserType(browser_type),
                            device_type=device_type,
                            version=version,
                            os=os
                        ))
                    except Exception as e:
                        logger.warning(f"Error generating {browser_type} user agent: {e}")
            
            logger.info(f"Added {len(self.user_agents) - 6} user agents from fake-useragent")
            
        except ImportError:
            logger.warning("fake-useragent package not available, using default user agents only")
        except Exception as e:
            logger.warning(f"Error initializing fake-useragent: {e}")
        
        logger.info(f"User agent rotator initialized with {len(self.user_agents)} user agents")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    def get_user_agent(self) -> Optional[UserAgentInfo]:
        """
        Get a user agent from the pool.
        
        Returns:
            UserAgentInfo if available, None otherwise
        """
        if not self.user_agents:
            logger.warning("No user agents available")
            return None
        
        # Find active user agents
        active_agents = [ua for ua in self.user_agents if ua.is_active and ua.user_agent not in self.blacklisted_agents]
        if not active_agents:
            logger.warning("No active user agents available")
            return None
        
        # Sort by success rate and last used time
        sorted_agents = sorted(
            active_agents,
            key=lambda ua: (ua.success_rate, -ua.last_used)
        )
        
        # Get the best user agent
        user_agent = sorted_agents[-1]
        user_agent.last_used = time.time()
        
        logger.info(f"Selected user agent: {user_agent.browser_type.value} on {user_agent.os}")
        return user_agent
    
    def rotate_user_agent(self) -> Optional[UserAgentInfo]:
        """
        Rotate to the next user agent in the pool.
        
        Returns:
            UserAgentInfo if available, None otherwise
        """
        if not self.user_agents:
            logger.warning("No user agents available for rotation")
            return None
        
        # Find active user agents
        active_agents = [ua for ua in self.user_agents if ua.is_active and ua.user_agent not in self.blacklisted_agents]
        if not active_agents:
            logger.warning("No active user agents available for rotation")
            return None
        
        # Increment index
        self.current_index = (self.current_index + 1) % len(active_agents)
        
        # Get the next user agent
        user_agent = active_agents[self.current_index]
        user_agent.last_used = time.time()
        
        logger.info(f"Rotated to user agent: {user_agent.browser_type.value} on {user_agent.os}")
        return user_agent
    
    def blacklist_user_agent(self, user_agent: UserAgentInfo) -> None:
        """
        Blacklist a user agent.
        
        Args:
            user_agent: User agent to blacklist
        """
        logger.info(f"Blacklisting user agent: {user_agent.browser_type.value} on {user_agent.os}")
        self.blacklisted_agents.add(user_agent.user_agent)
        user_agent.is_active = False
    
    def record_user_agent_success(self, user_agent: UserAgentInfo) -> None:
        """
        Record a successful user agent usage.
        
        Args:
            user_agent: User agent that was used successfully
        """
        if user_agent:
            user_agent.success_count += 1
            logger.debug(f"Recorded success for user agent: {user_agent.browser_type.value} on {user_agent.os}")
    
    def record_user_agent_failure(self, user_agent: UserAgentInfo) -> None:
        """
        Record a failed user agent usage.
        
        Args:
            user_agent: User agent that failed
        """
        if user_agent:
            user_agent.failure_count += 1
            logger.debug(f"Recorded failure for user agent: {user_agent.browser_type.value} on {user_agent.os}")
            
            # Check if user agent should be deactivated
            if user_agent.failure_count >= 3:
                logger.warning(f"User agent deactivated after {user_agent.failure_count} failures: {user_agent.browser_type.value} on {user_agent.os}")
                user_agent.is_active = False
    
    def get_user_agent_stats(self) -> Dict[str, Any]:
        """
        Get user agent statistics.
        
        Returns:
            Dictionary with user agent statistics
        """
        total = len(self.user_agents)
        active = len([ua for ua in self.user_agents if ua.is_active])
        blacklisted = len(self.blacklisted_agents)
        
        browser_types = {}
        device_types = {}
        
        for ua in self.user_agents:
            browser_type = ua.browser_type.value
            device_type = ua.device_type.value
            
            browser_types[browser_type] = browser_types.get(browser_type, 0) + 1
            device_types[device_type] = device_types.get(device_type, 0) + 1
        
        success_rates = [ua.success_rate for ua in self.user_agents if ua.success_count + ua.failure_count > 0]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        
        return {
            "total": total,
            "active": active,
            "blacklisted": blacklisted,
            "browser_types": browser_types,
            "device_types": device_types,
            "avg_success_rate": avg_success_rate
        }