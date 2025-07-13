"""
Start command handler and basic bot information
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from database.models import User, UserSettings
from utils.helpers import generate_referral_code, get_user_info
from middleware.subscription_check import check_force_subscription

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Check if user exists in database
        existing_user = await db.get_user(user.id)
        
        if not existing_user:
            # Create new user
            referral_code = generate_referral_code()
            new_user = User(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                referral_code=referral_code
            )
            
            # Handle referral if present
            if context.args and context.args[0].startswith('ref_'):
                referrer_code = context.args[0][4:]  # Remove 'ref_' prefix
                referrer = await db.get_user_by_referral_code(referrer_code)
                if referrer:
                    new_user.referred_by = referrer.user_id
                    # Grant referral bonus to referrer
                    await db.update_user(referrer.user_id, {
                        "is_premium": True,
                        "premium_expires": None  # Extended premium
                    })
            
            await db.create_user(new_user)
            
            # Create default settings
            settings = UserSettings(user_id=user.id)
            await db.create_user_settings(settings)
            
            logger.info(f"New user registered: {user.id}")
        else:
            # Update existing user info
            await db.update_user(user.id, {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code
            })
        
        # Check force subscription
        if not await check_force_subscription(user.id, context):
            keyboard = [[InlineKeyboardButton("🔄 Check Subscription", callback_data="sub_check")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🚫 **Access Restricted**\n\n"
                "To use this bot, you must join our official channels first:\n\n"
                "Please join all required channels and then click the button below.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return
        
        # Welcome message
        welcome_text = f"""
🎉 **Welcome to File Rename Bot!**

Hi {user.first_name}! I'm here to help you rename and process your files efficiently.

🔧 **What I can do:**
• 📁 Rename files with custom templates
• 🖼️ Add custom thumbnails to videos
• ⚡ Auto-rename files based on patterns
• 🎵 Process audio, video, and documents
• 📊 Support files up to 5GB

🚀 **Quick Start:**
1. Send me a file to rename
2. Use /settings to configure rename templates
3. Use /thumbnail to manage thumbnails
4. Use /autorename to enable automatic renaming

💡 **Commands:**
/help - Show all commands
/settings - Configure bot settings
/premium - Upgrade to premium
/about - About this bot

Ready to get started? Send me any file!
        """
        
        keyboard = [
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")],
            [InlineKeyboardButton("💎 Premium", callback_data="sub_premium")],
            [InlineKeyboardButton("📚 Help", callback_data="help_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while processing your request. Please try again."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📚 **Bot Commands Help**

🔧 **Basic Commands:**
/start - Start the bot and get welcome message
/help - Show this help message
/about - Information about the bot
/settings - Configure bot settings

📁 **File Operations:**
Just send any file to rename it!
• Documents (PDF, DOC, etc.)
• Videos (MP4, AVI, MKV, etc.)
• Audio (MP3, WAV, etc.)
• Maximum file size: 5GB

🎨 **Thumbnail Commands:**
/thumbnail - Upload custom thumbnails
/mythumbnails - View your thumbnails

⚡ **Auto Features:**
/autorename - Toggle automatic renaming

💎 **Premium Features:**
/premium - Upgrade to premium
/referral - Get your referral link

🔤 **Rename Templates:**
Use variables in your rename templates:
• {title} - Original filename
• {season} - Season number (S01, S02, etc.)
• {episode} - Episode number (E01, E02, etc.)
• {year} - Year (2024, 2025, etc.)
• {quality} - Quality (1080p, 720p, etc.)

📝 **Example Templates:**
• `{title} - {season}{episode}`
• `{title} ({year}) [{quality}]`
• `Movie - {title} - {year}`

❓ **Need Help?**
Contact support through the bot or join our support channel.
    """
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command"""
    about_text = """
🤖 **About File Rename Bot**

**Version:** 1.0.0
**Developer:** @YourUsername
**Last Updated:** July 2025

🌟 **Features:**
• Advanced file renaming with templates
• Custom thumbnail support
• Auto-rename functionality
• Premium subscription system
• Referral program
• Support for large files (up to 5GB)
• MongoDB data persistence

🔧 **Technology Stack:**
• Python 3.8+
• python-telegram-bot
• MongoDB
• FFmpeg for media processing
• PIL for image processing

📊 **Statistics:**
• Total Users: Getting stats...
• Files Processed: Getting stats...
• Premium Users: Getting stats...

🤝 **Support:**
If you encounter any issues or have suggestions, please contact our support team.

💝 **Support Development:**
This bot is free to use. Consider upgrading to premium to support development and unlock advanced features!
    """
    
    try:
        stats = await db.get_bot_stats()
        about_text = about_text.replace("Getting stats...", f"{stats.total_users:,}")
        about_text = about_text.replace("Getting stats...", f"{stats.total_files_processed:,}")
        about_text = about_text.replace("Getting stats...", f"{stats.premium_users:,}")
    except Exception as e:
        logger.error(f"Error getting stats for about: {e}")
    
    keyboard = [
        [InlineKeyboardButton("🏠 Home", callback_data="start_main")],
        [InlineKeyboardButton("💎 Premium", callback_data="sub_premium")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        about_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
