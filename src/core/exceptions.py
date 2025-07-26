"""
Custom exceptions and error handling framework for the Instagram auto signup system.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors for better classification."""
    BROWSER_ERROR = "browser_error"
    EMAIL_SERVICE_ERROR = "email_service_error"
    PROXY_ERROR = "proxy_error"
    INSTAGRAM_ERROR = "instagram_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"


class BaseInstagramSignupError(Exception):
    """Base exception class for Instagram signup system."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp
        }


class BrowserError(BaseInstagramSignupError):
    """Errors related to browser automation."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.BROWSER_ERROR, details)


class ElementNotFoundError(BrowserError):
    """Error when a required element is not found on the page."""
    
    def __init__(self, selector: str, page_url: str = ""):
        message = f"Element not found: {selector}"
        details = {"selector": selector, "page_url": page_url}
        super().__init__(message, details)


class CaptchaDetectedError(BrowserError):
    """Error when CAPTCHA is detected."""
    
    def __init__(self, captcha_type: str = "unknown"):
        message = f"CAPTCHA detected: {captcha_type}"
        details = {"captcha_type": captcha_type}
        super().__init__(message, details)


class EmailServiceError(BaseInstagramSignupError):
    """Errors related to email services."""
    
    def __init__(self, message: str, service_name: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["service_name"] = service_name
        super().__init__(message, ErrorCategory.EMAIL_SERVICE_ERROR, details)


class EmailTimeoutError(EmailServiceError):
    """Error when email verification times out."""
    
    def __init__(self, service_name: str, timeout_seconds: int):
        message = f"Email verification timeout after {timeout_seconds} seconds"
        details = {"timeout_seconds": timeout_seconds}
        super().__init__(message, service_name, details)


class VerificationCodeNotFoundError(EmailServiceError):
    """Error when verification code cannot be extracted from email."""
    
    def __init__(self, service_name: str, email_content: str = ""):
        message = "Verification code not found in email"
        details = {"email_content": email_content[:200]}  # Truncate for logging
        super().__init__(message, service_name, details)


class ProxyError(BaseInstagramSignupError):
    """Errors related to proxy usage."""
    
    def __init__(self, message: str, proxy_config: Optional[Dict[str, Any]] = None):
        details = {"proxy_config": proxy_config} if proxy_config else {}
        super().__init__(message, ErrorCategory.PROXY_ERROR, details)


class ProxyConnectionError(ProxyError):
    """Error when proxy connection fails."""
    
    def __init__(self, proxy_config: Dict[str, Any]):
        message = f"Failed to connect through proxy: {proxy_config.get('ip', 'unknown')}"
        super().__init__(message, proxy_config)


class InstagramError(BaseInstagramSignupError):
    """Errors specific to Instagram interactions."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.INSTAGRAM_ERROR, details)


class AccountCreationBlockedError(InstagramError):
    """Error when Instagram blocks account creation."""
    
    def __init__(self, reason: str = "unknown"):
        message = f"Account creation blocked by Instagram: {reason}"
        details = {"block_reason": reason}
        super().__init__(message, details)
        self.recoverable = False  # Usually not recoverable immediately


class RateLimitError(InstagramError):
    """Error when Instagram rate limits are hit."""
    
    def __init__(self, retry_after: Optional[int] = None):
        message = "Instagram rate limit exceeded"
        details = {"retry_after": retry_after}
        super().__init__(message, details)


class ConfigurationError(BaseInstagramSignupError):
    """Errors related to configuration."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, ErrorCategory.CONFIGURATION_ERROR, details)
        self.recoverable = False  # Configuration errors usually need manual fix


class ValidationError(BaseInstagramSignupError):
    """Errors related to data validation."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, field_value: Any = None):
        details = {}
        if field_name:
            details["field_name"] = field_name
        if field_value is not None:
            details["field_value"] = str(field_value)
        super().__init__(message, ErrorCategory.VALIDATION_ERROR, details)


class NetworkError(BaseInstagramSignupError):
    """Errors related to network connectivity."""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None):
        details = {}
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, ErrorCategory.NETWORK_ERROR, details)