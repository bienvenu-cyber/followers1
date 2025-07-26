"""
Error handling utilities and decorators for the Instagram auto signup system.
"""

import functools
import asyncio
from typing import Callable, Any, Optional, Type, Union, List
from datetime import datetime

from .exceptions import BaseInstagramSignupError, ErrorCategory
from .logging_config import get_logger


logger = get_logger(__name__)


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self):
        self.error_counts = {}
        self.last_errors = {}
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        recoverable: bool = True
    ) -> None:
        """Handle and log an error with context."""
        error_key = f"{type(error).__name__}:{context or 'general'}"
        
        # Update error counts
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_errors[error_key] = datetime.now()
        
        # Log the error
        if isinstance(error, BaseInstagramSignupError):
            error.timestamp = datetime.now()
            logger.error(
                f"Error in {context}: {error.message}",
                extra={
                    "error_details": error.to_dict(),
                    "error_count": self.error_counts[error_key]
                }
            )
        else:
            logger.error(
                f"Unexpected error in {context}: {str(error)}",
                extra={
                    "error_type": type(error).__name__,
                    "error_count": self.error_counts[error_key]
                },
                exc_info=True
            )
    
    def get_error_stats(self) -> dict:
        """Get error statistics."""
        return {
            "error_counts": self.error_counts.copy(),
            "last_errors": {k: v.isoformat() for k, v in self.last_errors.items()}
        }
    
    def should_retry(self, error: Exception, max_retries: int = 3) -> bool:
        """Determine if an operation should be retried based on error type and count."""
        if isinstance(error, BaseInstagramSignupError):
            if not error.recoverable:
                return False
        
        error_key = f"{type(error).__name__}:general"
        return self.error_counts.get(error_key, 0) < max_retries


# Global error handler instance
error_handler = ErrorHandler()


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], tuple] = Exception
):
    """Decorator to retry function on specific exceptions."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        error_handler.handle_error(e, f"{func.__name__}:retry_exhausted")
                        raise
                    
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {wait_time:.1f} seconds..."
                    )
                    await asyncio.sleep(wait_time)
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        error_handler.handle_error(e, f"{func.__name__}:retry_exhausted")
                        raise
                    
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {wait_time:.1f} seconds..."
                    )
                    import time
                    time.sleep(wait_time)
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def handle_errors(context: Optional[str] = None, reraise: bool = True):
    """Decorator to handle and log errors with context."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context or func.__name__)
                if reraise:
                    raise
                return None
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context or func.__name__)
                if reraise:
                    raise
                return None
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern implementation for error handling."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self) -> None:
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"