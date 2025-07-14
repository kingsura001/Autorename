#!/usr/bin/env python3

"""
Telegram File Renaming Bot - Main Application
A comprehensive bot for automated file renaming and media processing
"""

import os
import logging
import asyncio
import signal
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from database.connection import init_database, close_database
from handlers import (
    start, settings, files, admin, subscription, thumbnails, autorename,
    caption, replace, metadata, mode, preview, settemplate, banner, leaderboard
)
from middleware.subscription_check import subscription_required
from utils.logger import setup_logger

# Setup logging
setup_logger()
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.config = Config()
        self.application = None
        self._shutdown_event = asyncio.Event()

    async def setup_application(self):
        """Initialize the Telegram bot application"""
        try:
            self.application = Application.builder().token(self.config.BOT_TOKEN).build()
            
            # Initialize database
            await init_database()
            
            # Register handlers
            self.register_handlers()
            
            logger.info("Bot application setup completed")
        except Exception as e:
            logger.error(f"Failed to setup application: {e}")
            raise

    def register_handlers(self):
        """Register all command and message handlers"""
        app = self.application

        # Command handlers
        app.add_handler(CommandHandler("start", start.start_command))
        app.add_handler(CommandHandler("settings", settings.settings_command))
        app.add_handler(CommandHandler("about", start.about_command))
        app.add_handler(CommandHandler("help", start.help_command))
        app.add_handler(CommandHandler("autorename", autorename.autorename_command))
        app.add_handler(CommandHandler("thumbnail", thumbnails.thumbnail_command))
        app.add_handler(CommandHandler("mythumbnails", thumbnails.list_thumbnails_command))
        app.add_handler(CommandHandler("premium", subscription.premium_command))
        app.add_handler(CommandHandler("referral", subscription.referral_command))

        # New feature commands
        app.add_handler(CommandHandler("caption", caption.caption_command))
        app.add_handler(CommandHandler("replace", replace.replace_command))
        app.add_handler(CommandHandler("setreplace", replace.setreplace_command))
        app.add_handler(CommandHandler("metadata", metadata.metadata_command))
        app.add_handler(CommandHandler("mode", mode.mode_command))
        app.add_handler(CommandHandler("manual", mode.manual_command))
        app.add_handler(CommandHandler("preview", preview.preview_command))
        app.add_handler(CommandHandler("settemplate", settemplate.settemplate_command))
        app.add_handler(CommandHandler("banner", banner.banner_command))
        app.add_handler(CommandHandler("leaderboard", leaderboard.leaderboard_command))

        # Admin commands
        app.add_handler(CommandHandler("admin", admin.admin_panel_command))
        app.add_handler(CommandHandler("broadcast", admin.broadcast_command))
        app.add_handler(CommandHandler("stats", admin.stats_command))
        app.add_handler(CommandHandler("addchannel", admin.add_channel_command))
        app.add_handler(CommandHandler("removechannel", admin.remove_channel_command))
        app.add_handler(CommandHandler("addpremium", admin.add_premium_command))
        app.add_handler(CommandHandler("removepremium", admin.remove_premium_command))

        # Callback query handlers
        app.add_handler(CallbackQueryHandler(settings.settings_callback, pattern="^settings_"))
        app.add_handler(CallbackQueryHandler(thumbnails.thumbnail_callback, pattern="^thumb_"))
        app.add_handler(CallbackQueryHandler(autorename.autorename_callback, pattern="^autorename_"))
        app.add_handler(CallbackQueryHandler(subscription.subscription_callback, pattern="^sub_"))
        app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern="^admin_"))
        app.add_handler(CallbackQueryHandler(caption.caption_callback, pattern="^caption_"))
        app.add_handler(CallbackQueryHandler(replace.replace_callback, pattern="^replace_"))
        app.add_handler(CallbackQueryHandler(metadata.metadata_callback, pattern="^metadata_"))
        app.add_handler(CallbackQueryHandler(mode.mode_callback, pattern="^mode_"))
        app.add_handler(CallbackQueryHandler(preview.preview_callback, pattern="^preview_"))
        app.add_handler(CallbackQueryHandler(settemplate.template_callback, pattern="^template_"))
        app.add_handler(CallbackQueryHandler(banner.banner_callback, pattern="^banner_"))
        app.add_handler(CallbackQueryHandler(leaderboard.leaderboard_callback, pattern="^leaderboard_"))

        # File handlers
        app.add_handler(MessageHandler(filters.Document.ALL, files.handle_document))
        app.add_handler(MessageHandler(filters.VIDEO, files.handle_video))
        app.add_handler(MessageHandler(filters.AUDIO, files.handle_audio))
        app.add_handler(MessageHandler(filters.PHOTO, thumbnails.handle_thumbnail_upload))

        # Text message handlers
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, files.handle_rename_text))

        # Error handler
        app.add_error_handler(self.error_handler)

        logger.info("All handlers registered successfully")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors that occur during bot operation"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred while processing your request. "
                    "Please try again later or contact support."
                )
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")

    async def shutdown(self):
        """Gracefully shutdown the bot"""
        try:
            logger.info("Shutting down bot...")
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
            await close_database()
            logger.info("Bot shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def run(self):
        """Start the bot"""
        try:
            await self.setup_application()
            
            logger.info("Starting bot...")
            
            # Initialize and start the application
            await self.application.initialize()
            await self.application.start()
            
            # Start polling
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise
        finally:
            await self.shutdown()

# Global bot instance
bot = TelegramBot()

async def main():
    """Main entry point"""
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

def start_bot():
    """Start the bot - handles event loop properly"""
    try:
        # Check if we're in an existing event loop
        try:
            loop = asyncio.get_running_loop()
            logger.info("Running in existing event loop")
            # Create a task in the existing loop
            task = loop.create_task(main())
            # Wait for the task to complete
            return task
        except RuntimeError:
            # No existing loop, create new one
            logger.info("Creating new event loop")
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_bot()
