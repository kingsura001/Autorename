"""
Logging configuration for the Telegram bot
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

from config import Config

def setup_logger(logger_name: str = None, level: str = None) -> logging.Logger:
    """
    Setup logger with file and console handlers
    
    Args:
        logger_name: Name of the logger (default: root logger)
        level: Logging level (default: from config)
    
    Returns:
        Configured logger instance
    """
    
    # Get or create logger
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    
    # Set logging level
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    try:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Error file handler (only for errors)
        error_log_file = Config.LOG_FILE.replace('.log', '_errors.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
        
    except Exception as e:
        logger.error(f"Failed to setup file logging: {e}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get logger with the specified name
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

class TelegramLogHandler(logging.Handler):
    """
    Custom log handler that sends critical errors to Telegram
    """
    
    def __init__(self, bot_token: str, chat_id: str, level: int = logging.ERROR):
        super().__init__(level)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.session = None
        
    def emit(self, record):
        """Send log record to Telegram"""
        try:
            if record.levelno >= self.level:
                message = self.format(record)
                self._send_to_telegram(message)
        except Exception:
            # Don't let logging errors crash the application
            pass
    
    def _send_to_telegram(self, message: str):
        """Send message to Telegram"""
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": f"🚨 Bot Error:\n\n{message}",
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            # Log to file instead if Telegram fails
            logging.getLogger(__name__).error(f"Failed to send log to Telegram: {e}")

class DatabaseLogHandler(logging.Handler):
    """
    Custom log handler that stores logs in database
    """
    
    def __init__(self, db_connection, level: int = logging.WARNING):
        super().__init__(level)
        self.db = db_connection
        
    def emit(self, record):
        """Store log record in database"""
        try:
            if record.levelno >= self.level:
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "filename": record.filename,
                    "line_number": record.lineno,
                    "function_name": record.funcName,
                    "module": record.module
                }
                
                # This would store in database
                # self.db.logs.insert_one(log_entry)
                
        except Exception:
            # Don't let logging errors crash the application
            pass

class UserActionLogger:
    """
    Logger for user actions and bot analytics
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.logger = logging.getLogger('user_actions')
        
    def log_user_action(self, user_id: int, action: str, details: dict = None):
        """Log user action"""
        try:
            log_data = {
                "user_id": user_id,
                "action": action,
                "timestamp": datetime.now(),
                "details": details or {}
            }
            
            # Log to file
            self.logger.info(f"User {user_id} performed action: {action}")
            
            # Store in database if available
            if self.db:
                # self.db.user_actions.insert_one(log_data)
                pass
                
        except Exception as e:
            self.logger.error(f"Error logging user action: {e}")
    
    def log_file_processing(self, user_id: int, file_name: str, status: str, processing_time: float = None):
        """Log file processing events"""
        try:
            details = {
                "file_name": file_name,
                "status": status,
                "processing_time": processing_time
            }
            
            self.log_user_action(user_id, "file_processing", details)
            
        except Exception as e:
            self.logger.error(f"Error logging file processing: {e}")
    
    def log_subscription_event(self, user_id: int, event_type: str, details: dict = None):
        """Log subscription-related events"""
        try:
            self.log_user_action(user_id, f"subscription_{event_type}", details)
            
        except Exception as e:
            self.logger.error(f"Error logging subscription event: {e}")
    
    def log_error_event(self, user_id: int, error_type: str, error_message: str):
        """Log error events"""
        try:
            details = {
                "error_type": error_type,
                "error_message": error_message
            }
            
            self.log_user_action(user_id, "error", details)
            
        except Exception as e:
            self.logger.error(f"Error logging error event: {e}")

class PerformanceLogger:
    """
    Logger for performance monitoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
        
    def log_processing_time(self, operation: str, duration: float, file_size: int = None):
        """Log processing time for operations"""
        try:
            message = f"Operation '{operation}' took {duration:.2f} seconds"
            if file_size:
                message += f" for {file_size} bytes"
            
            self.logger.info(message)
            
        except Exception as e:
            self.logger.error(f"Error logging processing time: {e}")
    
    def log_memory_usage(self, operation: str, memory_mb: float):
        """Log memory usage"""
        try:
            self.logger.info(f"Operation '{operation}' used {memory_mb:.2f} MB memory")
            
        except Exception as e:
            self.logger.error(f"Error logging memory usage: {e}")

class SecurityLogger:
    """
    Logger for security events
    """
    
    def __init__(self):
        self.logger = logging.getLogger('security')
        
    def log_failed_authentication(self, user_id: int, attempt_type: str):
        """Log failed authentication attempts"""
        try:
            self.logger.warning(f"Failed authentication attempt by user {user_id}: {attempt_type}")
            
        except Exception as e:
            self.logger.error(f"Error logging failed authentication: {e}")
    
    def log_suspicious_activity(self, user_id: int, activity: str, details: dict = None):
        """Log suspicious activities"""
        try:
            message = f"Suspicious activity by user {user_id}: {activity}"
            if details:
                message += f" - Details: {details}"
            
            self.logger.warning(message)
            
        except Exception as e:
            self.logger.error(f"Error logging suspicious activity: {e}")
    
    def log_rate_limit_exceeded(self, user_id: int, limit_type: str):
        """Log rate limit violations"""
        try:
            self.logger.warning(f"Rate limit exceeded by user {user_id}: {limit_type}")
            
        except Exception as e:
            self.logger.error(f"Error logging rate limit: {e}")

def setup_all_loggers():
    """Setup all logging components"""
    try:
        # Setup main logger
        main_logger = setup_logger()
        
        # Setup specialized loggers
        user_action_logger = UserActionLogger()
        performance_logger = PerformanceLogger()
        security_logger = SecurityLogger()
        
        # Setup Telegram error notifications if configured
        if Config.BOT_TOKEN and Config.ADMIN_IDS:
            for admin_id in Config.ADMIN_IDS:
                try:
                    telegram_handler = TelegramLogHandler(
                        Config.BOT_TOKEN,
                        str(admin_id),
                        logging.CRITICAL
                    )
                    main_logger.addHandler(telegram_handler)
                except Exception as e:
                    main_logger.error(f"Failed to setup Telegram logging for admin {admin_id}: {e}")
        
        main_logger.info("All loggers initialized successfully")
        
        return {
            "main": main_logger,
            "user_actions": user_action_logger,
            "performance": performance_logger,
            "security": security_logger
        }
        
    except Exception as e:
        print(f"Failed to setup loggers: {e}")
        return {"main": logging.getLogger()}

# Context manager for performance logging
class LogProcessingTime:
    """Context manager for logging processing time"""
    
    def __init__(self, operation: str, file_size: int = None):
        self.operation = operation
        self.file_size = file_size
        self.start_time = None
        self.performance_logger = PerformanceLogger()
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.performance_logger.log_processing_time(
                self.operation,
                duration,
                self.file_size
            )

# Usage example:
# with LogProcessingTime("file_processing", file_size=1024*1024):
#     # Your processing code here
#     pass

def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling function {func.__name__} with args: {args}, kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Function {func.__name__} failed with error: {e}")
            raise
    
    return wrapper

def log_async_function_call(func):
    """Decorator to log async function calls"""
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling async function {func.__name__} with args: {args}, kwargs: {kwargs}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Async function {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Async function {func.__name__} failed with error: {e}")
            raise
    
    return wrapper

# Initialize loggers on module import
if __name__ != "__main__":
    setup_logger()
