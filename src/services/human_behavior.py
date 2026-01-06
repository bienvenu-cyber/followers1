"""
Human behavior simulation to avoid bot detection.
"""

import asyncio
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class HumanBehavior:
    """Simulates human-like behavior in browser."""
    
    def __init__(self, driver):
        self.driver = driver
        self.actions = ActionChains(driver)
    
    async def random_delay(self, min_sec=0.5, max_sec=2.0):
        """Random delay between actions."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def human_type(self, element, text, mistakes=True):
        """Type like a human with random delays and occasional mistakes."""
        element.click()
        await self.random_delay(0.3, 0.8)
        
        for i, char in enumerate(text):
            # Occasional typo (5% chance)
            if mistakes and random.random() < 0.05 and char.isalpha():
                # Type wrong char then correct
                wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                element.send_keys(wrong_char)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                element.send_keys(Keys.BACKSPACE)
                await asyncio.sleep(random.uniform(0.1, 0.2))
            
            element.send_keys(char)
            
            # Variable typing speed
            if char == ' ':
                await asyncio.sleep(random.uniform(0.1, 0.3))
            else:
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Occasional pause (thinking)
            if random.random() < 0.03:
                await asyncio.sleep(random.uniform(0.5, 1.5))
    
    async def random_mouse_movement(self):
        """Move mouse randomly on page."""
        try:
            width = self.driver.execute_script("return window.innerWidth")
            height = self.driver.execute_script("return window.innerHeight")
            
            # Random movements
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)
                
                self.actions.move_by_offset(
                    random.randint(-50, 50),
                    random.randint(-50, 50)
                ).perform()
                
                await asyncio.sleep(random.uniform(0.1, 0.4))
            
            self.actions.reset_actions()
        except:
            pass
    
    async def random_scroll(self):
        """Scroll page randomly like a human."""
        try:
            scroll_amount = random.randint(100, 400)
            direction = random.choice([1, -1])
            
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount * direction})")
            await self.random_delay(0.3, 1.0)
        except:
            pass
    
    async def browse_around(self, duration=3):
        """Simulate browsing behavior for a few seconds."""
        end_time = asyncio.get_event_loop().time() + duration
        
        while asyncio.get_event_loop().time() < end_time:
            action = random.choice(['scroll', 'mouse', 'wait'])
            
            if action == 'scroll':
                await self.random_scroll()
            elif action == 'mouse':
                await self.random_mouse_movement()
            else:
                await self.random_delay(0.5, 1.5)
    
    async def human_click(self, element):
        """Click element with human-like behavior."""
        try:
            # Move to element with slight offset
            self.actions.move_to_element(element).perform()
            await self.random_delay(0.2, 0.5)
            
            # Small random offset from center
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            
            self.actions.move_by_offset(offset_x, offset_y).perform()
            await self.random_delay(0.1, 0.3)
            
            element.click()
            self.actions.reset_actions()
        except:
            element.click()
    
    async def focus_blur_field(self, element):
        """Focus and blur field like human tabbing."""
        element.click()
        await self.random_delay(0.1, 0.3)
        element.send_keys(Keys.TAB)
        await self.random_delay(0.2, 0.5)
