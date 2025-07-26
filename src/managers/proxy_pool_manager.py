"""
Proxy pool manager module for the Instagram auto signup system.

This module provides functionality for managing a pool of proxy servers,
including validation, rotation, and performance tracking.
"""

import logging
import time
import random
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Proxy configuration data class."""
    ip: str
    port: int
    type: str = "http"
    username: str = ""
    password: str = ""
    last_used: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    is_active: bool = True
    
    @property
    def url(self) -> str:
        """Get proxy URL."""
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        return f"{self.type}://{auth}{self.ip}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total


class ProxyPoolManager(ResourceManager):
    """Manager for proxy server pool."""
    
    def __init__(self):
        """Initialize the proxy pool manager."""
        super().__init__("ProxyPoolManager")
        self.proxies: List[ProxyConfig] = []
        self.current_proxy_index = 0
        self.test_urls = [
            "https://www.google.com",
            "https://www.instagram.com",
            "https://www.facebook.com"
        ]
        self.validation_timeout = 10
        self.rotation_threshold = 10
        self.blacklisted_ips = set()
        logger.info(f"Initialized ProxyPoolManager with {len(self.test_urls)} test URLs")
    
    async def initialize(self) -> bool:
        """Initialize the proxy pool manager."""
        logger.info("Initializing proxy pool manager...")
        
        # Load proxies from configuration
        from ..core.config import config_manager
        config = config_manager.get_config()
        
        if hasattr(config, "proxies") and config.proxies:
            for proxy_data in config.proxies:
                proxy = ProxyConfig(
                    ip=proxy_data.get("ip", ""),
                    port=proxy_data.get("port", 0),
                    type=proxy_data.get("type", "http"),
                    username=proxy_data.get("username", ""),
                    password=proxy_data.get("password", "")
                )
                self.proxies.append(proxy)
            
            logger.info(f"Loaded {len(self.proxies)} proxies from configuration")
            
            # Validate proxies
            await self.validate_all_proxies()
            
            return True
        else:
            logger.warning("No proxies configured")
            return True  # Return True even if no proxies, as this is not a critical error
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    async def validate_proxy(self, proxy: ProxyConfig) -> bool:
        """
        Validate a proxy by testing connectivity.
        
        Args:
            proxy: Proxy configuration to validate
            
        Returns:
            True if proxy is valid, False otherwise
        """
        if proxy.ip in self.blacklisted_ips:
            logger.warning(f"Proxy {proxy.ip}:{proxy.port} is blacklisted")
            return False
        
        # Test connectivity to test URLs
        success = False
        
        for url in self.test_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    proxy_url = proxy.url
                    start_time = time.time()
                    
                    async with session.get(
                        url,
                        proxy=proxy_url,
                        timeout=self.validation_timeout
                    ) as response:
                        elapsed = time.time() - start_time
                        
                        if response.status == 200:
                            logger.info(f"Proxy {proxy.ip}:{proxy.port} successfully connected to {url} in {elapsed:.2f}s")
                            success = True
                            break
                        else:
                            logger.warning(f"Proxy {proxy.ip}:{proxy.port} returned status {response.status} for {url}")
                
            except asyncio.TimeoutError:
                logger.warning(f"Proxy {proxy.ip}:{proxy.port} timed out connecting to {url}")
            except Exception as e:
                logger.warning(f"Proxy {proxy.ip}:{proxy.port} error connecting to {url}: {e}")
        
        # Update proxy status
        if success:
            proxy.success_count += 1
            proxy.is_active = True
        else:
            proxy.failure_count += 1
            if proxy.failure_count >= 3:
                logger.warning(f"Proxy {proxy.ip}:{proxy.port} marked as inactive after {proxy.failure_count} failures")
                proxy.is_active = False
        
        return success
    
    async def validate_all_proxies(self) -> Tuple[int, int]:
        """
        Validate all proxies in the pool.
        
        Returns:
            Tuple of (valid_count, total_count)
        """
        valid_count = 0
        total_count = len(self.proxies)
        
        if total_count == 0:
            logger.warning("No proxies to validate")
            return 0, 0
        
        logger.info(f"Validating {total_count} proxies...")
        
        # Validate each proxy
        for proxy in self.proxies:
            if await self.validate_proxy(proxy):
                valid_count += 1
        
        logger.info(f"Proxy validation complete: {valid_count}/{total_count} valid")
        return valid_count, total_count
    
    def get_proxy(self) -> Optional[ProxyConfig]:
        """
        Get the next proxy from the pool.
        
        Returns:
            ProxyConfig if available, None otherwise
        """
        if not self.proxies:
            logger.warning("No proxies available")
            return None
        
        # Find active proxies
        active_proxies = [p for p in self.proxies if p.is_active]
        if not active_proxies:
            logger.warning("No active proxies available")
            return None
        
        # Sort by success rate and last used time
        sorted_proxies = sorted(
            active_proxies,
            key=lambda p: (p.success_rate, -p.last_used)
        )
        
        # Get the best proxy
        proxy = sorted_proxies[-1]
        proxy.last_used = time.time()
        
        logger.info(f"Selected proxy {proxy.ip}:{proxy.port} with success rate {proxy.success_rate:.2f}")
        return proxy
    
    def rotate_proxy(self) -> Optional[ProxyConfig]:
        """
        Rotate to the next proxy in the pool.
        
        Returns:
            ProxyConfig if available, None otherwise
        """
        if not self.proxies:
            logger.warning("No proxies available for rotation")
            return None
        
        # Find active proxies
        active_proxies = [p for p in self.proxies if p.is_active]
        if not active_proxies:
            logger.warning("No active proxies available for rotation")
            return None
        
        # Increment index
        self.current_proxy_index = (self.current_proxy_index + 1) % len(active_proxies)
        
        # Get the next proxy
        proxy = active_proxies[self.current_proxy_index]
        proxy.last_used = time.time()
        
        logger.info(f"Rotated to proxy {proxy.ip}:{proxy.port}")
        return proxy
    
    def blacklist_proxy(self, proxy: ProxyConfig) -> None:
        """
        Blacklist a proxy.
        
        Args:
            proxy: Proxy to blacklist
        """
        logger.info(f"Blacklisting proxy {proxy.ip}:{proxy.port}")
        self.blacklisted_ips.add(proxy.ip)
        proxy.is_active = False
    
    def record_proxy_success(self, proxy: ProxyConfig) -> None:
        """
        Record a successful proxy usage.
        
        Args:
            proxy: Proxy that was used successfully
        """
        if proxy:
            proxy.success_count += 1
            logger.debug(f"Recorded success for proxy {proxy.ip}:{proxy.port}")
    
    def record_proxy_failure(self, proxy: ProxyConfig) -> None:
        """
        Record a failed proxy usage.
        
        Args:
            proxy: Proxy that failed
        """
        if proxy:
            proxy.failure_count += 1
            logger.debug(f"Recorded failure for proxy {proxy.ip}:{proxy.port}")
            
            # Check if proxy should be deactivated
            if proxy.failure_count >= self.rotation_threshold:
                logger.warning(f"Proxy {proxy.ip}:{proxy.port} deactivated after {proxy.failure_count} failures")
                proxy.is_active = False
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """
        Get proxy statistics.
        
        Returns:
            Dictionary with proxy statistics
        """
        total = len(self.proxies)
        active = len([p for p in self.proxies if p.is_active])
        blacklisted = len(self.blacklisted_ips)
        
        success_rates = [p.success_rate for p in self.proxies if p.success_count + p.failure_count > 0]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        
        return {
            "total": total,
            "active": active,
            "blacklisted": blacklisted,
            "avg_success_rate": avg_success_rate
        }