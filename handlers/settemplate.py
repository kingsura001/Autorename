"""
Set template command handler
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from utils.template_parser import TemplateParser
from middleware.auth import require_auth
from middleware.subscription_check import subscription_required

logger = logging.getLogger(__name__)

# Predefined templates
TEMPLATE_PRESETS = {
    'basic': {
        'name': 'Basic',
        'template': '{title}',
        'description': 'Just the title',
        'example': 'Movie Name'
    },
    'series': {
        'name': 'TV Series',
        'template': '{title} - {season}{episode}',
        'description': 'Title with season and episode',
        'example': 'Game of Thrones - S01E01'
    },
    'movie': {
        'name': 'Movie',
        'template': '{title} ({year}) [{quality}]',
        'description': 'Title with year and quality',
        'example': 'Inception (2010) [1080p]'
    },
    'detailed': {
        'name': 'Detailed',
        'template': '{title} - {season}{episode} - {quality}',
        'description': 'Full details with quality',
        'example': 'Breaking Bad - S05E14 - 720p'
    },
    'minimal': {
        'name': 'Minimal',
        'template': '{title}.{extension}',
        'description': 'Clean title with extension',
        'example': 'Document Name.pdf'
    },
    'audio': {
        'name': 'Audio',
        'template': '{artist} - {title}',
        'description': 'Artist and title for music',
        'example': 'Artist Name - Song Title'
    },
    'date': {
        'name': 'With Date',
        'template': '{title} - {year}',
        'description': 'Title with year',
        'example': 'Document Name - 2024'
    },
    'quality': {
        'name': 'Quality Focus',
        'template': '{title} [{quality}] [{codec}]',
        'description': 'Focus on quality and codec',
        'example': 'Movie Name [1080p] [x264]'
    }
}

@require_auth
@subscription_required
async def settemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settemplate command"""
    user_id = update.effective_user.id
    
    try:
        if context.args:
            # Direct template setting: /settemplate {title} - {season}{episode}
            template = ' '.join(context.args)
            await set_custom_template(update, context, user_id, template)
        else:
            # Show template selection menu
            await show_template_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in settemplate command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while setting template."
        )

async def show_template_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show template selection menu"""
    try:
        settings = await db.get_user_settings(user_id)
        current_template = getattr(settings, 'rename_template', '{title}')
        
        message_text = "📝 **Set Rename Template**\n\n"
        message_text += "Choose a template for automatic file renaming:\n\n"
        
        message_text += f"**Current Template:** `{current_template}`\n"
        
        # Show preview with current template
        sample_file = "Game.of.Thrones.S01E01.1080p.BluRay.x264-GROUP.mkv"
        try:
            parser = TemplateParser(current_template)
            preview = parser.parse(sample_file)
            message_text += f"**Preview:** `{preview}`\n\n"
        except:
            message_text += f"**Preview:** Error parsing template\n\n"
        
        message_text += "**Available Templates:**\n"
        
        keyboard = []
        for preset_key, preset_info in TEMPLATE_PRESETS.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 {preset_info['name']}", 
                    callback_data=f"template_preset_{preset_key}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("✏️ Custom Template", callback_data="template_custom"),
            InlineKeyboardButton("🔄 Test Template", callback_data="template_test")
        ])
        keyboard.append([
            InlineKeyboardButton("📚 Variables Help", callback_data="template_variables"),
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
        logger.error(f"Error showing template menu: {e}")
        await update.message.reply_text("❌ Error loading template menu.")

async def template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle template callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data.startswith("template_preset_"):
            preset = data.replace("template_preset_", "")
            await set_preset_template(update, context, user_id, preset)
        elif data == "template_custom":
            await show_custom_template_input(update, context, user_id)
        elif data == "template_test":
            await show_template_test(update, context, user_id)
        elif data == "template_variables":
            await show_template_variables(update, context, user_id)
        elif data.startswith("template_confirm_"):
            preset = data.replace("template_confirm_", "")
            await confirm_preset_template(update, context, user_id, preset)
            
    except Exception as e:
        logger.error(f"Error handling template callback: {e}")
        await query.edit_message_text("❌ Error processing template settings.")

async def set_preset_template(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, preset: str):
    """Set a preset template"""
    try:
        if preset not in TEMPLATE_PRESETS:
            await update.callback_query.edit_message_text("❌ Invalid template preset.")
            return
        
        preset_info = TEMPLATE_PRESETS[preset]
        template = preset_info['template']
        
        # Show confirmation with preview
        confirm_text = f"📋 **{preset_info['name']} Template**\n\n"
        confirm_text += f"**Template:** `{template}`\n"
        confirm_text += f"**Description:** {preset_info['description']}\n"
        confirm_text += f"**Example:** `{preset_info['example']}`\n\n"
        
        # Show preview with sample files
        sample_files = [
            "Game.of.Thrones.S01E01.1080p.BluRay.x264-GROUP.mkv",
            "The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mkv",
            "Document.Name.2024.pdf"
        ]
        
        confirm_text += "**Preview with sample files:**\n"
        parser = TemplateParser(template)
        for sample in sample_files:
            try:
                preview = parser.parse(sample)
                confirm_text += f"• `{sample}`\n"
                confirm_text += f"  → `{preview}`\n\n"
            except Exception as e:
                confirm_text += f"• `{sample}`\n"
                confirm_text += f"  → Error: {str(e)}\n\n"
        
        confirm_text += "**Apply this template?**"
        
        keyboard = [
            [InlineKeyboardButton("✅ Apply Template", callback_data=f"template_confirm_{preset}")],
            [InlineKeyboardButton("🔙 Back to Templates", callback_data="template_main")]
        ]
        
        await update.callback_query.edit_message_text(
            confirm_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error setting preset template: {e}")
        await update.callback_query.edit_message_text("❌ Error setting preset template.")

async def confirm_preset_template(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, preset: str):
    """Confirm and apply preset template"""
    try:
        if preset not in TEMPLATE_PRESETS:
            await update.callback_query.edit_message_text("❌ Invalid template preset.")
            return
        
        preset_info = TEMPLATE_PRESETS[preset]
        template = preset_info['template']
        
        # Update user settings
        await db.update_user_settings(user_id, {"rename_template": template})
        
        success_text = f"✅ **Template Applied Successfully**\n\n"
        success_text += f"**Template:** `{template}`\n"
        success_text += f"**Type:** {preset_info['name']}\n"
        success_text += f"**Description:** {preset_info['description']}\n\n"
        success_text += "This template will be used for all future automatic renames.\n\n"
        success_text += "**Next steps:**\n"
        success_text += "• Upload files to test the template\n"
        success_text += "• Use /preview to see more examples\n"
        success_text += "• Enable auto-rename with /autorename"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Preview", callback_data="template_test")],
            [InlineKeyboardButton("⚡ Enable Auto-Rename", callback_data="autorename_enable")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        await update.callback_query.edit_message_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} set template to: {template}")
        
    except Exception as e:
        logger.error(f"Error confirming preset template: {e}")
        await update.callback_query.edit_message_text("❌ Error applying template.")

async def show_custom_template_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show custom template input interface"""
    try:
        custom_text = "✏️ **Custom Template Input**\n\n"
        custom_text += "Create your own rename template using variables:\n\n"
        
        custom_text += "**Available Variables:**\n"
        custom_text += "• `{title}` - Original filename without extension\n"
        custom_text += "• `{season}` - Season number (S01, S02, etc.)\n"
        custom_text += "• `{episode}` - Episode number (E01, E02, etc.)\n"
        custom_text += "• `{year}` - Year (2024, 2025, etc.)\n"
        custom_text += "• `{quality}` - Quality (1080p, 720p, etc.)\n"
        custom_text += "• `{codec}` - Video codec (x264, x265, etc.)\n"
        custom_text += "• `{source}` - Source (BluRay, WEB-DL, etc.)\n"
        custom_text += "• `{group}` - Release group name\n"
        custom_text += "• `{extension}` - File extension\n\n"
        
        custom_text += "**Example Templates:**\n"
        custom_text += "• `{title} - {season}{episode}`\n"
        custom_text += "• `{title} ({year}) [{quality}]`\n"
        custom_text += "• `{title} - {season}{episode} - {quality}`\n"
        custom_text += "• `[{group}] {title} - {season}{episode}`\n"
        custom_text += "• `{title}.{year}.{quality}.{codec}`\n\n"
        
        custom_text += "**Send your custom template now:**"
        
        keyboard = [
            [InlineKeyboardButton("📚 More Variables", callback_data="template_variables")],
            [InlineKeyboardButton("🔙 Back", callback_data="template_main")]
        ]
        
        await update.callback_query.edit_message_text(
            custom_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Set state for text input
        context.user_data['waiting_for_custom_template'] = True
        
    except Exception as e:
        logger.error(f"Error showing custom template input: {e}")
        await update.callback_query.edit_message_text("❌ Error loading custom template input.")

async def show_template_test(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show template testing interface"""
    try:
        settings = await db.get_user_settings(user_id)
        current_template = getattr(settings, 'rename_template', '{title}')
        
        test_text = "🔄 **Template Testing**\n\n"
        test_text += f"**Current Template:** `{current_template}`\n\n"
        test_text += "**Test Results:**\n"
        
        # Test with various sample files
        test_files = [
            "Game.of.Thrones.S01E01.1080p.BluRay.x264-GROUP.mkv",
            "The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mkv",
            "Breaking.Bad.S05E14.720p.HDTV.x264-IMMERSE.mp4",
            "Document.Name.2024.pdf",
            "Artist.Name.Song.Title.320kbps.mp3"
        ]
        
        parser = TemplateParser(current_template)
        for test_file in test_files:
            try:
                result = parser.parse(test_file)
                test_text += f"• `{test_file}`\n"
                test_text += f"  → `{result}`\n\n"
            except Exception as e:
                test_text += f"• `{test_file}`\n"
                test_text += f"  → ❌ Error: {str(e)}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Test Custom File", callback_data="template_test_custom")],
            [InlineKeyboardButton("📝 Edit Template", callback_data="template_custom")],
            [InlineKeyboardButton("🔙 Back", callback_data="template_main")]
        ]
        
        await update.callback_query.edit_message_text(
            test_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing template test: {e}")
        await update.callback_query.edit_message_text("❌ Error loading template test.")

async def show_template_variables(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show detailed template variables help"""
    try:
        variables_text = "📚 **Template Variables Reference**\n\n"
        variables_text += "Complete list of available variables:\n\n"
        
        variables_text += "**📁 Basic Variables:**\n"
        variables_text += "• `{title}` - Original filename without extension\n"
        variables_text += "• `{extension}` - File extension (.mkv, .mp4, etc.)\n"
        variables_text += "• `{filename}` - Full original filename\n\n"
        
        variables_text += "**📺 TV Show Variables:**\n"
        variables_text += "• `{season}` - Season number (S01, S02, etc.)\n"
        variables_text += "• `{episode}` - Episode number (E01, E02, etc.)\n"
        variables_text += "• `{series}` - Series name\n\n"
        
        variables_text += "**🎬 Movie Variables:**\n"
        variables_text += "• `{year}` - Release year (2024, 2025, etc.)\n"
        variables_text += "• `{movie}` - Movie title\n\n"
        
        variables_text += "**🎥 Quality Variables:**\n"
        variables_text += "• `{quality}` - Video quality (1080p, 720p, etc.)\n"
        variables_text += "• `{resolution}` - Resolution (1920x1080, etc.)\n"
        variables_text += "• `{codec}` - Video codec (x264, x265, etc.)\n"
        variables_text += "• `{source}` - Source (BluRay, WEB-DL, HDTV, etc.)\n\n"
        
        variables_text += "**🏷️ Metadata Variables:**\n"
        variables_text += "• `{group}` - Release group name\n"
        variables_text += "• `{language}` - Language code\n"
        variables_text += "• `{audio}` - Audio codec/info\n\n"
        
        variables_text += "**📅 Date Variables:**\n"
        variables_text += "• `{date}` - Current date (YYYY-MM-DD)\n"
        variables_text += "• `{time}` - Current time (HH:MM)\n"
        variables_text += "• `{timestamp}` - Unix timestamp\n\n"
        
        variables_text += "**💡 Tips:**\n"
        variables_text += "• Use `-` or `_` as separators\n"
        variables_text += "• Variables are case-sensitive\n"
        variables_text += "• Unknown variables are left as-is\n"
        variables_text += "• Test your template before applying\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 Try Custom Template", callback_data="template_custom")],
            [InlineKeyboardButton("🔄 Test Template", callback_data="template_test")],
            [InlineKeyboardButton("🔙 Back", callback_data="template_main")]
        ]
        
        await update.callback_query.edit_message_text(
            variables_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing template variables: {e}")
        await update.callback_query.edit_message_text("❌ Error loading variables help.")

async def set_custom_template(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, template: str):
    """Set a custom template"""
    try:
        # Validate template
        if not template.strip():
            await update.message.reply_text("❌ Template cannot be empty.")
            return
        
        # Test template with sample file
        test_file = "Sample.File.S01E01.1080p.BluRay.x264-GROUP.mkv"
        try:
            parser = TemplateParser(template)
            preview = parser.parse(test_file)
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Template Error**\n\n"
                f"Template: `{template}`\n"
                f"Error: {str(e)}\n\n"
                f"Please check your template syntax and try again."
            )
            return
        
        # Update user settings
        await db.update_user_settings(user_id, {"rename_template": template})
        
        success_text = f"✅ **Custom Template Set**\n\n"
        success_text += f"**Template:** `{template}`\n"
        success_text += f"**Preview:** `{preview}`\n\n"
        success_text += "Your custom template has been applied successfully!\n\n"
        success_text += "**Next steps:**\n"
        success_text += "• Upload files to test the template\n"
        success_text += "• Use /preview to see more examples\n"
        success_text += "• Enable auto-rename with /autorename"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Preview", callback_data="template_test")],
            [InlineKeyboardButton("⚡ Enable Auto-Rename", callback_data="autorename_enable")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        await update.message.reply_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} set custom template: {template}")
        
    except Exception as e:
        logger.error(f"Error setting custom template: {e}")
        await update.message.reply_text("❌ Error setting custom template.")

async def handle_custom_template_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom template input from user"""
    try:
        if not context.user_data.get('waiting_for_custom_template'):
            return
        
        user_id = update.effective_user.id
        template = update.message.text.strip()
        
        # Clear waiting state
        context.user_data['waiting_for_custom_template'] = False
        
        await set_custom_template(update, context, user_id, template)
        
    except Exception as e:
        logger.error(f"Error handling custom template input: {e}")
        await update.message.reply_text("❌ Error processing custom template.")

def get_user_template(user_settings) -> str:
    """Get user's current template"""
    return getattr(user_settings, 'rename_template', '{title}')

def validate_template(template: str) -> tuple[bool, str]:
    """Validate template syntax"""
    try:
        if not template.strip():
            return False, "Template cannot be empty"
        
        # Test with sample file
        parser = TemplateParser(template)
        parser.parse("Sample.File.S01E01.1080p.BluRay.x264-GROUP.mkv")
        
        return True, "Template is valid"
        
    except Exception as e:
        return False, str(e)