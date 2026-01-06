"""
Captcha solver using multiple APIs (NopeCHA free, Capsolver, 2Captcha).
"""

import asyncio
import aiohttp
import logging
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Solves captchas using multiple APIs."""
    
    def __init__(self, api_key: str = None, service: str = "nopecha"):
        self.api_key = api_key
        self.service = service.lower()
        self.session = None
        
        # API URLs
        self.urls = {
            "capsolver": "https://api.capsolver.com",
            "nopecha": "https://api.nopecha.com",
            "2captcha": "https://2captcha.com"
        }
        
    async def initialize(self) -> bool:
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120))
        
        if not self.api_key:
            logger.warning("No API key - trying NopeCHA free tier (100/day)")
            self.service = "nopecha_free"
            return True
        
        # Check balance based on service
        if self.service == "capsolver":
            balance = await self.get_capsolver_balance()
            if balance is not None:
                logger.info(f"Capsolver balance: ${balance}")
                return True
        elif self.service == "nopecha":
            logger.info("NopeCHA API key configured")
            return True
        elif self.service == "2captcha":
            balance = await self.get_2captcha_balance()
            if balance is not None:
                logger.info(f"2Captcha balance: ${balance}")
                return True
        
        return True
    
    async def get_capsolver_balance(self) -> Optional[float]:
        if not self.api_key:
            return None
        try:
            data = {"clientKey": self.api_key}
            async with self.session.post(f"{self.urls['capsolver']}/getBalance", json=data) as resp:
                result = await resp.json()
                if result.get('errorId') == 0:
                    return result.get('balance', 0)
        except Exception as e:
            logger.error(f"Capsolver balance error: {e}")
        return None
    
    async def get_2captcha_balance(self) -> Optional[float]:
        if not self.api_key:
            return None
        try:
            async with self.session.get(f"{self.urls['2captcha']}/res.php?key={self.api_key}&action=getbalance") as resp:
                text = await resp.text()
                return float(text)
        except:
            return None
    
    async def cleanup(self):
        if self.session:
            await self.session.close()
    
    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA v2 using configured service."""
        
        # Try NopeCHA free first if no API key
        if self.service == "nopecha_free" or self.service == "nopecha":
            return await self._solve_nopecha(site_key, page_url, "recaptcha2")
        elif self.service == "capsolver":
            return await self._solve_capsolver(site_key, page_url, "ReCaptchaV2TaskProxyLess")
        elif self.service == "2captcha":
            return await self._solve_2captcha(site_key, page_url, "recaptcha")
        
        return None
    
    async def _solve_nopecha(self, site_key: str, page_url: str, captcha_type: str) -> Optional[str]:
        """Solve using NopeCHA API."""
        try:
            data = {
                "type": captcha_type,
                "sitekey": site_key,
                "url": page_url
            }
            
            if self.api_key:
                data["key"] = self.api_key
            
            logger.info(f"NopeCHA solving {captcha_type}...")
            
            async with self.session.post(f"{self.urls['nopecha']}/token", json=data) as resp:
                result = await resp.json()
                
                if result.get('error'):
                    logger.error(f"NopeCHA error: {result}")
                    return None
                
                # NopeCHA returns job ID, need to poll
                job_id = result.get('data')
                if not job_id:
                    logger.error(f"No job ID: {result}")
                    return None
                
                logger.info(f"NopeCHA job: {job_id}")
                
                # Poll for result
                for _ in range(60):
                    await asyncio.sleep(3)
                    
                    check_data = {"key": self.api_key} if self.api_key else {}
                    check_data["id"] = job_id
                    
                    async with self.session.get(f"{self.urls['nopecha']}/token/{job_id}") as check_resp:
                        check_result = await check_resp.json()
                        
                        if check_result.get('error'):
                            if 'incomplete' in str(check_result.get('message', '')).lower():
                                continue
                            logger.error(f"NopeCHA poll error: {check_result}")
                            return None
                        
                        token = check_result.get('data')
                        if token and isinstance(token, str) and len(token) > 50:
                            logger.info("✅ NopeCHA solved!")
                            return token
                
                logger.error("NopeCHA timeout")
                return None
                
        except Exception as e:
            logger.error(f"NopeCHA error: {e}")
            return None
    
    async def _solve_capsolver(self, site_key: str, page_url: str, task_type: str) -> Optional[str]:
        """Solve using Capsolver API."""
        if not self.api_key:
            return None
        
        try:
            task_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": page_url,
                    "websiteKey": site_key
                }
            }
            
            async with self.session.post(f"{self.urls['capsolver']}/createTask", json=task_data) as resp:
                result = await resp.json()
            
            if result.get('errorId') != 0:
                logger.error(f"Capsolver error: {result}")
                return None
            
            task_id = result.get('taskId')
            logger.info(f"Capsolver task: {task_id}")
            
            for _ in range(60):
                await asyncio.sleep(3)
                
                get_data = {"clientKey": self.api_key, "taskId": task_id}
                async with self.session.post(f"{self.urls['capsolver']}/getTaskResult", json=get_data) as resp:
                    result = await resp.json()
                
                if result.get('status') == 'ready':
                    logger.info("✅ Capsolver solved!")
                    return result.get('solution', {}).get('gRecaptchaResponse')
                elif result.get('errorId') != 0:
                    logger.error(f"Capsolver task error: {result}")
                    return None
            
            return None
        except Exception as e:
            logger.error(f"Capsolver error: {e}")
            return None
    
    async def _solve_2captcha(self, site_key: str, page_url: str, captcha_type: str) -> Optional[str]:
        """Solve using 2Captcha API."""
        if not self.api_key:
            return None
        
        try:
            # Submit task
            params = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            
            async with self.session.get(f"{self.urls['2captcha']}/in.php", params=params) as resp:
                result = await resp.json()
            
            if result.get('status') != 1:
                logger.error(f"2Captcha error: {result}")
                return None
            
            task_id = result.get('request')
            logger.info(f"2Captcha task: {task_id}")
            
            # Poll for result
            await asyncio.sleep(20)  # 2Captcha needs more time
            
            for _ in range(60):
                params = {"key": self.api_key, "action": "get", "id": task_id, "json": 1}
                async with self.session.get(f"{self.urls['2captcha']}/res.php", params=params) as resp:
                    result = await resp.json()
                
                if result.get('status') == 1:
                    logger.info("✅ 2Captcha solved!")
                    return result.get('request')
                elif result.get('request') != 'CAPCHA_NOT_READY':
                    logger.error(f"2Captcha error: {result}")
                    return None
                
                await asyncio.sleep(5)
            
            return None
        except Exception as e:
            logger.error(f"2Captcha error: {e}")
            return None
    
    async def solve_recaptcha_v2_enterprise(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA v2 Enterprise."""
        if self.service == "nopecha_free" or self.service == "nopecha":
            return await self._solve_nopecha(site_key, page_url, "recaptcha2")
        elif self.service == "capsolver":
            return await self._solve_capsolver(site_key, page_url, "ReCaptchaV2EnterpriseTaskProxyLess")
        return None
    
    async def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve hCaptcha."""
        if self.service == "nopecha_free" or self.service == "nopecha":
            return await self._solve_nopecha(site_key, page_url, "hcaptcha")
        elif self.service == "capsolver":
            return await self._solve_capsolver(site_key, page_url, "HCaptchaTaskProxyLess")
        return None
    
    def detect_captcha(self, page_source: str) -> Dict[str, Any]:
        """Detect captcha type from page."""
        result = {'type': None, 'site_key': None}
        
        # reCAPTCHA
        match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_source)
        if match:
            result['type'] = 'recaptcha_v2'
            result['site_key'] = match.group(1)
            return result
        
        # reCAPTCHA in script
        match = re.search(r'grecaptcha\.render\([^,]+,\s*\{[^}]*["\']sitekey["\']\s*:\s*["\']([^"\']+)["\']', page_source)
        if match:
            result['type'] = 'recaptcha_v2'
            result['site_key'] = match.group(1)
            return result
        
        # Enterprise reCAPTCHA
        if 'enterprise.js' in page_source or 'recaptcha-enterprise' in page_source:
            match = re.search(r'sitekey["\']?\s*[:=]\s*["\']([^"\']+)["\']', page_source)
            if match:
                result['type'] = 'recaptcha_v2_enterprise'
                result['site_key'] = match.group(1)
                return result
        
        # hCaptcha
        match = re.search(r'data-sitekey=["\']([^"\']+)["\'].*h-captcha', page_source, re.DOTALL)
        if match:
            result['type'] = 'hcaptcha'
            result['site_key'] = match.group(1)
            return result
        
        return result
    
    async def solve_from_page(self, driver, page_url: str) -> Optional[str]:
        """Detect and solve captcha from page."""
        page_source = driver.page_source
        captcha_info = self.detect_captcha(page_source)
        
        if not captcha_info['type']:
            logger.info("No captcha detected")
            return None
        
        logger.info(f"Detected: {captcha_info['type']}")
        
        if captcha_info['type'] == 'recaptcha_v2':
            return await self.solve_recaptcha_v2(captcha_info['site_key'], page_url)
        elif captcha_info['type'] == 'recaptcha_v2_enterprise':
            return await self.solve_recaptcha_v2_enterprise(captcha_info['site_key'], page_url)
        elif captcha_info['type'] == 'hcaptcha':
            return await self.solve_hcaptcha(captcha_info['site_key'], page_url)
        
        return None
    
    def inject_token(self, driver, token: str) -> bool:
        """Inject solved token into page."""
        try:
            driver.execute_script(f'''
                var textarea = document.getElementById("g-recaptcha-response");
                if (textarea) {{
                    textarea.innerHTML = "{token}";
                    textarea.style.display = "block";
                }}
                var textarea2 = document.querySelector('[name="g-recaptcha-response"]');
                if (textarea2) {{
                    textarea2.value = "{token}";
                }}
                var textarea3 = document.querySelector('[name="h-captcha-response"]');
                if (textarea3) {{
                    textarea3.value = "{token}";
                }}
            ''')
            logger.info("Token injected")
            return True
        except Exception as e:
            logger.error(f"Inject error: {e}")
            return False
