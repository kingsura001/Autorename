"""
File handling and processing
"""

import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import Config
from database.connection import db
from database.models import FileRecord
from utils.file_processor import FileProcessor
from utils.template_parser import TemplateParser
from utils.helpers import format_file_size, get_file_extension
from middleware.subscription_check import check_force_subscription

logger = logging.getLogger(__name__)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document files"""
    await handle_file(update, context, "document")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video files"""
    await handle_file(update, context, "video")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle audio files"""
    await handle_file(update, context, "audio")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_type: str):
    """Handle any file upload"""
    user_id = update.effective_user.id
    
    try:
        # Check force subscription
        if not await check_force_subscription(user_id, context):
            keyboard = [[InlineKeyboardButton("🔄 Check Subscription", callback_data="sub_check")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🚫 **Access Restricted**\n\n"
                "Please join our required channels to use this bot.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return
        
        # Get file info
        if file_type == "document":
            file_obj = update.message.document
            file_name = file_obj.file_name
            file_size = file_obj.file_size
            mime_type = file_obj.mime_type
        elif file_type == "video":
            file_obj = update.message.video
            file_name = file_obj.file_name or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            file_size = file_obj.file_size
            mime_type = file_obj.mime_type
        elif file_type == "audio":
            file_obj = update.message.audio
            file_name = file_obj.file_name or f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            file_size = file_obj.file_size
            mime_type = file_obj.mime_type
        else:
            await update.message.reply_text("❌ Unsupported file type.")
            return
        
        # Check file size
        if file_size > Config.MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ File too large! Maximum size allowed: {format_file_size(Config.MAX_FILE_SIZE)}\n"
                f"Your file size: {format_file_size(file_size)}"
            )
            return
        
        # Get user settings
        settings = await db.get_user_settings(user_id)
        if not settings:
            from database.models import UserSettings
            settings = UserSettings(user_id=user_id)
            await db.create_user_settings(settings)
        
        # Create file record
        file_record = FileRecord(
            file_id=file_obj.file_id,
            user_id=user_id,
            original_name=file_name,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            processing_status="pending"
        )
        
        await db.create_file_record(file_record)
        
        # Store file info in context for rename
        context.user_data['current_file'] = {
            'file_id': file_obj.file_id,
            'file_name': file_name,
            'file_size': file_size,
            'file_type': file_type,
            'mime_type': mime_type
        }
        
        # Check if auto-rename is enabled
        if settings.auto_rename:
            await auto_rename_file(update, context, file_record, settings)
        else:
            await prompt_for_rename(update, context, file_record)
        
    except Exception as e:
        logger.error(f"Error handling file: {e}")
        await update.message.reply_text(
            "❌ An error occurred while processing your file. Please try again."
        )

async def prompt_for_rename(update: Update, context: ContextTypes.DEFAULT_TYPE, file_record: FileRecord):
    """Prompt user for file rename"""
    try:
        # Get user settings for template
        settings = await db.get_user_settings(file_record.user_id)
        
        file_info = f"""
📁 **File Received**

**Original Name:** `{file_record.original_name}`
**Size:** {format_file_size(file_record.file_size)}
**Type:** {file_record.file_type.title()}

🔧 **Current Template:** `{settings.rename_template if settings else '{title}'}`

**Choose an action:**
        """
        
        keyboard = [
            [InlineKeyboardButton("✏️ Custom Name", callback_data="rename_custom")],
            [InlineKeyboardButton("🎯 Use Template", callback_data="rename_template")],
            [InlineKeyboardButton("📤 Send Original", callback_data="rename_original")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            file_info,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error prompting for rename: {e}")
        await update.message.reply_text(
            "❌ An error occurred while processing your request."
        )

async def auto_rename_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_record: FileRecord, settings):
    """Automatically rename file using template"""
    try:
        # Parse template
        template_parser = TemplateParser(settings.rename_template)
        new_name = template_parser.parse(file_record.original_name)
        
        # Process file
        await process_file_rename(update, context, file_record, new_name)
        
    except Exception as e:
        logger.error(f"Error in auto rename: {e}")
        await update.message.reply_text(
            "❌ Auto rename failed. Please try manual rename."
        )

async def handle_rename_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for file renaming"""
    user_id = update.effective_user.id
    
    try:
        # Check if user has a file waiting for rename
        if 'current_file' not in context.user_data:
            return  # No file to rename
        
        file_info = context.user_data['current_file']
        new_name = update.message.text.strip()
        
        # Validate new name
        if not new_name:
            await update.message.reply_text("❌ Please provide a valid file name.")
            return
        
        # Add original extension if not present
        original_ext = get_file_extension(file_info['file_name'])
        if not new_name.endswith(original_ext):
            new_name += original_ext
        
        # Create file record
        file_record = FileRecord(
            file_id=file_info['file_id'],
            user_id=user_id,
            original_name=file_info['file_name'],
            file_size=file_info['file_size'],
            file_type=file_info['file_type'],
            mime_type=file_info['mime_type'],
            processing_status="pending"
        )
        
        # Process file
        await process_file_rename(update, context, file_record, new_name)
        
        # Clear context
        del context.user_data['current_file']
        
    except Exception as e:
        logger.error(f"Error handling rename text: {e}")
        await update.message.reply_text(
            "❌ An error occurred while renaming your file."
        )

async def process_file_rename(update: Update, context: ContextTypes.DEFAULT_TYPE, file_record: FileRecord, new_name: str):
    """Process file renaming and upload"""
    try:
        # Update processing status
        await db.update_file_record(file_record.file_id, {
            "processing_status": "processing",
            "renamed_name": new_name
        })
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "⏳ **Processing your file...**\n\n"
            f"**Original:** `{file_record.original_name}`\n"
            f"**New Name:** `{new_name}`\n\n"
            "Please wait while I process your file.",
            parse_mode="Markdown"
        )
        
        # Get file from Telegram
        file_obj = await context.bot.get_file(file_record.file_id)
        
        # Download file
        download_path = os.path.join(Config.DOWNLOAD_PATH, f"{file_record.file_id}_{file_record.original_name}")
        await file_obj.download_to_drive(download_path)
        
        # Process file
        processor = FileProcessor()
        
        # Get user settings for thumbnail
        settings = await db.get_user_settings(file_record.user_id)
        
        processed_file_path = await processor.process_file(
            download_path,
            new_name,
            file_record.file_type,
            settings
        )
        
        # Upload processed file
        await upload_processed_file(update, context, processed_file_path, new_name, file_record)
        
        # Update file record
        await db.update_file_record(file_record.file_id, {
            "processing_status": "completed",
            "completed_at": datetime.now()
        })
        
        # Update user stats
        await db.update_user(file_record.user_id, {
            "total_files_processed": 1  # This would be incremented in actual implementation
        })
        
        # Clean up files
        if os.path.exists(download_path):
            os.remove(download_path)
        if os.path.exists(processed_file_path):
            os.remove(processed_file_path)
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error processing file rename: {e}")
        
        # Update file record with error
        await db.update_file_record(file_record.file_id, {
            "processing_status": "failed",
            "error_message": str(e)
        })
        
        await update.message.reply_text(
            f"❌ **Processing Failed**\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again or contact support if the issue persists."
        )

async def upload_processed_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str, new_name: str, file_record: FileRecord):
    """Upload processed file to Telegram"""
    try:
        # Get user settings
        settings = await db.get_user_settings(file_record.user_id)
        
        # Prepare caption
        caption = f"✅ **File Processed Successfully**\n\n"
        caption += f"**Original:** `{file_record.original_name}`\n"
        caption += f"**New Name:** `{new_name}`\n"
        caption += f"**Size:** {format_file_size(file_record.file_size)}"
        
        # Upload based on file type
        if file_record.file_type == "video":
            # Get thumbnail if available
            thumbnail = None
            if settings and settings.default_thumbnail:
                thumbnail_path = os.path.join(Config.THUMBNAIL_PATH, settings.default_thumbnail)
                if os.path.exists(thumbnail_path):
                    thumbnail = open(thumbnail_path, 'rb')
            
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(file_path, 'rb'),
                caption=caption,
                parse_mode="Markdown",
                filename=new_name,
                thumbnail=thumbnail
            )
            
            if thumbnail:
                thumbnail.close()
        
        elif file_record.file_type == "audio":
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=open(file_path, 'rb'),
                caption=caption,
                parse_mode="Markdown",
                filename=new_name
            )
        
        else:  # document
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(file_path, 'rb'),
                caption=caption,
                parse_mode="Markdown",
                filename=new_name
            )
        
        # Send completion message
        keyboard = [
            [InlineKeyboardButton("🔄 Process Another", callback_data="process_another")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎉 **Processing Complete!**\n\n"
            "Your file has been processed and uploaded successfully. "
            "You can now process another file or adjust your settings.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error uploading processed file: {e}")
        raise
