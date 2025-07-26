"""
Real-time statistics and analytics system for the Instagram auto signup system.
"""

import time
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import threading
from collections import deque

from .logging_config import get_logger
from .interfaces import PerformanceMetrics


logger = get_logger(__name__)


@dataclass
class CycleStatistics:
    """Statistics for a single creation cycle."""
    cycle_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_attempts: int = 0
    successful_creations: int = 0
    failed_creations: int = 0
    average_creation_time: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_creations / self.total_attempts) * 100
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate cycle duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['start_time'] = self.start_time.isoformat()
        if self.end_time:
            result['end_time'] = self.end_time.isoformat()
        result['success_rate'] = self.success_rate
        result['duration'] = self.duration
        return result


@dataclass
class ServicePerformance:
    """Performance metrics for a specific service."""
    service_name: str
    service_type: str  # email, proxy, browser
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    average_response_time: float = 0.0
    last_used: Optional[datetime] = None
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_uses == 0:
            return 0.0
        return (self.successful_uses / self.total_uses) * 100


@dataclass
class GlobalStatistics:
    """Global statistics for the entire system."""
    start_time: datetime
    total_cycles: int = 0
    total_attempts: int = 0
    successful_creations: int = 0
    failed_creations: int = 0
    average_creation_time: float = 0.0
    service_performance: Dict[str, ServicePerformance] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_creations / self.total_attempts) * 100
    
    @property
    def uptime(self) -> float:
        """Calculate system uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def accounts_per_hour(self) -> float:
        """Calculate accounts created per hour."""
        hours = self.uptime / 3600
        if hours < 0.01:  # Avoid division by very small numbers
            return 0.0
        return self.successful_creations / hours


class StatisticsManager:
    """Manager for collecting and analyzing system statistics."""
    
    def __init__(self, stats_file_path: str = "logs/statistics.json"):
        self.stats_file_path = stats_file_path
        self.global_stats = GlobalStatistics(start_time=datetime.now())
        self.current_cycle: Optional[CycleStatistics] = None
        self.cycle_history: deque = deque(maxlen=100)  # Keep last 100 cycles
        self.performance_history: Dict[str, List[Tuple[datetime, float]]] = {
            'success_rate': [],
            'creation_time': [],
            'accounts_per_hour': []
        }
        self._lock = threading.RLock()
        self._update_interval = 5  # seconds
        self._running = False
        self._display_thread = None
    
    async def initialize(self) -> bool:
        """Initialize the statistics manager."""
        logger.info("Initializing statistics manager...")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_display_thread()
    
    def start_cycle(self) -> str:
        """Start a new creation cycle and return its ID."""
        with self._lock:
            cycle_id = f"cycle_{self.global_stats.total_cycles + 1}"
            self.current_cycle = CycleStatistics(
                cycle_id=cycle_id,
                start_time=datetime.now()
            )
            return cycle_id
    
    def end_cycle(self) -> CycleStatistics:
        """End the current cycle and return its statistics."""
        with self._lock:
            if self.current_cycle is None:
                logger.warning("Attempted to end a cycle when none was active")
                return CycleStatistics(cycle_id="invalid", start_time=datetime.now())
            
            self.current_cycle.end_time = datetime.now()
            self.global_stats.total_cycles += 1
            
            # Add to history and return a copy
            cycle_stats = self.current_cycle
            self.cycle_history.append(cycle_stats)
            self.current_cycle = None
            
            # Update performance history
            self._update_performance_history()
            
            # Save statistics to file
            self._save_statistics()
            
            return cycle_stats
    
    def record_attempt(self, success: bool, creation_time: float, error_type: Optional[str] = None) -> None:
        """Record an account creation attempt."""
        with self._lock:
            # Update global statistics
            self.global_stats.total_attempts += 1
            if success:
                self.global_stats.successful_creations += 1
            else:
                self.global_stats.failed_creations += 1
                if error_type:
                    self.global_stats.error_counts[error_type] = self.global_stats.error_counts.get(error_type, 0) + 1
            
            # Update average creation time
            total = self.global_stats.successful_creations
            if total > 0:
                current_avg = self.global_stats.average_creation_time
                self.global_stats.average_creation_time = ((current_avg * (total - 1)) + creation_time) / total
            
            # Update cycle statistics if a cycle is active
            if self.current_cycle:
                self.current_cycle.total_attempts += 1
                if success:
                    self.current_cycle.successful_creations += 1
                else:
                    self.current_cycle.failed_creations += 1
                    if error_type:
                        self.current_cycle.error_counts[error_type] = self.current_cycle.error_counts.get(error_type, 0) + 1
                
                # Update average creation time for the cycle
                total = self.current_cycle.successful_creations
                if total > 0:
                    current_avg = self.current_cycle.average_creation_time
                    self.current_cycle.average_creation_time = ((current_avg * (total - 1)) + creation_time) / total
    
    def record_service_usage(
        self,
        service_name: str,
        service_type: str,
        success: bool,
        response_time: float,
        error_type: Optional[str] = None
    ) -> None:
        """Record usage of a service (email, proxy, etc.)."""
        with self._lock:
            # Get or create service performance record
            key = f"{service_type}:{service_name}"
            if key not in self.global_stats.service_performance:
                self.global_stats.service_performance[key] = ServicePerformance(
                    service_name=service_name,
                    service_type=service_type
                )
            
            # Update service performance
            service_perf = self.global_stats.service_performance[key]
            service_perf.total_uses += 1
            if success:
                service_perf.successful_uses += 1
            else:
                service_perf.failed_uses += 1
                if error_type:
                    service_perf.error_counts[error_type] = service_perf.error_counts.get(error_type, 0) + 1
            
            # Update average response time
            total = service_perf.total_uses
            if total > 0:
                current_avg = service_perf.average_response_time
                service_perf.average_response_time = ((current_avg * (total - 1)) + response_time) / total
            
            service_perf.last_used = datetime.now()
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global statistics as a dictionary."""
        with self._lock:
            result = {
                'start_time': self.global_stats.start_time.isoformat(),
                'uptime': self.global_stats.uptime,
                'total_cycles': self.global_stats.total_cycles,
                'total_attempts': self.global_stats.total_attempts,
                'successful_creations': self.global_stats.successful_creations,
                'failed_creations': self.global_stats.failed_creations,
                'success_rate': self.global_stats.success_rate,
                'average_creation_time': self.global_stats.average_creation_time,
                'accounts_per_hour': self.global_stats.accounts_per_hour,
                'error_counts': dict(self.global_stats.error_counts)
            }
            
            # Add current cycle if active
            if self.current_cycle:
                result['current_cycle'] = self.current_cycle.to_dict()
            
            return result
    
    def get_service_performance(self, service_type: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for services, optionally filtered by type."""
        with self._lock:
            result = {}
            for key, perf in self.global_stats.service_performance.items():
                if service_type is None or perf.service_type == service_type:
                    result[key] = {
                        'service_name': perf.service_name,
                        'service_type': perf.service_type,
                        'total_uses': perf.total_uses,
                        'successful_uses': perf.successful_uses,
                        'failed_uses': perf.failed_uses,
                        'success_rate': perf.success_rate,
                        'average_response_time': perf.average_response_time,
                        'last_used': perf.last_used.isoformat() if perf.last_used else None,
                        'error_counts': dict(perf.error_counts)
                    }
            return result
    
    def get_performance_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical performance data for charting."""
        with self._lock:
            result = {}
            for metric, history in self.performance_history.items():
                result[metric] = [
                    {'timestamp': ts.isoformat(), 'value': val}
                    for ts, val in history
                ]
            return result
    
    def get_cycle_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of recent cycles."""
        with self._lock:
            return [cycle.to_dict() for cycle in list(self.cycle_history)[-limit:]]
    
    def _update_performance_history(self) -> None:
        """Update performance history with current values."""
        now = datetime.now()
        self.performance_history['success_rate'].append((now, self.global_stats.success_rate))
        self.performance_history['creation_time'].append((now, self.global_stats.average_creation_time))
        self.performance_history['accounts_per_hour'].append((now, self.global_stats.accounts_per_hour))
        
        # Trim history to keep only last 24 hours
        one_day_ago = now - timedelta(days=1)
        for metric, history in self.performance_history.items():
            self.performance_history[metric] = [
                (ts, val) for ts, val in history
                if ts >= one_day_ago
            ]
    
    def _save_statistics(self) -> None:
        """Save statistics to file."""
        try:
            stats = {
                'global': self.get_global_statistics(),
                'services': self.get_service_performance(),
                'history': {
                    'performance': self.get_performance_history(),
                    'cycles': self.get_cycle_history(limit=100)
                }
            }
            
            with open(self.stats_file_path, 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save statistics: {e}")
    
    def start_display_thread(self) -> None:
        """Start a thread to periodically display statistics."""
        if self._running:
            return
        
        self._running = True
        self._display_thread = threading.Thread(target=self._display_loop)
        self._display_thread.daemon = True
        self._display_thread.start()
    
    def stop_display_thread(self) -> None:
        """Stop the statistics display thread."""
        self._running = False
        if self._display_thread:
            self._display_thread.join(timeout=1.0)
    
    def _display_loop(self) -> None:
        """Loop to periodically display statistics."""
        while self._running:
            self.display_statistics()
            time.sleep(self._update_interval)
    
    def display_statistics(self) -> None:
        """Display current statistics to console."""
        stats = self.get_global_statistics()
        
        # Clear previous output (works in most terminals)
        print("\033c", end="")
        
        # Display header
        print("=" * 80)
        print(f"INSTAGRAM AUTO SIGNUP - REAL-TIME STATISTICS")
        print(f"Uptime: {timedelta(seconds=int(stats['uptime']))}")
        print("=" * 80)
        
        # Display global stats
        print(f"\nGLOBAL STATISTICS:")
        print(f"  Total Attempts: {stats['total_attempts']}")
        print(f"  Successful Creations: {stats['successful_creations']}")
        print(f"  Failed Creations: {stats['failed_creations']}")
        print(f"  Success Rate: {stats['success_rate']:.2f}%")
        print(f"  Average Creation Time: {stats['average_creation_time']:.2f} seconds")
        print(f"  Accounts Per Hour: {stats['accounts_per_hour']:.2f}")
        
        # Display current cycle if active
        if 'current_cycle' in stats:
            cycle = stats['current_cycle']
            elapsed = (datetime.now() - datetime.fromisoformat(cycle['start_time'])).total_seconds()
            print(f"\nCURRENT CYCLE: {cycle['cycle_id']} (Running for {elapsed:.1f} seconds)")
            print(f"  Attempts: {cycle['total_attempts']}")
            print(f"  Successful: {cycle['successful_creations']}")
            print(f"  Failed: {cycle['failed_creations']}")
            print(f"  Success Rate: {cycle['success_rate']:.2f}%")
        
        # Display top errors
        if stats['error_counts']:
            print("\nTOP ERRORS:")
            sorted_errors = sorted(
                stats['error_counts'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Show top 5 errors
            for error_type, count in sorted_errors:
                print(f"  {error_type}: {count}")
        
        # Display service performance
        service_perf = self.get_service_performance()
        if service_perf:
            print("\nSERVICE PERFORMANCE:")
            
            # Group by service type
            by_type = {}
            for key, perf in service_perf.items():
                service_type = perf['service_type']
                if service_type not in by_type:
                    by_type[service_type] = []
                by_type[service_type].append(perf)
            
            # Display each service type
            for service_type, services in by_type.items():
                print(f"\n  {service_type.upper()} SERVICES:")
                
                # Sort by success rate
                sorted_services = sorted(
                    services,
                    key=lambda x: x['success_rate'],
                    reverse=True
                )
                
                for perf in sorted_services:
                    print(f"    {perf['service_name']}: {perf['success_rate']:.2f}% success rate, "
                          f"{perf['total_uses']} uses")
        
        print("\n" + "=" * 80)


# Global statistics manager instance
statistics_manager = StatisticsManager()


def get_statistics_manager() -> StatisticsManager:
    """Get the global statistics manager instance."""
    return statistics_manager