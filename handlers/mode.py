"""
Mode management handler for rename modes
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from middleware.auth import require_auth
from middleware.subscription_check import subscription_required

logger = logging.getLogger(__name__)

RENAME_MODES = {
    'auto': {
        'name': 'Auto Rename',
        'description': 'Automatically rename files using templates',
        'icon': '⚡',
        'features': ['Template-based renaming', 'Variable substitution', 'Instant processing']
    },
    'manual': {
        'name': 'Manual Rename',
        'description': 'Ask for new name for each file',
        'icon': '✏️',
        'features': ['Interactive naming', 'Custom input', 'Full control']
    },
    'replace': {
        'name': 'Replace Mode',
        'description': 'Use text replacement rules',
        'icon': '🔄',
        'features': ['Text replacement', 'Pattern matching', 'Rule-based']
    }
}

@require_auth
@subscription_required
async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mode command"""
    user_id = update.effective_user.id
    
    try:
        await show_mode_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in mode command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading mode settings."
        )

@require_auth
@subscription_required
async def manual_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /manual command"""
    user_id = update.effective_user.id
    
    try:
        await set_rename_mode(update, context, user_id, 'manual')
        await update.message.reply_text(
            "✏️ **Manual Rename Mode Enabled**\n\n"
            "From now on, I'll ask you for a new name for each file you send.\n\n"
            "Send a file to try it out!"
        )
    except Exception as e:
        logger.error(f"Error in manual command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while setting manual mode."
        )

async def show_mode_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show rename mode selection menu"""
    try:
        # Get current mode
        settings = await db.get_user_settings(user_id)
        current_mode = getattr(settings, 'rename_mode', 'auto')
        
        message_text = "🎯 **Rename Mode Settings**\n\n"
        message_text += "Choose how you want files to be renamed:\n\n"
        
        # Show current mode
        current_mode_info = RENAME_MODES.get(current_mode, RENAME_MODES['auto'])
        message_text += f"**Current Mode:** {current_mode_info['icon']} {current_mode_info['name']}\n"
        message_text += f"**Description:** {current_mode_info['description']}\n\n"
        
        # Show all modes
        keyboard = []
        for mode_key, mode_info in RENAME_MODES.items():
            status = "✅" if mode_key == current_mode else "◻️"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {mode_info['icon']} {mode_info['name']}", 
                    callback_data=f"mode_set_{mode_key}"
                )
            ])
        
        # Add action buttons
        keyboard.append([
            InlineKeyboardButton("ℹ️ Mode Details", callback_data="mode_details"),
            InlineKeyboardButton("🔄 Preview", callback_data="mode_preview")
        ])
        keyboard.append([
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
        logger.error(f"Error showing mode menu: {e}")
        await update.message.reply_text("❌ Error loading mode settings.")

async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mode callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data.startswith("mode_set_"):
            mode = data.replace("mode_set_", "")
            await set_rename_mode(update, context, user_id, mode)
            
        elif data == "mode_details":
            await show_mode_details(update, context, user_id)
            
        elif data == "mode_preview":
            await show_mode_preview(update, context, user_id)
            
        elif data.startswith("mode_detail_"):
            mode = data.replace("mode_detail_", "")
            await show_specific_mode_detail(update, context, user_id, mode)
            
    except Exception as e:
        logger.error(f"Error handling mode callback: {e}")
        await query.edit_message_text("❌ Error processing mode settings.")

async def set_rename_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, mode: str):
    """Set rename mode for user"""
    try:
        if mode not in RENAME_MODES:
            await update.callback_query.edit_message_text("❌ Invalid rename mode.")
            return
        
        # Update user settings
        await db.update_user_settings(user_id, {"rename_mode": mode})
        
        mode_info = RENAME_MODES[mode]
        
        success_text = f"✅ **Mode Changed Successfully**\n\n"
        success_text += f"**New Mode:** {mode_info['icon']} {mode_info['name']}\n"
        success_text += f"**Description:** {mode_info['description']}\n\n"
        
        success_text += "**Features:**\n"
        for feature in mode_info['features']:
            success_text += f"• {feature}\n"
        
        success_text += "\n**What's next?**\n"
        if mode == 'auto':
            success_text += "Configure your rename template in settings"
        elif mode == 'manual':
            success_text += "Send a file and I'll ask for the new name"
        elif mode == 'replace':
            success_text += "Set up your text replacement rules"
        
        keyboard = [
            [InlineKeyboardButton("⚙️ Configure", callback_data=f"mode_configure_{mode}")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                success_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                success_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        logger.info(f"User {user_id} set rename mode to {mode}")
        
    except Exception as e:
        logger.error(f"Error setting rename mode: {e}")
        await update.callback_query.edit_message_text("❌ Error updating rename mode.")

async def show_mode_details(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show detailed information about all modes"""
    try:
        details_text = "ℹ️ **Rename Mode Details**\n\n"
        details_text += "Learn about each rename mode:\n\n"
        
        keyboard = []
        for mode_key, mode_info in RENAME_MODES.items():
            details_text += f"**{mode_info['icon']} {mode_info['name']}**\n"
            details_text += f"{mode_info['description']}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📖 {mode_info['name']} Details", 
                    callback_data=f"mode_detail_{mode_key}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Modes", callback_data="mode_main")
        ])
        
        await update.callback_query.edit_message_text(
            details_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing mode details: {e}")
        await update.callback_query.edit_message_text("❌ Error loading mode details.")

async def show_specific_mode_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, mode: str):
    """Show detailed information about a specific mode"""
    try:
        if mode not in RENAME_MODES:
            await update.callback_query.edit_message_text("❌ Invalid mode.")
            return
        
        mode_info = RENAME_MODES[mode]
        
        detail_text = f"📖 **{mode_info['icon']} {mode_info['name']} - Detailed Guide**\n\n"
        detail_text += f"**Description:** {mode_info['description']}\n\n"
        
        detail_text += "**Features:**\n"
        for feature in mode_info['features']:
            detail_text += f"• {feature}\n"
        detail_text += "\n"
        
        # Mode-specific details
        if mode == 'auto':
            detail_text += "**How it works:**\n"
            detail_text += "1. Set up a rename template with variables\n"
            detail_text += "2. Upload files and they're renamed automatically\n"
            detail_text += "3. Variables are extracted from filename\n\n"
            
            detail_text += "**Example Template:** `{title} - {season}{episode}`\n"
            detail_text += "**Result:** `Game.of.Thrones.S01E01.mkv` → `Game of Thrones - S01E01.mkv`\n\n"
            
            detail_text += "**Best for:** Batch processing, consistent naming\n"
            
        elif mode == 'manual':
            detail_text += "**How it works:**\n"
            detail_text += "1. Upload a file\n"
            detail_text += "2. Bot asks for new filename\n"
            detail_text += "3. Type the new name\n"
            detail_text += "4. File is renamed and sent back\n\n"
            
            detail_text += "**Best for:** Custom names, one-off renames\n"
            
        elif mode == 'replace':
            detail_text += "**How it works:**\n"
            detail_text += "1. Set up text replacement rules\n"
            detail_text += "2. Upload files\n"
            detail_text += "3. Rules are applied automatically\n\n"
            
            detail_text += "**Example Rule:** Replace `.` with ` `\n"
            detail_text += "**Result:** `Movie.Name.2024.mkv` → `Movie Name 2024.mkv`\n\n"
            
            detail_text += "**Best for:** Pattern-based cleaning, bulk fixes\n"
        
        keyboard = [
            [InlineKeyboardButton(f"🎯 Use {mode_info['name']}", callback_data=f"mode_set_{mode}")],
            [InlineKeyboardButton("🔙 Back to Details", callback_data="mode_details")]
        ]
        
        await update.callback_query.edit_message_text(
            detail_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing specific mode detail: {e}")
        await update.callback_query.edit_message_text("❌ Error loading mode details.")

async def show_mode_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show preview of how different modes work"""
    try:
        preview_text = "🔄 **Mode Preview**\n\n"
        preview_text += "Here's how each mode would handle the same file:\n\n"
        
        sample_file = "Game.of.Thrones.S01E01.1080p.BluRay.x264-GROUP.mkv"
        preview_text += f"**Sample File:** `{sample_file}`\n\n"
        
        # Auto mode preview
        preview_text += "**⚡ Auto Mode:**\n"
        preview_text += f"Template: `{{title}} - {{season}}{{episode}}`\n"
        preview_text += f"Result: `Game of Thrones - S01E01.mkv`\n\n"
        
        # Manual mode preview
        preview_text += "**✏️ Manual Mode:**\n"
        preview_text += f"Bot asks: \"What should I rename this file to?\"\n"
        preview_text += f"You type: `Game of Thrones Episode 1`\n"
        preview_text += f"Result: `Game of Thrones Episode 1.mkv`\n\n"
        
        # Replace mode preview
        preview_text += "**🔄 Replace Mode:**\n"
        preview_text += f"Rules: Replace `.` with ` `, Remove `-GROUP`\n"
        preview_text += f"Result: `Game of Thrones S01E01 1080p BluRay x264.mkv`\n\n"
        
        preview_text += "**💡 Tip:** You can switch between modes anytime using /mode"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Choose Mode", callback_data="mode_main")],
            [InlineKeyboardButton("🔙 Back", callback_data="mode_main")]
        ]
        
        await update.callback_query.edit_message_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing mode preview: {e}")
        await update.callback_query.edit_message_text("❌ Error generating preview.")

def get_user_rename_mode(user_settings) -> str:
    """Get user's current rename mode"""
    return getattr(user_settings, 'rename_mode', 'auto')

def is_auto_mode(user_settings) -> bool:
    """Check if user is in auto rename mode"""
    return get_user_rename_mode(user_settings) == 'auto'

def is_manual_mode(user_settings) -> bool:
    """Check if user is in manual rename mode"""
    return get_user_rename_mode(user_settings) == 'manual'

def is_replace_mode(user_settings) -> bool:
    """Check if user is in replace mode"""
    return get_user_rename_mode(user_settings) == 'replace'