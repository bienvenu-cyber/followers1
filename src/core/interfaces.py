"""
Core interfaces and abstract base classes for the Instagram auto signup system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ServiceStatus(Enum):
    """Status enumeration for services."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    BLACKLISTED = "blacklisted"


@dataclass
class PerformanceMetrics:
    """Performance metrics for system components."""
    success_count: int = 0
    failure_count: int = 0
    total_attempts: int = 0
    average_response_time: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.success_count / self.total_attempts) * 100


class BaseService(ABC):
    """Abstract base class for all services."""
    
    def __init__(self, name: str):
        self.name = name
        self.status = ServiceStatus.INACTIVE
        self.metrics = PerformanceMetrics()
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the service."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup service resources."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        pass
    
    def update_metrics(self, success: bool, response_time: float = 0.0) -> None:
        """Update service performance metrics."""
        self.metrics.total_attempts += 1
        if success:
            self.metrics.success_count += 1
            self.metrics.last_success = datetime.now()
        else:
            self.metrics.failure_count += 1
            self.metrics.last_failure = datetime.now()
        
        # Update average response time
        if response_time > 0:
            current_avg = self.metrics.average_response_time
            total = self.metrics.total_attempts
            self.metrics.average_response_time = ((current_avg * (total - 1)) + response_time) / total


class ResourceManager(ABC):
    """Abstract base class for resource managers."""
    
    def __init__(self, name: str):
        self.name = name
        self.resources: List[Any] = []
        self.metrics = PerformanceMetrics()
    
    @abstractmethod
    async def get_resource(self) -> Any:
        """Get an available resource."""
        pass
    
    @abstractmethod
    async def release_resource(self, resource: Any) -> None:
        """Release a resource back to the pool."""
        pass
    
    @abstractmethod
    async def validate_resource(self, resource: Any) -> bool:
        """Validate if a resource is still usable."""
        pass
    
    @abstractmethod
    async def refresh_resources(self) -> None:
        """Refresh the resource pool."""
        pass


class EmailService(BaseService):
    """Abstract base class for email services."""
    
    @abstractmethod
    async def create_email(self) -> Dict[str, Any]:
        """Create a temporary email address."""
        pass
    
    @abstractmethod
    async def get_messages(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get messages for an email address."""
        pass
    
    @abstractmethod
    async def extract_verification_code(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract verification code from email message."""
        pass


class BrowserManager(BaseService):
    """Abstract base class for browser management."""
    
    @abstractmethod
    async def create_browser_instance(self, proxy_config: Optional[Dict[str, Any]] = None) -> Any:
        """Create a new browser instance."""
        pass
    
    @abstractmethod
    async def close_browser_instance(self, browser: Any) -> None:
        """Close a browser instance."""
        pass
    
    @abstractmethod
    async def simulate_human_behavior(self, browser: Any) -> None:
        """Simulate human-like behavior."""
        pass


class ProxyManager(ResourceManager):
    """Abstract base class for proxy management."""
    
    @abstractmethod
    async def get_working_proxy(self) -> Dict[str, Any]:
        """Get a working proxy configuration."""
        pass
    
    @abstractmethod
    async def mark_proxy_failed(self, proxy: Dict[str, Any]) -> None:
        """Mark a proxy as failed."""
        pass


class ConfigurationManager(ABC):
    """Abstract base class for configuration management."""
    
    @abstractmethod
    async def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        pass
    
    @abstractmethod
    async def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        pass
    
    @abstractmethod
    async def reload_config(self) -> Dict[str, Any]:
        """Reload configuration with hot-reload capability."""
        pass
    
    @abstractmethod
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value."""
        pass


class PerformanceMonitor(ABC):
    """Abstract base class for performance monitoring."""
    
    @abstractmethod
    async def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a performance metric."""
        pass
    
    @abstractmethod
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        pass
    
    @abstractmethod
    async def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance and provide insights."""
        pass


class AccountCreator(ABC):
    """Abstract base class for account creation."""
    
    @abstractmethod
    async def create_account(self) -> Dict[str, Any]:
        """Create a new Instagram account."""
        pass
    
    @abstractmethod
    async def generate_account_data(self) -> Dict[str, Any]:
        """Generate account data for creation."""
        pass
    
    @abstractmethod
    async def validate_account_creation(self, account_data: Dict[str, Any]) -> bool:
        """Validate if account was created successfully."""
        pass