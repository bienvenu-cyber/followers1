"""
Data models for Instagram account creation and management.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum
import json


class AccountStatus(Enum):
    """Status of an Instagram account."""
    PENDING = "pending"
    CREATED = "created"
    VERIFIED = "verified"
    FAILED = "failed"
    BLOCKED = "blocked"


class GenderType(Enum):
    """Gender options for account creation."""
    MALE = "male"
    FEMALE = "female"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


@dataclass
class AccountData:
    """Complete data for an Instagram account."""
    # Basic account information
    email: str
    full_name: str
    username: str
    password: str
    birth_date: date
    
    # Optional information
    phone_number: Optional[str] = None
    gender: Optional[GenderType] = None
    profile_picture_url: Optional[str] = None
    bio: Optional[str] = None
    
    # Account status and metadata
    status: AccountStatus = AccountStatus.PENDING
    created_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # Creation context
    proxy_used: Optional[str] = None
    user_agent_used: Optional[str] = None
    creation_ip: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert account data to dictionary."""
        return {
            'email': self.email,
            'full_name': self.full_name,
            'username': self.username,
            'password': self.password,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'phone_number': self.phone_number,
            'gender': self.gender.value if self.gender else None,
            'profile_picture_url': self.profile_picture_url,
            'bio': self.bio,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'proxy_used': self.proxy_used,
            'user_agent_used': self.user_agent_used,
            'creation_ip': self.creation_ip,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountData':
        """Create AccountData from dictionary."""
        # Parse dates
        birth_date = None
        if data.get('birth_date'):
            birth_date = date.fromisoformat(data['birth_date'])
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        verified_at = None
        if data.get('verified_at'):
            verified_at = datetime.fromisoformat(data['verified_at'])
        
        last_login = None
        if data.get('last_login'):
            last_login = datetime.fromisoformat(data['last_login'])
        
        # Parse enums
        status = AccountStatus(data.get('status', 'pending'))
        gender = GenderType(data['gender']) if data.get('gender') else None
        
        return cls(
            email=data['email'],
            full_name=data['full_name'],
            username=data['username'],
            password=data['password'],
            birth_date=birth_date,
            phone_number=data.get('phone_number'),
            gender=gender,
            profile_picture_url=data.get('profile_picture_url'),
            bio=data.get('bio'),
            status=status,
            created_at=created_at,
            verified_at=verified_at,
            last_login=last_login,
            proxy_used=data.get('proxy_used'),
            user_agent_used=data.get('user_agent_used'),
            creation_ip=data.get('creation_ip'),
            metadata=data.get('metadata', {})
        )


@dataclass
class EmailData:
    """Email account data for verification."""
    email_address: str
    password: Optional[str] = None
    provider: str = "temporary"
    access_token: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'email_address': self.email_address,
            'password': self.password,
            'provider': self.provider,
            'access_token': self.access_token,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }


@dataclass
class CreationResult:
    """Result of account creation attempt."""
    success: bool
    account_data: Optional[AccountData] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    captcha_encountered: bool = False
    verification_required: bool = False
    creation_time_seconds: float = 0.0
    steps_completed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'account_data': self.account_data.to_dict() if self.account_data else None,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'captcha_encountered': self.captcha_encountered,
            'verification_required': self.verification_required,
            'creation_time_seconds': self.creation_time_seconds,
            'steps_completed': self.steps_completed
        }