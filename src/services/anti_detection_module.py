"""
Anti-detection module for simulating human-like behavior during Instagram account creation.
Implements sophisticated techniques to avoid detection by Instagram's anti-bot systems.
"""

import random
import time
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable
import json
import os
from collections import defaultdict, deque

from ..core.interfaces import BaseService, ServiceStatus


@dataclass
class TypingPattern:
    """Represents a human typing pattern."""
    base_delay: float
    variance: float
    burst_probability: float
    pause_probability: float
    error_probability: float


@dataclass
class MouseMovementPattern:
    """Represents mouse movement characteristics."""
    movement_speed: float
    curve_intensity: float
    pause_probability: float
    overshoot_probability: float


@dataclass
class InteractionTiming:
    """Timing patterns for various interactions."""
    reading_time_per_word: float
    form_field_pause: Tuple[float, float]
    button_hover_time: Tuple[float, float]
    page_load_wait: Tuple[float, float]


class CaptchaType(Enum):
    """Types of CAPTCHAs that can be detected."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    IMAGE_CAPTCHA = "image_captcha"
    TEXT_CAPTCHA = "text_captcha"
    UNKNOWN = "unknown"


@dataclass
class CaptchaDetection:
    """Information about a detected CAPTCHA."""
    captcha_type: CaptchaType
    element: Optional[WebElement]
    confidence: float
    bypass_strategy: str
    detected_at: datetime


@dataclass
class BehaviorPattern:
    """Represents a learned behavior pattern."""
    pattern_id: str
    typing_pattern: TypingPattern
    mouse_pattern: MouseMovementPattern
    interaction_timing: InteractionTiming
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for this pattern."""
        total = self.success_count + self.failure_count
        return (self.success_count / total) if total > 0 else 0.0
    
    @property
    def usage_count(self) -> int:
        """Total usage count."""
        return self.success_count + self.failure_count


@dataclass
class DetectionEvent:
    """Represents a detection event and context."""
    event_type: str  # 'captcha', 'block', 'timeout', 'success'
    timestamp: datetime
    pattern_id: str
    context: Dict[str, Any]
    success: bool


@dataclass
class StrategyPerformance:
    """Tracks performance of different strategies."""
    strategy_name: str
    success_count: int = 0
    failure_count: int = 0
    avg_response_time: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return (self.success_count / total) if total > 0 else 0.0


class AntiDetectionModule(BaseService):
    """
    Advanced anti-detection module that simulates human-like behavior
    to avoid detection by Instagram's anti-bot systems.
    """
    
    def __init__(self, name: str = "AntiDetectionModule"):
        super().__init__(name)
        self.logger = logging.getLogger(__name__)
        
        # Human behavior patterns
        self.typing_patterns = self._initialize_typing_patterns()
        self.mouse_patterns = self._initialize_mouse_patterns()
        self.interaction_timings = self._initialize_interaction_timings()
        
        # Behavioral state tracking
        self.current_typing_pattern = random.choice(self.typing_patterns)
        self.current_mouse_pattern = random.choice(self.mouse_patterns)
        self.session_start_time = datetime.now()
        self.interaction_count = 0
        
        # Performance tracking
        self.successful_interactions = 0
        self.failed_interactions = 0
        
        # CAPTCHA detection and handling
        self.captcha_detections = []
        self.captcha_bypass_strategies = self._initialize_captcha_strategies()
        self.resource_switch_callback: Optional[Callable] = None
        
        # Adaptive behavior learning system
        self.learned_patterns: Dict[str, BehaviorPattern] = {}
        self.detection_events: deque = deque(maxlen=1000)  # Keep last 1000 events
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        self.current_pattern_id: Optional[str] = None
        
        # Pattern learning configuration
        self.learning_enabled = True
        self.min_pattern_usage = 10  # Minimum usage before considering pattern reliable
        self.pattern_adaptation_threshold = 0.3  # Adapt if success rate drops below 30%
        self.success_pattern_threshold = 0.8  # Consider pattern successful if above 80%
        
        # Load existing learned patterns
        self._load_learned_patterns()
    
    def _load_learned_patterns(self) -> None:
        """Load previously learned behavior patterns."""
        try:
            patterns_file = "data/learned_patterns.json"
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r') as f:
                    data = json.load(f)
                    # Load patterns from file (simplified for now)
                    self.logger.info(f"Loaded {len(data.get('patterns', []))} learned patterns")
            else:
                self.logger.info("No learned patterns file found, starting fresh")
        except Exception as e:
            self.logger.warning(f"Failed to load learned patterns: {e}")
    
    def _initialize_captcha_strategies(self) -> Dict[str, Any]:
        """Initialize CAPTCHA bypass strategies."""
        return {
            "recaptcha_v2": {
                "detection_selectors": [
                    "iframe[src*='recaptcha']",
                    ".g-recaptcha",
                    "#recaptcha"
                ],
                "bypass_method": "resource_switch"
            },
            "hcaptcha": {
                "detection_selectors": [
                    "iframe[src*='hcaptcha']",
                    ".h-captcha",
                    "#hcaptcha"
                ],
                "bypass_method": "resource_switch"
            },
            "funcaptcha": {
                "detection_selectors": [
                    "iframe[src*='funcaptcha']",
                    ".funcaptcha",
                    "#funcaptcha"
                ],
                "bypass_method": "resource_switch"
            }
        }

    async def initialize(self) -> bool:
        """Initialize the anti-detection module."""
        try:
            self.logger.info("Initializing AntiDetectionModule")
            self.status = ServiceStatus.ACTIVE
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize AntiDetectionModule: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup module resources."""
        self.logger.info("Cleaning up AntiDetectionModule")
        self.status = ServiceStatus.INACTIVE
    
    async def health_check(self) -> bool:
        """Check if the module is healthy."""
        return self.status == ServiceStatus.ACTIVE
    
    def _initialize_typing_patterns(self) -> List[TypingPattern]:
        """Initialize various human typing patterns."""
        return [
            # Fast typist
            TypingPattern(
                base_delay=0.08,
                variance=0.04,
                burst_probability=0.3,
                pause_probability=0.1,
                error_probability=0.02
            ),
            # Average typist
            TypingPattern(
                base_delay=0.15,
                variance=0.08,
                burst_probability=0.2,
                pause_probability=0.15,
                error_probability=0.05
            ),
            # Slow/careful typist
            TypingPattern(
                base_delay=0.25,
                variance=0.12,
                burst_probability=0.1,
                pause_probability=0.25,
                error_probability=0.08
            ),
            # Hunt and peck typist
            TypingPattern(
                base_delay=0.4,
                variance=0.2,
                burst_probability=0.05,
                pause_probability=0.3,
                error_probability=0.12
            )
        ]
    
    def _initialize_mouse_patterns(self) -> List[MouseMovementPattern]:
        """Initialize various mouse movement patterns."""
        return [
            # Precise user
            MouseMovementPattern(
                movement_speed=1.2,
                curve_intensity=0.3,
                pause_probability=0.1,
                overshoot_probability=0.05
            ),
            # Average user
            MouseMovementPattern(
                movement_speed=1.0,
                curve_intensity=0.5,
                pause_probability=0.2,
                overshoot_probability=0.15
            ),
            # Imprecise user
            MouseMovementPattern(
                movement_speed=0.8,
                curve_intensity=0.8,
                pause_probability=0.3,
                overshoot_probability=0.25
            )
        ]
    
    def _initialize_interaction_timings(self) -> InteractionTiming:
        """Initialize interaction timing patterns."""
        return InteractionTiming(
            reading_time_per_word=0.3,
            form_field_pause=(0.5, 2.0),
            button_hover_time=(0.3, 1.2),
            page_load_wait=(1.0, 3.0)
        )
    
    async def simulate_human_typing(self, element: WebElement, text: str, 
                                  clear_first: bool = True) -> bool:
        """
        Simulate human-like typing with realistic delays, errors, and corrections.
        
        Args:
            element: The web element to type into
            text: The text to type
            clear_first: Whether to clear the element first
            
        Returns:
            bool: True if typing was successful
        """
        try:
            if clear_first:
                element.clear()
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Focus on the element
            element.click()
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            typed_text = ""
            i = 0
            
            while i < len(text):
                char = text[i]
                
                # Simulate typing errors
                if random.random() < self.current_typing_pattern.error_probability:
                    # Type wrong character
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    element.send_keys(wrong_char)
                    typed_text += wrong_char
                    
                    # Pause to "notice" the error
                    await asyncio.sleep(random.uniform(0.2, 0.8))
                    
                    # Backspace to correct
                    element.send_keys('\b')
                    typed_text = typed_text[:-1]
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Type the correct character
                element.send_keys(char)
                typed_text += char
                
                # Calculate delay for this keystroke
                delay = self._calculate_keystroke_delay(char, i, len(text))
                await asyncio.sleep(delay)
                
                # Simulate occasional pauses (thinking)
                if random.random() < self.current_typing_pattern.pause_probability:
                    pause_duration = random.uniform(0.5, 2.0)
                    await asyncio.sleep(pause_duration)
                
                i += 1
            
            # Final pause after typing
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
            self.successful_interactions += 1
            self.interaction_count += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error in simulate_human_typing: {e}")
            self.failed_interactions += 1
            return False
    
    def _calculate_keystroke_delay(self, char: str, position: int, total_length: int) -> float:
        """Calculate realistic delay between keystrokes."""
        base_delay = self.current_typing_pattern.base_delay
        variance = self.current_typing_pattern.variance
        
        # Add variance
        delay = base_delay + random.uniform(-variance, variance)
        
        # Adjust for character type
        if char.isspace():
            delay *= 1.2  # Slightly longer for spaces
        elif char.isupper():
            delay *= 1.1  # Slightly longer for capitals (shift key)
        elif char.isdigit():
            delay *= 0.9  # Slightly faster for numbers
        
        # Adjust for position in text
        if position == 0:
            delay *= 1.5  # Longer delay for first character
        elif position == total_length - 1:
            delay *= 1.2  # Slightly longer for last character
        
        # Simulate burst typing occasionally
        if random.random() < self.current_typing_pattern.burst_probability:
            delay *= 0.5
        
        return max(0.02, delay)  # Minimum 20ms delay
    
    async def simulate_mouse_movement(self, driver: WebDriver, target_element: WebElement,
                                    hover_before_click: bool = True) -> bool:
        """
        Simulate human-like mouse movement to an element.
        
        Args:
            driver: WebDriver instance
            target_element: Element to move to
            hover_before_click: Whether to hover before clicking
            
        Returns:
            bool: True if movement was successful
        """
        try:
            actions = ActionChains(driver)
            
            # Get current mouse position (approximate)
            current_pos = self._get_approximate_mouse_position(driver)
            target_pos = self._get_element_center(target_element)
            
            # Generate curved path to target
            path_points = self._generate_mouse_path(current_pos, target_pos)
            
            # Move along the path
            for point in path_points:
                if point[0] != 0 or point[1] != 0:  # Only move if there's actual movement
                    actions.move_by_offset(point[0], point[1])
                
                # Add small random pauses during movement
                if random.random() < self.current_mouse_pattern.pause_probability:
                    actions.pause(random.uniform(0.01, 0.05))
            
            # Hover over target if requested
            if hover_before_click:
                try:
                    actions.move_to_element(target_element)
                    hover_time = random.uniform(*self.interaction_timings.button_hover_time)
                    actions.pause(hover_time)
                except Exception:
                    # Fallback: move to element center coordinates
                    target_center = self._get_element_center(target_element)
                    current_center = self._get_approximate_mouse_position(driver)
                    offset_x = target_center[0] - current_center[0]
                    offset_y = target_center[1] - current_center[1]
                    actions.move_by_offset(offset_x, offset_y)
                    hover_time = random.uniform(*self.interaction_timings.button_hover_time)
                    actions.pause(hover_time)
            
            # Simulate overshoot occasionally
            if random.random() < self.current_mouse_pattern.overshoot_probability:
                overshoot_x = random.randint(-5, 5)
                overshoot_y = random.randint(-5, 5)
                actions.move_by_offset(overshoot_x, overshoot_y)
                actions.pause(random.uniform(0.1, 0.3))
                actions.move_by_offset(-overshoot_x, -overshoot_y)
            
            # Execute the action chain
            actions.perform()
            
            self.successful_interactions += 1
            self.interaction_count += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error in simulate_mouse_movement: {e}")
            self.failed_interactions += 1
            return False
    
    def _get_approximate_mouse_position(self, driver: WebDriver) -> Tuple[int, int]:
        """Get approximate current mouse position."""
        # Since we can't get actual mouse position, use viewport center as approximation
        viewport_size = driver.get_window_size()
        return (viewport_size['width'] // 2, viewport_size['height'] // 2)
    
    def _get_element_center(self, element: WebElement) -> Tuple[int, int]:
        """Get the center coordinates of an element."""
        location = element.location
        size = element.size
        center_x = location['x'] + size['width'] // 2
        center_y = location['y'] + size['height'] // 2
        return (center_x, center_y)
    
    def _generate_mouse_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Generate a curved path between two points."""
        path_points = []
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = (dx**2 + dy**2)**0.5
        
        if distance < 10:  # Very short distance, move directly
            return [(dx, dy)]
        
        # Number of steps based on distance
        steps = max(5, int(distance / 20))
        
        for i in range(1, steps + 1):
            progress = i / steps
            
            # Linear interpolation
            x = start[0] + dx * progress
            y = start[1] + dy * progress
            
            # Add curve using sine wave
            curve_offset = self.current_mouse_pattern.curve_intensity * 20 * \
                          math.sin(progress * math.pi)
            
            # Apply curve perpendicular to movement direction
            if abs(dx) > abs(dy):
                y += curve_offset
            else:
                x += curve_offset
            
            # Add small random variations
            x += random.uniform(-2, 2)
            y += random.uniform(-2, 2)
            
            # Calculate relative movement from previous point
            if i == 1:
                rel_x = int(x - start[0])
                rel_y = int(y - start[1])
            else:
                # Calculate cumulative position from previous points
                cumulative_x = start[0] + sum(p[0] for p in path_points)
                cumulative_y = start[1] + sum(p[1] for p in path_points)
                rel_x = int(x - cumulative_x)
                rel_y = int(y - cumulative_y)
            
            path_points.append((rel_x, rel_y))
        
        return path_points
    
    async def add_random_interaction_delay(self, interaction_type: str = "general") -> None:
        """
        Add realistic delays between interactions based on human behavior patterns.
        
        Args:
            interaction_type: Type of interaction (form_field, button, page_load, etc.)
        """
        if interaction_type == "form_field":
            delay = random.uniform(*self.interaction_timings.form_field_pause)
        elif interaction_type == "button":
            delay = random.uniform(*self.interaction_timings.button_hover_time)
        elif interaction_type == "page_load":
            delay = random.uniform(*self.interaction_timings.page_load_wait)
        elif interaction_type == "reading":
            # Simulate reading time (assuming average text length)
            words = random.randint(5, 15)
            delay = words * self.interaction_timings.reading_time_per_word
            delay += random.uniform(0.5, 2.0)  # Add thinking time
        else:
            # General interaction delay
            delay = random.uniform(0.3, 1.5)
        
        await asyncio.sleep(delay)
    
    async def simulate_page_reading(self, driver: WebDriver, duration_range: Tuple[float, float] = (2.0, 8.0)) -> None:
        """
        Simulate reading behavior on a page with realistic scrolling and pauses.
        
        Args:
            driver: WebDriver instance
            duration_range: Range of time to spend "reading"
        """
        try:
            reading_duration = random.uniform(*duration_range)
            start_time = time.time()
            
            # Get page height for scrolling
            page_height = driver.execute_script("return document.body.scrollHeight")
            viewport_height = driver.execute_script("return window.innerHeight")
            
            scroll_positions = []
            current_scroll = 0
            
            # Generate realistic scroll positions
            while current_scroll < page_height - viewport_height:
                scroll_increment = random.randint(100, 300)
                current_scroll = min(current_scroll + scroll_increment, page_height - viewport_height)
                scroll_positions.append(current_scroll)
            
            # Simulate reading with scrolling
            for i, scroll_pos in enumerate(scroll_positions):
                if time.time() - start_time >= reading_duration:
                    break
                
                # Scroll to position
                driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                
                # Pause to "read" content
                read_pause = random.uniform(1.0, 3.0)
                await asyncio.sleep(read_pause)
                
                # Occasionally scroll back up (re-reading)
                if random.random() < 0.2 and i > 0:
                    back_scroll = scroll_positions[i-1]
                    driver.execute_script(f"window.scrollTo(0, {back_scroll});")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
            
            # Return to top occasionally
            if random.random() < 0.3:
                driver.execute_script("window.scrollTo(0, 0);")
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            self.logger.error(f"Error in simulate_page_reading: {e}")
    
    def adapt_behavior_pattern(self, success_rate: float) -> None:
        """
        Adapt behavior patterns based on success rate.
        
        Args:
            success_rate: Current success rate (0.0 to 1.0)
        """
        if success_rate < 0.5:  # Low success rate, be more human-like
            # Switch to slower, more careful patterns
            self.current_typing_pattern = max(self.typing_patterns, 
                                            key=lambda p: p.base_delay)
            self.current_mouse_pattern = max(self.mouse_patterns,
                                           key=lambda p: p.curve_intensity)
            self.logger.info("Adapted to more careful behavior patterns due to low success rate")
        
        elif success_rate > 0.8:  # High success rate, can be slightly faster
            # Switch to faster patterns
            self.current_typing_pattern = min(self.typing_patterns,
                                            key=lambda p: p.base_delay)
            self.current_mouse_pattern = min(self.mouse_patterns,
                                           key=lambda p: p.movement_speed)
            self.logger.info("Adapted to faster behavior patterns due to high success rate")
    
    def get_behavior_statistics(self) -> Dict[str, Any]:
        """Get statistics about behavior simulation performance."""
        total_interactions = self.successful_interactions + self.failed_interactions
        success_rate = (self.successful_interactions / total_interactions * 100) if total_interactions > 0 else 0
        
        return {
            "total_interactions": total_interactions,
            "successful_interactions": self.successful_interactions,
            "failed_interactions": self.failed_interactions,
            "success_rate": success_rate,
            "session_duration": (datetime.now() - self.session_start_time).total_seconds(),
            "current_typing_pattern": {
                "base_delay": self.current_typing_pattern.base_delay,
                "variance": self.current_typing_pattern.variance,
                "error_probability": self.current_typing_pattern.error_probability
            },
            "current_mouse_pattern": {
                "movement_speed": self.current_mouse_pattern.movement_speed,
                "curve_intensity": self.current_mouse_pattern.curve_intensity
            }
        }


# Import math for mouse path calculations
import math