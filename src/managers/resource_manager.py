"""
Resource manager base class for the Instagram auto signup system.

This module provides a base class for resource managers like proxy pool manager
and user agent rotator.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ResourceManager(ABC):
    """Base class for resource managers."""
    
    def __init__(self, name: str):
        """
        Initialize the resource manager.
        
        Args:
            name: Name of the resource manager
        """
        self.name = name
        self.resources = []
        self.resource_usage = {}
        self.resource_performance = {}
        logger.info(f"Initialized {self.name} with {len(self.resources)} resources")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the resource manager.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    def record_resource_usage(self, resource_id: str) -> None:
        """
        Record resource usage.
        
        Args:
            resource_id: ID of the resource
        """
        self.resource_usage[resource_id] = self.resource_usage.get(resource_id, 0) + 1
    
    def record_resource_performance(self, resource_id: str, success: bool, duration: float) -> None:
        """
        Record resource performance.
        
        Args:
            resource_id: ID of the resource
            success: Whether the operation was successful
            duration: Duration of the operation in seconds
        """
        if resource_id not in self.resource_performance:
            self.resource_performance[resource_id] = {
                'success_count': 0,
                'failure_count': 0,
                'total_duration': 0.0,
                'min_duration': float('inf'),
                'max_duration': 0.0
            }
        
        perf = self.resource_performance[resource_id]
        
        if success:
            perf['success_count'] += 1
        else:
            perf['failure_count'] += 1
        
        perf['total_duration'] += duration
        perf['min_duration'] = min(perf['min_duration'], duration)
        perf['max_duration'] = max(perf['max_duration'], duration)
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get resource statistics.
        
        Returns:
            Dictionary with resource statistics
        """
        total_resources = len(self.resources)
        total_usage = sum(self.resource_usage.values())
        
        success_count = sum(p['success_count'] for p in self.resource_performance.values())
        failure_count = sum(p['failure_count'] for p in self.resource_performance.values())
        total_count = success_count + failure_count
        
        success_rate = success_count / total_count if total_count > 0 else 0.0
        
        return {
            'total_resources': total_resources,
            'total_usage': total_usage,
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': success_rate
        }
    
    def get_best_performing_resources(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the best performing resources.
        
        Args:
            limit: Maximum number of resources to return
            
        Returns:
            List of dictionaries with resource statistics
        """
        # Calculate success rate for each resource
        resource_stats = []
        
        for resource_id, perf in self.resource_performance.items():
            total = perf['success_count'] + perf['failure_count']
            if total == 0:
                continue
                
            success_rate = perf['success_count'] / total
            avg_duration = perf['total_duration'] / total if total > 0 else 0.0
            
            resource_stats.append({
                'resource_id': resource_id,
                'success_rate': success_rate,
                'avg_duration': avg_duration,
                'usage_count': self.resource_usage.get(resource_id, 0)
            })
        
        # Sort by success rate (descending) and average duration (ascending)
        resource_stats.sort(key=lambda x: (-x['success_rate'], x['avg_duration']))
        
        return resource_stats[:limit]