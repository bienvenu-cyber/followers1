"""
Performance optimization engine for the Instagram auto signup system.
"""

import time
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading
import random

from .logging_config import get_logger
from .statistics_manager import get_statistics_manager, StatisticsManager


logger = get_logger(__name__)


@dataclass
class OptimizationSuggestion:
    """Suggestion for performance optimization."""
    component: str
    suggestion_type: str
    suggestion: str
    confidence: float  # 0.0 to 1.0
    impact: str  # "high", "medium", "low"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "component": self.component,
            "suggestion_type": self.suggestion_type,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "impact": self.impact,
            "timestamp": self.timestamp.isoformat()
        }


class PerformanceOptimizer:
    """Automatic performance optimization engine."""
    
    def __init__(self, stats_manager: Optional[StatisticsManager] = None):
        self.stats_manager = stats_manager or get_statistics_manager()
        self.optimization_history: List[OptimizationSuggestion] = []
        self.suggestions: List[OptimizationSuggestion] = []
        self.applied_optimizations: Set[str] = set()
        self.optimization_results: Dict[str, float] = {}
        self.learning_data: Dict[str, List[Dict[str, Any]]] = {
            "email_services": [],
            "proxies": [],
            "user_agents": [],
            "timing_patterns": []
        }
        self._lock = threading.RLock()
        self._running = False
        self._optimizer_thread = None
    
    async def initialize(self) -> bool:
        """Initialize the performance optimizer."""
        logger.info("Initializing performance optimizer...")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_optimizer()
    
    def start_optimizer(self, interval: int = 300) -> None:
        """Start the optimizer thread."""
        if self._running:
            return
        
        self._running = True
        self._optimizer_thread = threading.Thread(
            target=self._optimization_loop,
            args=(interval,)
        )
        self._optimizer_thread.daemon = True
        self._optimizer_thread.start()
        logger.info(f"Performance optimizer started with interval {interval} seconds")
    
    def stop_optimizer(self) -> None:
        """Stop the optimizer thread."""
        self._running = False
        if self._optimizer_thread:
            self._optimizer_thread.join(timeout=1.0)
            logger.info("Performance optimizer stopped")
    
    def _optimization_loop(self, interval: int) -> None:
        """Main optimization loop."""
        while self._running:
            try:
                self.analyze_performance()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                time.sleep(10)  # Shorter interval on error
    
    def analyze_performance(self) -> List[OptimizationSuggestion]:
        """Analyze performance and generate optimization suggestions."""
        with self._lock:
            # Get current statistics
            global_stats = self.stats_manager.get_global_statistics()
            service_perf = self.stats_manager.get_service_performance()
            
            # Clear old suggestions (keep only last 24 hours)
            one_day_ago = datetime.now() - timedelta(days=1)
            self.suggestions = [
                s for s in self.suggestions
                if s.timestamp >= one_day_ago
            ]
            
            # Generate new suggestions
            new_suggestions = []
            
            # Check overall success rate
            if global_stats["success_rate"] < 40.0:
                new_suggestions.append(
                    OptimizationSuggestion(
                        component="global",
                        suggestion_type="success_rate",
                        suggestion="Overall success rate is low. Consider adjusting proxy rotation frequency and user agent diversity.",
                        confidence=0.8,
                        impact="high"
                    )
                )
            
            # Analyze email services
            email_services = {
                k: v for k, v in service_perf.items()
                if v["service_type"] == "email"
            }
            
            if email_services:
                # Find best and worst performing email services
                sorted_email = sorted(
                    email_services.items(),
                    key=lambda x: x[1]["success_rate"],
                    reverse=True
                )
                
                best_email = sorted_email[0][1]
                worst_email = sorted_email[-1][1]
                
                # If there's a significant difference, suggest prioritizing the best service
                if (best_email["success_rate"] - worst_email["success_rate"] > 30.0 and
                        best_email["total_uses"] > 5):
                    new_suggestions.append(
                        OptimizationSuggestion(
                            component="email_service",
                            suggestion_type="prioritization",
                            suggestion=f"Prioritize '{best_email['service_name']}' email service which has {best_email['success_rate']:.1f}% success rate vs {worst_email['service_name']} with {worst_email['success_rate']:.1f}%",
                            confidence=0.7,
                            impact="medium"
                        )
                    )
            
            # Analyze proxy services
            proxy_services = {
                k: v for k, v in service_perf.items()
                if v["service_type"] == "proxy"
            }
            
            if proxy_services:
                # Calculate average proxy success rate
                avg_proxy_rate = sum(p["success_rate"] for p in proxy_services.values()) / len(proxy_services)
                
                # If average proxy success rate is low, suggest more frequent rotation
                if avg_proxy_rate < 50.0:
                    new_suggestions.append(
                        OptimizationSuggestion(
                            component="proxy",
                            suggestion_type="rotation",
                            suggestion="Proxy success rate is low. Increase proxy rotation frequency and consider adding more residential proxies.",
                            confidence=0.75,
                            impact="high"
                        )
                    )
            
            # Analyze error patterns
            if "error_counts" in global_stats and global_stats["error_counts"]:
                top_errors = sorted(
                    global_stats["error_counts"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]  # Top 3 errors
                
                for error_type, count in top_errors:
                    if count > 10:  # Only suggest for frequent errors
                        suggestion = self._get_error_suggestion(error_type)
                        if suggestion:
                            new_suggestions.append(suggestion)
            
            # Add new suggestions
            self.suggestions.extend(new_suggestions)
            
            # Update learning data
            self._update_learning_data(global_stats, service_perf)
            
            return new_suggestions
    
    def _get_error_suggestion(self, error_type: str) -> Optional[OptimizationSuggestion]:
        """Generate a suggestion based on error type."""
        if "captcha" in error_type.lower():
            return OptimizationSuggestion(
                component="anti_detection",
                suggestion_type="captcha",
                suggestion="High rate of CAPTCHA errors. Adjust browser fingerprinting and consider reducing creation frequency.",
                confidence=0.8,
                impact="high"
            )
        elif "timeout" in error_type.lower():
            return OptimizationSuggestion(
                component="network",
                suggestion_type="timeout",
                suggestion="Frequent timeout errors. Check proxy response times and consider increasing timeout thresholds.",
                confidence=0.7,
                impact="medium"
            )
        elif "element" in error_type.lower() and "not found" in error_type.lower():
            return OptimizationSuggestion(
                component="element_selector",
                suggestion_type="selectors",
                suggestion="Element selectors may be outdated. Update selectors and add fallback mechanisms.",
                confidence=0.75,
                impact="high"
            )
        elif "blocked" in error_type.lower() or "ban" in error_type.lower():
            return OptimizationSuggestion(
                component="anti_detection",
                suggestion_type="blocking",
                suggestion="Account creation is being blocked. Enhance anti-detection measures and reduce creation frequency.",
                confidence=0.9,
                impact="high"
            )
        
        return None
    
    def _update_learning_data(self, global_stats: Dict[str, Any], service_perf: Dict[str, Dict[str, Any]]) -> None:
        """Update learning data for pattern recognition."""
        now = datetime.now()
        
        # Update email service data
        for key, perf in service_perf.items():
            if perf["service_type"] == "email" and perf["total_uses"] > 0:
                self.learning_data["email_services"].append({
                    "timestamp": now.isoformat(),
                    "service_name": perf["service_name"],
                    "success_rate": perf["success_rate"],
                    "total_uses": perf["total_uses"]
                })
        
        # Update proxy data
        for key, perf in service_perf.items():
            if perf["service_type"] == "proxy" and perf["total_uses"] > 0:
                self.learning_data["proxies"].append({
                    "timestamp": now.isoformat(),
                    "proxy_name": perf["service_name"],
                    "success_rate": perf["success_rate"],
                    "total_uses": perf["total_uses"]
                })
        
        # Update timing patterns
        hour_of_day = now.hour
        day_of_week = now.weekday()
        
        self.learning_data["timing_patterns"].append({
            "timestamp": now.isoformat(),
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "success_rate": global_stats["success_rate"],
            "accounts_per_hour": global_stats["accounts_per_hour"]
        })
        
        # Trim learning data to keep only last 7 days
        seven_days_ago = (now - timedelta(days=7)).isoformat()
        for key in self.learning_data:
            self.learning_data[key] = [
                item for item in self.learning_data[key]
                if item["timestamp"] >= seven_days_ago
            ]
    
    def get_suggestions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent optimization suggestions."""
        with self._lock:
            # Sort by timestamp (newest first) and confidence
            sorted_suggestions = sorted(
                self.suggestions,
                key=lambda s: (s.timestamp, s.confidence),
                reverse=True
            )
            
            return [s.to_dict() for s in sorted_suggestions[:limit]]
    
    def get_best_email_service(self) -> Optional[str]:
        """Get the name of the best performing email service."""
        with self._lock:
            if not self.learning_data["email_services"]:
                return None
            
            # Group by service name and calculate average success rate
            service_stats = {}
            for entry in self.learning_data["email_services"]:
                name = entry["service_name"]
                if name not in service_stats:
                    service_stats[name] = {"total_rate": 0.0, "count": 0}
                
                service_stats[name]["total_rate"] += entry["success_rate"]
                service_stats[name]["count"] += 1
            
            # Calculate average success rate for each service
            for name, stats in service_stats.items():
                stats["avg_rate"] = stats["total_rate"] / stats["count"]
            
            # Find service with highest average success rate
            best_service = max(service_stats.items(), key=lambda x: x[1]["avg_rate"])
            return best_service[0]
    
    def get_best_creation_times(self) -> List[Dict[str, Any]]:
        """Get the best times for account creation based on historical data."""
        with self._lock:
            if not self.learning_data["timing_patterns"]:
                return []
            
            # Group by hour of day and day of week
            time_stats = {}
            for entry in self.learning_data["timing_patterns"]:
                key = (entry["day_of_week"], entry["hour_of_day"])
                if key not in time_stats:
                    time_stats[key] = {
                        "success_rates": [],
                        "accounts_per_hour": []
                    }
                
                time_stats[key]["success_rates"].append(entry["success_rate"])
                time_stats[key]["accounts_per_hour"].append(entry["accounts_per_hour"])
            
            # Calculate averages
            result = []
            for (day, hour), stats in time_stats.items():
                avg_success = sum(stats["success_rates"]) / len(stats["success_rates"])
                avg_accounts = sum(stats["accounts_per_hour"]) / len(stats["accounts_per_hour"])
                
                result.append({
                    "day_of_week": day,
                    "hour_of_day": hour,
                    "avg_success_rate": avg_success,
                    "avg_accounts_per_hour": avg_accounts,
                    "sample_size": len(stats["success_rates"])
                })
            
            # Sort by success rate and accounts per hour
            return sorted(
                result,
                key=lambda x: (x["avg_success_rate"], x["avg_accounts_per_hour"]),
                reverse=True
            )
    
    def apply_optimization(self, suggestion_id: str) -> bool:
        """Apply an optimization suggestion."""
        with self._lock:
            # Find the suggestion
            for suggestion in self.suggestions:
                if suggestion.component + ":" + suggestion.suggestion_type == suggestion_id:
                    # Mark as applied
                    self.applied_optimizations.add(suggestion_id)
                    logger.info(f"Applied optimization: {suggestion.suggestion}")
                    return True
            
            return False
    
    def get_optimization_results(self) -> Dict[str, Any]:
        """Get results of applied optimizations."""
        with self._lock:
            return {
                "applied_optimizations": list(self.applied_optimizations),
                "optimization_results": self.optimization_results,
                "best_email_service": self.get_best_email_service(),
                "best_creation_times": self.get_best_creation_times()[:5]
            }
    
    def save_learning_data(self, file_path: str = "data/learning_data.json") -> None:
        """Save learning data to file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.learning_data, f, indent=2)
            logger.info(f"Learning data saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")
    
    def load_learning_data(self, file_path: str = "data/learning_data.json") -> bool:
        """Load learning data from file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.learning_data = data
            logger.info(f"Learning data loaded from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load learning data: {e}")
            return False


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    return performance_optimizer