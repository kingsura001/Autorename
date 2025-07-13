"""
Auto-rename functionality handler
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from utils.template_parser import TemplateParser
from middleware.subscription_check import check_force_subscription

logger = logging.getLogger(__name__)

async def autorename_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autorename command"""
    user_id = update.effective_user.id
    
    try:
        # Check force subscription
        if not await check_force_subscription(user_id, context):
            keyboard = [[InlineKeyboardButton("🔄 Check Subscription", callback_data="sub_check")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🚫 **Access Restricted**\n\n"
                "Please join our required channels to use auto-rename features.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return
        
        await show_autorename_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error in autorename command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading auto-rename features."
        )

async def show_autorename_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show auto-rename menu"""
    try:
        user_id = update.effective_user.id
        
        # Get user settings
        settings = await db.get_user_settings(user_id)
        if not settings:
            from database.models import UserSettings
            settings = UserSettings(user_id=user_id)
            await db.create_user_settings(settings)
        
        # Get user info for premium status
        user = await db.get_user(user_id)
        is_premium = user.is_premium_active() if user else False
        
        status_text = "✅ Enabled" if settings.auto_rename else "❌ Disabled"
        
        autorename_text = f"""
⚡ **Auto-Rename Feature**

**Current Status:** {status_text}
**Template:** `{settings.rename_template}`
**Premium Status:** {'✅ Active' if is_premium else '❌ Inactive'}

🔧 **How It Works:**
When auto-rename is enabled, files are automatically renamed using your template without prompting you each time.

📋 **Current Template Variables:**
• `{{title}}` - Original filename
• `{{season}}` - Season number (S01, S02, etc.)
• `{{episode}}` - Episode number (E01, E02, etc.)
• `{{year}}` - Year (2024, 2025, etc.)
• `{{quality}}` - Quality (1080p, 720p, etc.)

💡 **Template Examples:**
• `{{title}} - {{season}}{{episode}}`
• `{{title}} ({{year}}) [{{quality}}]`
• `Movie - {{title}} - {{year}}`

{'🌟 **Premium Features:**' if is_premium else '⭐ **Premium Features (Upgrade Required):**'}
• Advanced template variables
• Batch processing
• Custom naming patterns
• Priority processing queue
        """
        
        keyboard = []
        
        if settings.auto_rename:
            keyboard.append([InlineKeyboardButton("❌ Disable Auto-Rename", callback_data="autorename_disable")])
        else:
            keyboard.append([InlineKeyboardButton("✅ Enable Auto-Rename", callback_data="autorename_enable")])
        
        keyboard.extend([
            [InlineKeyboardButton("📝 Edit Template", callback_data="autorename_template")],
            [InlineKeyboardButton("🧪 Test Template", callback_data="autorename_test")],
            [InlineKeyboardButton("📊 Usage Statistics", callback_data="autorename_stats")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
        ])
        
        if not is_premium:
            keyboard.insert(-2, [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="sub_premium")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                autorename_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                autorename_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing autorename menu: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading auto-rename menu."
        )

async def autorename_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle autorename callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data.replace("autorename_", "")
    
    try:
        if action == "main":
            await show_autorename_menu(update, context)
        
        elif action == "enable":
            await toggle_autorename(update, context, user_id, True)
        
        elif action == "disable":
            await toggle_autorename(update, context, user_id, False)
        
        elif action == "template":
            await show_template_editor(update, context, user_id)
        
        elif action == "test":
            await show_template_tester(update, context, user_id)
        
        elif action == "stats":
            await show_autorename_stats(update, context, user_id)
        
        elif action.startswith("template_"):
            await handle_template_action(update, context, action, user_id)
        
        elif action.startswith("test_"):
            await handle_test_action(update, context, action, user_id)
            
    except Exception as e:
        logger.error(f"Error in autorename callback: {e}")
        await query.edit_message_text(
            "❌ An error occurred while processing your request."
        )

async def toggle_autorename(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, enable: bool):
    """Toggle auto-rename feature"""
    try:
        # Update user settings
        success = await db.update_user_settings(user_id, {"auto_rename": enable})
        
        if success:
            status = "enabled" if enable else "disabled"
            
            message_text = f"""
{'✅' if enable else '❌'} **Auto-Rename {status.title()}**

Auto-rename has been {status} successfully.

{f'''🔧 **Next Steps:**
• Upload files to see auto-rename in action
• Files will be renamed using your template: 
• Use /settings to modify your template
• Premium users get advanced features''' if enable else '''💡 **Manual Mode:**
• You'll be prompted to rename each file
• More control over individual files
• Can still use templates when needed'''}
            """
            
            keyboard = [
                [InlineKeyboardButton("📝 Edit Template", callback_data="autorename_template")],
                [InlineKeyboardButton("⬅️ Back to Auto-Rename", callback_data="autorename_main")]
            ]
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.callback_query.edit_message_text(
                "❌ Failed to update auto-rename setting. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Error toggling autorename: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while updating your settings."
        )

async def show_template_editor(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show template editor"""
    try:
        # Get current settings
        settings = await db.get_user_settings(user_id)
        current_template = settings.rename_template if settings else "{title}"
        
        template_text = f"""
📝 **Edit Rename Template**

**Current Template:** `{current_template}`

🔤 **Available Variables:**
• `{{title}}` - Original filename (without extension)
• `{{season}}` - Season number (S01, S02, etc.)
• `{{episode}}` - Episode number (E01, E02, etc.)
• `{{year}}` - Year (2024, 2025, etc.)
• `{{quality}}` - Quality (1080p, 720p, etc.)

📋 **Quick Templates:**
Choose a template below or send a custom one:
        """
        
        keyboard = [
            [InlineKeyboardButton("📄 Basic: {title}", callback_data="autorename_template_basic")],
            [InlineKeyboardButton("📺 Series: {title} - {season}{episode}", callback_data="autorename_template_series")],
            [InlineKeyboardButton("🎬 Movie: {title} ({year}) [{quality}]", callback_data="autorename_template_movie")],
            [InlineKeyboardButton("🎯 Detailed: {title} - {season}{episode} - {quality}", callback_data="autorename_template_detailed")],
            [InlineKeyboardButton("✏️ Custom Template", callback_data="autorename_template_custom")],
            [InlineKeyboardButton("🧪 Test Current", callback_data="autorename_test")],
            [InlineKeyboardButton("⬅️ Back", callback_data="autorename_main")]
        ]
        
        await update.callback_query.edit_message_text(
            template_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing template editor: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading template editor."
        )

async def show_template_tester(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show template testing interface"""
    try:
        # Get current settings
        settings = await db.get_user_settings(user_id)
        current_template = settings.rename_template if settings else "{title}"
        
        # Test the template with sample data
        template_parser = TemplateParser(current_template)
        
        test_cases = [
            "Game.of.Thrones.S01E01.1080p.BluRay.x264-GROUP.mkv",
            "The.Matrix.1999.1080p.BluRay.x264-YIFY.mp4",
            "Breaking.Bad.S05E14.720p.HDTV.x264-EVOLVE.avi",
            "Avengers.Endgame.2019.2160p.UHD.BluRay.x265-TERMINAL.mkv",
            "simple_document.pdf"
        ]
        
        test_text = f"""
🧪 **Template Tester**

**Current Template:** `{current_template}`

**Test Results:**
        """
        
        for i, test_file in enumerate(test_cases, 1):
            try:
                result = template_parser.parse(test_file)
                test_text += f"{i}. `{test_file}`\n"
                test_text += f"   → `{result}`\n\n"
            except Exception as e:
                test_text += f"{i}. `{test_file}`\n"
                test_text += f"   → ❌ Error: {str(e)}\n\n"
        
        test_text += """
💡 **Tips:**
• Check if results match your expectations
• Modify template if needed
• Test with your actual filenames
        """
        
        keyboard = [
            [InlineKeyboardButton("📝 Edit Template", callback_data="autorename_template")],
            [InlineKeyboardButton("🔄 Run Test Again", callback_data="autorename_test")],
            [InlineKeyboardButton("⬅️ Back", callback_data="autorename_main")]
        ]
        
        await update.callback_query.edit_message_text(
            test_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing template tester: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while testing the template."
        )

async def show_autorename_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show auto-rename usage statistics"""
    try:
        # Get user's file records
        file_records = await db.get_user_file_records(user_id, limit=100)
        
        # Calculate stats
        total_files = len(file_records)
        auto_renamed = len([r for r in file_records if r.renamed_name and r.renamed_name != r.original_name])
        success_rate = (auto_renamed / total_files * 100) if total_files > 0 else 0
        
        # Get recent activity
        from datetime import datetime, timedelta
        recent_files = [r for r in file_records if (datetime.now() - r.created_at).days <= 7]
        
        stats_text = f"""
📊 **Auto-Rename Statistics**

📈 **Overall Performance:**
• Total Files Processed: {total_files:,}
• Auto-Renamed Files: {auto_renamed:,}
• Success Rate: {success_rate:.1f}%
• Manual Renames: {total_files - auto_renamed:,}

⏰ **Recent Activity (7 days):**
• Files Processed: {len(recent_files):,}
• Auto-Renamed: {len([r for r in recent_files if r.renamed_name and r.renamed_name != r.original_name]):,}

🎯 **File Type Breakdown:**
• Documents: {len([r for r in file_records if r.file_type == 'document']):,}
• Videos: {len([r for r in file_records if r.file_type == 'video']):,}
• Audio: {len([r for r in file_records if r.file_type == 'audio']):,}

💡 **Tips for Better Results:**
• Use descriptive templates
• Test templates before enabling
• Check results regularly
• Update templates as needed
        """
        
        keyboard = [
            [InlineKeyboardButton("📝 Optimize Template", callback_data="autorename_template")],
            [InlineKeyboardButton("🧪 Test Template", callback_data="autorename_test")],
            [InlineKeyboardButton("⬅️ Back", callback_data="autorename_main")]
        ]
        
        await update.callback_query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing autorename stats: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading statistics."
        )

async def handle_template_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, user_id: int):
    """Handle template-related actions"""
    try:
        template_type = action.replace("template_", "")
        
        templates = {
            "basic": "{title}",
            "series": "{title} - {season}{episode}",
            "movie": "{title} ({year}) [{quality}]",
            "detailed": "{title} - {season}{episode} - {quality}"
        }
        
        if template_type == "custom":
            # Set up custom template input
            context.user_data['awaiting_custom_template'] = True
            
            await update.callback_query.edit_message_text(
                "✏️ **Custom Template**\n\n"
                "Send your custom rename template.\n\n"
                "🔤 **Available Variables:**\n"
                "• `{title}` - Original filename\n"
                "• `{season}` - Season (S01, S02, etc.)\n"
                "• `{episode}` - Episode (E01, E02, etc.)\n"
                "• `{year}` - Year (2024, 2025, etc.)\n"
                "• `{quality}` - Quality (1080p, 720p, etc.)\n\n"
                "📝 **Example:** `{title} - {season}{episode} [{quality}]`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Cancel", callback_data="autorename_template")
                ]])
            )
            return
        
        if template_type in templates:
            # Update template
            success = await db.update_user_settings(user_id, {
                "rename_template": templates[template_type]
            })
            
            if success:
                await update.callback_query.edit_message_text(
                    f"✅ **Template Updated**\n\n"
                    f"**New Template:** `{templates[template_type]}`\n\n"
                    f"This template will be used for auto-renaming your files.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🧪 Test Template", callback_data="autorename_test")],
                        [InlineKeyboardButton("⬅️ Back", callback_data="autorename_main")]
                    ])
                )
            else:
                await update.callback_query.edit_message_text(
                    "❌ Failed to update template. Please try again."
                )
                
    except Exception as e:
        logger.error(f"Error handling template action: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while updating the template."
        )

async def handle_test_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, user_id: int):
    """Handle test-related actions"""
    try:
        # This could be extended for more test actions
        await show_template_tester(update, context, user_id)
        
    except Exception as e:
        logger.error(f"Error handling test action: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while running the test."
        )

async def handle_custom_template_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom template input from user"""
    user_id = update.effective_user.id
    
    try:
        if not context.user_data.get('awaiting_custom_template'):
            return
        
        custom_template = update.message.text.strip()
        
        # Basic validation
        if not custom_template:
            await update.message.reply_text("❌ Please provide a valid template.")
            return
        
        if len(custom_template) > 100:
            await update.message.reply_text("❌ Template too long. Maximum 100 characters.")
            return
        
        # Test the template
        try:
            template_parser = TemplateParser(custom_template)
            test_result = template_parser.parse("Test.File.S01E01.1080p.mkv")
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Template Error**\n\n"
                f"Error: {str(e)}\n\n"
                f"Please check your template syntax and try again."
            )
            return
        
        # Update template
        success = await db.update_user_settings(user_id, {
            "rename_template": custom_template
        })
        
        if success:
            await update.message.reply_text(
                f"✅ **Custom Template Saved**\n\n"
                f"**Template:** `{custom_template}`\n"
                f"**Test Result:** `{test_result}`\n\n"
                f"Your custom template has been saved and will be used for auto-renaming."
            )
        else:
            await update.message.reply_text(
                "❌ Failed to save custom template. Please try again."
            )
        
        # Clear context
        context.user_data.pop('awaiting_custom_template', None)
        
    except Exception as e:
        logger.error(f"Error handling custom template input: {e}")
        await update.message.reply_text(
            "❌ An error occurred while saving your custom template."
        )
