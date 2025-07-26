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
            "temp-mail": self._temp_mail_service,
            "10minutemail": self._ten_minute_mail_service,
            "guerrillamail": self._guerrilla_mail_service
        }
        self.current_service = None
        self.service_priority = []
        self.failed_services = set()
        self.session = None
    
    async def initialize(self) -> bool:
        """Initialize the email service handler."""
        logger.info("Initializing email service handler...")
        
        # Load configuration
        from ..core.config import config_manager
        config = config_manager.get_config()
        
        # Set service priority from configuration
        if hasattr(config, 'email_services') and config.email_services:
            self.service_priority = sorted(
                config.email_services,
                key=lambda x: x.get('priority', 999)
            )
        else:
            # Default services
            self.service_priority = [
                {"name": "temp-mail", "priority": 1},
                {"name": "10minutemail", "priority": 2},
                {"name": "guerrillamail", "priority": 3}
            ]
        
        # Create HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        logger.info(f"Email service handler initialized with {len(self.service_priority)} services")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def create_email(self) -> Optional[EmailAccount]:
        """
        Create a temporary email account.
        
        Returns:
            EmailAccount if successful, None otherwise
        """
        for service_config in self.service_priority:
            service_name = service_config.get('name')
            
            if service_name in self.failed_services:
                logger.warning(f"Skipping failed service: {service_name}")
                continue
            
            if service_name not in self.email_services:
                logger.warning(f"Unknown email service: {service_name}")
                continue
            
            try:
                logger.info(f"Attempting to create email with service: {service_name}")
                email_account = await self.email_services[service_name]()
                
                if email_account:
                    logger.info(f"Email created successfully: {email_account.email_address}")
                    self.current_service = service_name
                    return email_account
                
            except Exception as e:
                logger.error(f"Error creating email with {service_name}: {e}")
                self.failed_services.add(service_name)
        
        logger.error("Failed to create email with all available services")
        return None
    
    async def get_messages(self, email_account: EmailAccount) -> List[Dict[str, Any]]:
        """
        Get messages for an email account.
        
        Args:
            email_account: Email account to check
            
        Returns:
            List of messages
        """
        if not self.current_service or self.current_service not in self.email_services:
            logger.error("No active email service")
            return []
        
        try:
            service_method = self.email_services[self.current_service]
            return await service_method(email_account, action="get_messages")
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    async def _temp_mail_service(self, email_account: Optional[EmailAccount] = None, action: str = "create") -> Any:
        """
        Temp-mail.org service implementation.
        
        Args:
            email_account: Email account (for get_messages action)
            action: Action to perform ("create" or "get_messages")
            
        Returns:
            EmailAccount for create action, List of messages for get_messages action
        """
        if action == "create":
            try:
                # Generate a simple temporary email for demo
                username = f"user{random.randint(1000, 9999)}{int(time.time())}"
                email_address = f"{username}@temp-mail.org"
                
                return EmailAccount(
                    email_address=email_address,
                    provider="temp-mail"
                )
            
            except Exception as e:
                logger.error(f"Temp-mail create error: {e}")
                return None
        
        elif action == "get_messages":
            # For demo purposes, return empty list
            return []
        
        return None
    
    async def _ten_minute_mail_service(self, email_account: Optional[EmailAccount] = None, action: str = "create") -> Any:
        """
        10minutemail.com service implementation.
        
        Args:
            email_account: Email account (for get_messages action)
            action: Action to perform ("create" or "get_messages")
            
        Returns:
            EmailAccount for create action, List of messages for get_messages action
        """
        if action == "create":
            try:
                # Generate a simple temporary email
                username = f"user{random.randint(1000, 9999)}{int(time.time())}"
                email_address = f"{username}@10minutemail.com"
                
                return EmailAccount(
                    email_address=email_address,
                    provider="10minutemail",
                    expires_at=datetime.now() + timedelta(minutes=10)
                )
            
            except Exception as e:
                logger.error(f"10minutemail create error: {e}")
                return None
        
        elif action == "get_messages":
            # For demo purposes, return empty list
            return []
        
        return None
    
    async def _guerrilla_mail_service(self, email_account: Optional[EmailAccount] = None, action: str = "create") -> Any:
        """
        Guerrillamail.com service implementation.
        
        Args:
            email_account: Email account (for get_messages action)
            action: Action to perform ("create" or "get_messages")
            
        Returns:
            EmailAccount for create action, List of messages for get_messages action
        """
        if action == "create":
            try:
                # Generate a simple temporary email for demo
                username = f"user{random.randint(1000, 9999)}{int(time.time())}"
                email_address = f"{username}@guerrillamail.com"
                
                return EmailAccount(
                    email_address=email_address,
                    provider="guerrillamail"
                )
            
            except Exception as e:
                logger.error(f"Guerrillamail create error: {e}")
                return None
        
        elif action == "get_messages":
            # For demo purposes, return empty list
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