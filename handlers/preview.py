
"""
Preview functionality for file renaming
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from utils.template_parser import TemplateParser
from utils.helpers import extract_file_info
from handlers.replace import get_user_replace_rules, apply_replace_rules
from handlers.mode import get_user_rename_mode
from middleware.auth import require_auth
from middleware.subscription_check import subscription_required

logger = logging.getLogger(__name__)

@require_auth
@subscription_required
async def preview_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /preview command"""
    user_id = update.effective_user.id
    
    try:
        await show_preview_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in preview command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading preview."
        )

async def show_preview_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show rename preview menu"""
    try:
        settings = await db.get_user_settings(user_id)
        rename_mode = get_user_rename_mode(settings)
        
        message_text = "🔍 **Rename Preview**\n\n"
        message_text += "See how your current settings will rename files:\n\n"
        
        message_text += f"**Current Mode:** {rename_mode.title()}\n"
        
        if rename_mode == 'auto':
            template = getattr(settings, 'rename_template', '{title}')
            message_text += f"**Template:** `{template}`\n"
        elif rename_mode == 'replace':
            replace_rules = get_user_replace_rules(settings)
            rule_count = len(replace_rules)
            message_text += f"**Replace Rules:** {rule_count} active\n"
        
        message_text += "\n**Options:**\n"
        message_text += "• Preview with sample files\n"
        message_text += "• Test with custom filename\n"
        message_text += "• Batch preview multiple files\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 Sample Files", callback_data="preview_samples")],
            [InlineKeyboardButton("✏️ Custom Test", callback_data="preview_custom")],
            [InlineKeyboardButton("📊 Batch Preview", callback_data="preview_batch")],
            [InlineKeyboardButton("🔄 Live Preview", callback_data="preview_live")],
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
        logger.error(f"Error showing preview menu: {e}")
        await update.message.reply_text("❌ Error loading preview.")

async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle preview callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data == "preview_samples":
            await show_sample_preview(update, context, user_id)
        elif data == "preview_custom":
            await show_custom_preview(update, context, user_id)
        elif data == "preview_batch":
            await show_batch_preview(update, context, user_id)
        elif data == "preview_live":
            await show_live_preview(update, context, user_id)
        elif data.startswith("preview_category_"):
            category = data.split("_")[2]
            await show_category_preview(update, context, user_id, category)
            
    except Exception as e:
        logger.error(f"Error handling preview callback: {e}")
        await query.edit_message_text("❌ Error processing preview.")

async def show_sample_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show preview with sample files"""
    try:
        settings = await db.get_user_settings(user_id)
        
        preview_text = "📝 **Sample Files Preview**\n\n"
        preview_text += "Here's how your settings will rename different types of files:\n\n"
        
        # Sample files for different categories
        sample_files = {
            "TV Shows": [
                "Game.of.Thrones.S01E01.1080p.BluRay.x264-GROUP.mkv",
                "Breaking.Bad.S05E14.720p.HDTV.x264-IMMERSE.mp4",
                "The.Office.US.S02E10.WEB-DL.1080p.H264.mp4"
            ],
            "Movies": [
                "The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mkv",
                "Inception.2010.720p.BRRip.x264-YIFY.mp4",
                "Avengers.Endgame.2019.4K.UHD.BluRay.x265-TERMINAL.mkv"
            ],
            "Documents": [
                "Important.Document.2024.pdf",
                "Meeting.Notes.Jan.15.2024.docx",
                "Project.Report.Final.Version.pdf"
            ],
            "Audio": [
                "Artist.Name.Song.Title.320kbps.mp3",
                "Album.Name.Track.01.Artist.Name.flac",
                "Podcast.Episode.123.Audio.Quality.mp3"
            ]
        }
        
        for category, files in sample_files.items():
            preview_text += f"**{category}:**\n"
            for original in files[:2]:  # Show first 2 files
                renamed = await preview_rename(original, settings)
                preview_text += f"• `{original}`\n"
                preview_text += f"  → `{renamed}`\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📺 TV Shows", callback_data="preview_category_tv")],
            [InlineKeyboardButton("🎬 Movies", callback_data="preview_category_movies")],
            [InlineKeyboardButton("📄 Documents", callback_data="preview_category_docs")],
            [InlineKeyboardButton("🎵 Audio", callback_data="preview_category_audio")],
            [InlineKeyboardButton("🔙 Back", callback_data="preview_main")]
        ]
        
        await update.callback_query.edit_message_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing sample preview: {e}")
        await update.callback_query.edit_message_text("❌ Error generating sample preview.")

async def show_custom_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show custom filename preview interface"""
    try:
        custom_text = "✏️ **Custom Filename Test**\n\n"
        custom_text += "Test your rename settings with a custom filename:\n\n"
        custom_text += "**Instructions:**\n"
        custom_text += "1. Send any filename you want to test\n"
        custom_text += "2. I'll show you how it would be renamed\n"
        custom_text += "3. You can test multiple files\n\n"
        custom_text += "**Examples to try:**\n"
        custom_text += "• `Movie.Name.2024.1080p.BluRay.mkv`\n"
        custom_text += "• `TV.Show.S01E01.720p.HDTV.mp4`\n"
        custom_text += "• `Document.Name.With.Dots.pdf`\n"
        custom_text += "• `Audio.Track.Artist.Name.mp3`\n\n"
        custom_text += "**Send a filename to test:**"
        
        keyboard = [
            [InlineKeyboardButton("📝 Common Examples", callback_data="preview_examples")],
            [InlineKeyboardButton("🔙 Back", callback_data="preview_main")]
        ]
        
        await update.callback_query.edit_message_text(
            custom_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Set state for text input
        context.user_data['waiting_for_preview_filename'] = True
        
    except Exception as e:
        logger.error(f"Error showing custom preview: {e}")
        await update.callback_query.edit_message_text("❌ Error loading custom preview.")

async def show_batch_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show batch preview for multiple files"""
    try:
        batch_text = "📊 **Batch Preview**\n\n"
        batch_text += "Preview multiple files at once:\n\n"
        
        # Get recent user files for batch preview
        file_records = await db.get_user_file_records(user_id, limit=10)
        
        if file_records:
            settings = await db.get_user_settings(user_id)
            
            batch_text += "**Your Recent Files:**\n"
            for i, record in enumerate(file_records[:5], 1):
                original = record.original_name
                renamed = await preview_rename(original, settings)
                batch_text += f"{i}. `{original}`\n"
                batch_text += f"   → `{renamed}`\n\n"
            
            if len(file_records) > 5:
                batch_text += f"... and {len(file_records) - 5} more files\n\n"
        else:
            batch_text += "**No recent files found.**\n"
            batch_text += "Upload some files first to see batch preview.\n\n"
        
        batch_text += "**Options:**\n"
        batch_text += "• Preview all recent files\n"
        batch_text += "• Export preview to file\n"
        batch_text += "• Apply to all files\n"
        
        keyboard = [
            [InlineKeyboardButton("📋 Full List", callback_data="preview_full_batch")],
            [InlineKeyboardButton("💾 Export", callback_data="preview_export")],
            [InlineKeyboardButton("🔄 Apply All", callback_data="preview_apply_all")],
            [InlineKeyboardButton("🔙 Back", callback_data="preview_main")]
        ]
        
        await update.callback_query.edit_message_text(
            batch_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing batch preview: {e}")
        await update.callback_query.edit_message_text("❌ Error loading batch preview.")

async def show_live_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show live preview mode"""
    try:
        live_text = "🔄 **Live Preview Mode**\n\n"
        live_text += "Real-time preview as you change settings:\n\n"
        
        settings = await db.get_user_settings(user_id)
        sample_file = "Sample.File.S01E01.1080p.BluRay.x264-GROUP.mkv"
        
        live_text += f"**Test File:** `{sample_file}`\n"
        live_text += f"**Current Result:** `{await preview_rename(sample_file, settings)}`\n\n"
        
        live_text += "**Quick Settings:**\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 Change Template", callback_data="preview_live_template")],
            [InlineKeyboardButton("🔄 Change Mode", callback_data="preview_live_mode")],
            [InlineKeyboardButton("🔧 Replace Rules", callback_data="preview_live_replace")],
            [InlineKeyboardButton("🎯 Test File", callback_data="preview_live_test")],
            [InlineKeyboardButton("🔙 Back", callback_data="preview_main")]
        ]
        
        await update.callback_query.edit_message_text(
            live_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing live preview: {e}")
        await update.callback_query.edit_message_text("❌ Error loading live preview.")

async def show_category_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, category: str):
    """Show preview for specific file category"""
    try:
        category_files = {
            "tv": [
                "Game.of.Thrones.S01E01.1080p.BluRay.x264-GROUP.mkv",
                "Breaking.Bad.S05E14.720p.HDTV.x264-IMMERSE.mp4",
                "The.Office.US.S02E10.WEB-DL.1080p.H264.mp4",
                "Stranger.Things.S04E01.2160p.NF.WEB-DL.x265-NTb.mkv",
                "Friends.S01E01.720p.BluRay.x264-PSYCHD.mkv"
            ],
            "movies": [
                "The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mkv",
                "Inception.2010.720p.BRRip.x264-YIFY.mp4",
                "Avengers.Endgame.2019.4K.UHD.BluRay.x265-TERMINAL.mkv",
                "Pulp.Fiction.1994.1080p.BluRay.x264-AMIABLE.mkv",
                "The.Matrix.1999.2160p.UHD.BluRay.x265-SCOTCH.mkv"
            ],
            "docs": [
                "Important.Document.2024.pdf",
                "Meeting.Notes.Jan.15.2024.docx",
                "Project.Report.Final.Version.pdf",
                "User.Manual.Version.2.1.pdf",
                "Presentation.Slides.Marketing.pptx"
            ],
            "audio": [
                "Artist.Name.Song.Title.320kbps.mp3",
                "Album.Name.Track.01.Artist.Name.flac",
                "Podcast.Episode.123.Audio.Quality.mp3",
                "Classical.Music.Symphony.No.5.wav",
                "Electronic.Dance.Music.Mix.2024.mp3"
            ]
        }
        
        category_names = {
            "tv": "📺 TV Shows",
            "movies": "🎬 Movies", 
            "docs": "📄 Documents",
            "audio": "🎵 Audio Files"
        }
        
        if category not in category_files:
            await update.callback_query.edit_message_text("❌ Invalid category.")
            return
        
        settings = await db.get_user_settings(user_id)
        
        preview_text = f"{category_names[category]} **Preview**\n\n"
        preview_text += "Here's how your settings will rename these files:\n\n"
        
        for original in category_files[category]:
            renamed = await preview_rename(original, settings)
            preview_text += f"**Original:** `{original}`\n"
            preview_text += f"**Renamed:** `{renamed}`\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 More Samples", callback_data="preview_samples")],
            [InlineKeyboardButton("✏️ Test Custom", callback_data="preview_custom")],
            [InlineKeyboardButton("🔙 Back", callback_data="preview_samples")]
        ]
        
        await update.callback_query.edit_message_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing category preview: {e}")
        await update.callback_query.edit_message_text("❌ Error loading category preview.")

async def preview_rename(filename: str, settings) -> str:
    """Preview how a filename would be renamed"""
    try:
        rename_mode = get_user_rename_mode(settings)
        
        if rename_mode == 'auto':
            # Use template parser
            template = getattr(settings, 'rename_template', '{title}')
            parser = TemplateParser(template)
            return parser.parse(filename)
            
        elif rename_mode == 'replace':
            # Apply replacement rules
            replace_rules = get_user_replace_rules(settings)
            return apply_replace_rules(filename, replace_rules)
            
        elif rename_mode == 'manual':
            return f"[Manual: {filename}]"
            
        return filename
        
    except Exception as e:
        logger.error(f"Error previewing rename: {e}")
        return filename

async def handle_preview_filename_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle filename input for custom preview"""
    try:
        if not context.user_data.get('waiting_for_preview_filename'):
            return
        
        user_id = update.effective_user.id
        filename = update.message.text.strip()
        
        if not filename:
            await update.message.reply_text("❌ Please enter a valid filename.")
            return
        
        # Get user settings and preview
        settings = await db.get_user_settings(user_id)
        renamed = await preview_rename(filename, settings)
        
        preview_text = f"✏️ **Custom Preview Result**\n\n"
        preview_text += f"**Original:** `{filename}`\n"
        preview_text += f"**Renamed:** `{renamed}`\n\n"
        
        # Show settings used
        rename_mode = get_user_rename_mode(settings)
        preview_text += f"**Mode:** {rename_mode.title()}\n"
        
        if rename_mode == 'auto':
            template = getattr(settings, 'rename_template', '{title}')
            preview_text += f"**Template:** `{template}`\n"
        elif rename_mode == 'replace':
            replace_rules = get_user_replace_rules(settings)
            preview_text += f"**Rules:** {len(replace_rules)} active\n"
        
        preview_text += "\n**Try another filename or go back to menu:**"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Test Another", callback_data="preview_custom")],
            [InlineKeyboardButton("🔙 Back to Preview", callback_data="preview_main")]
        ]
        
        await update.message.reply_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Keep waiting for more input
        context.user_data['waiting_for_preview_filename'] = True
        
    except Exception as e:
        logger.error(f"Error handling preview filename input: {e}")
        await update.message.reply_text("❌ Error processing filename preview.")

async def generate_preview_report(filenames: list, settings) -> str:
    """Generate a detailed preview report"""
    try:
        report = "📊 **Rename Preview Report**\n\n"
        report += f"**Total Files:** {len(filenames)}\n"
        report += f"**Mode:** {get_user_rename_mode(settings).title()}\n"
        
        if get_user_rename_mode(settings) == 'auto':
            template = getattr(settings, 'rename_template', '{title}')
            report += f"**Template:** `{template}`\n"
        elif get_user_rename_mode(settings) == 'replace':
            replace_rules = get_user_replace_rules(settings)
            report += f"**Rules:** {len(replace_rules)} active\n"
        
        report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        report += "**Preview Results:**\n"
        for i, filename in enumerate(filenames, 1):
            renamed = await preview_rename(filename, settings)
            report += f"{i}. `{filename}`\n"
            report += f"   → `{renamed}`\n\n"
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating preview report: {e}")
        return "❌ Error generating preview report."
