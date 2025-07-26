"""
Element selector module for the Instagram auto signup system.

This module provides functionality for finding and interacting with web elements
in a reliable way, with fallback mechanisms and adaptive selection strategies.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    StaleElementReferenceException,
    ElementNotInteractableException
)

logger = logging.getLogger(__name__)


class ElementSelector:
    """Element selector for finding and interacting with web elements."""
    
    def __init__(self):
        """Initialize the element selector."""
        self.selector_strategies = [
            (By.ID, "id"),
            (By.NAME, "name"),
            (By.XPATH, "xpath"),
            (By.CSS_SELECTOR, "css"),
            (By.CLASS_NAME, "class"),
            (By.TAG_NAME, "tag"),
            (By.LINK_TEXT, "link"),
            (By.PARTIAL_LINK_TEXT, "partial_link")
        ]
        self.successful_selectors = {}
        self.failed_selectors = {}
    
    async def initialize(self) -> bool:
        """Initialize the element selector."""
        logger.info("Initializing element selector...")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    async def wait_and_find_element(
        self, 
        driver: WebDriver, 
        by: By, 
        selector: str, 
        timeout: int = 10
    ) -> Optional[WebElement]:
        """
        Wait for an element to be present and return it.
        
        Args:
            driver: WebDriver instance
            by: Selector type (By.ID, By.XPATH, etc.)
            selector: Selector value
            timeout: Maximum time to wait in seconds
            
        Returns:
            WebElement if found, None otherwise
        """
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            
            # Record successful selector
            key = f"{by}:{selector}"
            self.successful_selectors[key] = self.successful_selectors.get(key, 0) + 1
            
            return element
        except (TimeoutException, NoSuchElementException) as e:
            # Record failed selector
            key = f"{by}:{selector}"
            self.failed_selectors[key] = self.failed_selectors.get(key, 0) + 1
            
            logger.warning(f"Element not found: {by}={selector}, error: {e}")
            return None
    
    async def wait_and_find_elements(
        self, 
        driver: WebDriver, 
        by: By, 
        selector: str, 
        timeout: int = 10
    ) -> List[WebElement]:
        """
        Wait for elements to be present and return them.
        
        Args:
            driver: WebDriver instance
            by: Selector type (By.ID, By.XPATH, etc.)
            selector: Selector value
            timeout: Maximum time to wait in seconds
            
        Returns:
            List of WebElements if found, empty list otherwise
        """
        try:
            elements = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((by, selector))
            )
            
            # Record successful selector
            key = f"{by}:{selector}"
            self.successful_selectors[key] = self.successful_selectors.get(key, 0) + 1
            
            return elements
        except (TimeoutException, NoSuchElementException) as e:
            # Record failed selector
            key = f"{by}:{selector}"
            self.failed_selectors[key] = self.failed_selectors.get(key, 0) + 1
            
            logger.warning(f"Elements not found: {by}={selector}, error: {e}")
            return []
    
    async def wait_and_find_clickable_element(
        self, 
        driver: WebDriver, 
        by: By, 
        selector: str, 
        timeout: int = 10
    ) -> Optional[WebElement]:
        """
        Wait for an element to be clickable and return it.
        
        Args:
            driver: WebDriver instance
            by: Selector type (By.ID, By.XPATH, etc.)
            selector: Selector value
            timeout: Maximum time to wait in seconds
            
        Returns:
            WebElement if found and clickable, None otherwise
        """
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            
            # Record successful selector
            key = f"{by}:{selector}"
            self.successful_selectors[key] = self.successful_selectors.get(key, 0) + 1
            
            return element
        except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
            # Record failed selector
            key = f"{by}:{selector}"
            self.failed_selectors[key] = self.failed_selectors.get(key, 0) + 1
            
            logger.warning(f"Clickable element not found: {by}={selector}, error: {e}")
            return None
    
    async def find_element_with_fallback(
        self, 
        driver: WebDriver, 
        selectors: List[Tuple[By, str]], 
        timeout: int = 10
    ) -> Optional[WebElement]:
        """
        Try multiple selectors until an element is found.
        
        Args:
            driver: WebDriver instance
            selectors: List of (By, selector) tuples
            timeout: Maximum time to wait in seconds per selector
            
        Returns:
            WebElement if found, None otherwise
        """
        for by, selector in selectors:
            element = await self.wait_and_find_element(driver, by, selector, timeout)
            if element:
                return element
        
        logger.warning(f"Element not found with any of the provided selectors")
        return None
    
    async def find_element_by_text(
        self, 
        driver: WebDriver, 
        text: str, 
        tag: str = "*", 
        timeout: int = 10
    ) -> Optional[WebElement]:
        """
        Find an element by its text content.
        
        Args:
            driver: WebDriver instance
            text: Text to search for
            tag: HTML tag to limit the search to
            timeout: Maximum time to wait in seconds
            
        Returns:
            WebElement if found, None otherwise
        """
        xpath = f"//{tag}[contains(text(), '{text}')]"
        return await self.wait_and_find_element(driver, By.XPATH, xpath, timeout)
    
    async def wait_for_element_to_disappear(
        self, 
        driver: WebDriver, 
        by: By, 
        selector: str, 
        timeout: int = 10
    ) -> bool:
        """
        Wait for an element to disappear from the page.
        
        Args:
            driver: WebDriver instance
            by: Selector type (By.ID, By.XPATH, etc.)
            selector: Selector value
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if element disappeared, False otherwise
        """
        try:
            WebDriverWait(driver, timeout).until_not(
                EC.presence_of_element_located((by, selector))
            )
            return True
        except TimeoutException:
            logger.warning(f"Element did not disappear: {by}={selector}")
            return False
    
    async def wait_for_page_load(
        self, 
        driver: WebDriver, 
        timeout: int = 30
    ) -> bool:
        """
        Wait for page to finish loading.
        
        Args:
            driver: WebDriver instance
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if page loaded, False otherwise
        """
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            logger.warning("Page did not finish loading within timeout")
            return False
    
    async def get_element_text(
        self, 
        driver: WebDriver, 
        by: By, 
        selector: str, 
        timeout: int = 10
    ) -> Optional[str]:
        """
        Get text from an element.
        
        Args:
            driver: WebDriver instance
            by: Selector type (By.ID, By.XPATH, etc.)
            selector: Selector value
            timeout: Maximum time to wait in seconds
            
        Returns:
            Element text if found, None otherwise
        """
        element = await self.wait_and_find_element(driver, by, selector, timeout)
        if element:
            return element.text
        return None
    
    async def is_element_present(
        self, 
        driver: WebDriver, 
        by: By, 
        selector: str, 
        timeout: int = 5
    ) -> bool:
        """
        Check if an element is present on the page.
        
        Args:
            driver: WebDriver instance
            by: Selector type (By.ID, By.XPATH, etc.)
            selector: Selector value
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if element is present, False otherwise
        """
        element = await self.wait_and_find_element(driver, by, selector, timeout)
        return element is not None
    
    async def get_selector_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about selector usage.
        
        Returns:
            Dictionary with successful and failed selectors
        """
        return {
            "successful": self.successful_selectors,
            "failed": self.failed_selectors
        }
    
    async def clear_statistics(self) -> None:
        """Clear selector statistics."""
        self.successful_selectors = {}
        self.failed_selectors = {}