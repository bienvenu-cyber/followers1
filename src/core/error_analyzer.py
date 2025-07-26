"""
Advanced error analysis and pattern recognition for the Instagram auto signup system.
"""

import re
import json
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
import threading

from .logging_config import get_logger
from .statistics_manager import get_statistics_manager


logger = get_logger(__name__)


@dataclass
class ErrorContext:
    """Context information for an error."""
    component: str
    operation: str
    timestamp: datetime
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    account_data: Optional[Dict[str, Any]] = None
    browser_info: Optional[Dict[str, Any]] = None
    proxy_info: Optional[Dict[str, Any]] = None
    email_service: Optional[str] = None
    attempt_number: int = 1
    cycle_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@
dataclass
class ErrorPattern:
    """Pattern of recurring errors."""
    pattern_id: str
    error_type: str
    component: str
    occurrences: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    contexts: List[Dict[str, Any]] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)
    
    def add_occurrence(self, context: ErrorContext) -> None:
        """Add an occurrence of this error pattern."""
        self.occurrences += 1
        self.last_seen = context.timestamp
        if self.first_seen is None:
            self.first_seen = context.timestamp
        
        # Keep only the last 10 contexts to avoid memory issues
        if len(self.contexts) >= 10:
            self.contexts.pop(0)
        
        self.contexts.append(context.to_dict())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            'pattern_id': self.pattern_id,
            'error_type': self.error_type,
            'component': self.component,
            'occurrences': self.occurrences,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'contexts': self.contexts[:5],  # Include only the last 5 contexts
            'related_patterns': self.related_patterns
        }
        return result

cl
ass ErrorAnalyzer:
    """Advanced error analysis and pattern recognition system."""
    
    def __init__(self, error_log_path: str = "logs/detailed_errors.json"):
        self.error_log_path = error_log_path
        self.errors: List[ErrorContext] = []
        self.patterns: Dict[str, ErrorPattern] = {}
        self.component_errors: Dict[str, int] = defaultdict(int)
        self.error_type_counts: Dict[str, int] = defaultdict(int)
        self.hourly_error_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self._max_errors = 1000  # Maximum number of errors to keep in memory
        self._pattern_threshold = 3  # Minimum occurrences to consider a pattern
        self._stats_manager = get_statistics_manager()
    
    def log_error(self, context: ErrorContext) -> str:
        """Log an error with its context and analyze patterns."""
        with self._lock:
            # Add to errors list
            self.errors.append(context)
            
            # Trim errors list if needed
            if len(self.errors) > self._max_errors:
                self.errors = self.errors[-self._max_errors:]
            
            # Update statistics
            self.component_errors[context.component] += 1
            self.error_type_counts[context.error_type] += 1
            
            # Update hourly stats
            hour_key = context.timestamp.strftime("%Y-%m-%d %H:00")
            self.hourly_error_counts[hour_key] += 1
            
            # Generate pattern ID
            pattern_id = self._generate_pattern_id(context)
            
            # Update or create pattern
            if pattern_id in self.patterns:
                self.patterns[pattern_id].add_occurrence(context)
            else:
                self.patterns[pattern_id] = ErrorPattern(
                    pattern_id=pattern_id,
                    error_type=context.error_type,
                    component=context.component
                )
                self.patterns[pattern_id].add_occurrence(context)
            
            # Find related patterns
            self._update_related_patterns(pattern_id, context)
            
            # Save to log file
            self._save_error_to_log(context)
            
            # Return pattern ID
            return pattern_id  
  
    def _generate_pattern_id(self, context: ErrorContext) -> str:
        """Generate a pattern ID for an error context."""
        # Basic pattern: component + error_type
        pattern = f"{context.component}:{context.error_type}"
        
        # Add operation for more specificity
        if context.operation:
            pattern += f":{context.operation}"
        
        # Add proxy type if available
        if context.proxy_info and 'type' in context.proxy_info:
            pattern += f":proxy_{context.proxy_info['type']}"
        
        # Add email service if available
        if context.email_service:
            pattern += f":email_{context.email_service}"
        
        return pattern
    
    def _update_related_patterns(self, pattern_id: str, context: ErrorContext) -> None:
        """Find and update related error patterns."""
        if pattern_id not in self.patterns:
            return
        
        current_pattern = self.patterns[pattern_id]
        
        # Find patterns with the same component or error type
        for pid, pattern in self.patterns.items():
            if pid == pattern_id:
                continue
            
            # Check if related by component or error type
            if (pattern.component == context.component or 
                pattern.error_type == context.error_type):
                
                # Add to related patterns if not already there
                if pid not in current_pattern.related_patterns:
                    current_pattern.related_patterns.append(pid)
                
                # Add reciprocal relationship
                if pattern_id not in pattern.related_patterns:
                    pattern.related_patterns.append(pattern_id)
    
    def _save_error_to_log(self, context: ErrorContext) -> None:
        """Save error context to log file."""
        try:
            with open(self.error_log_path, 'a') as f:
                f.write(json.dumps(context.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to save error to log: {e}")
    
    def get_error_patterns(self, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """Get error patterns with minimum occurrences."""
        with self._lock:
            patterns = [
                p.to_dict() for p in self.patterns.values()
                if p.occurrences >= min_occurrences
            ]
            
            # Sort by occurrences (most frequent first)
            return sorted(patterns, key=lambda p: p['occurrences'], reverse=True)    
  
  def get_component_error_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get error statistics by component."""
        with self._lock:
            result = {}
            
            for component, count in self.component_errors.items():
                # Find all patterns for this component
                component_patterns = [
                    p for p in self.patterns.values()
                    if p.component == component
                ]
                
                # Get most common error types for this component
                error_types = Counter([p.error_type for p in component_patterns])
                most_common = error_types.most_common(3)  # Top 3 error types
                
                result[component] = {
                    'total_errors': count,
                    'most_common_errors': [
                        {'error_type': error_type, 'count': error_count}
                        for error_type, error_count in most_common
                    ]
                }
            
            return result
    
    def get_error_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get error trend over the specified number of hours."""
        with self._lock:
            now = datetime.now()
            start_time = now - timedelta(hours=hours)
            
            # Generate all hour keys in the range
            result = []
            current = start_time.replace(minute=0, second=0, microsecond=0)
            while current <= now:
                hour_key = current.strftime("%Y-%m-%d %H:00")
                result.append({
                    'hour': hour_key,
                    'count': self.hourly_error_counts.get(hour_key, 0)
                })
                current += timedelta(hours=1)
            
            return result  
  
    def analyze_error_patterns(self) -> List[Dict[str, Any]]:
        """Analyze error patterns and provide insights."""
        with self._lock:
            insights = []
            
            # Check for rapid increase in errors
            error_trend = self.get_error_trend(hours=6)
            if len(error_trend) >= 3:
                recent_errors = sum(item['count'] for item in error_trend[-3:])
                previous_errors = sum(item['count'] for item in error_trend[-6:-3])
                
                if previous_errors > 0 and recent_errors / previous_errors > 2:
                    insights.append({
                        'type': 'trend',
                        'severity': 'high',
                        'message': f"Error rate increased by {(recent_errors / previous_errors - 1) * 100:.1f}% in the last 3 hours"
                    })
            
            # Check for persistent error patterns
            persistent_patterns = [
                p for p in self.patterns.values()
                if p.occurrences >= 10 and p.last_seen and 
                (datetime.now() - p.last_seen).total_seconds() < 3600  # Last hour
            ]
            
            for pattern in persistent_patterns:
                insights.append({
                    'type': 'pattern',
                    'severity': 'medium',
                    'message': f"Persistent error pattern: {pattern.error_type} in {pattern.component} ({pattern.occurrences} occurrences)",
                    'pattern_id': pattern.pattern_id
                })
            
            # Check for components with high error rates
            component_stats = self.get_component_error_stats()
            for component, stats in component_stats.items():
                if stats['total_errors'] >= 20:
                    insights.append({
                        'type': 'component',
                        'severity': 'medium',
                        'message': f"High error rate in component: {component} ({stats['total_errors']} errors)",
                        'component': component,
                        'most_common_errors': stats['most_common_errors']
                    })
            
            # Sort insights by severity
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            return sorted(insights, key=lambda x: severity_order[x['severity']])
    
    def get_error_details(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an error pattern."""
        with self._lock:
            if pattern_id not in self.patterns:
                return None
            
            pattern = self.patterns[pattern_id]
            result = pattern.to_dict()
            
            # Add related pattern details
            result['related_pattern_details'] = []
            for related_id in pattern.related_patterns:
                if related_id in self.patterns:
                    related = self.patterns[related_id]
                    result['related_pattern_details'].append({
                        'pattern_id': related.pattern_id,
                        'error_type': related.error_type,
                        'component': related.component,
                        'occurrences': related.occurrences
                    })
            
            return result


# Global error analyzer instance
error_analyzer = ErrorAnalyzer()


def get_error_analyzer() -> ErrorAnalyzer:
    """Get the global error analyzer instance."""
    return error_analyzer


def log_detailed_error(
    component: str,
    operation: str,
    error_type: str,
    error_message: str,
    traceback: Optional[str] = None,
    account_data: Optional[Dict[str, Any]] = None,
    browser_info: Optional[Dict[str, Any]] = None,
    proxy_info: Optional[Dict[str, Any]] = None,
    email_service: Optional[str] = None,
    attempt_number: int = 1,
    cycle_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """Convenience function to log a detailed error."""
    context = ErrorContext(
        component=component,
        operation=operation,
        timestamp=datetime.now(),
        error_type=error_type,
        error_message=error_message,
        traceback=traceback,
        account_data=account_data,
        browser_info=browser_info,
        proxy_info=proxy_info,
        email_service=email_service,
        attempt_number=attempt_number,
        cycle_id=cycle_id,
        additional_data=additional_data or {}
    )
    
    return get_error_analyzer().log_error(context)    
def analyze_error_patterns(self) -> List[Dict[str, Any]]:
        """Analyze error patterns and provide insights."""
        with self._lock:
            insights = []
            
            # Check for rapid increase in errors
            error_trend = self.get_error_trend(hours=6)
            if len(error_trend) >= 3:
                recent_errors = sum(item['count'] for item in error_trend[-3:])
                previous_errors = sum(item['count'] for item in error_trend[-6:-3])
                
                if previous_errors > 0 and recent_errors / previous_errors > 2:
                    insights.append({
                        'type': 'trend',
                        'severity': 'high',
                        'message': f"Error rate increased by {(recent_errors / previous_errors - 1) * 100:.1f}% in the last 3 hours"
                    })
            
            # Check for persistent error patterns
            persistent_patterns = [
                p for p in self.patterns.values()
                if p.occurrences >= 10 and p.last_seen and 
                (datetime.now() - p.last_seen).total_seconds() < 3600  # Last hour
            ]
            
            for pattern in persistent_patterns:
                insights.append({
                    'type': 'pattern',
                    'severity': 'medium',
                    'message': f"Persistent error pattern: {pattern.error_type} in {pattern.component} ({pattern.occurrences} occurrences)",
                    'pattern_id': pattern.pattern_id
                })
            
            # Check for components with high error rates
            component_stats = self.get_component_error_stats()
            for component, stats in component_stats.items():
                if stats['total_errors'] >= 20:
                    insights.append({
                        'type': 'component',
                        'severity': 'medium',
                        'message': f"High error rate in component: {component} ({stats['total_errors']} errors)",
                        'component': component,
                        'most_common_errors': stats['most_common_errors']
                    })
            
            # Sort insights by severity
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            return sorted(insights, key=lambda x: severity_order[x['severity']])
    
    def get_error_details(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an error pattern."""
        with self._lock:
            if pattern_id not in self.patterns:
                return None
            
            pattern = self.patterns[pattern_id]
            result = pattern.to_dict()
            
            # Add related pattern details
            result['related_pattern_details'] = []
            for related_id in pattern.related_patterns:
                if related_id in self.patterns:
                    related = self.patterns[related_id]
                    result['related_pattern_details'].append({
                        'pattern_id': related.pattern_id,
                        'error_type': related.error_type,
                        'component': related.component,
                        'occurrences': related.occurrences
                    })
            
            return result    

    def clear_old_data(self, days: int = 7) -> None:
        """Clear error data older than the specified number of days."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # Clear old errors
            self.errors = [
                e for e in self.errors
                if e.timestamp >= cutoff_time
            ]
            
            # Clear old hourly counts
            cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:00")
            self.hourly_error_counts = {
                k: v for k, v in self.hourly_error_counts.items()
                if k >= cutoff_str
            }
            
            # Update patterns
            for pattern_id, pattern in list(self.patterns.items()):
                if pattern.last_seen and pattern.last_seen < cutoff_time:
                    del self.patterns[pattern_id]
                else:
                    # Filter contexts
                    pattern.contexts = [
                        c for c in pattern.contexts
                        if datetime.fromisoformat(c['timestamp']) >= cutoff_time
                    ]
            
            logger.info(f"Cleared error data older than {days} days")
    
    def export_error_data(self, file_path: str) -> bool:
        """Export all error data to a file."""
        try:
            with self._lock:
                data = {
                    'errors': [e.to_dict() for e in self.errors],
                    'patterns': {pid: p.to_dict() for pid, p in self.patterns.items()},
                    'component_errors': dict(self.component_errors),
                    'error_type_counts': dict(self.error_type_counts),
                    'hourly_error_counts': dict(self.hourly_error_counts),
                    'export_time': datetime.now().isoformat()
                }
                
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Exported error data to {file_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to export error data: {e}")
            return False 
   
    def import_error_data(self, file_path: str) -> bool:
        """Import error data from a file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            with self._lock:
                # Import errors
                self.errors = []
                for e_dict in data.get('errors', []):
                    e_dict['timestamp'] = datetime.fromisoformat(e_dict['timestamp'])
                    context = ErrorContext(**e_dict)
                    self.errors.append(context)
                
                # Import patterns
                self.patterns = {}
                for pid, p_dict in data.get('patterns', {}).items():
                    if 'first_seen' in p_dict and p_dict['first_seen']:
                        p_dict['first_seen'] = datetime.fromisoformat(p_dict['first_seen'])
                    if 'last_seen' in p_dict and p_dict['last_seen']:
                        p_dict['last_seen'] = datetime.fromisoformat(p_dict['last_seen'])
                    
                    pattern = ErrorPattern(
                        pattern_id=p_dict['pattern_id'],
                        error_type=p_dict['error_type'],
                        component=p_dict['component'],
                        occurrences=p_dict['occurrences'],
                        first_seen=p_dict.get('first_seen'),
                        last_seen=p_dict.get('last_seen'),
                        contexts=p_dict.get('contexts', []),
                        related_patterns=p_dict.get('related_patterns', [])
                    )
                    self.patterns[pid] = pattern
                
                # Import statistics
                self.component_errors = defaultdict(int, data.get('component_errors', {}))
                self.error_type_counts = defaultdict(int, data.get('error_type_counts', {}))
                self.hourly_error_counts = defaultdict(int, data.get('hourly_error_counts', {}))
                
                logger.info(f"Imported error data from {file_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to import error data: {e}")
            return False


# Global error analyzer instance
error_analyzer = ErrorAnalyzer()


def get_error_analyzer() -> ErrorAnalyzer:
    """Get the global error analyzer instance."""
    return error_analyzer


def log_detailed_error(
    component: str,
    operation: str,
    error_type: str,
    error_message: str,
    traceback: Optional[str] = None,
    account_data: Optional[Dict[str, Any]] = None,
    browser_info: Optional[Dict[str, Any]] = None,
    proxy_info: Optional[Dict[str, Any]] = None,
    email_service: Optional[str] = None,
    attempt_number: int = 1,
    cycle_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """Convenience function to log a detailed error."""
    context = ErrorContext(
        component=component,
        operation=operation,
        timestamp=datetime.now(),
        error_type=error_type,
        error_message=error_message,
        traceback=traceback,
        account_data=account_data,
        browser_info=browser_info,
        proxy_info=proxy_info,
        email_service=email_service,
        attempt_number=attempt_number,
        cycle_id=cycle_id,
        additional_data=additional_data or {}
    )
    
    return get_error_analyzer().log_error(context)