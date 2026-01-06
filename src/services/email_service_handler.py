"""
Email service handler module for the Instagram auto signup system.

This module provides functionality for handling email services,
including creating temporary emails and retrieving verification codes.
"""

import logging
import time
import asyncio
import aiohttp
import random
import string
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class EmailAccount:
    """Email account data class."""
    email_address: str
    password: Optional[str] = None
    provider: str = "temporary"
    access_token: Optional[str] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class EmailServiceHandler:
    """Handler for email services."""
    
    def __init__(self):
        """Initialize the email service handler."""
        self.email_services = {
            "guerrillamail": self._guerrilla_mail_service,
            "1secmail": self._one_sec_mail_service,
            "mail-tm": self._mail_tm_service,
        }
        self.current_service = None
        self.current_account = None
        self.service_priority = []
        self.failed_services = set()
        self.session = None
        self.mail_tm_token = None
        self.mail_tm_account_id = None
    
    async def initialize(self) -> bool:
        """Initialize the email service handler."""
        logger.info("Initializing email service handler...")
        
        # Default services priority
        self.service_priority = [
            {"name": "guerrillamail", "priority": 1},
            {"name": "1secmail", "priority": 2},
            {"name": "mail-tm", "priority": 3},
        ]
        
        # Create HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        
        logger.info(f"Email service handler initialized with {len(self.service_priority)} services")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def create_email(self) -> Optional[Dict[str, Any]]:
        """
        Create a temporary email account.
        
        Returns:
            Dict with email_address and metadata if successful, None otherwise
        """
        for service_config in self.service_priority:
            service_name = service_config.get('name')
            
            if service_name in self.failed_services:
                continue
            
            if service_name not in self.email_services:
                continue
            
            try:
                logger.info(f"Creating email with: {service_name}")
                result = await self.email_services[service_name](action="create")
                
                if result and result.get('email_address'):
                    logger.info(f"✅ Email created: {result['email_address']}")
                    self.current_service = service_name
                    self.current_account = result
                    return result
                
            except Exception as e:
                logger.error(f"Error with {service_name}: {e}")
                self.failed_services.add(service_name)
        
        logger.error("All email services failed")
        return None
    
    async def get_messages(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get messages for an email account."""
        if not self.current_service:
            return []
        
        try:
            return await self.email_services[self.current_service](action="get_messages", email_data=email_data)
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    async def get_verification_code(self, email_data: Dict[str, Any], timeout: int = 120) -> Optional[str]:
        """Wait for and extract Instagram verification code."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            messages = await self.get_messages(email_data)
            
            for msg in messages:
                # Check subject for Instagram code
                subject = msg.get('subject', '')
                if 'Instagram' in subject or 'code' in subject.lower():
                    # Extract 6-digit code from subject
                    code_match = re.search(r'\b(\d{6})\b', subject)
                    if code_match:
                        code = code_match.group(1)
                        logger.info(f"✅ Verification code found: {code}")
                        return code
                    
                    # Try intro/body
                    intro = msg.get('intro', '') or msg.get('body', '')
                    code_match = re.search(r'\b(\d{6})\b', intro)
                    if code_match:
                        code = code_match.group(1)
                        logger.info(f"✅ Verification code found: {code}")
                        return code
            
            await asyncio.sleep(5)
        
        logger.warning("Verification code not received in time")
        return None
    
    async def _mail_tm_service(self, action: str = "create", email_data: Dict = None) -> Any:
        """
        Mail.tm API - REAL working implementation.
        """
        base_url = "https://api.mail.tm"
        
        if action == "create":
            try:
                # 1. Get available domains
                async with self.session.get(f"{base_url}/domains") as resp:
                    if resp.status != 200:
                        logger.error(f"mail.tm domains error: {resp.status}")
                        return None
                    domains_data = await resp.json()
                
                # Handle both list and dict response
                if isinstance(domains_data, list):
                    domains = domains_data
                else:
                    domains = domains_data.get('hydra:member', [])
                if not domains:
                    logger.error("No mail.tm domains available")
                    return None
                
                domain = domains[0]['domain']
                
                # 2. Generate random username
                username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                email_address = f"{username}@{domain}"
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                
                # 3. Create account
                create_data = {
                    "address": email_address,
                    "password": password
                }
                
                async with self.session.post(f"{base_url}/accounts", json=create_data) as resp:
                    if resp.status not in [200, 201]:
                        error_text = await resp.text()
                        logger.error(f"mail.tm create error: {resp.status} - {error_text}")
                        return None
                    account_data = await resp.json()
                
                account_id = account_data.get('id')
                
                # 4. Get auth token
                auth_data = {
                    "address": email_address,
                    "password": password
                }
                
                async with self.session.post(f"{base_url}/token", json=auth_data) as resp:
                    if resp.status != 200:
                        logger.error(f"mail.tm auth error: {resp.status}")
                        return None
                    token_data = await resp.json()
                
                token = token_data.get('token')
                
                # Store for later use
                self.mail_tm_token = token
                self.mail_tm_account_id = account_id
                
                return {
                    'email_address': email_address,
                    'password': password,
                    'token': token,
                    'account_id': account_id,
                    'provider': 'mail-tm'
                }
                
            except Exception as e:
                logger.error(f"mail.tm error: {e}")
                return None
        
        elif action == "get_messages":
            try:
                token = None
                if email_data:
                    if isinstance(email_data, dict):
                        token = email_data.get('token')
                    elif hasattr(email_data, 'token'):
                        token = email_data.token
                
                if not token:
                    token = self.mail_tm_token
                
                if not token:
                    return []
                
                headers = {'Authorization': f'Bearer {token}'}
                
                async with self.session.get(f"{base_url}/messages", headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                
                # Handle both list and dict response
                if isinstance(data, list):
                    messages = data
                else:
                    messages = data.get('hydra:member', [])
                
                return messages
                
            except Exception as e:
                logger.error(f"mail.tm get_messages error: {e}")
                return []
        
        return None
    
    async def _one_sec_mail_service(self, action: str = "create", email_data: Dict = None) -> Any:
        """
        1secmail.com API - backup service.
        """
        # Try alternative endpoints
        endpoints = [
            "https://www.1secmail.com/api/v1/",
            "https://1secmail.com/api/v1/",
        ]
        
        if action == "create":
            try:
                # Generate random email with known domains
                domains = ['1secmail.com', '1secmail.org', '1secmail.net']
                username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                domain = random.choice(domains)
                email_address = f"{username}@{domain}"
                
                return {
                    'email_address': email_address,
                    'login': username,
                    'domain': domain,
                    'provider': '1secmail'
                }
                
            except Exception as e:
                logger.error(f"1secmail error: {e}")
                return None
        
        elif action == "get_messages":
            try:
                email = email_data.get('email_address', '') if isinstance(email_data, dict) else ''
                if '@' not in email:
                    return []
                
                login, domain = email.split('@')
                
                for base_url in endpoints:
                    try:
                        async with self.session.get(
                            f"{base_url}?action=getMessages&login={login}&domain={domain}",
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            if resp.status == 200:
                                messages = await resp.json()
                                
                                result = []
                                for msg in messages[:5]:
                                    msg_id = msg.get('id')
                                    async with self.session.get(
                                        f"{base_url}?action=readMessage&login={login}&domain={domain}&id={msg_id}"
                                    ) as msg_resp:
                                        if msg_resp.status == 200:
                                            full_msg = await msg_resp.json()
                                            result.append({
                                                'subject': full_msg.get('subject', ''),
                                                'body': full_msg.get('body', ''),
                                                'from': full_msg.get('from', '')
                                            })
                                
                                return result
                    except:
                        continue
                
                return []
                
            except Exception as e:
                logger.error(f"1secmail get_messages error: {e}")
                return []
        
        return None
    
    async def _guerrilla_mail_service(self, action: str = "create", email_data: Dict = None) -> Any:
        """Guerrilla Mail API."""
        base_url = "https://api.guerrillamail.com/ajax.php"
        
        if action == "create":
            try:
                params = {'f': 'get_email_address'}
                async with self.session.get(base_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        email = data.get('email_addr')
                        sid = data.get('sid_token')
                        
                        if email:
                            return {
                                'email_address': email,
                                'sid_token': sid,
                                'provider': 'guerrillamail'
                            }
                return None
            except Exception as e:
                logger.error(f"Guerrilla mail error: {e}")
                return None
        
        elif action == "get_messages":
            try:
                sid = email_data.get('sid_token') if isinstance(email_data, dict) else None
                if not sid:
                    return []
                
                params = {'f': 'get_email_list', 'offset': 0, 'sid_token': sid}
                async with self.session.get(base_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        messages = data.get('list', [])
                        return [{'subject': m.get('mail_subject', ''), 'body': m.get('mail_body', '')} for m in messages]
                return []
            except Exception as e:
                logger.error(f"Guerrilla get_messages error: {e}")
                return []
        
        return None
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get email service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            "current_service": self.current_service,
            "available_services": list(self.email_services.keys()),
            "failed_services": list(self.failed_services),
            "service_priority": self.service_priority
        }