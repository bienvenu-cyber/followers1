"""
Adaptive failure handling system for the Instagram auto signup system.

This module implements strategies to detect and respond to high failure rates
by dynamically adjusting system parameters and rotating resources.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading

from .config import config_manager
from .performance_optimizer import get_performance_optimizer, OptimizationSuggestion
from .statistics_manager import get_statistics_manager


logger = logging.getLogger(__name__)


@dataclass
class FailurePattern:
    """Pattern of failures detected in the system."""
    pattern_type: str  # "proxy", "captcha", "element", "timeout", etc.
    frequency: float  # 0.0 to 1.0
    first_seen: datetime
    last_seen: datetime
    occurrences: int
    related_errors: List[str]
    
    @property
    def duration(self) -> timedelta:
        """Get the duration of this pattern."""
        return self.last_seen - self.first_seen


class AdaptiveFailureHandler:
    """
    Handles high failure rates by dynamically adjusting system parameters
    and rotating resources.
    """
    
    def __init__(self):
        """Initialize the adaptive failure handler."""
        self.config = config_manager.get_config()
        self.stats_manager = get_statistics_manager()
        self.performance_optimizer = get_performance_optimizer()
        
        # Failure tracking
        self.failure_threshold = 0.8  # 80% failure rate
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.failure_patterns: List[FailurePattern] = []
        self.last_strategy_change = datetime.now()
        self.strategy_change_cooldown = 300  # seconds
        
        # Resource rotation tracking
        self.rotated_resources = set()
        self.last_full_rotation = datetime.now()
        
        # Lock for thread safety
        self._lock = threading.RLock()
    
    def check_failure_rate(self, cycle_stats) -> bool:
        """
        Check if the failure rate exceeds the threshold.
        
        Args:
            cycle_stats: Statistics for the current cycle
            
        Returns:
            bool: True if failure rate exceeds threshold
        """
        if cycle_stats.total_attempts == 0:
            return False
        
        failure_rate = cycle_stats.failed_creations / cycle_stats.total_attempts
        high_failure = failure_rate >= self.failure_threshold
        
        if high_failure:
            with self._lock:
                self.consecutive_failures += 1
                logger.warning(f"High failure rate detected: {failure_rate:.2%} "
                              f"(consecutive: {self.consecutive_failures})")
        else:
            with self._lock:
                self.consecutive_failures = 0
        
        return high_failure
    
    def analyze_error_patterns(self) -> List[FailurePattern]:
        """
        Analyze error patterns from recent failures.
        
        Returns:
            List[FailurePattern]: Detected failure patterns
        """
        with self._lock:
            # Get global statistics
            stats = self.stats_manager.get_global_statistics()
            error_counts = stats.get("error_counts", {})
            
            if not error_counts:
                return []
            
            # Calculate total errors
            total_errors = sum(error_counts.values())
            if total_errors == 0:
                return []
            
            # Identify patterns
            patterns = []
            
            # Group errors by type
            error_groups = {
                "proxy": ["proxy", "connection", "timeout", "network"],
                "captcha": ["captcha", "challenge", "verification"],
                "element": ["element", "selector", "not found", "stale"],
                "account": ["account", "username", "email", "password"],
                "browser": ["browser", "webdriver", "selenium"]
            }
            
            for group_name, keywords in error_groups.items():
                group_errors = []
                group_count = 0
                
                for error, count in error_counts.items():
                    if any(keyword in error.lower() for keyword in keywords):
                        group_errors.append(error)
                        group_count += count
                
                if group_count > 0:
                    frequency = group_count / total_errors
                    if frequency >= 0.2:  # At least 20% of errors
                        patterns.append(FailurePattern(
                            pattern_type=group_name,
                            frequency=frequency,
                            first_seen=datetime.now() - timedelta(hours=1),  # Approximate
                            last_seen=datetime.now(),
                            occurrences=group_count,
                            related_errors=group_errors
                        ))
            
            # Sort by frequency
            patterns.sort(key=lambda p: p.frequency, reverse=True)
            return patterns
    
    def handle_high_failure_rate(self) -> List[str]:
        """
        Handle high failure rate by adjusting strategies and rotating resources.
        
        Returns:
            List[str]: List of actions taken
        """
        with self._lock:
            now = datetime.now()
            actions_taken = []
            
            # Check if we're in cooldown period
            if (now - self.last_strategy_change).total_seconds() < self.strategy_change_cooldown:
                logger.info("Strategy change cooldown active, skipping adjustments")
                return ["cooldown_active"]
            
            # Analyze error patterns
            patterns = self.analyze_error_patterns()
            
            # Get optimization suggestions
            suggestions = self.performance_optimizer.analyze_performance()
            
            # Apply optimizations based on patterns and suggestions
            if patterns:
                dominant_pattern = patterns[0]
                logger.info(f"Dominant failure pattern: {dominant_pattern.pattern_type} "
                           f"({dominant_pattern.frequency:.2%})")
                
                if dominant_pattern.pattern_type == "proxy":
                    actions_taken.extend(self._handle_proxy_failures())
                
                elif dominant_pattern.pattern_type == "captcha":
                    actions_taken.extend(self._handle_captcha_failures())
                
                elif dominant_pattern.pattern_type == "element":
                    actions_taken.extend(self._handle_element_failures())
                
                elif dominant_pattern.pattern_type == "browser":
                    actions_taken.extend(self._handle_browser_failures())
            
            # Apply general optimizations from suggestions
            for suggestion in suggestions:
                action = self._apply_optimization_suggestion(suggestion)
                if action:
                    actions_taken.append(action)
            
            # If consecutive failures exceed threshold, take more drastic measures
            if self.consecutive_failures >= self.max_consecutive_failures:
                logger.warning(f"Maximum consecutive failures reached ({self.consecutive_failures}), "
                              "performing full resource rotation")
                actions_taken.extend(self._perform_full_resource_rotation())
                self.consecutive_failures = 0  # Reset counter
            
            # Update last strategy change time
            if actions_taken:
                self.last_strategy_change = now
            
            return actions_taken
    
    def _handle_proxy_failures(self) -> List[str]:
        """
        Handle proxy-related failures.
        
        Returns:
            List[str]: Actions taken
        """
        actions = []
        
        # Increase proxy rotation frequency
        current = self.config.proxy_rotation_frequency
        new_value = max(1, current // 2)
        config_manager.update_config_value("proxy_rotation_frequency", new_value)
        actions.append(f"increased_proxy_rotation_to_{new_value}")
        
        # Increase proxy timeout
        current = self.config.proxy_timeout
        new_value = min(30, current + 5)
        config_manager.update_config_value("proxy_timeout", new_value)
        actions.append(f"increased_proxy_timeout_to_{new_value}")
        
        return actions
    
    def _handle_captcha_failures(self) -> List[str]:
        """
        Handle CAPTCHA-related failures.
        
        Returns:
            List[str]: Actions taken
        """
        actions = []
        
        # Enhance anti-detection measures
        config_manager.update_config({
            "min_typing_delay": min(1.0, self.config.min_typing_delay * 1.5),
            "max_typing_delay": min(2.0, self.config.max_typing_delay * 1.5),
            "min_action_delay": min(3.0, self.config.min_action_delay * 1.5),
            "max_action_delay": min(5.0, self.config.max_action_delay * 1.5)
        })
        actions.append("enhanced_anti_detection_measures")
        
        # Increase creation interval to reduce detection
        current = self.config.creation_interval
        new_value = min(1800, current * 2)  # Max 30 minutes
        config_manager.update_config_value("creation_interval", new_value)
        actions.append(f"increased_creation_interval_to_{new_value}")
        
        return actions
    
    def _handle_element_failures(self) -> List[str]:
        """
        Handle element selector failures.
        
        Returns:
            List[str]: Actions taken
        """
        actions = []
        
        # Increase browser timeout values
        config_manager.update_config({
            "browser_timeout": min(60, self.config.browser_timeout + 10),
            "page_load_timeout": min(40, self.config.page_load_timeout + 10),
            "implicit_wait": min(20, self.config.implicit_wait + 5)
        })
        actions.append("increased_browser_timeouts")
        
        return actions
    
    def _handle_browser_failures(self) -> List[str]:
        """
        Handle browser-related failures.
        
        Returns:
            List[str]: Actions taken
        """
        actions = []
        
        # Reduce concurrent creations to reduce browser load
        current = self.config.max_concurrent_creations
        if current > 1:
            new_value = current - 1
            config_manager.update_config_value("max_concurrent_creations", new_value)
            actions.append(f"reduced_concurrent_creations_to_{new_value}")
        
        return actions
    
    def _apply_optimization_suggestion(self, suggestion: OptimizationSuggestion) -> Optional[str]:
        """
        Apply an optimization suggestion.
        
        Args:
            suggestion: Optimization suggestion
            
        Returns:
            Optional[str]: Action taken or None
        """
        if suggestion.component == "proxy" and suggestion.suggestion_type == "rotation":
            current = self.config.proxy_rotation_frequency
            new_value = max(1, current // 2)
            config_manager.update_config_value("proxy_rotation_frequency", new_value)
            return f"applied_suggestion_proxy_rotation_{new_value}"
        
        elif suggestion.component == "anti_detection" and suggestion.suggestion_type == "captcha":
            config_manager.update_config({
                "min_typing_delay": min(1.0, self.config.min_typing_delay * 1.5),
                "max_typing_delay": min(2.0, self.config.max_typing_delay * 1.5)
            })
            return "applied_suggestion_anti_detection"
        
        elif suggestion.component == "network" and suggestion.suggestion_type == "timeout":
            current = self.config.browser_timeout
            new_value = min(60, current + 10)
            config_manager.update_config_value("browser_timeout", new_value)
            return f"applied_suggestion_browser_timeout_{new_value}"
        
        elif suggestion.component == "element_selector" and suggestion.suggestion_type == "selectors":
            current = self.config.implicit_wait
            new_value = min(20, current + 5)
            config_manager.update_config_value("implicit_wait", new_value)
            return f"applied_suggestion_implicit_wait_{new_value}"
        
        return None
    
    def _perform_full_resource_rotation(self) -> List[str]:
        """
        Perform a full rotation of all resources.
        
        Returns:
            List[str]: Actions taken
        """
        actions = []
        
        # Record full rotation
        self.last_full_rotation = datetime.now()
        
        # Increase creation interval temporarily
        original_interval = self.config.creation_interval
        config_manager.update_config_value("creation_interval", original_interval * 2)
        actions.append(f"increased_creation_interval_to_{original_interval * 2}")
        
        # Schedule restoration of original interval after a few cycles
        def restore_interval():
            time.sleep(original_interval * 3)  # Wait for 3 cycles
            config_manager.update_config_value("creation_interval", original_interval)
            logger.info(f"Restored creation interval to {original_interval}")
        
        # Start restoration thread
        thread = threading.Thread(target=restore_interval)
        thread.daemon = True
        thread.start()
        
        # Mark all resources as needing rotation
        self.rotated_resources = set(["proxies", "user_agents", "browser_profiles"])
        actions.append("marked_all_resources_for_rotation")
        
        return actions
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the adaptive failure handler.
        
        Returns:
            Dict[str, Any]: Status information
        """
        with self._lock:
            return {
                "consecutive_failures": self.consecutive_failures,
                "failure_threshold": self.failure_threshold,
                "last_strategy_change": self.last_strategy_change.isoformat(),
                "strategy_change_cooldown": self.strategy_change_cooldown,
                "rotated_resources": list(self.rotated_resources),
                "last_full_rotation": self.last_full_rotation.isoformat(),
                "failure_patterns": [
                    {
                        "pattern_type": p.pattern_type,
                        "frequency": p.frequency,
                        "occurrences": p.occurrences,
                        "related_errors": p.related_errors
                    }
                    for p in self.analyze_error_patterns()
                ]
            }


# Global adaptive failure handler instance
adaptive_failure_handler = AdaptiveFailureHandler()


def get_adaptive_failure_handler() -> AdaptiveFailureHandler:
    """Get the global adaptive failure handler instance."""
    return adaptive_failure_handler