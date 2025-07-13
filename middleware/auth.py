"""
Authentication middleware for the Telegram bot
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from database.connection import db
from utils.helpers import is_admin
from utils.logger import SecurityLogger

logger = logging.getLogger(__name__)
security_logger = SecurityLogger()

class AuthMiddleware:
    """Authentication and authorization middleware"""
    
    def __init__(self):
        self.banned_users = set()
        self.rate_limits = {}
        self.session_cache = {}
        
    async def check_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            # Check cache first
            if user_id in self.banned_users:
                return True
            
            # Check database
            user = await db.get_user(user_id)
            if user and user.is_banned:
                self.banned_users.add(user_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking banned user: {e}")
            return False
    
    async def check_rate_limit(self, user_id: int, action: str = "general") -> bool:
        """Check if user has exceeded rate limit"""
        try:
            current_time = datetime.now()
            user_key = f"{user_id}_{action}"
            
            # Clean old entries
            if user_key in self.rate_limits:
                self.rate_limits[user_key] = [
                    timestamp for timestamp in self.rate_limits[user_key]
                    if current_time - timestamp < timedelta(seconds=Config.RATE_LIMIT_WINDOW)
                ]
            
            # Check current rate
            if user_key not in self.rate_limits:
                self.rate_limits[user_key] = []
            
            if len(self.rate_limits[user_key]) >= Config.RATE_LIMIT_MESSAGES:
                security_logger.log_rate_limit_exceeded(user_id, action)
                return False
            
            # Add current request
            self.rate_limits[user_key].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    async def validate_user_session(self, user_id: int) -> bool:
        """Validate user session"""
        try:
            # Check if user exists and is valid
            user = await db.get_user(user_id)
            if not user:
                return False
            
            # Update last activity
            await db.update_user(user_id, {"last_activity": datetime.now()})
            
            # Cache user info
            self.session_cache[user_id] = {
                "user": user,
                "last_update": datetime.now()
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating user session: {e}")
            return False
    
    async def log_user_activity(self, user_id: int, action: str, details: Dict[str, Any] = None):
        """Log user activity"""
        try:
            # This could be expanded to store detailed activity logs
            logger.info(f"User {user_id} performed action: {action}")
            
            if details:
                logger.debug(f"Action details: {details}")
            
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")

# Global middleware instance
auth_middleware = AuthMiddleware()

def require_auth(func):
    """Decorator to require authentication"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check if user is banned
        if await auth_middleware.check_user_banned(user_id):
            await update.message.reply_text(
                "🚫 **Access Denied**\n\n"
                "Your account has been suspended. Contact support if you believe this is an error."
            )
            security_logger.log_failed_authentication(user_id, "banned_user_attempt")
            return
        
        # Check rate limit
        if not await auth_middleware.check_rate_limit(user_id):
            await update.message.reply_text(
                "⏰ **Rate Limit Exceeded**\n\n"
                "You're sending messages too quickly. Please wait a moment and try again."
            )
            return
        
        # Validate session
        if not await auth_middleware.validate_user_session(user_id):
            await update.message.reply_text(
                "❌ **Authentication Required**\n\n"
                "Please start the bot with /start to authenticate."
            )
            return
        
        # Log activity
        await auth_middleware.log_user_activity(user_id, func.__name__)
        
        # Call original function
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def require_admin(func):
    """Decorator to require admin privileges"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id):
            await update.message.reply_text(
                "🚫 **Access Denied**\n\n"
                "You don't have permission to use this command."
            )
            security_logger.log_failed_authentication(user_id, "admin_access_attempt")
            return
        
        # Apply regular auth checks
        return await require_auth(func)(update, context, *args, **kwargs)
    
    return wrapper

def require_premium(func):
    """Decorator to require premium subscription"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check premium status
        user = await db.get_user(user_id)
        if not user or not user.is_premium_active():
            await update.message.reply_text(
                "💎 **Premium Required**\n\n"
                "This feature is available for premium users only.\n"
                "Upgrade to premium to unlock this feature!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Upgrade to Premium", callback_data="sub_premium")
                ]])
            )
            return
        
        # Apply regular auth checks
        return await require_auth(func)(update, context, *args, **kwargs)
    
    return wrapper

def rate_limit(action: str = "general", limit: int = None, window: int = None):
    """Decorator for custom rate limiting"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Use custom limits if provided
            if limit and window:
                current_time = datetime.now()
                user_key = f"{user_id}_{action}"
                
                # Check custom rate limit
                if user_key not in auth_middleware.rate_limits:
                    auth_middleware.rate_limits[user_key] = []
                
                # Clean old entries
                auth_middleware.rate_limits[user_key] = [
                    timestamp for timestamp in auth_middleware.rate_limits[user_key]
                    if current_time - timestamp < timedelta(seconds=window)
                ]
                
                # Check limit
                if len(auth_middleware.rate_limits[user_key]) >= limit:
                    await update.message.reply_text(
                        f"⏰ **Rate Limit Exceeded**\n\n"
                        f"You can only use this feature {limit} times per {window} seconds."
                    )
                    return
                
                # Add current request
                auth_middleware.rate_limits[user_key].append(current_time)
            else:
                # Use default rate limit
                if not await auth_middleware.check_rate_limit(user_id, action):
                    await update.message.reply_text(
                        "⏰ **Rate Limit Exceeded**\n\n"
                        "You're using this feature too frequently. Please wait a moment."
                    )
                    return
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator

def log_activity(action: str = None):
    """Decorator to log specific activities"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            activity_name = action or func.__name__
            
            # Log activity start
            await auth_middleware.log_user_activity(user_id, f"{activity_name}_start")
            
            try:
                result = await func(update, context, *args, **kwargs)
                
                # Log activity success
                await auth_middleware.log_user_activity(user_id, f"{activity_name}_success")
                
                return result
                
            except Exception as e:
                # Log activity failure
                await auth_middleware.log_user_activity(
                    user_id, 
                    f"{activity_name}_failed", 
                    {"error": str(e)}
                )
                raise
        
        return wrapper
    return decorator

class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_file_upload(filename: str, file_size: int) -> tuple[bool, str]:
        """Validate file upload for security"""
        try:
            # Check file size
            if file_size > Config.MAX_FILE_SIZE:
                return False, "File size exceeds maximum allowed size"
            
            # Check filename for malicious patterns
            dangerous_patterns = [
                '../', '..\\', '.exe', '.bat', '.cmd', '.scr', '.com', '.pif'
            ]
            
            filename_lower = filename.lower()
            for pattern in dangerous_patterns:
                if pattern in filename_lower:
                    return False, f"Filename contains dangerous pattern: {pattern}"
            
            # Check for null bytes
            if '\x00' in filename:
                return False, "Filename contains null bytes"
            
            # Check filename length
            if len(filename) > 255:
                return False, "Filename too long"
            
            return True, "File is safe"
            
        except Exception as e:
            logger.error(f"Error validating file upload: {e}")
            return False, "Validation error"
    
    @staticmethod
    def validate_user_input(text: str, max_length: int = 1000) -> tuple[bool, str]:
        """Validate user text input"""
        try:
            # Check length
            if len(text) > max_length:
                return False, f"Text too long (max {max_length} characters)"
            
            # Check for malicious scripts
            dangerous_patterns = [
                '<script', '</script>', 'javascript:', 'data:', 'vbscript:'
            ]
            
            text_lower = text.lower()
            for pattern in dangerous_patterns:
                if pattern in text_lower:
                    return False, f"Text contains dangerous pattern: {pattern}"
            
            return True, "Text is safe"
            
        except Exception as e:
            logger.error(f"Error validating user input: {e}")
            return False, "Validation error"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        import re
        
        # Remove path traversal attempts
        filename = filename.replace('..', '')
        filename = filename.replace('/', '_')
        filename = filename.replace('\\', '_')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
        
        return filename

def security_check(check_type: str = "basic"):
    """Decorator for security checks"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Basic security checks
            if check_type == "basic":
                # Check if user is banned
                if await auth_middleware.check_user_banned(user_id):
                    return
                
                # Check rate limit
                if not await auth_middleware.check_rate_limit(user_id):
                    return
            
            # File upload security checks
            elif check_type == "file_upload":
                if update.message.document:
                    filename = update.message.document.file_name
                    file_size = update.message.document.file_size
                    
                    is_safe, message = SecurityValidator.validate_file_upload(filename, file_size)
                    if not is_safe:
                        await update.message.reply_text(f"🚫 **File Rejected**\n\n{message}")
                        security_logger.log_suspicious_activity(
                            user_id, 
                            "unsafe_file_upload", 
                            {"filename": filename, "reason": message}
                        )
                        return
            
            # Text input security checks
            elif check_type == "text_input":
                if update.message.text:
                    is_safe, message = SecurityValidator.validate_user_input(update.message.text)
                    if not is_safe:
                        await update.message.reply_text(f"🚫 **Input Rejected**\n\n{message}")
                        security_logger.log_suspicious_activity(
                            user_id, 
                            "unsafe_text_input", 
                            {"text": update.message.text[:100], "reason": message}
                        )
                        return
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator

# Usage examples:
# @require_auth
# @require_admin
# @require_premium
# @rate_limit("file_upload", limit=5, window=60)
# @log_activity("file_processing")
# @security_check("file_upload")
