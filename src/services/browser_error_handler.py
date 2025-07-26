"""
Browser error handler module for the Instagram auto signup system.

This module provides functionality for handling browser errors, crashes,
timeouts, and other issues that may occur during browser automation.
"""

import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    JavascriptException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    NoSuchWindowException,
    SessionNotCreatedException
)

logger = logging.getLogger(__name__)


class BrowserErrorHandler:
    """Handler for browser errors and issues."""
    
    def __init__(self):
        """Initialize the browser error handler."""
        self.error_counts = {}
        self.error_patterns = {}
        self.recovery_attempts = {}
        self.max_recovery_attempts = 3
    
    async def initialize(self) -> bool:
        """Initialize the browser error handler."""
        logger.info("Initializing browser error handler...")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    async def handle_error(
        self, 
        driver: Optional[WebDriver], 
        error: Exception, 
        context: str = ""
    ) -> Tuple[bool, str]:
        """
        Handle a browser error.
        
        Args:
            driver: WebDriver instance (may be None if browser creation failed)
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Log the error
        logger.error(f"Browser error in {context}: {error_type} - {error_message}")
        
        # Update error counts
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Check if we've exceeded recovery attempts
        context_key = f"{context}:{error_type}"
        attempts = self.recovery_attempts.get(context_key, 0)
        
        if attempts >= self.max_recovery_attempts:
            logger.warning(f"Exceeded maximum recovery attempts for {context_key}")
            return False, error_type
        
        # Increment recovery attempts
        self.recovery_attempts[context_key] = attempts + 1
        
        # Handle specific error types
        if isinstance(error, SessionNotCreatedException):
            return await self._handle_session_creation_error(driver, error, context)
        elif isinstance(error, TimeoutException):
            return await self._handle_timeout_error(driver, error, context)
        elif isinstance(error, NoSuchElementException):
            return await self._handle_missing_element_error(driver, error, context)
        elif isinstance(error, StaleElementReferenceException):
            return await self._handle_stale_element_error(driver, error, context)
        elif isinstance(error, ElementNotInteractableException):
            return await self._handle_element_interaction_error(driver, error, context)
        elif isinstance(error, ElementClickInterceptedException):
            return await self._handle_click_intercepted_error(driver, error, context)
        elif isinstance(error, UnexpectedAlertPresentException):
            return await self._handle_alert_error(driver, error, context)
        elif isinstance(error, NoSuchWindowException):
            return await self._handle_window_error(driver, error, context)
        else:
            return await self._handle_generic_error(driver, error, context)
    
    async def _handle_session_creation_error(
        self, 
        driver: Optional[WebDriver], 
        error: SessionNotCreatedException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle session creation errors.
        
        Args:
            driver: WebDriver instance (may be None)
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.error(f"Failed to create browser session: {error}")
        
        # Check for common issues in the error message
        error_message = str(error).lower()
        
        if "chrome not reachable" in error_message:
            logger.info("Chrome not reachable - browser may have crashed")
            return False, "BROWSER_CRASHED"
        elif "chrome version" in error_message:
            logger.info("Chrome version mismatch - driver may be incompatible")
            return False, "DRIVER_INCOMPATIBLE"
        elif "permission" in error_message:
            logger.info("Permission issue - check browser executable permissions")
            return False, "PERMISSION_ERROR"
        
        return False, "SESSION_CREATION_FAILED"
    
    async def _handle_timeout_error(
        self, 
        driver: Optional[WebDriver], 
        error: TimeoutException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle timeout errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.warning(f"Timeout in {context}: {error}")
        
        if driver:
            # Try to refresh the page
            try:
                driver.refresh()
                logger.info("Page refreshed after timeout")
                return True, "TIMEOUT_RECOVERED"
            except Exception as refresh_error:
                logger.error(f"Failed to refresh page: {refresh_error}")
        
        return False, "TIMEOUT"
    
    async def _handle_missing_element_error(
        self, 
        driver: Optional[WebDriver], 
        error: NoSuchElementException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle missing element errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.warning(f"Missing element in {context}: {error}")
        
        # Wait a moment and try again
        if driver:
            time.sleep(2)
            return True, "ELEMENT_NOT_FOUND"
        
        return False, "ELEMENT_NOT_FOUND"
    
    async def _handle_stale_element_error(
        self, 
        driver: Optional[WebDriver], 
        error: StaleElementReferenceException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle stale element errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.warning(f"Stale element in {context}: {error}")
        
        # Wait a moment for the page to stabilize
        if driver:
            time.sleep(1)
            return True, "STALE_ELEMENT"
        
        return False, "STALE_ELEMENT"
    
    async def _handle_element_interaction_error(
        self, 
        driver: Optional[WebDriver], 
        error: ElementNotInteractableException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle element interaction errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.warning(f"Element not interactable in {context}: {error}")
        
        if driver:
            # Try to scroll the element into view
            try:
                element_id = str(error).split("element-")[-1].split(" ")[0]
                script = f"arguments[0].scrollIntoView({{behavior: 'smooth', block: 'center'}});"
                driver.execute_script(script, driver.find_element_by_id(element_id))
                logger.info("Scrolled element into view")
                time.sleep(1)
                return True, "ELEMENT_NOT_INTERACTABLE"
            except Exception as scroll_error:
                logger.error(f"Failed to scroll element into view: {scroll_error}")
        
        return False, "ELEMENT_NOT_INTERACTABLE"
    
    async def _handle_click_intercepted_error(
        self, 
        driver: Optional[WebDriver], 
        error: ElementClickInterceptedException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle click intercepted errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.warning(f"Click intercepted in {context}: {error}")
        
        if driver:
            # Try to use JavaScript to click the element
            try:
                element_id = str(error).split("element-")[-1].split(" ")[0]
                script = "arguments[0].click();"
                driver.execute_script(script, driver.find_element_by_id(element_id))
                logger.info("Clicked element using JavaScript")
                return True, "CLICK_INTERCEPTED"
            except Exception as js_error:
                logger.error(f"Failed to click element using JavaScript: {js_error}")
        
        return False, "CLICK_INTERCEPTED"
    
    async def _handle_alert_error(
        self, 
        driver: Optional[WebDriver], 
        error: UnexpectedAlertPresentException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle alert errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.warning(f"Unexpected alert in {context}: {error}")
        
        if driver:
            # Try to dismiss the alert
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                logger.info(f"Alert text: {alert_text}")
                alert.dismiss()
                logger.info("Alert dismissed")
                return True, "ALERT_DISMISSED"
            except NoAlertPresentException:
                logger.info("Alert no longer present")
                return True, "ALERT_GONE"
            except Exception as alert_error:
                logger.error(f"Failed to handle alert: {alert_error}")
        
        return False, "UNEXPECTED_ALERT"
    
    async def _handle_window_error(
        self, 
        driver: Optional[WebDriver], 
        error: NoSuchWindowException, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle window errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        logger.warning(f"Window error in {context}: {error}")
        
        if driver:
            # Try to switch to the main window
            try:
                windows = driver.window_handles
                if windows:
                    driver.switch_to.window(windows[0])
                    logger.info("Switched to main window")
                    return True, "WINDOW_SWITCHED"
            except Exception as window_error:
                logger.error(f"Failed to switch window: {window_error}")
        
        return False, "NO_SUCH_WINDOW"
    
    async def _handle_generic_error(
        self, 
        driver: Optional[WebDriver], 
        error: Exception, 
        context: str
    ) -> Tuple[bool, str]:
        """
        Handle generic errors.
        
        Args:
            driver: WebDriver instance
            error: Exception that occurred
            context: Context in which the error occurred
            
        Returns:
            Tuple of (success, error_type)
        """
        error_type = type(error).__name__
        logger.error(f"Generic error in {context}: {error_type} - {error}")
        
        # For generic errors, we usually can't recover
        return False, error_type
    
    async def get_error_statistics(self) -> Dict[str, int]:
        """
        Get statistics about errors.
        
        Returns:
            Dictionary with error counts by type
        """
        return self.error_counts
    
    async def clear_statistics(self) -> None:
        """Clear error statistics."""
        self.error_counts = {}
        self.recovery_attempts = {}