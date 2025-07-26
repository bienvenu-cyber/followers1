"""
Email service health monitoring and automatic fallback management.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from ..core.interfaces import EmailService, ServiceStatus


class HealthCheckType(Enum):
    """Types of health checks."""
    BASIC = "basic"
    CONNECTIVITY = "connectivity"
    FUNCTIONALITY = "functionality"
    PERFORMANCE = "performance"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service_name: str
    check_type: HealthCheckType
    success: bool
    response_time: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict = field(default_factory=dict)


@dataclass
class ServiceHealthStatus:
    """Health status for a service."""
    service_name: str
    is_healthy: bool = True
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_response_time: float = 0.0
    last_error: Optional[str] = None
    blacklisted_until: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.success_count / self.total_checks) * 100
    
    @property
    def is_blacklisted(self) -> bool:
        """Check if service is currently blacklisted."""
        if self.blacklisted_until is None:
            return False
        return datetime.now() < self.blacklisted_until


class EmailServiceHealthMonitor:
    """
    Monitors email service health and manages automatic fallback mechanisms.
    """
    
    def __init__(self, 
                 check_interval: int = 300,  # 5 minutes
                 failure_threshold: int = 3,
                 blacklist_duration: int = 1800):  # 30 minutes
        """
        Initialize the health monitor.
        
        Args:
            check_interval: Interval between health checks in seconds
            failure_threshold: Number of consecutive failures before blacklisting
            blacklist_duration: Duration to blacklist failed services in seconds
        """
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.blacklist_duration = blacklist_duration
        
        self.services: Dict[str, EmailService] = {}
        self.health_status: Dict[str, ServiceHealthStatus] = {}
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        self.logger = logging.getLogger(__name__)
        
        # Callbacks for health status changes
        self.health_change_callbacks: List[Callable[[str, bool], None]] = []
        self.blacklist_callbacks: List[Callable[[str, bool], None]] = []
    
    def register_service(self, service: EmailService) -> None:
        """
        Register a service for health monitoring.
        
        Args:
            service: Email service to monitor
        """
        self.services[service.name] = service
        self.health_status[service.name] = ServiceHealthStatus(service_name=service.name)
        self.logger.info(f"Registered service for health monitoring: {service.name}")
    
    def unregister_service(self, service_name: str) -> None:
        """
        Unregister a service from health monitoring.
        
        Args:
            service_name: Name of service to unregister
        """
        if service_name in self.services:
            del self.services[service_name]
            del self.health_status[service_name]
            self.logger.info(f"Unregistered service from health monitoring: {service_name}")
    
    def add_health_change_callback(self, callback: Callable[[str, bool], None]) -> None:
        """
        Add callback for health status changes.
        
        Args:
            callback: Function to call when service health changes
        """
        self.health_change_callbacks.append(callback)
    
    def add_blacklist_callback(self, callback: Callable[[str, bool], None]) -> None:
        """
        Add callback for blacklist status changes.
        
        Args:
            callback: Function to call when service blacklist status changes
        """
        self.blacklist_callbacks.append(callback)
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self.monitoring_active:
            self.logger.warning("Health monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Started email service health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        self.monitoring_active = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        self.logger.info("Stopped email service health monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self.check_all_services()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all registered services.
        
        Returns:
            Dictionary of service names to health check results
        """
        results = {}
        
        # Run health checks concurrently
        tasks = []
        for service_name in self.services:
            task = asyncio.create_task(
                self.check_service_health(service_name),
                name=f"health_check_{service_name}"
            )
            tasks.append((service_name, task))
        
        # Wait for all checks to complete
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result
                await self._process_health_result(result)
            except Exception as e:
                self.logger.error(f"Health check failed for {service_name}: {e}")
                # Create failure result
                result = HealthCheckResult(
                    service_name=service_name,
                    check_type=HealthCheckType.BASIC,
                    success=False,
                    error_message=str(e)
                )
                results[service_name] = result
                await self._process_health_result(result)
        
        return results
    
    async def check_service_health(self, service_name: str) -> HealthCheckResult:
        """
        Check health of a specific service.
        
        Args:
            service_name: Name of service to check
            
        Returns:
            HealthCheckResult with check details
        """
        if service_name not in self.services:
            return HealthCheckResult(
                service_name=service_name,
                check_type=HealthCheckType.BASIC,
                success=False,
                error_message="Service not registered"
            )
        
        service = self.services[service_name]
        start_time = time.time()
        
        try:
            # Basic health check
            is_healthy = await asyncio.wait_for(
                service.health_check(),
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                service_name=service_name,
                check_type=HealthCheckType.BASIC,
                success=is_healthy,
                response_time=response_time,
                details={'check_duration': response_time}
            )
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name=service_name,
                check_type=HealthCheckType.BASIC,
                success=False,
                response_time=response_time,
                error_message="Health check timeout"
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name=service_name,
                check_type=HealthCheckType.BASIC,
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    async def _process_health_result(self, result: HealthCheckResult) -> None:
        """
        Process health check result and update service status.
        
        Args:
            result: Health check result to process
        """
        service_name = result.service_name
        status = self.health_status.get(service_name)
        
        if not status:
            return
        
        # Update statistics
        status.total_checks += 1
        status.last_check = result.timestamp
        
        if result.success:
            status.success_count += 1
            status.consecutive_failures = 0
            
            # Update service status if it was unhealthy
            if not status.is_healthy:
                status.is_healthy = True
                self.logger.info(f"Service {service_name} is now healthy")
                await self._notify_health_change(service_name, True)
        else:
            status.failure_count += 1
            status.consecutive_failures += 1
            status.last_error = result.error_message
            
            # Mark as unhealthy if it was healthy
            if status.is_healthy:
                status.is_healthy = False
                self.logger.warning(f"Service {service_name} is now unhealthy: {result.error_message}")
                await self._notify_health_change(service_name, False)
            
            # Blacklist if too many consecutive failures
            if status.consecutive_failures >= self.failure_threshold and not status.is_blacklisted:
                await self._blacklist_service(service_name)
        
        # Update average response time
        if result.response_time > 0:
            current_avg = status.average_response_time
            total = status.total_checks
            status.average_response_time = ((current_avg * (total - 1)) + result.response_time) / total
        
        # Update service status in the service object
        if service_name in self.services:
            service = self.services[service_name]
            if status.is_blacklisted:
                service.status = ServiceStatus.BLACKLISTED
            elif not status.is_healthy:
                service.status = ServiceStatus.FAILED
            else:
                service.status = ServiceStatus.ACTIVE
    
    async def _blacklist_service(self, service_name: str) -> None:
        """
        Blacklist a service temporarily.
        
        Args:
            service_name: Name of service to blacklist
        """
        status = self.health_status.get(service_name)
        if not status:
            return
        
        status.blacklisted_until = datetime.now() + timedelta(seconds=self.blacklist_duration)
        
        self.logger.warning(f"Blacklisted service {service_name} for {self.blacklist_duration} seconds "
                          f"due to {status.consecutive_failures} consecutive failures")
        
        await self._notify_blacklist_change(service_name, True)
        
        # Schedule unblacklisting if event loop is running
        try:
            asyncio.create_task(self._schedule_unblacklist(service_name))
        except RuntimeError:
            # No event loop running, skip automatic unblacklisting
            self.logger.warning(f"Cannot schedule automatic unblacklisting for {service_name} - no event loop")
    
    async def _schedule_unblacklist(self, service_name: str) -> None:
        """
        Schedule automatic unblacklisting of a service.
        
        Args:
            service_name: Name of service to unblacklist
        """
        await asyncio.sleep(self.blacklist_duration)
        
        status = self.health_status.get(service_name)
        if status and status.is_blacklisted:
            status.blacklisted_until = None
            status.consecutive_failures = 0  # Reset failure count
            
            self.logger.info(f"Automatically unblacklisted service {service_name}")
            await self._notify_blacklist_change(service_name, False)
    
    async def _notify_health_change(self, service_name: str, is_healthy: bool) -> None:
        """Notify callbacks of health status change."""
        for callback in self.health_change_callbacks:
            try:
                callback(service_name, is_healthy)
            except Exception as e:
                self.logger.error(f"Error in health change callback: {e}")
    
    async def _notify_blacklist_change(self, service_name: str, is_blacklisted: bool) -> None:
        """Notify callbacks of blacklist status change."""
        for callback in self.blacklist_callbacks:
            try:
                callback(service_name, is_blacklisted)
            except Exception as e:
                self.logger.error(f"Error in blacklist change callback: {e}")
    
    def get_healthy_services(self) -> List[str]:
        """
        Get list of currently healthy services.
        
        Returns:
            List of healthy service names
        """
        healthy_services = []
        
        for service_name, status in self.health_status.items():
            if status.is_healthy and not status.is_blacklisted:
                healthy_services.append(service_name)
        
        return healthy_services
    
    def get_service_health_status(self, service_name: str) -> Optional[ServiceHealthStatus]:
        """
        Get health status for a specific service.
        
        Args:
            service_name: Name of service
            
        Returns:
            ServiceHealthStatus or None if not found
        """
        return self.health_status.get(service_name)
    
    def get_all_health_status(self) -> Dict[str, ServiceHealthStatus]:
        """
        Get health status for all services.
        
        Returns:
            Dictionary of service names to health status
        """
        return self.health_status.copy()
    
    def manually_blacklist_service(self, service_name: str, duration_seconds: Optional[int] = None) -> None:
        """
        Manually blacklist a service.
        
        Args:
            service_name: Name of service to blacklist
            duration_seconds: Duration to blacklist (uses default if None)
        """
        status = self.health_status.get(service_name)
        if not status:
            self.logger.warning(f"Cannot blacklist unknown service: {service_name}")
            return
        
        duration = duration_seconds or self.blacklist_duration
        status.blacklisted_until = datetime.now() + timedelta(seconds=duration)
        
        self.logger.info(f"Manually blacklisted service {service_name} for {duration} seconds")
        
        # Schedule unblacklisting if event loop is running
        try:
            asyncio.create_task(self._schedule_unblacklist(service_name))
        except RuntimeError:
            # No event loop running, skip automatic unblacklisting
            self.logger.warning(f"Cannot schedule automatic unblacklisting for {service_name} - no event loop")
    
    def manually_unblacklist_service(self, service_name: str) -> None:
        """
        Manually unblacklist a service.
        
        Args:
            service_name: Name of service to unblacklist
        """
        status = self.health_status.get(service_name)
        if not status:
            self.logger.warning(f"Cannot unblacklist unknown service: {service_name}")
            return
        
        if status.is_blacklisted:
            status.blacklisted_until = None
            status.consecutive_failures = 0
            self.logger.info(f"Manually unblacklisted service {service_name}")
        else:
            self.logger.info(f"Service {service_name} is not blacklisted")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.stop_monitoring()
        self.services.clear()
        self.health_status.clear()
        self.health_change_callbacks.clear()
        self.blacklist_callbacks.clear()