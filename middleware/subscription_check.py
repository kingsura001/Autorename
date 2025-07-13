"""
Subscription check middleware for force subscription feature
"""

import logging
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from database.connection import db
from database.models import ForceSubChannel
from utils.helpers import is_admin

logger = logging.getLogger(__name__)

async def check_force_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user has subscribed to all required channels
    
    Args:
        user_id: Telegram user ID
        context: Bot context
        
    Returns:
        True if user has subscribed to all channels or no channels required
    """
    try:
        # Skip check for admins
        if is_admin(user_id):
            return True
        
        # Get force subscription channels
        channels = await db.get_force_sub_channels()
        
        # If no channels configured, allow access
        if not channels:
            return True
        
        # Check subscription status for each channel
        for channel in channels:
            if not await check_channel_subscription(user_id, channel, context):
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking force subscription: {e}")
        # On error, allow access to prevent blocking legitimate users
        return True

async def check_channel_subscription(user_id: int, channel: ForceSubChannel, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is subscribed to a specific channel
    
    Args:
        user_id: Telegram user ID
        channel: Force subscription channel object
        context: Bot context
        
    Returns:
        True if user is subscribed to the channel
    """
    try:
        # Get chat member information
        member = await context.bot.get_chat_member(channel.channel_id, user_id)
        
        # Check if user is a member (not left or kicked)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        
        return False
        
    except TelegramError as e:
        logger.error(f"Telegram error checking subscription to {channel.channel_id}: {e}")
        
        # Handle specific errors
        if "chat not found" in str(e).lower():
            logger.warning(f"Channel {channel.channel_id} not found, removing from requirements")
            # In a real implementation, you might want to deactivate this channel
            return True
        elif "user not found" in str(e).lower():
            logger.warning(f"User {user_id} not found in channel {channel.channel_id}")
            return False
        elif "forbidden" in str(e).lower():
            logger.warning(f"Bot doesn't have permission to check {channel.channel_id}")
            # If bot can't check, assume user is subscribed to avoid blocking
            return True
        
        # On other errors, assume not subscribed for security
        return False
    except Exception as e:
        logger.error(f"Error checking channel subscription: {e}")
        return False

async def get_subscription_message(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> tuple[str, InlineKeyboardMarkup]:
    """
    Get subscription message and keyboard for unsubscribed user
    
    Args:
        user_id: Telegram user ID
        context: Bot context
        
    Returns:
        Tuple of (message_text, keyboard_markup)
    """
    try:
        channels = await db.get_force_sub_channels()
        
        message_text = "🚫 **Subscription Required**\n\n"
        message_text += "To use this bot, you must join our official channels:\n\n"
        
        keyboard = []
        
        for i, channel in enumerate(channels, 1):
            # Add channel info to message
            message_text += f"{i}. **{channel.channel_name}**\n"
            
            # Create join button
            if channel.channel_username:
                # Public channel with username
                join_url = f"https://t.me/{channel.channel_username.replace('@', '')}"
                button_text = f"📺 Join {channel.channel_name}"
            else:
                # Private channel with invite link
                try:
                    # Try to get invite link
                    invite_link = await context.bot.export_chat_invite_link(channel.channel_id)
                    join_url = invite_link
                    button_text = f"📺 Join {channel.channel_name}"
                except Exception as e:
                    logger.error(f"Error getting invite link for {channel.channel_id}: {e}")
                    # Fallback to channel ID (will open in Telegram)
                    join_url = f"https://t.me/c/{channel.channel_id.replace('-100', '')}"
                    button_text = f"📺 Join {channel.channel_name}"
            
            keyboard.append([InlineKeyboardButton(button_text, url=join_url)])
        
        message_text += "\n✅ **After joining all channels, click the button below to verify your subscription.**"
        
        # Add verification button
        keyboard.append([InlineKeyboardButton("🔄 Verify Subscription", callback_data="sub_check")])
        
        return message_text, InlineKeyboardMarkup(keyboard)
        
    except Exception as e:
        logger.error(f"Error getting subscription message: {e}")
        return (
            "🚫 **Subscription Required**\n\nPlease join our required channels to use this bot.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Try Again", callback_data="sub_check")]])
        )

async def handle_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle subscription check callback
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        # Check subscription status
        if await check_force_subscription(user_id, context):
            await query.edit_message_text(
                "✅ **Subscription Verified!**\n\n"
                "Welcome! You can now use all bot features.\n\n"
                "Type /help to see available commands.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")
                ]])
            )
        else:
            # Still not subscribed, show subscription message again
            message_text, keyboard = await get_subscription_message(user_id, context)
            await query.edit_message_text(
                message_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error(f"Error handling subscription check: {e}")
        await query.edit_message_text(
            "❌ An error occurred while checking your subscription. Please try again.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Try Again", callback_data="sub_check")
            ]])
        )

def subscription_required(func):
    """
    Decorator to require subscription before executing function
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check subscription
        if not await check_force_subscription(user_id, context):
            message_text, keyboard = await get_subscription_message(user_id, context)
            
            if update.message:
                await update.message.reply_text(
                    message_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    message_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            
            return
        
        # User is subscribed, execute original function
        return await func(update, context, *args, **kwargs)
    
    return wrapper

async def get_unsubscribed_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> List[ForceSubChannel]:
    """
    Get list of channels user is not subscribed to
    
    Args:
        user_id: Telegram user ID
        context: Bot context
        
    Returns:
        List of channels user is not subscribed to
    """
    try:
        channels = await db.get_force_sub_channels()
        unsubscribed = []
        
        for channel in channels:
            if not await check_channel_subscription(user_id, channel, context):
                unsubscribed.append(channel)
        
        return unsubscribed
        
    except Exception as e:
        logger.error(f"Error getting unsubscribed channels: {e}")
        return []

async def notify_subscription_update(channel_id: str, context: ContextTypes.DEFAULT_TYPE):
    """
    Notify when subscription requirements are updated
    
    Args:
        channel_id: Channel ID that was added/removed
        context: Bot context
    """
    try:
        # This could be used to notify users about changes
        # For now, just log the event
        logger.info(f"Subscription requirements updated for channel: {channel_id}")
        
        # In a real implementation, you might want to:
        # 1. Notify existing users about new requirements
        # 2. Update cached subscription status
        # 3. Send admin notifications
        
    except Exception as e:
        logger.error(f"Error notifying subscription update: {e}")

class SubscriptionManager:
    """
    Manager class for subscription-related operations
    """
    
    def __init__(self):
        self.subscription_cache = {}
        self.cache_expiry = 300  # 5 minutes
    
    async def is_subscribed(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Check subscription with caching
        
        Args:
            user_id: Telegram user ID
            context: Bot context
            
        Returns:
            True if user is subscribed
        """
        try:
            import time
            current_time = time.time()
            
            # Check cache
            if user_id in self.subscription_cache:
                cached_data = self.subscription_cache[user_id]
                if current_time - cached_data['timestamp'] < self.cache_expiry:
                    return cached_data['subscribed']
            
            # Check actual subscription
            subscribed = await check_force_subscription(user_id, context)
            
            # Update cache
            self.subscription_cache[user_id] = {
                'subscribed': subscribed,
                'timestamp': current_time
            }
            
            return subscribed
            
        except Exception as e:
            logger.error(f"Error checking subscription with cache: {e}")
            return False
    
    def clear_cache(self, user_id: int = None):
        """
        Clear subscription cache
        
        Args:
            user_id: Specific user ID to clear, or None for all
        """
        try:
            if user_id:
                self.subscription_cache.pop(user_id, None)
            else:
                self.subscription_cache.clear()
        except Exception as e:
            logger.error(f"Error clearing subscription cache: {e}")
    
    async def get_subscription_stats(self) -> dict:
        """
        Get subscription statistics
        
        Returns:
            Dictionary with subscription stats
        """
        try:
            channels = await db.get_force_sub_channels()
            
            stats = {
                'total_channels': len(channels),
                'active_channels': len([c for c in channels if c.is_active]),
                'public_channels': len([c for c in channels if c.channel_username]),
                'private_channels': len([c for c in channels if not c.channel_username])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            return {}

# Global subscription manager instance
subscription_manager = SubscriptionManager()

# Utility functions for common operations
async def add_required_channel(channel_id: str, channel_name: str, channel_username: str = None) -> bool:
    """
    Add a channel to force subscription requirements
    
    Args:
        channel_id: Channel ID
        channel_name: Channel name
        channel_username: Channel username (optional)
        
    Returns:
        True if successfully added
    """
    try:
        channel = ForceSubChannel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_username=channel_username
        )
        
        success = await db.add_force_sub_channel(channel)
        
        if success:
            logger.info(f"Added force subscription channel: {channel_name}")
            # Clear cache since requirements changed
            subscription_manager.clear_cache()
        
        return success
        
    except Exception as e:
        logger.error(f"Error adding required channel: {e}")
        return False

async def remove_required_channel(channel_id: str) -> bool:
    """
    Remove a channel from force subscription requirements
    
    Args:
        channel_id: Channel ID to remove
        
    Returns:
        True if successfully removed
    """
    try:
        success = await db.remove_force_sub_channel(channel_id)
        
        if success:
            logger.info(f"Removed force subscription channel: {channel_id}")
            # Clear cache since requirements changed
            subscription_manager.clear_cache()
        
        return success
        
    except Exception as e:
        logger.error(f"Error removing required channel: {e}")
        return False

async def validate_channel_access(channel_id: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Validate that bot has access to check channel membership
    
    Args:
        channel_id: Channel ID to validate
        context: Bot context
        
    Returns:
        True if bot can access the channel
    """
    try:
        # Try to get chat information
        chat = await context.bot.get_chat(channel_id)
        
        # Check if bot is admin (needed to check membership)
        bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        
        if bot_member.status in ['administrator', 'creator']:
            return True
        
        logger.warning(f"Bot is not admin in channel {channel_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error validating channel access: {e}")
        return False
