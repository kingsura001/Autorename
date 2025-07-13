"""
Helper utilities for the Telegram bot
"""

import os
import logging
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from telegram import User as TelegramUser

from config import Config

logger = logging.getLogger(__name__)

def generate_referral_code(length: int = 8) -> str:
    """Generate a random referral code"""
    try:
        # Use a combination of letters and numbers
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    except Exception as e:
        logger.error(f"Error generating referral code: {e}")
        return "DEFAULT"

def get_user_info(telegram_user: TelegramUser) -> Dict[str, Any]:
    """Extract user information from Telegram user object"""
    try:
        return {
            "user_id": telegram_user.id,
            "username": telegram_user.username,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name,
            "language_code": telegram_user.language_code,
            "is_bot": telegram_user.is_bot,
            "is_premium": telegram_user.is_premium if hasattr(telegram_user, 'is_premium') else False
        }
    except Exception as e:
        logger.error(f"Error extracting user info: {e}")
        return {"user_id": telegram_user.id}

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1
    
    return f"{size:.1f} {size_names[i]}"

def format_duration(seconds: int) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def format_date(date: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    try:
        return date.strftime(format_str)
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return "Unknown"

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    try:
        return os.path.splitext(filename)[1].lower()
    except Exception as e:
        logger.error(f"Error getting file extension: {e}")
        return ""

def get_file_type(filename: str) -> str:
    """Determine file type based on extension"""
    try:
        extension = get_file_extension(filename)
        
        video_exts = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg']
        audio_exts = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus']
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']
        document_exts = ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']
        archive_exts = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']
        
        if extension in video_exts:
            return "video"
        elif extension in audio_exts:
            return "audio"
        elif extension in image_exts:
            return "image"
        elif extension in document_exts:
            return "document"
        elif extension in archive_exts:
            return "archive"
        else:
            return "file"
            
    except Exception as e:
        logger.error(f"Error determining file type: {e}")
        return "file"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    try:
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255 - len(ext)] + ext
        
        return filename
        
    except Exception as e:
        logger.error(f"Error sanitizing filename: {e}")
        return "sanitized_file"

def generate_unique_filename(filename: str, directory: str) -> str:
    """Generate unique filename to avoid conflicts"""
    try:
        base_name, extension = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        
        while os.path.exists(os.path.join(directory, new_filename)):
            new_filename = f"{base_name}_{counter}{extension}"
            counter += 1
        
        return new_filename
        
    except Exception as e:
        logger.error(f"Error generating unique filename: {e}")
        return f"unique_{filename}"

def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """Calculate file hash"""
    try:
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
        
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    try:
        return user_id in Config.ADMIN_IDS
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

def format_progress(current: int, total: int, width: int = 20) -> str:
    """Format progress bar"""
    try:
        if total == 0:
            return "█" * width
        
        filled = int(width * current / total)
        bar = "█" * filled + "░" * (width - filled)
        percentage = (current / total) * 100
        
        return f"{bar} {percentage:.1f}%"
        
    except Exception as e:
        logger.error(f"Error formatting progress: {e}")
        return "Progress error"

def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None
        
    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return False

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    try:
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
        
    except Exception as e:
        logger.error(f"Error truncating text: {e}")
        return text

def generate_random_string(length: int = 10, chars: str = None) -> str:
    """Generate random string"""
    try:
        if chars is None:
            chars = string.ascii_letters + string.digits
        
        return ''.join(random.choice(chars) for _ in range(length))
        
    except Exception as e:
        logger.error(f"Error generating random string: {e}")
        return "random"

def parse_time_string(time_str: str) -> Optional[timedelta]:
    """Parse time string to timedelta"""
    try:
        # Parse formats like "1d", "2h", "30m", "45s"
        import re
        
        time_units = {
            's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
            'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
            'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
            'd': 86400, 'day': 86400, 'days': 86400,
            'w': 604800, 'week': 604800, 'weeks': 604800
        }
        
        pattern = r'(\d+)\s*([a-zA-Z]+)'
        matches = re.findall(pattern, time_str.lower())
        
        total_seconds = 0
        for value, unit in matches:
            if unit in time_units:
                total_seconds += int(value) * time_units[unit]
        
        return timedelta(seconds=total_seconds) if total_seconds > 0 else None
        
    except Exception as e:
        logger.error(f"Error parsing time string: {e}")
        return None

def is_valid_telegram_username(username: str) -> bool:
    """Validate Telegram username format"""
    try:
        import re
        
        # Remove @ if present
        username = username.lstrip('@')
        
        # Check format: 5-32 characters, alphanumeric + underscore, 
        # must start with letter, can't end with underscore
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$'
        
        if not re.match(pattern, username):
            return False
        
        # Can't end with underscore
        if username.endswith('_'):
            return False
        
        # Can't have consecutive underscores
        if '__' in username:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating username: {e}")
        return False

def format_user_mention(user_id: int, name: str) -> str:
    """Format user mention for Telegram"""
    try:
        # Escape markdown characters in name
        escaped_name = name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
        return f"[{escaped_name}](tg://user?id={user_id})"
        
    except Exception as e:
        logger.error(f"Error formatting user mention: {e}")
        return name

def get_mime_type(filename: str) -> str:
    """Get MIME type for file"""
    try:
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
        
    except Exception as e:
        logger.error(f"Error getting MIME type: {e}")
        return "application/octet-stream"

def clean_html(text: str) -> str:
    """Clean HTML tags from text"""
    try:
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
        
    except Exception as e:
        logger.error(f"Error cleaning HTML: {e}")
        return text

def escape_markdown(text: str) -> str:
    """Escape markdown characters"""
    try:
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
        
    except Exception as e:
        logger.error(f"Error escaping markdown: {e}")
        return text

def create_pagination_keyboard(items: list, page: int, per_page: int = 10, callback_prefix: str = "page") -> list:
    """Create pagination keyboard"""
    try:
        total_pages = (len(items) + per_page - 1) // per_page
        
        if total_pages <= 1:
            return []
        
        keyboard = []
        
        # Navigation buttons
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(f"◀️ {callback_prefix}_{page - 1}")
        
        nav_buttons.append(f"{page}/{total_pages}")
        
        if page < total_pages:
            nav_buttons.append(f"▶️ {callback_prefix}_{page + 1}")
        
        keyboard.append(nav_buttons)
        
        return keyboard
        
    except Exception as e:
        logger.error(f"Error creating pagination keyboard: {e}")
        return []

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        import psutil
        import platform
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent,
            "boot_time": psutil.boot_time()
        }
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {"error": str(e)}

def log_user_action(user_id: int, action: str, details: str = ""):
    """Log user action"""
    try:
        logger.info(f"User {user_id} performed action: {action} - {details}")
        
        # In a real implementation, you might want to store this in database
        # or send to analytics service
        
    except Exception as e:
        logger.error(f"Error logging user action: {e}")

def rate_limit_check(user_id: int, action: str, limit: int = 10, window: int = 60) -> bool:
    """Check if user is rate limited"""
    try:
        # This is a simple in-memory rate limiter
        # In production, you'd use Redis or similar
        
        current_time = datetime.now()
        
        # This would be implemented with proper storage
        # For now, always return True (no rate limiting)
        return True
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True

def backup_file(file_path: str, backup_dir: str = None) -> bool:
    """Create backup of file"""
    try:
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(file_path), "backups")
        
        os.makedirs(backup_dir, exist_ok=True)
        
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{timestamp}_{filename}"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        import shutil
        shutil.copy2(file_path, backup_path)
        
        logger.info(f"File backed up: {file_path} -> {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error backing up file: {e}")
        return False

def cleanup_old_files(directory: str, days: int = 7) -> int:
    """Clean up old files from directory"""
    try:
        if not os.path.exists(directory):
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted old file: {file_path}")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning up old files: {e}")
        return 0
