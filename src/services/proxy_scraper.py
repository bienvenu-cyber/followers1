"""
Proxy scraper - fetches free working proxies from multiple sources.
"""

import asyncio
import aiohttp
import logging
import random
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Proxy:
    ip: str
    port: int
    protocol: str = "http"
    country: str = ""
    speed: float = 0
    last_checked: float = 0
    working: bool = False


class ProxyScraper:
    """Scrapes and validates free proxies."""
    
    PROXY_SOURCES = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    ]
    
    def __init__(self):
        self.proxies: List[Proxy] = []
        self.working_proxies: List[Proxy] = []
        self.session = None
        self.current_index = 0
    
    async def initialize(self) -> bool:
        """Initialize proxy scraper."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        )
        
        # Fetch and validate proxies
        await self.fetch_proxies()
        await self.validate_proxies(max_proxies=50)
        
        logger.info(f"ProxyScraper initialized with {len(self.working_proxies)} working proxies")
        return len(self.working_proxies) > 0
    
    async def cleanup(self):
        if self.session:
            await self.session.close()
    
    async def fetch_proxies(self) -> int:
        """Fetch proxies from all sources."""
        all_proxies = set()
        
        for source in self.PROXY_SOURCES:
            try:
                async with self.session.get(source) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        lines = text.strip().split('\n')
                        
                        for line in lines:
                            line = line.strip()
                            if ':' in line:
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    ip = parts[0].strip()
                                    try:
                                        port = int(parts[1].strip())
                                        all_proxies.add((ip, port))
                                    except ValueError:
                                        continue
                        
                        logger.info(f"Fetched {len(lines)} proxies from {source[:50]}...")
                        
            except Exception as e:
                logger.warning(f"Error fetching from {source[:30]}: {e}")
        
        # Convert to Proxy objects
        self.proxies = [Proxy(ip=ip, port=port) for ip, port in all_proxies]
        logger.info(f"Total unique proxies fetched: {len(self.proxies)}")
        
        return len(self.proxies)
    
    async def validate_proxy(self, proxy: Proxy) -> bool:
        """Test if a proxy is working."""
        test_urls = [
            "http://httpbin.org/ip",
            "http://ip-api.com/json",
        ]
        
        proxy_url = f"http://{proxy.ip}:{proxy.port}"
        
        for test_url in test_urls:
            try:
                start = time.time()
                
                async with self.session.get(
                    test_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        proxy.speed = time.time() - start
                        proxy.working = True
                        proxy.last_checked = time.time()
                        return True
                        
            except Exception:
                continue
        
        proxy.working = False
        return False
    
    async def validate_proxies(self, max_proxies: int = 100) -> int:
        """Validate multiple proxies concurrently."""
        if not self.proxies:
            return 0
        
        # Shuffle and take sample
        sample = random.sample(self.proxies, min(max_proxies, len(self.proxies)))
        
        logger.info(f"Validating {len(sample)} proxies...")
        
        # Validate in batches
        batch_size = 20
        working = []
        
        for i in range(0, len(sample), batch_size):
            batch = sample[i:i+batch_size]
            tasks = [self.validate_proxy(p) for p in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for proxy, result in zip(batch, results):
                if result is True:
                    working.append(proxy)
                    logger.info(f"✅ Working proxy: {proxy.ip}:{proxy.port} ({proxy.speed:.2f}s)")
            
            # Stop if we have enough
            if len(working) >= 10:
                break
        
        # Sort by speed
        self.working_proxies = sorted(working, key=lambda p: p.speed)
        logger.info(f"Found {len(self.working_proxies)} working proxies")
        
        return len(self.working_proxies)
    
    def get_proxy(self) -> Optional[Dict]:
        """Get next working proxy."""
        if not self.working_proxies:
            return None
        
        proxy = self.working_proxies[self.current_index % len(self.working_proxies)]
        self.current_index += 1
        
        return {
            'ip': proxy.ip,
            'port': proxy.port,
            'url': f"http://{proxy.ip}:{proxy.port}",
            'protocol': proxy.protocol
        }
    
    def get_random_proxy(self) -> Optional[Dict]:
        """Get random working proxy."""
        if not self.working_proxies:
            return None
        
        proxy = random.choice(self.working_proxies)
        return {
            'ip': proxy.ip,
            'port': proxy.port,
            'url': f"http://{proxy.ip}:{proxy.port}",
            'protocol': proxy.protocol
        }
    
    def mark_proxy_failed(self, proxy_url: str):
        """Mark a proxy as failed and remove from working list."""
        for p in self.working_proxies:
            if f"{p.ip}:{p.port}" in proxy_url:
                p.working = False
                self.working_proxies.remove(p)
                logger.info(f"Removed failed proxy: {p.ip}:{p.port}")
                break
    
    async def refresh_proxies(self):
        """Refresh proxy list."""
        await self.fetch_proxies()
        await self.validate_proxies()
