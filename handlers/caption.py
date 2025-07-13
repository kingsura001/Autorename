"""
Caption handling and formatting for different styles
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from utils.helpers import is_admin
from middleware.auth import require_auth
from middleware.subscription_check import subscription_required

logger = logging.getLogger(__name__)

# Caption styles configuration
CAPTION_STYLES = {
    'normal': {
        'name': 'Normal',
        'format': '{filename}',
        'description': 'Standard caption with filename'
    },
    'no_caption': {
        'name': 'No Caption',
        'format': '',
        'description': 'No caption will be added'
    },
    'quote': {
        'name': 'Quote',
        'format': '> {filename}',
        'description': 'Quote formatting with > prefix'
    },
    'bold': {
        'name': 'Bold',
        'format': '**{filename}**',
        'description': 'Bold text formatting'
    },
    'italic': {
        'name': 'Italic',
        'format': '_{filename}_',
        'description': 'Italic text formatting'
    },
    'underline': {
        'name': 'Underline',
        'format': '___{filename}___',
        'description': 'Underlined text formatting'
    },
    'monospace': {
        'name': 'Monospace',
        'format': '`{filename}`',
        'description': 'Monospace font formatting'
    },
    'strikethrough': {
        'name': 'Strikethrough',
        'format': '~~{filename}~~',
        'description': 'Strikethrough text formatting'
    },
    'spoiler': {
        'name': 'Spoiler',
        'format': '||{filename}||',
        'description': 'Spoiler text formatting'
    },
    'reverse': {
        'name': 'Reverse',
        'format': '{filename}',
        'description': 'Reverse text direction',
        'special': True
    },
    'link': {
        'name': 'Link',
        'format': '[{filename}](https://t.me/{bot_username})',
        'description': 'Link formatting'
    }
}

@require_auth
@subscription_required
async def caption_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /caption command"""
    user_id = update.effective_user.id
    
    try:
        await show_caption_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in caption command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading caption settings."
        )

async def show_caption_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show caption style selection menu"""
    try:
        # Get current user settings
        settings = await db.get_user_settings(user_id)
        current_style = getattr(settings, 'caption_style', 'normal')
        
        message_text = "🎨 **Caption Style Settings**\n\n"
        message_text += "Choose how you want captions to be formatted for your files:\n\n"
        
        # Show current style
        current_style_info = CAPTION_STYLES.get(current_style, CAPTION_STYLES['normal'])
        message_text += f"**Current Style:** {current_style_info['name']}\n"
        message_text += f"**Format:** `{current_style_info['format']}`\n"
        message_text += f"**Description:** {current_style_info['description']}\n\n"
        
        # Create keyboard with all caption styles
        keyboard = []
        for style_key, style_info in CAPTION_STYLES.items():
            status = "✅" if style_key == current_style else "◻️"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {style_info['name']}", 
                    callback_data=f"caption_set_{style_key}"
                )
            ])
        
        # Add action buttons
        keyboard.append([
            InlineKeyboardButton("🔄 Preview", callback_data="caption_preview"),
            InlineKeyboardButton("🏠 Back", callback_data="settings_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                message_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing caption menu: {e}")
        await update.message.reply_text("❌ Error loading caption settings.")

async def caption_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle caption callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data.startswith("caption_set_"):
            # Set new caption style
            style = data.replace("caption_set_", "")
            await set_caption_style(update, context, user_id, style)
            
        elif data == "caption_preview":
            # Show preview of all caption styles
            await show_caption_preview(update, context, user_id)
            
        elif data == "caption_custom":
            # Show custom caption input
            await show_custom_caption_input(update, context, user_id)
            
    except Exception as e:
        logger.error(f"Error handling caption callback: {e}")
        await query.edit_message_text("❌ Error processing caption settings.")

async def set_caption_style(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, style: str):
    """Set caption style for user"""
    try:
        if style not in CAPTION_STYLES:
            await update.callback_query.edit_message_text("❌ Invalid caption style.")
            return
        
        # Update user settings
        await db.update_user_settings(user_id, {"caption_style": style})
        
        style_info = CAPTION_STYLES[style]
        
        success_text = f"✅ **Caption Style Updated**\n\n"
        success_text += f"**Style:** {style_info['name']}\n"
        success_text += f"**Format:** `{style_info['format']}`\n"
        success_text += f"**Description:** {style_info['description']}\n\n"
        success_text += "This style will be applied to all future file uploads."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Preview", callback_data="caption_preview")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        await update.callback_query.edit_message_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} set caption style to {style}")
        
    except Exception as e:
        logger.error(f"Error setting caption style: {e}")
        await update.callback_query.edit_message_text("❌ Error updating caption style.")

async def show_caption_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show preview of all caption styles"""
    try:
        preview_text = "🎨 **Caption Styles Preview**\n\n"
        preview_text += "Here's how your filename will look with different caption styles:\n\n"
        
        sample_filename = "Movie.Name.2024.1080p.BluRay.x264-GROUP"
        
        for style_key, style_info in CAPTION_STYLES.items():
            formatted_caption = format_caption(sample_filename, style_key, context)
            preview_text += f"**{style_info['name']}:**\n"
            preview_text += f"{formatted_caption}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Caption Settings", callback_data="caption_main")]
        ]
        
        await update.callback_query.edit_message_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing caption preview: {e}")
        await update.callback_query.edit_message_text("❌ Error generating preview.")

async def show_custom_caption_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show custom caption input instructions"""
    try:
        custom_text = "✏️ **Custom Caption Format**\n\n"
        custom_text += "You can create your own caption format using these variables:\n\n"
        custom_text += "• `{filename}` - Original filename\n"
        custom_text += "• `{title}` - Extracted title\n"
        custom_text += "• `{size}` - File size\n"
        custom_text += "• `{type}` - File type\n"
        custom_text += "• `{date}` - Current date\n"
        custom_text += "• `{time}` - Current time\n\n"
        custom_text += "**Example formats:**\n"
        custom_text += "• `📁 {filename} | {size}`\n"
        custom_text += "• `🎬 {title} - Uploaded on {date}`\n"
        custom_text += "• `**{filename}** _{size}_`\n\n"
        custom_text += "Send your custom format now:"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="caption_main")]
        ]
        
        await update.callback_query.edit_message_text(
            custom_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Store state for text handler
        context.user_data['waiting_for_custom_caption'] = True
        
    except Exception as e:
        logger.error(f"Error showing custom caption input: {e}")
        await update.callback_query.edit_message_text("❌ Error loading custom caption input.")

def format_caption(filename: str, style: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Format caption according to style"""
    try:
        if style not in CAPTION_STYLES:
            style = 'normal'
        
        style_info = CAPTION_STYLES[style]
        
        if style == 'no_caption':
            return ""
        
        # Handle special formatting
        if style == 'reverse':
            return filename[::-1]  # Reverse the string
        elif style == 'link':
            bot_username = context.bot.username or "FileRenameBot"
            return f"[{filename}](https://t.me/{bot_username})"
        else:
            return style_info['format'].format(filename=filename)
            
    except Exception as e:
        logger.error(f"Error formatting caption: {e}")
        return filename

async def handle_custom_caption_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom caption format input"""
    try:
        if not context.user_data.get('waiting_for_custom_caption'):
            return
        
        user_id = update.effective_user.id
        custom_format = update.message.text.strip()
        
        # Validate custom format
        if not custom_format:
            await update.message.reply_text("❌ Caption format cannot be empty.")
            return
        
        # Store custom format
        await db.update_user_settings(user_id, {
            "caption_style": "custom",
            "custom_caption_format": custom_format
        })
        
        # Clear waiting state
        context.user_data['waiting_for_custom_caption'] = False
        
        success_text = f"✅ **Custom Caption Format Saved**\n\n"
        success_text += f"**Format:** `{custom_format}`\n\n"
        success_text += "This format will be applied to all future file uploads."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Test Preview", callback_data="caption_preview")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        await update.message.reply_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} set custom caption format: {custom_format}")
        
    except Exception as e:
        logger.error(f"Error handling custom caption input: {e}")
        await update.message.reply_text("❌ Error saving custom caption format.")

def get_user_caption_style(user_settings) -> str:
    """Get user's caption style setting"""
    return getattr(user_settings, 'caption_style', 'normal')

def apply_caption_to_file(filename: str, file_info: dict, user_settings, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Apply caption formatting to file"""
    try:
        style = get_user_caption_style(user_settings)
        
        if style == 'custom':
            # Use custom format
            custom_format = getattr(user_settings, 'custom_caption_format', '{filename}')
            return custom_format.format(
                filename=filename,
                title=file_info.get('title', filename),
                size=file_info.get('size', 'Unknown'),
                type=file_info.get('type', 'Unknown'),
                date=file_info.get('date', ''),
                time=file_info.get('time', '')
            )
        else:
            return format_caption(filename, style, context)
            
    except Exception as e:
        logger.error(f"Error applying caption to file: {e}")
        return filename