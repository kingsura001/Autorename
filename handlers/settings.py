"""
Settings handler for user configuration
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from database.models import UserSettings

logger = logging.getLogger(__name__)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    user_id = update.effective_user.id
    
    try:
        # Get user settings
        settings = await db.get_user_settings(user_id)
        if not settings:
            settings = UserSettings(user_id=user_id)
            await db.create_user_settings(settings)
        
        await show_settings_menu(update, context, settings)
        
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading settings. Please try again."
        )

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: UserSettings):
    """Show main settings menu"""
    auto_rename_status = "✅ On" if settings.auto_rename else "❌ Off"
    thumbnail_mode_status = "✅ On" if settings.thumbnail_mode else "❌ Off"
    notifications_status = "✅ On" if settings.notification_enabled else "❌ Off"
    
    settings_text = f"""
⚙️ **Bot Settings**

📝 **Rename Template:** `{settings.rename_template}`
⚡ **Auto Rename:** {auto_rename_status}
🖼️ **Thumbnail Mode:** {thumbnail_mode_status}
🔔 **Notifications:** {notifications_status}
🎞️ **Quality Preference:** {settings.quality_preference.title()}

💡 **Template Variables:**
• `{{title}}` - Original filename
• `{{season}}` - Season (S01, S02, etc.)
• `{{episode}}` - Episode (E01, E02, etc.)
• `{{year}}` - Year (2024, 2025, etc.)
• `{{quality}}` - Quality (1080p, 720p, etc.)

📋 **Template Examples:**
• `{{title}} - {{season}}{{episode}}`
• `{{title}} ({{year}}) [{{quality}}]`
• `Movie - {{title}} - {{year}}`
    """
    
    keyboard = [
        [InlineKeyboardButton("📝 Change Template", callback_data="settings_template")],
        [InlineKeyboardButton("⚡ Auto Rename", callback_data="settings_autorename")],
        [InlineKeyboardButton("🖼️ Thumbnail Mode", callback_data="settings_thumbnail")],
        [InlineKeyboardButton("🎞️ Quality", callback_data="settings_quality")],
        [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
        [InlineKeyboardButton("🔄 Reset to Default", callback_data="settings_reset")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            settings_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data.replace("settings_", "")
    
    try:
        settings = await db.get_user_settings(user_id)
        if not settings:
            settings = UserSettings(user_id=user_id)
            await db.create_user_settings(settings)
        
        if action == "main":
            await show_settings_menu(update, context, settings)
        
        elif action == "template":
            await show_template_settings(update, context, settings)
        
        elif action == "autorename":
            # Toggle auto rename
            new_value = not settings.auto_rename
            await db.update_user_settings(user_id, {"auto_rename": new_value})
            
            status = "enabled" if new_value else "disabled"
            await query.edit_message_text(
                f"✅ Auto rename has been {status}!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")
                ]])
            )
        
        elif action == "thumbnail":
            # Toggle thumbnail mode
            new_value = not settings.thumbnail_mode
            await db.update_user_settings(user_id, {"thumbnail_mode": new_value})
            
            status = "enabled" if new_value else "disabled"
            await query.edit_message_text(
                f"✅ Thumbnail mode has been {status}!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")
                ]])
            )
        
        elif action == "quality":
            await show_quality_settings(update, context, settings)
        
        elif action == "notifications":
            # Toggle notifications
            new_value = not settings.notification_enabled
            await db.update_user_settings(user_id, {"notification_enabled": new_value})
            
            status = "enabled" if new_value else "disabled"
            await query.edit_message_text(
                f"✅ Notifications have been {status}!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")
                ]])
            )
        
        elif action == "reset":
            await reset_settings(update, context, user_id)
        
        elif action.startswith("quality_"):
            quality = action.replace("quality_", "")
            await db.update_user_settings(user_id, {"quality_preference": quality})
            
            await query.edit_message_text(
                f"✅ Quality preference set to: {quality.title()}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")
                ]])
            )
        
        elif action.startswith("template_"):
            template_type = action.replace("template_", "")
            templates = {
                "basic": "{title}",
                "series": "{title} - {season}{episode}",
                "movie": "{title} ({year}) [{quality}]",
                "detailed": "{title} - {season}{episode} - {quality}"
            }
            
            if template_type in templates:
                await db.update_user_settings(user_id, {"rename_template": templates[template_type]})
                
                await query.edit_message_text(
                    f"✅ Template updated to: `{templates[template_type]}`",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")
                    ]])
                )
        
    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        await query.edit_message_text(
            "❌ An error occurred while updating settings. Please try again."
        )

async def show_template_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: UserSettings):
    """Show template selection menu"""
    template_text = f"""
📝 **Rename Template Settings**

**Current Template:** `{settings.rename_template}`

Choose a template or send a custom one:

🔤 **Available Variables:**
• `{{title}}` - Original filename
• `{{season}}` - Season (S01, S02, etc.)
• `{{episode}}` - Episode (E01, E02, etc.)
• `{{year}}` - Year (2024, 2025, etc.)
• `{{quality}}` - Quality (1080p, 720p, etc.)

📋 **Quick Templates:**
    """
    
    keyboard = [
        [InlineKeyboardButton("📄 Basic: {title}", callback_data="settings_template_basic")],
        [InlineKeyboardButton("📺 Series: {title} - {season}{episode}", callback_data="settings_template_series")],
        [InlineKeyboardButton("🎬 Movie: {title} ({year}) [{quality}]", callback_data="settings_template_movie")],
        [InlineKeyboardButton("🎯 Detailed: {title} - {season}{episode} - {quality}", callback_data="settings_template_detailed")],
        [InlineKeyboardButton("✏️ Custom Template", callback_data="settings_template_custom")],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        template_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def show_quality_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: UserSettings):
    """Show quality preference settings"""
    quality_text = f"""
🎞️ **Quality Preference Settings**

**Current Setting:** {settings.quality_preference.title()}

Choose your preferred quality for processed files:

📊 **Quality Options:**
• **Original** - Keep original quality (recommended)
• **High** - High quality (1080p)
• **Medium** - Medium quality (720p)
• **Low** - Low quality (480p)

⚠️ **Note:** Lower quality settings will reduce file size but may affect visual quality.
    """
    
    keyboard = [
        [InlineKeyboardButton("🎯 Original", callback_data="settings_quality_original")],
        [InlineKeyboardButton("🔥 High", callback_data="settings_quality_high")],
        [InlineKeyboardButton("⚡ Medium", callback_data="settings_quality_medium")],
        [InlineKeyboardButton("💾 Low", callback_data="settings_quality_low")],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        quality_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Reset user settings to default"""
    try:
        default_settings = {
            "rename_template": "{title}",
            "auto_rename": False,
            "thumbnail_mode": False,
            "default_thumbnail": None,
            "quality_preference": "original",
            "auto_upload": False,
            "notification_enabled": True
        }
        
        await db.update_user_settings(user_id, default_settings)
        
        await update.callback_query.edit_message_text(
            "✅ Settings have been reset to default values!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings_main")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while resetting settings. Please try again."
        )
