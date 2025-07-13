"""
Database connection and operations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from config import Config
from database.models import User, UserSettings, FileRecord, Thumbnail, BotStats, ForceSubChannel

logger = logging.getLogger(__name__)

class Database:
    """Database connection and operations manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.connected = False
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(Config.MONGODB_URI)
            self.db = self.client[Config.DATABASE_NAME]
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes
            await self.create_indexes()
            
            self.connected = True
            logger.info("Connected to MongoDB successfully")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from MongoDB")
    
    async def create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Users collection indexes
            await self.db.users.create_index("user_id", unique=True)
            await self.db.users.create_index("username")
            await self.db.users.create_index("referral_code")
            await self.db.users.create_index("join_date")
            
            # User settings indexes
            await self.db.user_settings.create_index("user_id", unique=True)
            
            # File records indexes
            await self.db.file_records.create_index("file_id")
            await self.db.file_records.create_index("user_id")
            await self.db.file_records.create_index("created_at")
            
            # Thumbnails indexes
            await self.db.thumbnails.create_index("thumbnail_id", unique=True)
            await self.db.thumbnails.create_index("user_id")
            
            # Force sub channels indexes
            await self.db.force_sub_channels.create_index("channel_id", unique=True)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    # User operations
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            user_data = await self.db.users.find_one({"user_id": user_id})
            return User.from_dict(user_data) if user_data else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            await self.db.users.insert_one(user.to_dict())
            logger.info(f"Created user {user.user_id}")
            return True
        except DuplicateKeyError:
            logger.warning(f"User {user.user_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating user {user.user_id}: {e}")
            return False
    
    async def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user information"""
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {**updates, "last_activity": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    async def get_user_by_referral_code(self, referral_code: str) -> Optional[User]:
        """Get user by referral code"""
        try:
            user_data = await self.db.users.find_one({"referral_code": referral_code})
            return User.from_dict(user_data) if user_data else None
        except Exception as e:
            logger.error(f"Error getting user by referral code: {e}")
            return None
    
    # User settings operations
    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Get user settings"""
        try:
            settings_data = await self.db.user_settings.find_one({"user_id": user_id})
            return UserSettings.from_dict(settings_data) if settings_data else None
        except Exception as e:
            logger.error(f"Error getting user settings {user_id}: {e}")
            return None
    
    async def create_user_settings(self, settings: UserSettings) -> bool:
        """Create user settings"""
        try:
            await self.db.user_settings.insert_one(settings.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error creating user settings: {e}")
            return False
    
    async def update_user_settings(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user settings"""
        try:
            result = await self.db.user_settings.update_one(
                {"user_id": user_id},
                {"$set": {**updates, "updated_at": datetime.now()}},
                upsert=True
            )
            return result.upserted_id is not None or result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user settings {user_id}: {e}")
            return False
    
    # File record operations
    async def create_file_record(self, file_record: FileRecord) -> bool:
        """Create a file processing record"""
        try:
            await self.db.file_records.insert_one(file_record.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error creating file record: {e}")
            return False
    
    async def update_file_record(self, file_id: str, updates: Dict[str, Any]) -> bool:
        """Update file record"""
        try:
            result = await self.db.file_records.update_one(
                {"file_id": file_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating file record {file_id}: {e}")
            return False
    
    async def get_user_file_records(self, user_id: int, limit: int = 50) -> List[FileRecord]:
        """Get user's file records"""
        try:
            cursor = self.db.file_records.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            records = []
            async for record_data in cursor:
                records.append(FileRecord.from_dict(record_data))
            return records
        except Exception as e:
            logger.error(f"Error getting user file records: {e}")
            return []
    
    # Thumbnail operations
    async def create_thumbnail(self, thumbnail: Thumbnail) -> bool:
        """Create a thumbnail record"""
        try:
            await self.db.thumbnails.insert_one(thumbnail.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return False
    
    async def get_user_thumbnails(self, user_id: int) -> List[Thumbnail]:
        """Get user's thumbnails"""
        try:
            cursor = self.db.thumbnails.find({"user_id": user_id}).sort("created_at", -1)
            thumbnails = []
            async for thumb_data in cursor:
                thumbnails.append(Thumbnail.from_dict(thumb_data))
            return thumbnails
        except Exception as e:
            logger.error(f"Error getting user thumbnails: {e}")
            return []
    
    async def delete_thumbnail(self, thumbnail_id: str, user_id: int) -> bool:
        """Delete a thumbnail"""
        try:
            result = await self.db.thumbnails.delete_one({
                "thumbnail_id": thumbnail_id,
                "user_id": user_id
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting thumbnail: {e}")
            return False
    
    # Force subscription channels
    async def get_force_sub_channels(self) -> List[ForceSubChannel]:
        """Get all active force subscription channels"""
        try:
            cursor = self.db.force_sub_channels.find({"is_active": True})
            channels = []
            async for channel_data in cursor:
                channels.append(ForceSubChannel.from_dict(channel_data))
            return channels
        except Exception as e:
            logger.error(f"Error getting force sub channels: {e}")
            return []
    
    async def add_force_sub_channel(self, channel: ForceSubChannel) -> bool:
        """Add a force subscription channel"""
        try:
            await self.db.force_sub_channels.insert_one(channel.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error adding force sub channel: {e}")
            return False
    
    async def remove_force_sub_channel(self, channel_id: str) -> bool:
        """Remove a force subscription channel"""
        try:
            result = await self.db.force_sub_channels.delete_one({"channel_id": channel_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error removing force sub channel: {e}")
            return False
    
    # Statistics operations
    async def get_bot_stats(self) -> BotStats:
        """Get bot statistics"""
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            
            # Get basic stats
            total_users = await self.db.users.count_documents({})
            active_users_today = await self.db.users.count_documents({
                "last_activity": {"$gte": today_start}
            })
            active_users_week = await self.db.users.count_documents({
                "last_activity": {"$gte": week_start}
            })
            premium_users = await self.db.users.count_documents({
                "is_premium": True,
                "$or": [
                    {"premium_expires": {"$gt": now}},
                    {"premium_expires": None}
                ]
            })
            
            # Get file stats
            total_files = await self.db.file_records.count_documents({})
            files_today = await self.db.file_records.count_documents({
                "created_at": {"$gte": today_start}
            })
            
            return BotStats(
                total_users=total_users,
                active_users_today=active_users_today,
                active_users_week=active_users_week,
                total_files_processed=total_files,
                files_processed_today=files_today,
                premium_users=premium_users,
                last_updated=now
            )
            
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return BotStats()

# Global database instance
db = Database()

async def init_database():
    """Initialize database connection"""
    await db.connect()

async def close_database():
    """Close database connection"""
    await db.disconnect()
