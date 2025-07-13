"""
Metadata extraction and management for files
"""

import logging
import json
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from middleware.auth import require_auth
from middleware.subscription_check import subscription_required
from utils.helpers import format_file_size, get_file_extension

logger = logging.getLogger(__name__)

# Metadata fields configuration
METADATA_FIELDS = {
    'basic': {
        'name': 'Basic Info',
        'fields': ['filename', 'size', 'type', 'extension', 'date_created']
    },
    'video': {
        'name': 'Video Info',
        'fields': ['duration', 'resolution', 'fps', 'codec', 'bitrate', 'quality']
    },
    'audio': {
        'name': 'Audio Info',
        'fields': ['duration', 'bitrate', 'sample_rate', 'channels', 'codec']
    },
    'image': {
        'name': 'Image Info',
        'fields': ['dimensions', 'format', 'color_mode', 'dpi']
    },
    'document': {
        'name': 'Document Info',
        'fields': ['pages', 'author', 'title', 'subject', 'creation_date']
    },
    'media': {
        'name': 'Media Info',
        'fields': ['title', 'artist', 'album', 'genre', 'year', 'track_number']
    }
}

@require_auth
@subscription_required
async def metadata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /metadata command"""
    user_id = update.effective_user.id
    
    try:
        await show_metadata_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in metadata command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading metadata settings."
        )

async def show_metadata_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show metadata extraction menu"""
    try:
        settings = await db.get_user_settings(user_id)
        metadata_enabled = getattr(settings, 'metadata_enabled', True)
        auto_extract = getattr(settings, 'auto_extract_metadata', False)
        
        message_text = "🏷️ **Metadata Settings**\n\n"
        message_text += "Configure metadata extraction for your files:\n\n"
        
        message_text += f"**Status:** {'✅ Enabled' if metadata_enabled else '❌ Disabled'}\n"
        message_text += f"**Auto Extract:** {'✅ Yes' if auto_extract else '❌ No'}\n\n"
        
        message_text += "**Available Metadata:**\n"
        for category, info in METADATA_FIELDS.items():
            message_text += f"• {info['name']}\n"
        
        message_text += "\n**Features:**\n"
        message_text += "• Extract detailed file information\n"
        message_text += "• Use metadata in rename templates\n"
        message_text += "• Auto-populate filename variables\n"
        message_text += "• Export metadata to JSON/CSV\n"
        
        keyboard = [
            [InlineKeyboardButton("⚙️ Configure", callback_data="metadata_config")],
            [InlineKeyboardButton("🔍 Extract Now", callback_data="metadata_extract")],
            [InlineKeyboardButton("📊 View History", callback_data="metadata_history")],
            [InlineKeyboardButton("📋 Templates", callback_data="metadata_templates")],
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
        logger.error(f"Error showing metadata menu: {e}")
        await update.message.reply_text("❌ Error loading metadata settings.")

async def metadata_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle metadata callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data == "metadata_config":
            await show_metadata_config(update, context, user_id)
        elif data == "metadata_extract":
            await show_metadata_extract(update, context, user_id)
        elif data == "metadata_history":
            await show_metadata_history(update, context, user_id)
        elif data == "metadata_templates":
            await show_metadata_templates(update, context, user_id)
        elif data.startswith("metadata_toggle_"):
            setting = data.split("_")[2]
            await toggle_metadata_setting(update, context, user_id, setting)
        elif data.startswith("metadata_category_"):
            category = data.split("_")[2]
            await show_metadata_category(update, context, user_id, category)
            
    except Exception as e:
        logger.error(f"Error handling metadata callback: {e}")
        await query.edit_message_text("❌ Error processing metadata settings.")

async def show_metadata_config(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show metadata configuration options"""
    try:
        settings = await db.get_user_settings(user_id)
        metadata_enabled = getattr(settings, 'metadata_enabled', True)
        auto_extract = getattr(settings, 'auto_extract_metadata', False)
        include_thumbnails = getattr(settings, 'metadata_include_thumbnails', False)
        save_original = getattr(settings, 'metadata_save_original', True)
        
        config_text = "⚙️ **Metadata Configuration**\n\n"
        config_text += "Configure how metadata is extracted and used:\n\n"
        
        config_text += f"**General Settings:**\n"
        config_text += f"• Metadata Extraction: {'✅ Enabled' if metadata_enabled else '❌ Disabled'}\n"
        config_text += f"• Auto Extract: {'✅ Yes' if auto_extract else '❌ No'}\n"
        config_text += f"• Include Thumbnails: {'✅ Yes' if include_thumbnails else '❌ No'}\n"
        config_text += f"• Save Original: {'✅ Yes' if save_original else '❌ No'}\n\n"
        
        config_text += "**Categories:**\n"
        enabled_categories = json.loads(getattr(settings, 'metadata_categories', '[]'))
        for category, info in METADATA_FIELDS.items():
            status = "✅" if category in enabled_categories else "❌"
            config_text += f"• {status} {info['name']}\n"
        
        keyboard = [
            [InlineKeyboardButton(
                "❌ Disable" if metadata_enabled else "✅ Enable",
                callback_data="metadata_toggle_enabled"
            )],
            [InlineKeyboardButton(
                "❌ Manual" if auto_extract else "✅ Auto Extract",
                callback_data="metadata_toggle_auto"
            )],
            [InlineKeyboardButton("📂 Categories", callback_data="metadata_categories")],
            [InlineKeyboardButton("🔄 Reset", callback_data="metadata_reset")],
            [InlineKeyboardButton("🔙 Back", callback_data="metadata_main")]
        ]
        
        await update.callback_query.edit_message_text(
            config_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing metadata config: {e}")
        await update.callback_query.edit_message_text("❌ Error loading configuration.")

async def show_metadata_extract(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show metadata extraction interface"""
    try:
        extract_text = "🔍 **Extract Metadata**\n\n"
        extract_text += "Send a file to extract its metadata:\n\n"
        extract_text += "**Supported Files:**\n"
        extract_text += "• Videos (MP4, AVI, MKV, MOV, etc.)\n"
        extract_text += "• Audio (MP3, WAV, FLAC, AAC, etc.)\n"
        extract_text += "• Images (JPG, PNG, GIF, BMP, etc.)\n"
        extract_text += "• Documents (PDF, DOC, DOCX, etc.)\n"
        extract_text += "• Archives (ZIP, RAR, 7Z, etc.)\n\n"
        extract_text += "**What you'll get:**\n"
        extract_text += "• Detailed file information\n"
        extract_text += "• Technical specifications\n"
        extract_text += "• Embedded metadata\n"
        extract_text += "• Suggested rename templates\n"
        
        keyboard = [
            [InlineKeyboardButton("📁 Upload File", callback_data="metadata_upload")],
            [InlineKeyboardButton("🔙 Back", callback_data="metadata_main")]
        ]
        
        await update.callback_query.edit_message_text(
            extract_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Set state for file upload
        context.user_data['waiting_for_metadata_file'] = True
        
    except Exception as e:
        logger.error(f"Error showing metadata extract: {e}")
        await update.callback_query.edit_message_text("❌ Error loading extraction interface.")

async def show_metadata_history(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show metadata extraction history"""
    try:
        # Get recent file records with metadata
        file_records = await db.get_user_file_records(user_id, limit=10)
        
        if not file_records:
            await update.callback_query.edit_message_text(
                "❌ No metadata history found. Process some files first!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Extract Now", callback_data="metadata_extract"),
                    InlineKeyboardButton("🔙 Back", callback_data="metadata_main")
                ]])
            )
            return
        
        history_text = "📊 **Metadata History**\n\n"
        history_text += "Recent files with extracted metadata:\n\n"
        
        for i, record in enumerate(file_records[:5], 1):
            history_text += f"**{i}. {record.original_name}**\n"
            history_text += f"• Type: {record.file_type}\n"
            history_text += f"• Size: {format_file_size(record.file_size)}\n"
            history_text += f"• Date: {record.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📋 Export History", callback_data="metadata_export")],
            [InlineKeyboardButton("🗑️ Clear History", callback_data="metadata_clear_history")],
            [InlineKeyboardButton("🔙 Back", callback_data="metadata_main")]
        ]
        
        await update.callback_query.edit_message_text(
            history_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing metadata history: {e}")
        await update.callback_query.edit_message_text("❌ Error loading history.")

async def show_metadata_templates(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show metadata-based rename templates"""
    try:
        templates_text = "📋 **Metadata Templates**\n\n"
        templates_text += "Use metadata in your rename templates:\n\n"
        
        templates_text += "**Available Variables:**\n"
        templates_text += "• `{metadata.title}` - Media title\n"
        templates_text += "• `{metadata.artist}` - Artist name\n"
        templates_text += "• `{metadata.album}` - Album name\n"
        templates_text += "• `{metadata.year}` - Release year\n"
        templates_text += "• `{metadata.genre}` - Genre\n"
        templates_text += "• `{metadata.duration}` - Duration\n"
        templates_text += "• `{metadata.resolution}` - Video resolution\n"
        templates_text += "• `{metadata.bitrate}` - Audio/Video bitrate\n\n"
        
        templates_text += "**Example Templates:**\n"
        templates_text += "• `{metadata.artist} - {metadata.title}`\n"
        templates_text += "• `{metadata.title} ({metadata.year})`\n"
        templates_text += "• `{title} [{metadata.resolution}]`\n"
        templates_text += "• `{metadata.album} - {metadata.track} - {metadata.title}`\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 Create Template", callback_data="metadata_create_template")],
            [InlineKeyboardButton("🔄 Test Template", callback_data="metadata_test_template")],
            [InlineKeyboardButton("🔙 Back", callback_data="metadata_main")]
        ]
        
        await update.callback_query.edit_message_text(
            templates_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing metadata templates: {e}")
        await update.callback_query.edit_message_text("❌ Error loading templates.")

async def extract_file_metadata(file_path: str, file_type: str) -> Dict[str, Any]:
    """Extract metadata from file"""
    try:
        metadata = {
            'basic': {},
            'video': {},
            'audio': {},
            'image': {},
            'document': {},
            'media': {}
        }
        
        # Basic file info
        import os
        from pathlib import Path
        
        file_stat = os.stat(file_path)
        file_path_obj = Path(file_path)
        
        metadata['basic'] = {
            'filename': file_path_obj.name,
            'size': file_stat.st_size,
            'type': file_type,
            'extension': file_path_obj.suffix.lower(),
            'date_created': file_stat.st_ctime,
            'date_modified': file_stat.st_mtime
        }
        
        # Type-specific metadata extraction
        if file_type == 'video':
            metadata['video'] = await extract_video_metadata(file_path)
        elif file_type == 'audio':
            metadata['audio'] = await extract_audio_metadata(file_path)
        elif file_type == 'image':
            metadata['image'] = await extract_image_metadata(file_path)
        elif file_type == 'document':
            metadata['document'] = await extract_document_metadata(file_path)
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}

async def extract_video_metadata(file_path: str) -> Dict[str, Any]:
    """Extract video metadata using ffprobe"""
    try:
        import subprocess
        import json
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            video_stream = None
            audio_stream = None
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and not audio_stream:
                    audio_stream = stream
            
            metadata = {}
            
            if video_stream:
                metadata.update({
                    'duration': float(video_stream.get('duration', 0)),
                    'width': video_stream.get('width', 0),
                    'height': video_stream.get('height', 0),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                    'codec': video_stream.get('codec_name', ''),
                    'bitrate': int(video_stream.get('bit_rate', 0))
                })
                
                # Determine quality
                height = metadata.get('height', 0)
                if height >= 2160:
                    metadata['quality'] = '4K'
                elif height >= 1440:
                    metadata['quality'] = '1440p'
                elif height >= 1080:
                    metadata['quality'] = '1080p'
                elif height >= 720:
                    metadata['quality'] = '720p'
                elif height >= 480:
                    metadata['quality'] = '480p'
                else:
                    metadata['quality'] = 'SD'
                
                metadata['resolution'] = f"{metadata.get('width', 0)}x{metadata.get('height', 0)}"
            
            return metadata
            
    except Exception as e:
        logger.error(f"Error extracting video metadata: {e}")
    
    return {}

async def extract_audio_metadata(file_path: str) -> Dict[str, Any]:
    """Extract audio metadata"""
    try:
        import subprocess
        import json
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            audio_stream = None
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            metadata = {}
            
            if audio_stream:
                metadata.update({
                    'duration': float(audio_stream.get('duration', 0)),
                    'bitrate': int(audio_stream.get('bit_rate', 0)),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': audio_stream.get('channels', 0),
                    'codec': audio_stream.get('codec_name', '')
                })
            
            # Get tags from format
            format_info = data.get('format', {})
            tags = format_info.get('tags', {})
            
            # Normalize tag names (different formats use different cases)
            normalized_tags = {}
            for key, value in tags.items():
                normalized_key = key.lower().replace('-', '_')
                normalized_tags[normalized_key] = value
            
            metadata.update({
                'title': normalized_tags.get('title', ''),
                'artist': normalized_tags.get('artist', ''),
                'album': normalized_tags.get('album', ''),
                'genre': normalized_tags.get('genre', ''),
                'year': normalized_tags.get('date', '')[:4] if normalized_tags.get('date') else '',
                'track_number': normalized_tags.get('track', '')
            })
            
            return metadata
            
    except Exception as e:
        logger.error(f"Error extracting audio metadata: {e}")
    
    return {}

async def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    """Extract image metadata"""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        
        with Image.open(file_path) as img:
            metadata = {
                'dimensions': f"{img.width}x{img.height}",
                'format': img.format,
                'color_mode': img.mode,
                'width': img.width,
                'height': img.height
            }
            
            # Extract EXIF data
            exif = img.getexif()
            if exif:
                for tag_id in exif:
                    tag = TAGS.get(tag_id, tag_id)
                    data = exif.get(tag_id)
                    
                    if isinstance(data, bytes):
                        data = data.decode('utf-8', errors='ignore')
                    
                    metadata[f'exif_{tag}'] = data
            
            return metadata
            
    except Exception as e:
        logger.error(f"Error extracting image metadata: {e}")
    
    return {}

async def extract_document_metadata(file_path: str) -> Dict[str, Any]:
    """Extract document metadata"""
    try:
        metadata = {}
        
        # PDF metadata
        if file_path.lower().endswith('.pdf'):
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    info = reader.metadata
                    
                    if info:
                        metadata.update({
                            'title': info.get('/Title', ''),
                            'author': info.get('/Author', ''),
                            'subject': info.get('/Subject', ''),
                            'creator': info.get('/Creator', ''),
                            'producer': info.get('/Producer', ''),
                            'creation_date': info.get('/CreationDate', ''),
                            'modification_date': info.get('/ModDate', '')
                        })
                    
                    metadata['pages'] = len(reader.pages)
                    
            except ImportError:
                logger.warning("PyPDF2 not installed, skipping PDF metadata extraction")
            except Exception as e:
                logger.error(f"Error extracting PDF metadata: {e}")
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting document metadata: {e}")
    
    return {}

async def handle_metadata_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file upload for metadata extraction"""
    try:
        if not context.user_data.get('waiting_for_metadata_file'):
            return
        
        user_id = update.effective_user.id
        
        # Get file info
        file_obj = None
        file_type = None
        
        if update.message.document:
            file_obj = update.message.document
            file_type = 'document'
        elif update.message.video:
            file_obj = update.message.video
            file_type = 'video'
        elif update.message.audio:
            file_obj = update.message.audio
            file_type = 'audio'
        elif update.message.photo:
            file_obj = update.message.photo[-1]  # Get highest resolution
            file_type = 'image'
        else:
            await update.message.reply_text("❌ Unsupported file type for metadata extraction.")
            return
        
        # Download file
        file = await context.bot.get_file(file_obj.file_id)
        file_path = f"./temp_{user_id}_{file_obj.file_id}"
        await file.download_to_drive(file_path)
        
        # Extract metadata
        metadata = await extract_file_metadata(file_path, file_type)
        
        # Format metadata for display
        metadata_text = format_metadata_display(metadata, file_obj.file_name or "unknown")
        
        # Send metadata
        keyboard = [
            [InlineKeyboardButton("📋 Copy JSON", callback_data=f"metadata_json_{file_obj.file_id}")],
            [InlineKeyboardButton("📝 Use in Template", callback_data=f"metadata_template_{file_obj.file_id}")],
            [InlineKeyboardButton("🔍 Extract Another", callback_data="metadata_extract")]
        ]
        
        await update.message.reply_text(
            metadata_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Clean up
        import os
        try:
            os.remove(file_path)
        except:
            pass
        
        context.user_data['waiting_for_metadata_file'] = False
        context.user_data[f'metadata_{file_obj.file_id}'] = metadata
        
    except Exception as e:
        logger.error(f"Error handling metadata file upload: {e}")
        await update.message.reply_text("❌ Error extracting metadata from file.")

def format_metadata_display(metadata: Dict[str, Any], filename: str) -> str:
    """Format metadata for display"""
    try:
        display_text = f"🏷️ **Metadata for {filename}**\n\n"
        
        # Basic info
        if metadata.get('basic'):
            basic = metadata['basic']
            display_text += "**📁 Basic Information:**\n"
            display_text += f"• **Size:** {format_file_size(basic.get('size', 0))}\n"
            display_text += f"• **Type:** {basic.get('type', 'Unknown')}\n"
            display_text += f"• **Extension:** {basic.get('extension', 'Unknown')}\n\n"
        
        # Video info
        if metadata.get('video'):
            video = metadata['video']
            display_text += "**🎬 Video Information:**\n"
            if video.get('duration'):
                duration = int(video['duration'])
                minutes, seconds = divmod(duration, 60)
                display_text += f"• **Duration:** {minutes}:{seconds:02d}\n"
            if video.get('resolution'):
                display_text += f"• **Resolution:** {video['resolution']}\n"
            if video.get('quality'):
                display_text += f"• **Quality:** {video['quality']}\n"
            if video.get('fps'):
                display_text += f"• **FPS:** {video['fps']:.1f}\n"
            if video.get('codec'):
                display_text += f"• **Codec:** {video['codec']}\n"
            display_text += "\n"
        
        # Audio info
        if metadata.get('audio'):
            audio = metadata['audio']
            display_text += "**🎵 Audio Information:**\n"
            if audio.get('duration'):
                duration = int(audio['duration'])
                minutes, seconds = divmod(duration, 60)
                display_text += f"• **Duration:** {minutes}:{seconds:02d}\n"
            if audio.get('bitrate'):
                display_text += f"• **Bitrate:** {audio['bitrate']} bps\n"
            if audio.get('sample_rate'):
                display_text += f"• **Sample Rate:** {audio['sample_rate']} Hz\n"
            if audio.get('channels'):
                display_text += f"• **Channels:** {audio['channels']}\n"
            if audio.get('codec'):
                display_text += f"• **Codec:** {audio['codec']}\n"
            
            # Media tags
            if audio.get('title'):
                display_text += f"• **Title:** {audio['title']}\n"
            if audio.get('artist'):
                display_text += f"• **Artist:** {audio['artist']}\n"
            if audio.get('album'):
                display_text += f"• **Album:** {audio['album']}\n"
            if audio.get('genre'):
                display_text += f"• **Genre:** {audio['genre']}\n"
            if audio.get('year'):
                display_text += f"• **Year:** {audio['year']}\n"
            display_text += "\n"
        
        # Image info
        if metadata.get('image'):
            image = metadata['image']
            display_text += "**🖼️ Image Information:**\n"
            if image.get('dimensions'):
                display_text += f"• **Dimensions:** {image['dimensions']}\n"
            if image.get('format'):
                display_text += f"• **Format:** {image['format']}\n"
            if image.get('color_mode'):
                display_text += f"• **Color Mode:** {image['color_mode']}\n"
            display_text += "\n"
        
        # Document info
        if metadata.get('document'):
            doc = metadata['document']
            display_text += "**📄 Document Information:**\n"
            if doc.get('pages'):
                display_text += f"• **Pages:** {doc['pages']}\n"
            if doc.get('title'):
                display_text += f"• **Title:** {doc['title']}\n"
            if doc.get('author'):
                display_text += f"• **Author:** {doc['author']}\n"
            if doc.get('subject'):
                display_text += f"• **Subject:** {doc['subject']}\n"
            display_text += "\n"
        
        return display_text
        
    except Exception as e:
        logger.error(f"Error formatting metadata display: {e}")
        return f"🏷️ **Metadata for {filename}**\n\n❌ Error formatting metadata display."

def get_metadata_variables(metadata: Dict[str, Any]) -> Dict[str, str]:
    """Extract variables from metadata for template use"""
    try:
        variables = {}
        
        # Basic variables
        if metadata.get('basic'):
            basic = metadata['basic']
            variables.update({
                'metadata.filename': basic.get('filename', ''),
                'metadata.size': format_file_size(basic.get('size', 0)),
                'metadata.type': basic.get('type', ''),
                'metadata.extension': basic.get('extension', '')
            })
        
        # Video variables
        if metadata.get('video'):
            video = metadata['video']
            variables.update({
                'metadata.duration': str(int(video.get('duration', 0))),
                'metadata.resolution': video.get('resolution', ''),
                'metadata.quality': video.get('quality', ''),
                'metadata.fps': str(video.get('fps', '')),
                'metadata.codec': video.get('codec', '')
            })
        
        # Audio variables
        if metadata.get('audio'):
            audio = metadata['audio']
            variables.update({
                'metadata.title': audio.get('title', ''),
                'metadata.artist': audio.get('artist', ''),
                'metadata.album': audio.get('album', ''),
                'metadata.genre': audio.get('genre', ''),
                'metadata.year': audio.get('year', ''),
                'metadata.track': audio.get('track_number', ''),
                'metadata.bitrate': str(audio.get('bitrate', '')),
                'metadata.sample_rate': str(audio.get('sample_rate', ''))
            })
        
        return variables
        
    except Exception as e:
        logger.error(f"Error extracting metadata variables: {e}")
        return {}