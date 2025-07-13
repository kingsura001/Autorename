"""
Admin panel and management functions
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import Config
from database.connection import db
from database.models import ForceSubChannel
from utils.helpers import format_file_size, is_admin

logger = logging.getLogger(__name__)

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to access admin panel.")
        return
    
    try:
        await show_admin_panel(update, context)
    except Exception as e:
        logger.error(f"Error in admin panel: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading admin panel."
        )

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main admin panel"""
    try:
        # Get bot statistics
        stats = await db.get_bot_stats()
        
        admin_text = f"""
🔧 **Admin Panel**

📊 **Bot Statistics:**
• Total Users: {stats.total_users:,}
• Active Today: {stats.active_users_today:,}
• Active This Week: {stats.active_users_week:,}
• Premium Users: {stats.premium_users:,}
• Files Processed: {stats.total_files_processed:,}
• Files Today: {stats.files_processed_today:,}

⏰ **Last Updated:** {stats.last_updated.strftime('%Y-%m-%d %H:%M:%S')}

🔧 **Admin Functions:**
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📺 Manage Channels", callback_data="admin_channels")],
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("🔄 Update Stats", callback_data="admin_update_stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                admin_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                admin_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing admin panel: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading admin panel."
        )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ Access denied.")
        return
    
    action = query.data.replace("admin_", "")
    
    try:
        if action == "main":
            await show_admin_panel(update, context)
        
        elif action == "stats":
            await show_detailed_stats(update, context)
        
        elif action == "broadcast":
            await show_broadcast_menu(update, context)
        
        elif action == "channels":
            await show_channels_menu(update, context)
        
        elif action == "users":
            await show_users_menu(update, context)
        
        elif action == "update_stats":
            await update_bot_stats(update, context)
        
        elif action.startswith("channel_"):
            await handle_channel_action(update, context, action)
        
        elif action.startswith("user_"):
            await handle_user_action(update, context, action)
            
    except Exception as e:
        logger.error(f"Error in admin callback: {e}")
        await query.edit_message_text(
            "❌ An error occurred while processing your request."
        )

async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed bot statistics"""
    try:
        stats = await db.get_bot_stats()
        
        # Get additional stats
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # This would require additional database queries in a real implementation
        stats_text = f"""
📊 **Detailed Bot Statistics**

👥 **User Statistics:**
• Total Users: {stats.total_users:,}
• Active Today: {stats.active_users_today:,}
• Active This Week: {stats.active_users_week:,}
• Premium Users: {stats.premium_users:,}
• New Users Today: Calculating...
• New Users This Week: Calculating...

📁 **File Statistics:**
• Total Files Processed: {stats.total_files_processed:,}
• Files Processed Today: {stats.files_processed_today:,}
• Average File Size: Calculating...
• Most Popular File Type: Calculating...

💎 **Premium Statistics:**
• Premium Conversion Rate: Calculating...
• Active Premium Users: {stats.premium_users:,}
• Premium Revenue: Calculating...

📈 **Growth Statistics:**
• Daily Growth Rate: Calculating...
• Weekly Growth Rate: Calculating...
• Monthly Growth Rate: Calculating...

⏰ **Last Updated:** {stats.last_updated.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_update_stats")],
            [InlineKeyboardButton("📊 Export Data", callback_data="admin_export")],
            [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error showing detailed stats: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading detailed statistics."
        )

async def show_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show broadcast management menu"""
    broadcast_text = """
📢 **Broadcast Management**

Send a message to all bot users or specific groups.

⚠️ **Important:**
• Use broadcast responsibly
• Avoid spamming users
• Messages should be relevant and valuable

📝 **Broadcast Types:**
• All Users - Send to all registered users
• Premium Users - Send to premium users only
• Active Users - Send to users active in last 7 days
• Test Broadcast - Send to admins only

📋 **Instructions:**
1. Click the broadcast type below
2. Send your message in the next message
3. Confirm the broadcast
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 All Users", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("💎 Premium Users", callback_data="admin_broadcast_premium")],
        [InlineKeyboardButton("⚡ Active Users", callback_data="admin_broadcast_active")],
        [InlineKeyboardButton("🧪 Test Broadcast", callback_data="admin_broadcast_test")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        broadcast_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def show_channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show force subscription channels management"""
    try:
        channels = await db.get_force_sub_channels()
        
        channels_text = "📺 **Force Subscription Channels**\n\n"
        
        if channels:
            for i, channel in enumerate(channels, 1):
                status = "✅ Active" if channel.is_active else "❌ Inactive"
                channels_text += f"{i}. **{channel.channel_name}**\n"
                channels_text += f"   ID: `{channel.channel_id}`\n"
                channels_text += f"   Status: {status}\n\n"
        else:
            channels_text += "No force subscription channels configured.\n\n"
        
        channels_text += "🔧 **Management Options:**"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Channel", callback_data="admin_channel_add")],
            [InlineKeyboardButton("🗑️ Remove Channel", callback_data="admin_channel_remove")],
            [InlineKeyboardButton("✏️ Edit Channel", callback_data="admin_channel_edit")],
            [InlineKeyboardButton("🔄 Refresh List", callback_data="admin_channels")],
            [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            channels_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error showing channels menu: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading channels."
        )

async def show_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management menu"""
    users_text = """
👥 **User Management**

Manage bot users, view user details, and perform administrative actions.

🔧 **Available Actions:**
• View user details
• Ban/Unban users
• Grant/Revoke premium
• View user statistics
• Export user data

📝 **Instructions:**
Send a user ID or username to view user details, or use the options below.
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Recent Users", callback_data="admin_users_recent")],
        [InlineKeyboardButton("🚫 Banned Users", callback_data="admin_users_banned")],
        [InlineKeyboardButton("💎 Premium Users", callback_data="admin_users_premium")],
        [InlineKeyboardButton("🔍 Search User", callback_data="admin_users_search")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        users_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 **Broadcast Command Usage:**\n\n"
            "`/broadcast <message>`\n\n"
            "**Example:**\n"
            "`/broadcast Hello everyone! New features are now available.`"
        )
        return
    
    message = " ".join(context.args)
    
    try:
        # This would implement actual broadcasting logic
        await update.message.reply_text(
            f"📢 **Broadcast Preview:**\n\n"
            f"{message}\n\n"
            "⚠️ This is a preview. Use the admin panel to send actual broadcasts."
        )
        
    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while preparing the broadcast."
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    try:
        stats = await db.get_bot_stats()
        
        stats_text = f"""
📊 **Quick Bot Statistics**

👥 **Users:** {stats.total_users:,}
⚡ **Active Today:** {stats.active_users_today:,}
💎 **Premium:** {stats.premium_users:,}
📁 **Files Processed:** {stats.total_files_processed:,}
📈 **Files Today:** {stats.files_processed_today:,}

⏰ **Last Updated:** {stats.last_updated.strftime('%H:%M:%S')}
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading statistics."
        )

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addchannel command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "📺 **Add Channel Command Usage:**\n\n"
            "`/addchannel <channel_id> <channel_name>`\n\n"
            "**Example:**\n"
            "`/addchannel @mychannel My Channel`\n"
            "`/addchannel -1001234567890 My Private Channel`"
        )
        return
    
    channel_id = context.args[0]
    channel_name = " ".join(context.args[1:])
    
    try:
        # Create channel object
        channel = ForceSubChannel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_username=channel_id if channel_id.startswith('@') else None
        )
        
        # Add to database
        success = await db.add_force_sub_channel(channel)
        
        if success:
            await update.message.reply_text(
                f"✅ **Channel Added Successfully**\n\n"
                f"**Name:** {channel_name}\n"
                f"**ID:** `{channel_id}`\n\n"
                "Users will now be required to join this channel."
            )
        else:
            await update.message.reply_text(
                "❌ Failed to add channel. It may already exist."
            )
            
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        await update.message.reply_text(
            "❌ An error occurred while adding the channel."
        )

async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removechannel command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📺 **Remove Channel Command Usage:**\n\n"
            "`/removechannel <channel_id>`\n\n"
            "**Example:**\n"
            "`/removechannel @mychannel`\n"
            "`/removechannel -1001234567890`"
        )
        return
    
    channel_id = context.args[0]
    
    try:
        # Remove from database
        success = await db.remove_force_sub_channel(channel_id)
        
        if success:
            await update.message.reply_text(
                f"✅ **Channel Removed Successfully**\n\n"
                f"**ID:** `{channel_id}`\n\n"
                "Users will no longer be required to join this channel."
            )
        else:
            await update.message.reply_text(
                "❌ Channel not found or already removed."
            )
            
    except Exception as e:
        logger.error(f"Error removing channel: {e}")
        await update.message.reply_text(
            "❌ An error occurred while removing the channel."
        )

async def update_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update bot statistics"""
    try:
        stats = await db.get_bot_stats()
        
        await update.callback_query.edit_message_text(
            f"✅ **Statistics Updated**\n\n"
            f"**Total Users:** {stats.total_users:,}\n"
            f"**Active Today:** {stats.active_users_today:,}\n"
            f"**Files Processed:** {stats.total_files_processed:,}\n\n"
            f"**Updated:** {stats.last_updated.strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_main")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error updating stats: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while updating statistics."
        )

async def handle_channel_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Handle channel-related actions"""
    # Implementation for channel management actions
    pass

async def add_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addpremium command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "💎 **Add Premium Command Usage:**\n\n"
            "`/addpremium <user_id> <hours>`\n\n"
            "**Example:**\n"
            "`/addpremium 123456789 24`\n"
            "`/addpremium 987654321 168`  # 1 week"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        hours = int(context.args[1])
        
        # Get user
        user = await db.get_user(target_user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            return
        
        # Calculate new expiry time
        from datetime import datetime, timedelta
        
        current_time = datetime.now()
        if user.premium_expires and user.premium_expires > current_time:
            new_expiry = user.premium_expires + timedelta(hours=hours)
        else:
            new_expiry = current_time + timedelta(hours=hours)
        
        # Update user
        await db.update_user(target_user_id, {
            'is_premium': True,
            'premium_expires': new_expiry
        })
        
        username = user.username or f"User{target_user_id}"
        await update.message.reply_text(
            f"✅ **Premium Added Successfully**\n\n"
            f"**User:** {username}\n"
            f"**ID:** `{target_user_id}`\n"
            f"**Hours Added:** {hours}\n"
            f"**Expires:** {new_expiry.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or hours value.")
    except Exception as e:
        logger.error(f"Error adding premium: {e}")
        await update.message.reply_text("❌ An error occurred while adding premium.")

async def remove_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removepremium command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "💎 **Remove Premium Command Usage:**\n\n"
            "`/removepremium <user_id>`\n\n"
            "**Example:**\n"
            "`/removepremium 123456789`"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        # Get user
        user = await db.get_user(target_user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            return
        
        # Remove premium
        await db.update_user(target_user_id, {
            'is_premium': False,
            'premium_expires': None
        })
        
        username = user.username or f"User{target_user_id}"
        await update.message.reply_text(
            f"✅ **Premium Removed Successfully**\n\n"
            f"**User:** {username}\n"
            f"**ID:** `{target_user_id}`\n\n"
            "User's premium access has been revoked."
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
    except Exception as e:
        logger.error(f"Error removing premium: {e}")
        await update.message.reply_text("❌ An error occurred while removing premium.")

async def handle_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Handle user-related actions"""
    # Implementation for user management actions
    pass
