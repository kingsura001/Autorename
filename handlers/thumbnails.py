"""
Thumbnail management handler
"""

import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from PIL import Image
import uuid

from config import Config
from database.connection import db
from database.models import Thumbnail
from utils.helpers import format_file_size
from middleware.subscription_check import check_force_subscription

logger = logging.getLogger(__name__)

async def thumbnail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /thumbnail command"""
    user_id = update.effective_user.id
    
    try:
        # Check force subscription
        if not await check_force_subscription(user_id, context):
            keyboard = [[InlineKeyboardButton("🔄 Check Subscription", callback_data="sub_check")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🚫 **Access Restricted**\n\n"
                "Please join our required channels to use thumbnail features.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return
        
        await show_thumbnail_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error in thumbnail command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading thumbnail features."
        )

async def show_thumbnail_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show thumbnail management menu"""
    try:
        user_id = update.effective_user.id
        
        # Get user's thumbnails
        thumbnails = await db.get_user_thumbnails(user_id)
        
        thumbnail_text = f"""
🖼️ **Thumbnail Management**

Upload custom thumbnails to use with your video files!

📊 **Your Thumbnails:** {len(thumbnails)}
📝 **Status:** {'Premium Feature' if len(thumbnails) > 5 else 'Free Usage'}

🎯 **How to Use:**
1. Send a photo to upload as thumbnail
2. Give it a name for easy identification
3. Select it when processing video files
4. Delete unused thumbnails to save space

💡 **Tips:**
• Use high-quality images (1280x720 recommended)
• JPG/PNG formats supported
• Keep thumbnails relevant to your content
• Premium users get unlimited thumbnails
        """
        
        keyboard = [
            [InlineKeyboardButton("📤 Upload Thumbnail", callback_data="thumb_upload")],
            [InlineKeyboardButton("🖼️ My Thumbnails", callback_data="thumb_list")],
            [InlineKeyboardButton("🗑️ Manage Thumbnails", callback_data="thumb_manage")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                thumbnail_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                thumbnail_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing thumbnail menu: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading thumbnail menu."
        )

async def list_thumbnails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mythumbnails command"""
    user_id = update.effective_user.id
    
    try:
        await show_thumbnails_list(update, context, user_id)
        
    except Exception as e:
        logger.error(f"Error in list thumbnails command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading your thumbnails."
        )

async def show_thumbnails_list(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show user's thumbnails list"""
    try:
        thumbnails = await db.get_user_thumbnails(user_id)
        
        if not thumbnails:
            thumbnail_text = """
🖼️ **Your Thumbnails**

You don't have any thumbnails yet.

📤 **Upload Your First Thumbnail:**
1. Click "Upload Thumbnail" below
2. Send a photo
3. Give it a name
4. Start using it with your videos!

💡 **Why Use Thumbnails?**
• Make your videos more attractive
• Professional appearance
• Easy identification
• Better organization
            """
            
            keyboard = [
                [InlineKeyboardButton("📤 Upload Thumbnail", callback_data="thumb_upload")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
            ]
        else:
            thumbnail_text = f"🖼️ **Your Thumbnails ({len(thumbnails)})**\n\n"
            
            keyboard = []
            for i, thumb in enumerate(thumbnails[:10], 1):  # Show first 10
                thumbnail_text += f"{i}. **{thumb.name}**\n"
                thumbnail_text += f"   ID: `{thumb.thumbnail_id[:8]}...`\n"
                thumbnail_text += f"   Created: {thumb.created_at.strftime('%Y-%m-%d')}\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"🖼️ {thumb.name}", 
                    callback_data=f"thumb_view_{thumb.thumbnail_id}"
                )])
            
            if len(thumbnails) > 10:
                thumbnail_text += f"... and {len(thumbnails) - 10} more\n\n"
            
            keyboard.extend([
                [InlineKeyboardButton("📤 Upload New", callback_data="thumb_upload")],
                [InlineKeyboardButton("🗑️ Manage", callback_data="thumb_manage")],
                [InlineKeyboardButton("⬅️ Back", callback_data="thumb_menu")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                thumbnail_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                thumbnail_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing thumbnails list: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading your thumbnails."
        )

async def handle_thumbnail_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle thumbnail photo upload"""
    user_id = update.effective_user.id
    
    try:
        # Check if user is in upload mode
        if context.user_data.get('awaiting_thumbnail_upload'):
            photo = update.message.photo[-1]  # Get highest resolution
            
            # Get file
            file_obj = await context.bot.get_file(photo.file_id)
            
            # Generate thumbnail ID
            thumbnail_id = str(uuid.uuid4())
            
            # Download and process image
            temp_path = os.path.join(Config.THUMBNAIL_PATH, f"temp_{thumbnail_id}.jpg")
            await file_obj.download_to_drive(temp_path)
            
            # Process image
            processed_path = await process_thumbnail_image(temp_path, thumbnail_id)
            
            # Store in context for naming
            context.user_data['pending_thumbnail'] = {
                'file_id': photo.file_id,
                'thumbnail_id': thumbnail_id,
                'processed_path': processed_path
            }
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Ask for name
            await update.message.reply_text(
                "📝 **Name Your Thumbnail**\n\n"
                "Please send a name for this thumbnail (e.g., 'Action Movie', 'Tutorial Series', etc.)\n\n"
                "💡 Use descriptive names to easily identify your thumbnails later."
            )
            
            # Set state to awaiting name
            context.user_data['awaiting_thumbnail_name'] = True
            context.user_data['awaiting_thumbnail_upload'] = False
            
        else:
            await update.message.reply_text(
                "🖼️ **Thumbnail Upload**\n\n"
                "To upload a thumbnail, use the /thumbnail command first and click 'Upload Thumbnail'."
            )
            
    except Exception as e:
        logger.error(f"Error handling thumbnail upload: {e}")
        await update.message.reply_text(
            "❌ An error occurred while processing your thumbnail. Please try again."
        )

async def process_thumbnail_image(input_path: str, thumbnail_id: str) -> str:
    """Process uploaded thumbnail image"""
    try:
        # Open and process image
        with Image.open(input_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize to standard thumbnail size
            img.thumbnail((320, 180), Image.Resampling.LANCZOS)
            
            # Save processed image
            output_path = os.path.join(Config.THUMBNAIL_PATH, f"{thumbnail_id}.jpg")
            img.save(output_path, 'JPEG', quality=85, optimize=True)
            
            return output_path
            
    except Exception as e:
        logger.error(f"Error processing thumbnail image: {e}")
        raise

async def handle_thumbnail_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle thumbnail name input"""
    user_id = update.effective_user.id
    
    try:
        if not context.user_data.get('awaiting_thumbnail_name'):
            return
        
        if 'pending_thumbnail' not in context.user_data:
            await update.message.reply_text("❌ No thumbnail data found. Please try uploading again.")
            return
        
        thumbnail_name = update.message.text.strip()
        
        if not thumbnail_name or len(thumbnail_name) > 50:
            await update.message.reply_text(
                "❌ Please provide a valid name (1-50 characters)."
            )
            return
        
        # Get pending thumbnail data
        pending = context.user_data['pending_thumbnail']
        
        # Create thumbnail record
        thumbnail = Thumbnail(
            thumbnail_id=pending['thumbnail_id'],
            user_id=user_id,
            file_id=pending['file_id'],
            name=thumbnail_name
        )
        
        # Save to database
        success = await db.create_thumbnail(thumbnail)
        
        if success:
            await update.message.reply_text(
                f"✅ **Thumbnail Saved Successfully!**\n\n"
                f"**Name:** {thumbnail_name}\n"
                f"**ID:** `{thumbnail.thumbnail_id[:8]}...`\n\n"
                f"You can now use this thumbnail when processing video files!"
            )
            
            # Update user settings if this is their first thumbnail
            settings = await db.get_user_settings(user_id)
            if settings and not settings.default_thumbnail:
                await db.update_user_settings(user_id, {
                    "default_thumbnail": f"{thumbnail.thumbnail_id}.jpg"
                })
        else:
            await update.message.reply_text(
                "❌ Failed to save thumbnail. Please try again."
            )
        
        # Clean up context
        context.user_data.pop('awaiting_thumbnail_name', None)
        context.user_data.pop('pending_thumbnail', None)
        
    except Exception as e:
        logger.error(f"Error handling thumbnail name: {e}")
        await update.message.reply_text(
            "❌ An error occurred while saving your thumbnail."
        )

async def thumbnail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle thumbnail callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data.replace("thumb_", "")
    
    try:
        if action == "menu":
            await show_thumbnail_menu(update, context)
        
        elif action == "upload":
            await start_thumbnail_upload(update, context)
        
        elif action == "list":
            await show_thumbnails_list(update, context, user_id)
        
        elif action == "manage":
            await show_thumbnail_management(update, context, user_id)
        
        elif action.startswith("view_"):
            thumbnail_id = action.replace("view_", "")
            await show_thumbnail_details(update, context, thumbnail_id, user_id)
        
        elif action.startswith("delete_"):
            thumbnail_id = action.replace("delete_", "")
            await delete_thumbnail(update, context, thumbnail_id, user_id)
        
        elif action.startswith("set_default_"):
            thumbnail_id = action.replace("set_default_", "")
            await set_default_thumbnail(update, context, thumbnail_id, user_id)
            
    except Exception as e:
        logger.error(f"Error in thumbnail callback: {e}")
        await query.edit_message_text(
            "❌ An error occurred while processing your request."
        )

async def start_thumbnail_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start thumbnail upload process"""
    try:
        context.user_data['awaiting_thumbnail_upload'] = True
        
        await update.callback_query.edit_message_text(
            "📤 **Upload Thumbnail**\n\n"
            "Please send a photo to use as thumbnail.\n\n"
            "📋 **Requirements:**\n"
            "• JPG or PNG format\n"
            "• High quality recommended\n"
            "• Will be resized to 320x180\n\n"
            "💡 **Tips:**\n"
            "• Use clear, attractive images\n"
            "• Avoid copyrighted content\n"
            "• Landscape orientation works best",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="thumb_menu")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error starting thumbnail upload: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while starting upload process."
        )

async def show_thumbnail_management(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show thumbnail management options"""
    try:
        thumbnails = await db.get_user_thumbnails(user_id)
        
        if not thumbnails:
            await update.callback_query.edit_message_text(
                "🖼️ **No Thumbnails Found**\n\n"
                "You don't have any thumbnails to manage.\n"
                "Upload some thumbnails first!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📤 Upload Thumbnail", callback_data="thumb_upload"),
                    InlineKeyboardButton("⬅️ Back", callback_data="thumb_menu")
                ]])
            )
            return
        
        manage_text = f"""
🗑️ **Manage Thumbnails**

You have {len(thumbnails)} thumbnail(s).

**Select a thumbnail to manage:**
        """
        
        keyboard = []
        for thumb in thumbnails[:8]:  # Show first 8
            keyboard.append([InlineKeyboardButton(
                f"🖼️ {thumb.name}",
                callback_data=f"thumb_view_{thumb.thumbnail_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="thumb_menu")])
        
        await update.callback_query.edit_message_text(
            manage_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing thumbnail management: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading thumbnail management."
        )

async def show_thumbnail_details(update: Update, context: ContextTypes.DEFAULT_TYPE, thumbnail_id: str, user_id: int):
    """Show thumbnail details and options"""
    try:
        # Get thumbnail from database
        thumbnails = await db.get_user_thumbnails(user_id)
        thumbnail = next((t for t in thumbnails if t.thumbnail_id == thumbnail_id), None)
        
        if not thumbnail:
            await update.callback_query.edit_message_text(
                "❌ Thumbnail not found or you don't have permission to view it."
            )
            return
        
        # Get user settings to check if it's default
        settings = await db.get_user_settings(user_id)
        is_default = (settings and settings.default_thumbnail == f"{thumbnail_id}.jpg")
        
        details_text = f"""
🖼️ **Thumbnail Details**

**Name:** {thumbnail.name}
**ID:** `{thumbnail.thumbnail_id[:12]}...`
**Created:** {thumbnail.created_at.strftime('%Y-%m-%d %H:%M:%S')}
**Status:** {'🌟 Default' if is_default else '📁 Available'}

**Actions:**
        """
        
        keyboard = []
        
        if not is_default:
            keyboard.append([InlineKeyboardButton(
                "🌟 Set as Default",
                callback_data=f"thumb_set_default_{thumbnail_id}"
            )])
        
        keyboard.extend([
            [InlineKeyboardButton(
                "🗑️ Delete",
                callback_data=f"thumb_delete_{thumbnail_id}"
            )],
            [InlineKeyboardButton("⬅️ Back to List", callback_data="thumb_manage")]
        ])
        
        await update.callback_query.edit_message_text(
            details_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing thumbnail details: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading thumbnail details."
        )

async def delete_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE, thumbnail_id: str, user_id: int):
    """Delete a thumbnail"""
    try:
        # Delete from database
        success = await db.delete_thumbnail(thumbnail_id, user_id)
        
        if success:
            # Delete file from filesystem
            file_path = os.path.join(Config.THUMBNAIL_PATH, f"{thumbnail_id}.jpg")
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Update user settings if this was the default thumbnail
            settings = await db.get_user_settings(user_id)
            if settings and settings.default_thumbnail == f"{thumbnail_id}.jpg":
                await db.update_user_settings(user_id, {"default_thumbnail": None})
            
            await update.callback_query.edit_message_text(
                "✅ **Thumbnail Deleted Successfully**\n\n"
                "The thumbnail has been removed from your collection.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Management", callback_data="thumb_manage")
                ]])
            )
        else:
            await update.callback_query.edit_message_text(
                "❌ Failed to delete thumbnail. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Error deleting thumbnail: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while deleting the thumbnail."
        )

async def set_default_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE, thumbnail_id: str, user_id: int):
    """Set thumbnail as default"""
    try:
        # Update user settings
        success = await db.update_user_settings(user_id, {
            "default_thumbnail": f"{thumbnail_id}.jpg"
        })
        
        if success:
            await update.callback_query.edit_message_text(
                "✅ **Default Thumbnail Updated**\n\n"
                "This thumbnail will now be used automatically for your video files.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Management", callback_data="thumb_manage")
                ]])
            )
        else:
            await update.callback_query.edit_message_text(
                "❌ Failed to set default thumbnail. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Error setting default thumbnail: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while setting the default thumbnail."
        )
