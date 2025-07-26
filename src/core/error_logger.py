"""
Comprehensive error logging system with context capture and categorization.
"""

import functools
import traceback
import inspect
import sys
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime

from .error_analyzer import log_detailed_error, get_error_analyzer
from .logging_config import get_logger
from .statistics_manager import get_statistics_manager


logger = get_logger(__name__)


class ErrorLogger:
    """Enhanced error logger with context capture."""
    
    def __init__(self):
        self.error_analyzer = get_error_analyzer()
        self.stats_manager = get_statistics_manager()
        self.context_stack: List[Dict[str, Any]] = []
    
    def push_context(self, **context) -> None:
        """Push context information onto the stack."""
        self.context_stack.append(context)
    
    def pop_context(self) -> Optional[Dict[str, Any]]:
        """Pop context information from the stack."""
        return self.context_stack.pop() if self.context_stack else None
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get the current context by merging all stack levels."""
        result = {}
        for context in self.context_stack:
            result.update(context)
        return result
    
    def log_error(
        self,
        component: str,
        operation: str,
        error: Exception,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log an error with full context capture."""
        # Get current context
        context = self.get_current_context()
        if additional_context:
            context.update(additional_context)
        
        # Extract error information
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # Determine attempt number from context
        attempt_number = context.get('attempt_number', 1)
        
        # Get cycle ID from stats manager
        cycle_id = None
        if self.stats_manager.current_cycle:
            cycle_id = self.stats_manager.current_cycle.cycle_id
        
        # Log the detailed error
        pattern_id = log_detailed_error(
            component=component,
            operation=operation,
            error_type=error_type,
            error_message=error_message,
            traceback=error_traceback,
            account_data=context.get('account_data'),
            browser_info=context.get('browser_info'),
            proxy_info=context.get('proxy_info'),
            email_service=context.get('email_service'),
            attempt_number=attempt_number,
            cycle_id=cycle_id,
            additional_data=context
        )
        
        # Update statistics
        self.stats_manager.record_attempt(False, 0.0, error_type)
        
        # Log to standard logger as well
        logger.error(
            f"Error in {component}.{operation}: {error_message}",
            extra={
                'component': component,
                'operation': operation,
                'error_type': error_type,
                'pattern_id': pattern_id,
                'attempt_number': attempt_number,
                'cycle_id': cycle_id
            },
            exc_info=True
        )
        
        return pattern_id


# Global error logger instance
error_logger = ErrorLogger()


def get_error_logger() -> ErrorLogger:
    """Get the global error logger instance."""
    return error_logger


def with_error_logging(
    component: str,
    operation: Optional[str] = None,
    reraise: bool = True,
    return_on_error: Any = None
):
    """Decorator to automatically log errors with context."""
    
    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error
                error_logger.log_error(component, op_name, e)
                
                if reraise:
                    raise
                else:
                    return return_on_error
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log the error
                error_logger.log_error(component, op_name, e)
                
                if reraise:
                    raise
                else:
                    return return_on_error
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


class ErrorContext:
    """Context manager for error logging context."""
    
    def __init__(self, **context):
        self.context = context
        self.error_logger = get_error_logger()
    
    def __enter__(self):
        self.error_logger.push_context(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.error_logger.pop_context()
        
        # If an exception occurred, log it
        if exc_type is not None:
            component = self.context.get('component', 'unknown')
            operation = self.context.get('operation', 'unknown')
            self.error_logger.log_error(component, operation, exc_val)
        
        # Don't suppress the exception
        return False


def categorize_error(error: Exception) -> Dict[str, str]:
    """Categorize an error and provide suggested actions."""
    error_type = type(error).__name__
    error_message = str(error).lower()
    
    # Network-related errors
    if any(keyword in error_message for keyword in ['timeout', 'connection', 'network', 'dns']):
        return {
            'category': 'network',
            'severity': 'medium',
            'suggested_action': 'Check network connectivity and proxy configuration'
        }
    
    # Browser/Selenium errors
    elif any(keyword in error_message for keyword in ['element', 'selenium', 'webdriver', 'browser']):
        return {
            'category': 'browser',
            'severity': 'high',
            'suggested_action': 'Update element selectors or restart browser instance'
        }
    
    # Instagram-specific errors
    elif any(keyword in error_message for keyword in ['captcha', 'blocked', 'banned', 'rate limit']):
        return {
            'category': 'instagram_defense',
            'severity': 'high',
            'suggested_action': 'Enhance anti-detection measures and reduce frequency'
        }
    
    # Email service errors
    elif any(keyword in error_message for keyword in ['email', 'verification', 'code']):
        return {
            'category': 'email_service',
            'severity': 'medium',
            'suggested_action': 'Switch to alternative email service or check service status'
        }
    
    # Proxy errors
    elif any(keyword in error_message for keyword in ['proxy', 'forbidden', '403', '407']):
        return {
            'category': 'proxy',
            'severity': 'medium',
            'suggested_action': 'Rotate proxy or check proxy validity'
        }
    
    # Data/validation errors
    elif any(keyword in error_message for keyword in ['validation', 'invalid', 'format']):
        return {
            'category': 'data_validation',
            'severity': 'low',
            'suggested_action': 'Check data generation logic and validation rules'
        }
    
    # Default category
    else:
        return {
            'category': 'unknown',
            'severity': 'medium',
            'suggested_action': 'Review error details and implement specific handling'
        }


def get_error_summary() -> Dict[str, Any]:
    """Get a summary of recent errors and patterns."""
    analyzer = get_error_analyzer()
    
    # Get error patterns
    patterns = analyzer.get_error_patterns(min_occurrences=2)
    
    # Get component error stats
    component_stats = analyzer.get_component_error_stats()
    
    # Get error trend
    error_trend = analyzer.get_error_trend(hours=24)
    
    # Get insights
    insights = analyzer.analyze_error_patterns()
    
    return {
        'patterns': patterns[:10],  # Top 10 patterns
        'component_stats': component_stats,
        'error_trend': error_trend,
        'insights': insights,
        'total_patterns': len(patterns),
        'timestamp': datetime.now().isoformat()
    }


def export_error_report(file_path: str) -> bool:
    """Export a comprehensive error report."""
    try:
        analyzer = get_error_analyzer()
        summary = get_error_summary()
        
        # Add detailed patterns
        detailed_patterns = []
        for pattern in summary['patterns']:
            details = analyzer.get_error_details(pattern['pattern_id'])
            if details:
                detailed_patterns.append(details)
        
        report = {
            'report_generated': datetime.now().isoformat(),
            'summary': summary,
            'detailed_patterns': detailed_patterns
        }
        
        import json
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Error report exported to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export error report: {e}")
        return False