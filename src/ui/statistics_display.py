"""
Real-time statistics display for the Instagram auto signup system.
"""

import os
import time
import json
import curses
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta

from src.core.statistics_manager import get_statistics_manager, StatisticsManager


class StatisticsDisplay:
    """Terminal-based UI for displaying real-time statistics."""
    
    def __init__(self, refresh_interval: float = 1.0):
        self.stats_manager = get_statistics_manager()
        self.refresh_interval = refresh_interval
        self.running = False
        self.display_thread = None
    
    def start(self) -> None:
        """Start the statistics display in a separate thread."""
        if self.running:
            return
        
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop)
        self.display_thread.daemon = True
        self.display_thread.start()
    
    def stop(self) -> None:
        """Stop the statistics display."""
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=1.0)
    
    def _display_loop(self) -> None:
        """Main display loop."""
        try:
            curses.wrapper(self._curses_main)
        except Exception as e:
            print(f"Error in statistics display: {e}")
            self.running = False
    
    def _curses_main(self, stdscr) -> None:
        """Main curses application."""
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # Success
        curses.init_pair(2, curses.COLOR_RED, -1)    # Failure
        curses.init_pair(3, curses.COLOR_YELLOW, -1) # Warning
        curses.init_pair(4, curses.COLOR_CYAN, -1)   # Info
        curses.init_pair(5, curses.COLOR_MAGENTA, -1) # Highlight
        
        # Main display loop
        while self.running:
            try:
                # Get terminal size
                max_y, max_x = stdscr.getmaxyx()
                
                # Clear screen
                stdscr.clear()
                
                # Get statistics
                stats = self.stats_manager.get_global_statistics()
                service_perf = self.stats_manager.get_service_performance()
                
                # Display header
                self._draw_header(stdscr, stats)
                
                # Display global statistics
                self._draw_global_stats(stdscr, stats, start_y=3)
                
                # Display current cycle if active
                if 'current_cycle' in stats:
                    self._draw_current_cycle(stdscr, stats['current_cycle'], start_y=10)
                    cycle_end_y = 15
                else:
                    cycle_end_y = 10
                
                # Display error statistics
                self._draw_error_stats(stdscr, stats, start_y=cycle_end_y)
                
                # Display service performance
                self._draw_service_performance(stdscr, service_perf, start_y=cycle_end_y + 7)
                
                # Refresh the screen
                stdscr.refresh()
                
                # Wait for refresh interval
                time.sleep(self.refresh_interval)
                
            except Exception as e:
                # Handle any errors
                stdscr.clear()
                stdscr.addstr(0, 0, f"Error: {str(e)}")
                stdscr.refresh()
                time.sleep(2)
    
    def _draw_header(self, stdscr, stats: Dict[str, Any]) -> None:
        """Draw the header section."""
        max_y, max_x = stdscr.getmaxyx()
        
        # Draw title
        title = "INSTAGRAM AUTO SIGNUP - REAL-TIME STATISTICS"
        stdscr.addstr(0, (max_x - len(title)) // 2, title, curses.A_BOLD)
        
        # Draw uptime
        uptime_str = f"Uptime: {timedelta(seconds=int(stats['uptime']))}"
        stdscr.addstr(1, (max_x - len(uptime_str)) // 2, uptime_str)
        
        # Draw separator
        stdscr.addstr(2, 0, "=" * max_x)
    
    def _draw_global_stats(self, stdscr, stats: Dict[str, Any], start_y: int) -> None:
        """Draw the global statistics section."""
        max_y, max_x = stdscr.getmaxyx()
        
        # Section title
        stdscr.addstr(start_y, 2, "GLOBAL STATISTICS", curses.A_BOLD)
        
        # Draw statistics
        y = start_y + 1
        
        # Total attempts
        stdscr.addstr(y, 4, f"Total Attempts: {stats['total_attempts']}")
        y += 1
        
        # Successful creations
        stdscr.addstr(y, 4, "Successful Creations: ")
        stdscr.addstr(f"{stats['successful_creations']}", curses.color_pair(1))
        y += 1
        
        # Failed creations
        stdscr.addstr(y, 4, "Failed Creations: ")
        stdscr.addstr(f"{stats['failed_creations']}", curses.color_pair(2))
        y += 1
        
        # Success rate
        stdscr.addstr(y, 4, "Success Rate: ")
        success_rate = stats['success_rate']
        color = curses.color_pair(1) if success_rate >= 70 else (
            curses.color_pair(3) if success_rate >= 40 else curses.color_pair(2)
        )
        stdscr.addstr(f"{success_rate:.2f}%", color)
        y += 1
        
        # Average creation time
        stdscr.addstr(y, 4, f"Average Creation Time: {stats['average_creation_time']:.2f} seconds")
        y += 1
        
        # Accounts per hour
        stdscr.addstr(y, 4, f"Accounts Per Hour: {stats['accounts_per_hour']:.2f}")
    
    def _draw_current_cycle(self, stdscr, cycle: Dict[str, Any], start_y: int) -> None:
        """Draw the current cycle section."""
        max_y, max_x = stdscr.getmaxyx()
        
        # Calculate elapsed time
        start_time = datetime.fromisoformat(cycle['start_time'])
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Section title
        stdscr.addstr(start_y, 2, f"CURRENT CYCLE: {cycle['cycle_id']} (Running for {elapsed:.1f} seconds)", curses.A_BOLD)
        
        # Draw cycle statistics
        y = start_y + 1
        
        # Attempts
        stdscr.addstr(y, 4, f"Attempts: {cycle['total_attempts']}")
        y += 1
        
        # Successful
        stdscr.addstr(y, 4, "Successful: ")
        stdscr.addstr(f"{cycle['successful_creations']}", curses.color_pair(1))
        y += 1
        
        # Failed
        stdscr.addstr(y, 4, "Failed: ")
        stdscr.addstr(f"{cycle['failed_creations']}", curses.color_pair(2))
        y += 1
        
        # Success rate
        stdscr.addstr(y, 4, "Success Rate: ")
        success_rate = cycle['success_rate']
        color = curses.color_pair(1) if success_rate >= 70 else (
            curses.color_pair(3) if success_rate >= 40 else curses.color_pair(2)
        )
        stdscr.addstr(f"{success_rate:.2f}%", color)
    
    def _draw_error_stats(self, stdscr, stats: Dict[str, Any], start_y: int) -> None:
        """Draw the error statistics section."""
        max_y, max_x = stdscr.getmaxyx()
        
        # Section title
        stdscr.addstr(start_y, 2, "TOP ERRORS", curses.A_BOLD)
        
        # Draw error statistics
        y = start_y + 1
        
        if not stats['error_counts']:
            stdscr.addstr(y, 4, "No errors recorded", curses.color_pair(1))
            return
        
        # Sort errors by count
        sorted_errors = sorted(
            stats['error_counts'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Show top 5 errors
        
        for error_type, count in sorted_errors:
            if y < max_y - 1:  # Ensure we don't write past the screen
                stdscr.addstr(y, 4, f"{error_type}: ")
                stdscr.addstr(f"{count}", curses.color_pair(2))
                y += 1
    
    def _draw_service_performance(self, stdscr, service_perf: Dict[str, Dict[str, Any]], start_y: int) -> None:
        """Draw the service performance section."""
        max_y, max_x = stdscr.getmaxyx()
        
        # Section title
        stdscr.addstr(start_y, 2, "SERVICE PERFORMANCE", curses.A_BOLD)
        
        if not service_perf:
            stdscr.addstr(start_y + 1, 4, "No service data available")
            return
        
        # Group by service type
        by_type = {}
        for key, perf in service_perf.items():
            service_type = perf['service_type']
            if service_type not in by_type:
                by_type[service_type] = []
            by_type[service_type].append(perf)
        
        # Display each service type
        y = start_y + 1
        for service_type, services in by_type.items():
            if y >= max_y - 1:
                break
            
            # Service type header
            stdscr.addstr(y, 4, f"{service_type.upper()} SERVICES:", curses.color_pair(4) | curses.A_BOLD)
            y += 1
            
            # Sort by success rate
            sorted_services = sorted(
                services,
                key=lambda x: x['success_rate'],
                reverse=True
            )
            
            for perf in sorted_services:
                if y >= max_y - 1:
                    break
                
                # Service name and success rate
                stdscr.addstr(y, 6, f"{perf['service_name']}: ")
                
                success_rate = perf['success_rate']
                color = curses.color_pair(1) if success_rate >= 70 else (
                    curses.color_pair(3) if success_rate >= 40 else curses.color_pair(2)
                )
                stdscr.addstr(f"{success_rate:.2f}% success rate, ", color)
                stdscr.addstr(f"{perf['total_uses']} uses")
                
                y += 1
            
            # Add a blank line between service types
            y += 1


def start_statistics_display() -> StatisticsDisplay:
    """Start the statistics display and return the instance."""
    display = StatisticsDisplay()
    display.start()
    return display


if __name__ == "__main__":
    # Test the statistics display
    stats_manager = get_statistics_manager()
    
    # Simulate some data
    stats_manager.start_cycle()
    
    # Simulate some successful attempts
    for i in range(10):
        stats_manager.record_attempt(True, 5.0 + i * 0.2)
    
    # Simulate some failed attempts
    for i in range(5):
        stats_manager.record_attempt(False, 3.0, f"Error{i}")
    
    # Simulate service usage
    stats_manager.record_service_usage("OneSecMail", "email", True, 1.2)
    stats_manager.record_service_usage("MailTM", "email", False, 2.5, "Timeout")
    stats_manager.record_service_usage("Proxy1", "proxy", True, 0.5)
    stats_manager.record_service_usage("Proxy2", "proxy", False, 3.0, "Connection refused")
    
    # Start the display
    display = start_statistics_display()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        display.stop()