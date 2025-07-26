"""
Main controller system for the Instagram auto signup system.

This module implements the MainController class that orchestrates the account creation
process in cycles, manages system state, and handles graceful shutdown.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import threading
from enum import Enum

from .interfaces import BaseService
from .config import config_manager
from .statistics_manager import get_statistics_manager
from .performance_optimizer import get_performance_optimizer
from .error_handler import error_handler
from .adaptive_failure_handler import get_adaptive_failure_handler
from ..services.account_creator import AccountCreator


logger = logging.getLogger(__name__)


class SystemState(Enum):
    """System state enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"
    STOPPED = "stopped"


class MainController:
    """
    Main controller for the Instagram auto signup system.
    
    Orchestrates the account creation process in cycles, manages system state,
    and handles graceful shutdown.
    """
    
    def __init__(self, account_creator: AccountCreator):
        """
        Initialize the main controller.
        
        Args:
            account_creator: Account creator service
        """
        self.account_creator = account_creator
        self.config = config_manager.get_config()
        self.stats_manager = get_statistics_manager()
        self.performance_optimizer = get_performance_optimizer()
        self.adaptive_failure_handler = get_adaptive_failure_handler()
        
        # System state
        self.state = SystemState.INITIALIZING
        self.running = False
        self.creation_thread = None
        self.shutdown_event = threading.Event()
        
        # Cycle management
        self.current_cycle_id = None
        self.cycle_start_time = None
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
        
        # Register config change handler
        config_manager.register_change_callback(self._handle_config_change)
        
        logger.info("MainController initialized")
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame) -> None:
        """Handle termination signals."""
        logger.info(f"Received signal {sig}, initiating graceful shutdown")
        self.stop_creation()
    
    def _handle_config_change(self, new_config) -> None:
        """Handle configuration changes."""
        logger.info("Configuration changed, updating controller settings")
        self.config = new_config
    
    async def initialize_services(self) -> bool:
        """
        Initialize all required services.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            logger.info("Initializing services...")
            self.state = SystemState.INITIALIZING
            
            # Initialize account creator
            if not await self.account_creator.initialize():
                logger.error("Failed to initialize account creator")
                self.state = SystemState.ERROR
                return False
            
            # Start performance optimizer if enabled
            if self.config.performance_optimization_enabled:
                self.performance_optimizer.start_optimizer()
            
            # Start statistics display
            self.stats_manager.start_display_thread()
            
            self.state = SystemState.STOPPED
            logger.info("Services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            self.state = SystemState.ERROR
            return False
    
    def start_continuous_creation(self) -> None:
        """Start continuous account creation in a separate thread."""
        if self.running:
            logger.warning("Account creation already running")
            return
        
        self.running = True
        self.shutdown_event.clear()
        self.state = SystemState.RUNNING
        
        # Start creation thread
        self.creation_thread = threading.Thread(target=self._creation_loop)
        self.creation_thread.daemon = True
        self.creation_thread.start()
        
        logger.info("Continuous account creation started")
    
    def stop_creation(self) -> None:
        """Stop account creation gracefully."""
        if not self.running:
            logger.warning("Account creation not running")
            return
        
        logger.info("Stopping account creation...")
        self.state = SystemState.SHUTTING_DOWN
        self.running = False
        self.shutdown_event.set()
        
        # Wait for creation thread to finish
        if self.creation_thread and self.creation_thread.is_alive():
            self.creation_thread.join(timeout=30.0)
            if self.creation_thread.is_alive():
                logger.warning("Creation thread did not terminate within timeout")
        
        self.state = SystemState.STOPPED
        logger.info("Account creation stopped")
    
    def pause_creation(self) -> None:
        """Pause account creation."""
        if self.state != SystemState.RUNNING:
            logger.warning(f"Cannot pause: current state is {self.state.value}")
            return
        
        self.state = SystemState.PAUSED
        logger.info("Account creation paused")
    
    def resume_creation(self) -> None:
        """Resume account creation."""
        if self.state != SystemState.PAUSED:
            logger.warning(f"Cannot resume: current state is {self.state.value}")
            return
        
        self.state = SystemState.RUNNING
        logger.info("Account creation resumed")
    
    def _creation_loop(self) -> None:
        """Main creation loop running in a separate thread."""
        logger.info("Starting creation loop")
        
        while self.running:
            try:
                # Start a new cycle
                self.current_cycle_id = self.stats_manager.start_cycle()
                self.cycle_start_time = datetime.now()
                logger.info(f"Starting cycle {self.current_cycle_id}")
                
                # Create accounts
                self._execute_creation_cycle()
                
                # End cycle
                cycle_stats = self.stats_manager.end_cycle()
                logger.info(f"Cycle {self.current_cycle_id} completed: "
                           f"{cycle_stats.successful_creations} successful, "
                           f"{cycle_stats.failed_creations} failed")
                
                # Check for high failure rate
                if cycle_stats.total_attempts > 0:
                    high_failure = self.adaptive_failure_handler.check_failure_rate(cycle_stats)
                    if high_failure:
                        logger.warning("High failure rate detected, applying adaptive strategies")
                        actions = self.adaptive_failure_handler.handle_high_failure_rate()
                        logger.info(f"Adaptive actions taken: {actions}")
                
                # Wait for next cycle if not shutting down
                if self.running and not self.shutdown_event.is_set():
                    interval = self.config.creation_interval
                    logger.info(f"Waiting {interval} seconds until next cycle")
                    
                    # Use wait with timeout to allow for graceful shutdown
                    self.shutdown_event.wait(interval)
                
            except Exception as e:
                logger.error(f"Error in creation cycle: {e}", exc_info=True)
                error_handler.handle_error(e, "creation_cycle")
                
                # Brief pause before continuing to avoid rapid error loops
                time.sleep(5)
        
        logger.info("Creation loop terminated")
    
    def _execute_creation_cycle(self) -> None:
        """Execute a single account creation cycle."""
        # Run account creation asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create accounts concurrently up to max_concurrent_creations
            max_concurrent = self.config.max_concurrent_creations
            loop.run_until_complete(self._create_accounts_concurrently(max_concurrent))
            
        finally:
            loop.close()
    
    async def _create_accounts_concurrently(self, max_concurrent: int) -> None:
        """
        Create accounts concurrently.
        
        Args:
            max_concurrent: Maximum number of concurrent creations
        """
        tasks = []
        for _ in range(max_concurrent):
            if not self.running or self.state != SystemState.RUNNING:
                break
            
            task = asyncio.create_task(self._create_single_account())
            tasks.append(task)
        
        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _create_single_account(self) -> None:
        """Create a single account and handle the result."""
        try:
            # Check if we should continue
            if not self.running or self.state != SystemState.RUNNING:
                return
            
            # Create account
            start_time = time.time()
            result = await self.account_creator.create_account()
            creation_time = time.time() - start_time
            
            # Record result in statistics
            self.stats_manager.record_attempt(
                success=result.success,
                creation_time=creation_time,
                error_type=result.error_code if not result.success else None
            )
            
            if result.success:
                logger.info(f"Account created successfully: {result.account_data.username}")
            else:
                logger.warning(f"Account creation failed: {result.error_message}")
            
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            error_handler.handle_error(e, "create_single_account")
            
            # Record failure in statistics
            self.stats_manager.record_attempt(
                success=False,
                creation_time=0.0,
                error_type=type(e).__name__
            )
    
    def get_adaptive_status(self) -> Dict[str, Any]:
        """
        Get status of the adaptive failure handler.
        
        Returns:
            Dict[str, Any]: Adaptive failure handler status
        """
        return self.adaptive_failure_handler.get_status()
    
    def get_system_state(self) -> Dict[str, Any]:
        """
        Get current system state information.
        
        Returns:
            Dict[str, Any]: System state information
        """
        return {
            "state": self.state.value,
            "running": self.running,
            "current_cycle_id": self.current_cycle_id,
            "cycle_start_time": self.cycle_start_time.isoformat() if self.cycle_start_time else None,
            "statistics": self.stats_manager.get_global_statistics(),
            "error_stats": error_handler.get_error_stats(),
            "adaptive_status": self.get_adaptive_status()
        }
    
    async def shutdown(self) -> None:
        """Perform graceful shutdown of all services."""
        logger.info("Performing graceful shutdown")
        
        # Stop creation first
        self.stop_creation()
        
        # Stop performance optimizer
        if self.performance_optimizer:
            self.performance_optimizer.stop_optimizer()
        
        # Stop statistics display
        if self.stats_manager:
            self.stats_manager.stop_display_thread()
        
        # Cleanup account creator
        if self.account_creator:
            await self.account_creator.cleanup()
        
        logger.info("Graceful shutdown completed")