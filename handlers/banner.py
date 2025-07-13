"""
PDF Banner functionality for document processing
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from middleware.auth import require_auth
from middleware.subscription_check import subscription_required

logger = logging.getLogger(__name__)

BANNER_POSITIONS = {
    'start': {
        'name': 'Start',
        'description': 'Add banner at the beginning of PDF',
        'icon': '🔝'
    },
    'end': {
        'name': 'End',
        'description': 'Add banner at the end of PDF',
        'icon': '🔚'
    },
    'both': {
        'name': 'Both',
        'description': 'Add banner at start and end',
        'icon': '🔄'
    },
    'disabled': {
        'name': 'Disabled',
        'description': 'No banner will be added',
        'icon': '❌'
    }
}

@require_auth
@subscription_required
async def banner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /banner command"""
    user_id = update.effective_user.id
    
    try:
        await show_banner_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in banner command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading banner settings."
        )

async def show_banner_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show PDF banner settings menu"""
    try:
        settings = await db.get_user_settings(user_id)
        current_position = getattr(settings, 'banner_position', 'disabled')
        banner_enabled = getattr(settings, 'banner_enabled', False)
        
        message_text = "📑 **PDF Banner Settings**\n\n"
        message_text += "Configure banner placement for PDF documents:\n\n"
        
        current_info = BANNER_POSITIONS.get(current_position, BANNER_POSITIONS['disabled'])
        message_text += f"**Current Setting:** {current_info['icon']} {current_info['name']}\n"
        message_text += f"**Description:** {current_info['description']}\n"
        message_text += f"**Status:** {'✅ Enabled' if banner_enabled else '❌ Disabled'}\n\n"
        
        message_text += "**Banner Features:**\n"
        message_text += "• Custom banner text or image\n"
        message_text += "• Multiple position options\n"
        message_text += "• Automatic PDF processing\n"
        message_text += "• Premium templates available\n\n"
        
        message_text += "**Position Options:**\n"
        for pos_key, pos_info in BANNER_POSITIONS.items():
            status = "✅" if pos_key == current_position else "◻️"
            message_text += f"• {status} {pos_info['icon']} {pos_info['name']} - {pos_info['description']}\n"
        
        keyboard = [
            [InlineKeyboardButton("⚙️ Configure Position", callback_data="banner_position")],
            [InlineKeyboardButton("🎨 Banner Design", callback_data="banner_design")],
            [InlineKeyboardButton("📝 Banner Text", callback_data="banner_text")],
            [InlineKeyboardButton("🔄 Preview", callback_data="banner_preview")],
            [InlineKeyboardButton("🏠 Back", callback_data="settings_main")]
        ]
        
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
        logger.error(f"Error showing banner menu: {e}")
        await update.message.reply_text("❌ Error loading banner settings.")

async def banner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle banner callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data == "banner_position":
            await show_banner_position(update, context, user_id)
        elif data == "banner_design":
            await show_banner_design(update, context, user_id)
        elif data == "banner_text":
            await show_banner_text(update, context, user_id)
        elif data == "banner_preview":
            await show_banner_preview(update, context, user_id)
        elif data.startswith("banner_set_"):
            position = data.replace("banner_set_", "")
            await set_banner_position(update, context, user_id, position)
        elif data.startswith("banner_toggle_"):
            setting = data.replace("banner_toggle_", "")
            await toggle_banner_setting(update, context, user_id, setting)
            
    except Exception as e:
        logger.error(f"Error handling banner callback: {e}")
        await query.edit_message_text("❌ Error processing banner settings.")

async def show_banner_position(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show banner position selection"""
    try:
        settings = await db.get_user_settings(user_id)
        current_position = getattr(settings, 'banner_position', 'disabled')
        
        position_text = "🎯 **Banner Position Settings**\n\n"
        position_text += "Choose where to place the banner in PDF files:\n\n"
        
        keyboard = []
        for pos_key, pos_info in BANNER_POSITIONS.items():
            status = "✅" if pos_key == current_position else "◻️"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {pos_info['icon']} {pos_info['name']}", 
                    callback_data=f"banner_set_{pos_key}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Banner", callback_data="banner_main")
        ])
        
        await update.callback_query.edit_message_text(
            position_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing banner position: {e}")
        await update.callback_query.edit_message_text("❌ Error loading position settings.")

async def show_banner_design(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show banner design options"""
    try:
        settings = await db.get_user_settings(user_id)
        banner_style = getattr(settings, 'banner_style', 'simple')
        banner_color = getattr(settings, 'banner_color', '#000000')
        
        design_text = "🎨 **Banner Design Settings**\n\n"
        design_text += "Customize the appearance of your PDF banner:\n\n"
        
        design_text += f"**Current Style:** {banner_style.title()}\n"
        design_text += f"**Color:** {banner_color}\n\n"
        
        design_text += "**Available Styles:**\n"
        design_text += "• Simple - Basic text banner\n"
        design_text += "• Gradient - Gradient background\n"
        design_text += "• Border - With decorative border\n"
        design_text += "• Logo - Include custom logo\n"
        design_text += "• Watermark - Semi-transparent overlay\n\n"
        
        design_text += "**Color Options:**\n"
        design_text += "• Black (#000000)\n"
        design_text += "• Blue (#0066cc)\n"
        design_text += "• Red (#cc0000)\n"
        design_text += "• Green (#00cc00)\n"
        design_text += "• Custom color\n"
        
        keyboard = [
            [InlineKeyboardButton("🖌️ Style", callback_data="banner_style")],
            [InlineKeyboardButton("🎨 Color", callback_data="banner_color")],
            [InlineKeyboardButton("🖼️ Logo", callback_data="banner_logo")],
            [InlineKeyboardButton("🔙 Back", callback_data="banner_main")]
        ]
        
        await update.callback_query.edit_message_text(
            design_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing banner design: {e}")
        await update.callback_query.edit_message_text("❌ Error loading design settings.")

async def show_banner_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show banner text configuration"""
    try:
        settings = await db.get_user_settings(user_id)
        banner_text = getattr(settings, 'banner_text', 'Processed by File Rename Bot')
        
        text_config = "📝 **Banner Text Settings**\n\n"
        text_config += "Configure the text that appears in your PDF banner:\n\n"
        
        text_config += f"**Current Text:** `{banner_text}`\n\n"
        
        text_config += "**Available Variables:**\n"
        text_config += "• `{filename}` - Original filename\n"
        text_config += "• `{date}` - Current date\n"
        text_config += "• `{time}` - Current time\n"
        text_config += "• `{user}` - Your username\n"
        text_config += "• `{bot}` - Bot name\n\n"
        
        text_config += "**Template Examples:**\n"
        text_config += "• `Processed by {bot} on {date}`\n"
        text_config += "• `{filename} - Modified {date}`\n"
        text_config += "• `© {user} - {date}`\n"
        text_config += "• `Document processed at {time}`\n\n"
        
        text_config += "**Send your custom banner text:**"
        
        keyboard = [
            [InlineKeyboardButton("📋 Use Template", callback_data="banner_text_template")],
            [InlineKeyboardButton("🔄 Preview", callback_data="banner_text_preview")],
            [InlineKeyboardButton("🔙 Back", callback_data="banner_main")]
        ]
        
        await update.callback_query.edit_message_text(
            text_config,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Set state for text input
        context.user_data['waiting_for_banner_text'] = True
        
    except Exception as e:
        logger.error(f"Error showing banner text: {e}")
        await update.callback_query.edit_message_text("❌ Error loading text settings.")

async def show_banner_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show banner preview"""
    try:
        settings = await db.get_user_settings(user_id)
        banner_position = getattr(settings, 'banner_position', 'disabled')
        banner_text = getattr(settings, 'banner_text', 'Processed by File Rename Bot')
        banner_style = getattr(settings, 'banner_style', 'simple')
        
        if banner_position == 'disabled':
            await update.callback_query.edit_message_text(
                "❌ Banner is disabled. Enable it first to see preview.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚙️ Enable Banner", callback_data="banner_position"),
                    InlineKeyboardButton("🔙 Back", callback_data="banner_main")
                ]])
            )
            return
        
        preview_text = "🔄 **Banner Preview**\n\n"
        preview_text += "Here's how your banner will look:\n\n"
        
        preview_text += f"**Position:** {BANNER_POSITIONS[banner_position]['name']}\n"
        preview_text += f"**Style:** {banner_style.title()}\n"
        preview_text += f"**Text:** `{banner_text}`\n\n"
        
        # Generate preview
        sample_text = format_banner_text(banner_text, "Sample Document.pdf", user_id)
        
        preview_text += "**Banner Content:**\n"
        preview_text += f"```\n{sample_text}\n```\n\n"
        
        if banner_position == 'start':
            preview_text += "**Placement:** Top of first page\n"
        elif banner_position == 'end':
            preview_text += "**Placement:** Bottom of last page\n"
        elif banner_position == 'both':
            preview_text += "**Placement:** Top of first page and bottom of last page\n"
        
        preview_text += "\n**Note:** This is a text preview. The actual banner will be formatted according to your style settings."
        
        keyboard = [
            [InlineKeyboardButton("📄 Test with PDF", callback_data="banner_test_pdf")],
            [InlineKeyboardButton("🔙 Back", callback_data="banner_main")]
        ]
        
        await update.callback_query.edit_message_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing banner preview: {e}")
        await update.callback_query.edit_message_text("❌ Error generating preview.")

async def set_banner_position(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, position: str):
    """Set banner position"""
    try:
        if position not in BANNER_POSITIONS:
            await update.callback_query.edit_message_text("❌ Invalid banner position.")
            return
        
        # Update user settings
        settings_update = {
            "banner_position": position,
            "banner_enabled": position != 'disabled'
        }
        await db.update_user_settings(user_id, settings_update)
        
        position_info = BANNER_POSITIONS[position]
        
        success_text = f"✅ **Banner Position Updated**\n\n"
        success_text += f"**Position:** {position_info['icon']} {position_info['name']}\n"
        success_text += f"**Description:** {position_info['description']}\n"
        
        if position != 'disabled':
            success_text += f"**Status:** ✅ Enabled\n\n"
            success_text += "**Next steps:**\n"
            success_text += "• Configure banner text and design\n"
            success_text += "• Test with a PDF file\n"
            success_text += "• Upload PDFs to see banner in action\n"
        else:
            success_text += f"**Status:** ❌ Disabled\n\n"
            success_text += "Banner will not be added to PDF files."
        
        keyboard = [
            [InlineKeyboardButton("🎨 Design Settings", callback_data="banner_design")],
            [InlineKeyboardButton("🔄 Preview", callback_data="banner_preview")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        await update.callback_query.edit_message_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} set banner position to {position}")
        
    except Exception as e:
        logger.error(f"Error setting banner position: {e}")
        await update.callback_query.edit_message_text("❌ Error updating banner position.")

async def handle_banner_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle banner text input from user"""
    try:
        if not context.user_data.get('waiting_for_banner_text'):
            return
        
        user_id = update.effective_user.id
        banner_text = update.message.text.strip()
        
        if not banner_text:
            await update.message.reply_text("❌ Banner text cannot be empty.")
            return
        
        # Update user settings
        await db.update_user_settings(user_id, {"banner_text": banner_text})
        
        # Clear waiting state
        context.user_data['waiting_for_banner_text'] = False
        
        # Show preview
        sample_text = format_banner_text(banner_text, "Sample Document.pdf", user_id)
        
        success_text = f"✅ **Banner Text Updated**\n\n"
        success_text += f"**Text:** `{banner_text}`\n\n"
        success_text += f"**Preview:**\n"
        success_text += f"```\n{sample_text}\n```\n\n"
        success_text += "This text will be added to your PDF files according to your position settings."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Preview Banner", callback_data="banner_preview")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        await update.message.reply_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} set banner text: {banner_text}")
        
    except Exception as e:
        logger.error(f"Error handling banner text input: {e}")
        await update.message.reply_text("❌ Error updating banner text.")

def format_banner_text(template: str, filename: str, user_id: int) -> str:
    """Format banner text with variables"""
    try:
        from datetime import datetime
        
        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Replace variables
        formatted = template.replace('{filename}', filename)
        formatted = formatted.replace('{date}', date_str)
        formatted = formatted.replace('{time}', time_str)
        formatted = formatted.replace('{user}', f"User{user_id}")
        formatted = formatted.replace('{bot}', "File Rename Bot")
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting banner text: {e}")
        return template

async def add_banner_to_pdf(pdf_path: str, banner_settings: dict, filename: str, user_id: int) -> str:
    """Add banner to PDF file"""
    try:
        # This is a placeholder for PDF banner functionality
        # In a real implementation, you would use a library like PyPDF2 or ReportLab
        
        banner_position = banner_settings.get('banner_position', 'disabled')
        
        if banner_position == 'disabled':
            return pdf_path
        
        banner_text = banner_settings.get('banner_text', 'Processed by File Rename Bot')
        formatted_text = format_banner_text(banner_text, filename, user_id)
        
        logger.info(f"Adding banner to PDF: {pdf_path}")
        logger.info(f"Banner position: {banner_position}")
        logger.info(f"Banner text: {formatted_text}")
        
        # TODO: Implement actual PDF banner addition
        # For now, just return the original path
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error adding banner to PDF: {e}")
        return pdf_path

def get_user_banner_settings(user_settings) -> dict:
    """Get user's banner settings"""
    try:
        return {
            'banner_enabled': getattr(user_settings, 'banner_enabled', False),
            'banner_position': getattr(user_settings, 'banner_position', 'disabled'),
            'banner_text': getattr(user_settings, 'banner_text', 'Processed by File Rename Bot'),
            'banner_style': getattr(user_settings, 'banner_style', 'simple'),
            'banner_color': getattr(user_settings, 'banner_color', '#000000')
        }
    except Exception as e:
        logger.error(f"Error getting banner settings: {e}")
        return {
            'banner_enabled': False,
            'banner_position': 'disabled',
            'banner_text': 'Processed by File Rename Bot',
            'banner_style': 'simple',
            'banner_color': '#000000'
        }

def is_banner_enabled(user_settings) -> bool:
    """Check if banner is enabled"""
    return getattr(user_settings, 'banner_enabled', False)

def should_add_banner(file_type: str, user_settings) -> bool:
    """Check if banner should be added to file"""
    return file_type == 'document' and is_banner_enabled(user_settings)