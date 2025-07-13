"""
Configuration settings for the Telegram bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot configuration
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "FileRenameBot")
    
    # MongoDB configuration
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "telegram_bot")
    
    # File handling
    MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB in bytes
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
    UPLOAD_PATH = os.getenv("UPLOAD_PATH", "./uploads")
    THUMBNAIL_PATH = os.getenv("THUMBNAIL_PATH", "./thumbnails")
    
    # Admin configuration
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
    
    # Force subscription channels
    FORCE_SUB_CHANNELS = os.getenv("FORCE_SUB_CHANNELS", "").split(",") if os.getenv("FORCE_SUB_CHANNELS") else []
    
    # Premium features
    PREMIUM_ENABLED = os.getenv("PREMIUM_ENABLED", "false").lower() == "true"
    REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "30"))  # Days
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "bot.log")
    
    # Web server (optional)
    WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", "8000"))
    
    # FFmpeg path
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
    
    # Rate limiting
    RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "10"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required")
        
        # Create necessary directories
        os.makedirs(cls.DOWNLOAD_PATH, exist_ok=True)
        os.makedirs(cls.UPLOAD_PATH, exist_ok=True)
        os.makedirs(cls.THUMBNAIL_PATH, exist_ok=True)
        
        return True

# Validate configuration on import
Config.validate()
