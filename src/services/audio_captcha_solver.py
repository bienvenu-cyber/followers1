"""
Free audio captcha solver using wit.ai (Meta's free speech-to-text API).
70-80% success rate.
"""

import asyncio
import aiohttp
import logging
import os
import tempfile
import random
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


class AudioCaptchaSolver:
    """Solves reCAPTCHA using audio challenge + wit.ai transcription."""
    
    def __init__(self, wit_api_keys: list = None):
        """
        Initialize with wit.ai API keys.
        Get free keys at: https://wit.ai/apps - create app, go to Settings, copy Server Access Token
        """
        self.wit_api_keys = wit_api_keys or []
        self.current_key_index = 0
        self.session = None
        
    async def initialize(self) -> bool:
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        
        if not self.wit_api_keys:
            logger.warning("No wit.ai API keys configured")
            logger.info("Get free keys at: https://wit.ai/apps")
            return False
        
        logger.info(f"AudioCaptchaSolver initialized with {len(self.wit_api_keys)} wit.ai keys")
        return True
    
    async def cleanup(self):
        if self.session:
            await self.session.close()
    
    def _get_next_key(self) -> str:
        """Rotate through API keys."""
        if not self.wit_api_keys:
            return None
        key = self.wit_api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.wit_api_keys)
        return key
    
    async def _download_audio(self, audio_url: str) -> Optional[bytes]:
        """Download audio file from reCAPTCHA."""
        try:
            async with self.session.get(audio_url) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.error(f"Audio download failed: {resp.status}")
        except Exception as e:
            logger.error(f"Audio download error: {e}")
        return None
    
    async def _transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio using wit.ai."""
        api_key = self._get_next_key()
        if not api_key:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'audio/mpeg3'
            }
            
            async with self.session.post(
                'https://api.wit.ai/speech?v=20220622',
                headers=headers,
                data=audio_data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    text = result.get('text', '')
                    if text:
                        logger.info(f"Transcription: {text}")
                        return text.lower().strip()
                else:
                    error = await resp.text()
                    logger.error(f"wit.ai error {resp.status}: {error}")
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        
        return None
    
    async def solve(self, driver) -> Optional[str]:
        """
        Solve reCAPTCHA on the current page.
        Returns the token if successful, None otherwise.
        """
        try:
            wait = WebDriverWait(driver, 10)
            
            # Find and click the reCAPTCHA checkbox
            logger.info("Looking for reCAPTCHA...")
            
            # Switch to reCAPTCHA iframe
            recaptcha_frame = None
            frames = driver.find_elements(By.TAG_NAME, 'iframe')
            
            for frame in frames:
                src = frame.get_attribute('src') or ''
                if 'recaptcha' in src and 'anchor' in src:
                    recaptcha_frame = frame
                    break
            
            if not recaptcha_frame:
                logger.error("reCAPTCHA frame not found")
                return None
            
            driver.switch_to.frame(recaptcha_frame)
            
            # Click checkbox
            checkbox = wait.until(EC.element_to_be_clickable(
                (By.ID, 'recaptcha-anchor')
            ))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            checkbox.click()
            logger.info("Clicked checkbox")
            
            await asyncio.sleep(2)
            
            # Switch back to main content
            driver.switch_to.default_content()
            
            # Check if we got lucky (no challenge)
            token = self._get_token(driver)
            if token:
                logger.info("Solved without challenge!")
                return token
            
            # Find challenge iframe
            challenge_frame = None
            frames = driver.find_elements(By.TAG_NAME, 'iframe')
            
            for frame in frames:
                src = frame.get_attribute('src') or ''
                if 'recaptcha' in src and 'bframe' in src:
                    challenge_frame = frame
                    break
            
            if not challenge_frame:
                logger.error("Challenge frame not found")
                return None
            
            driver.switch_to.frame(challenge_frame)
            
            # Click audio button
            try:
                audio_btn = wait.until(EC.element_to_be_clickable(
                    (By.ID, 'recaptcha-audio-button')
                ))
                await asyncio.sleep(random.uniform(0.3, 0.8))
                audio_btn.click()
                logger.info("Clicked audio button")
            except:
                logger.error("Audio button not found - might be blocked")
                driver.switch_to.default_content()
                return None
            
            await asyncio.sleep(2)
            
            # Try up to 3 times
            for attempt in range(3):
                logger.info(f"Audio attempt {attempt + 1}/3")
                
                # Get audio URL
                try:
                    audio_source = driver.find_element(By.ID, 'audio-source')
                    audio_url = audio_source.get_attribute('src')
                    
                    if not audio_url:
                        logger.error("No audio URL")
                        continue
                    
                    logger.info(f"Audio URL: {audio_url[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Could not get audio: {e}")
                    
                    # Check if blocked
                    try:
                        error_msg = driver.find_element(By.CLASS_NAME, 'rc-doscaptcha-header-text')
                        if error_msg and 'try again later' in error_msg.text.lower():
                            logger.error("BLOCKED - Try again later")
                            driver.switch_to.default_content()
                            return None
                    except:
                        pass
                    continue
                
                # Download and transcribe
                audio_data = await self._download_audio(audio_url)
                if not audio_data:
                    continue
                
                transcription = await self._transcribe_audio(audio_data)
                if not transcription:
                    # Reload audio
                    try:
                        reload_btn = driver.find_element(By.ID, 'recaptcha-reload-button')
                        reload_btn.click()
                        await asyncio.sleep(2)
                    except:
                        pass
                    continue
                
                # Enter transcription
                response_input = driver.find_element(By.ID, 'audio-response')
                response_input.clear()
                
                for char in transcription:
                    response_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.1))
                
                await asyncio.sleep(0.5)
                
                # Click verify
                verify_btn = driver.find_element(By.ID, 'recaptcha-verify-button')
                verify_btn.click()
                logger.info("Clicked verify")
                
                await asyncio.sleep(3)
                
                # Check for token
                driver.switch_to.default_content()
                token = self._get_token(driver)
                
                if token:
                    logger.info("✅ CAPTCHA SOLVED!")
                    return token
                
                # Check if need more solutions
                driver.switch_to.frame(challenge_frame)
                
                try:
                    error_elem = driver.find_element(By.CLASS_NAME, 'rc-audiochallenge-error-message')
                    if error_elem.is_displayed():
                        logger.warning("Multiple solutions required, retrying...")
                        continue
                except:
                    pass
            
            driver.switch_to.default_content()
            logger.error("Failed after 3 attempts")
            return None
            
        except Exception as e:
            logger.error(f"Solve error: {e}")
            try:
                driver.switch_to.default_content()
            except:
                pass
            return None
    
    def _get_token(self, driver) -> Optional[str]:
        """Extract reCAPTCHA token from page."""
        try:
            textarea = driver.find_element(By.ID, 'g-recaptcha-response')
            token = textarea.get_attribute('value')
            if token and len(token) > 50:
                return token
        except:
            pass
        
        try:
            textarea = driver.find_element(By.NAME, 'g-recaptcha-response')
            token = textarea.get_attribute('value')
            if token and len(token) > 50:
                return token
        except:
            pass
        
        return None
