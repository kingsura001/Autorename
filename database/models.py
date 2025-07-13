"""
Database models for the Telegram bot
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class User:
    """User model for storing user information"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = "en"
    is_premium: bool = False
    premium_expires: Optional[datetime] = None
    referral_code: Optional[str] = None
    referred_by: Optional[int] = None
    total_files_processed: int = 0
    join_date: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_banned: bool = False
    ban_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "language_code": self.language_code,
            "is_premium": self.is_premium,
            "premium_expires": self.premium_expires,
            "referral_code": self.referral_code,
            "referred_by": self.referred_by,
            "total_files_processed": self.total_files_processed,
            "join_date": self.join_date,
            "last_activity": self.last_activity,
            "is_banned": self.is_banned,
            "ban_reason": self.ban_reason
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user object from dictionary"""
        return cls(**data)
    
    def is_premium_active(self) -> bool:
        """Check if user has active premium subscription"""
        if not self.is_premium:
            return False
        if self.premium_expires and self.premium_expires < datetime.now():
            return False
        return True

@dataclass
class UserSettings:
    """User settings model"""
    user_id: int
    rename_template: str = "{title}"
    auto_rename: bool = False
    thumbnail_mode: bool = False
    default_thumbnail: Optional[str] = None
    quality_preference: str = "original"  # original, high, medium, low
    auto_upload: bool = False
    notification_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings object to dictionary"""
        return {
            "user_id": self.user_id,
            "rename_template": self.rename_template,
            "auto_rename": self.auto_rename,
            "thumbnail_mode": self.thumbnail_mode,
            "default_thumbnail": self.default_thumbnail,
            "quality_preference": self.quality_preference,
            "auto_upload": self.auto_upload,
            "notification_enabled": self.notification_enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSettings':
        """Create settings object from dictionary"""
        return cls(**data)

@dataclass
class FileRecord:
    """File processing record"""
    file_id: str
    user_id: int
    original_name: str
    renamed_name: Optional[str] = None
    file_size: int = 0
    file_type: str = "document"
    mime_type: Optional[str] = None
    thumbnail_id: Optional[str] = None
    processing_status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert file record to dictionary"""
        return {
            "file_id": self.file_id,
            "user_id": self.user_id,
            "original_name": self.original_name,
            "renamed_name": self.renamed_name,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "thumbnail_id": self.thumbnail_id,
            "processing_status": self.processing_status,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileRecord':
        """Create file record from dictionary"""
        return cls(**data)

@dataclass
class Thumbnail:
    """Thumbnail model"""
    thumbnail_id: str
    user_id: int
    file_id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thumbnail to dictionary"""
        return {
            "thumbnail_id": self.thumbnail_id,
            "user_id": self.user_id,
            "file_id": self.file_id,
            "name": self.name,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Thumbnail':
        """Create thumbnail from dictionary"""
        return cls(**data)

@dataclass
class BotStats:
    """Bot statistics model"""
    total_users: int = 0
    active_users_today: int = 0
    active_users_week: int = 0
    total_files_processed: int = 0
    files_processed_today: int = 0
    premium_users: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "total_users": self.total_users,
            "active_users_today": self.active_users_today,
            "active_users_week": self.active_users_week,
            "total_files_processed": self.total_files_processed,
            "files_processed_today": self.files_processed_today,
            "premium_users": self.premium_users,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotStats':
        """Create stats from dictionary"""
        return cls(**data)

@dataclass
class ForceSubChannel:
    """Force subscription channel model"""
    channel_id: str
    channel_name: str
    channel_username: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert channel to dictionary"""
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "channel_username": self.channel_username,
            "is_active": self.is_active,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ForceSubChannel':
        """Create channel from dictionary"""
        return cls(**data)
