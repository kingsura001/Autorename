"""
Subscription and premium features handler
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from database.models import User
from utils.helpers import generate_referral_code
from middleware.subscription_check import check_force_subscription

logger = logging.getLogger(__name__)

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /premium command"""
    user_id = update.effective_user.id
    
    try:
        # Check force subscription first
        if not await check_force_subscription(user_id, context):
            keyboard = [[InlineKeyboardButton("🔄 Check Subscription", callback_data="sub_check")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🚫 **Access Restricted**\n\n"
                "Please join our required channels to access premium features.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return
        
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please start the bot first.")
            return
        
        await show_premium_menu(update, context, user)
        
    except Exception as e:
        logger.error(f"Error in premium command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading premium features."
        )

async def show_premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Show premium features menu"""
    try:
        is_premium = user.is_premium_active()
        
        if is_premium:
            premium_text = f"""
💎 **Premium Status: ACTIVE**

✅ **Your Premium Benefits:**
• 📁 Unlimited file processing
• 🚀 Priority processing queue
• 🎨 Custom thumbnails
• ⚡ Advanced auto-rename features
• 📊 Detailed processing statistics
• 🔧 Advanced settings options
• 🎯 Batch file processing
• 💾 Extended file storage

⏰ **Premium Valid Until:** {user.premium_expires.strftime('%Y-%m-%d %H:%M:%S') if user.premium_expires else 'Lifetime'}

🎁 **Invite Friends:**
Share your referral link and get premium extensions!
            """
            
            keyboard = [
                [InlineKeyboardButton("🔗 Get Referral Link", callback_data="sub_referral")],
                [InlineKeyboardButton("📊 Premium Stats", callback_data="sub_stats")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
            ]
        else:
            premium_text = f"""
💎 **Upgrade to Premium**

🚀 **Premium Features:**
• 📁 **Unlimited Processing** - No daily limits
• 🎨 **Custom Thumbnails** - Add your own thumbnails
• ⚡ **Priority Queue** - Faster processing
• 🔧 **Advanced Settings** - More customization options
• 📊 **Detailed Statistics** - Track your usage
• 🎯 **Batch Processing** - Process multiple files
• 💾 **Extended Storage** - Keep files longer
• 🔄 **Auto-Rename Plus** - Advanced templates

💰 **Pricing:**
• 1 Month: $4.99
• 3 Months: $12.99 (Save 13%)
• 6 Months: $22.99 (Save 23%)
• 1 Year: $39.99 (Save 33%)

🎁 **Get Premium Free:**
Refer friends and get premium extensions!
            """
            
            keyboard = [
                [InlineKeyboardButton("💳 1 Month - $4.99", callback_data="sub_buy_1m")],
                [InlineKeyboardButton("💳 3 Months - $12.99", callback_data="sub_buy_3m")],
                [InlineKeyboardButton("💳 6 Months - $22.99", callback_data="sub_buy_6m")],
                [InlineKeyboardButton("💳 1 Year - $39.99", callback_data="sub_buy_1y")],
                [InlineKeyboardButton("🎁 Get Free Premium", callback_data="sub_referral")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                premium_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                premium_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing premium menu: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading premium information."
        )

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /referral command"""
    user_id = update.effective_user.id
    
    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please start the bot first.")
            return
        
        await show_referral_info(update, context, user)
        
    except Exception as e:
        logger.error(f"Error in referral command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading referral information."
        )

async def show_referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Show referral information"""
    try:
        # Get referral statistics
        # This would require additional database queries in a real implementation
        referral_count = 0  # Number of users referred
        premium_earned = 0  # Premium days earned
        
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.referral_code}"
        
        referral_text = f"""
🎁 **Referral Program**

**Your Referral Code:** `{user.referral_code}`
**Your Referral Link:** {referral_link}

📊 **Your Referral Stats:**
• Total Referrals: {referral_count}
• Premium Days Earned: {premium_earned}
• Current Premium Status: {'✅ Active' if user.is_premium_active() else '❌ Inactive'}

🎯 **How it Works:**
1. Share your referral link with friends
2. When they start the bot, you both get benefits
3. You get 30 days of premium for each referral
4. Your friends get 7 days of premium bonus

💡 **Tips to Get More Referrals:**
• Share in groups and channels
• Tell friends about the bot's features
• Post on social media
• Help others with file processing

🎁 **Referral Rewards:**
• 1 Referral = 30 days premium
• 5 Referrals = 6 months premium
• 10 Referrals = 1 year premium
• 25 Referrals = Lifetime premium
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Link", callback_data="sub_copy_link")],
            [InlineKeyboardButton("📤 Share Link", callback_data="sub_share_link")],
            [InlineKeyboardButton("📊 Referral Stats", callback_data="sub_referral_stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                referral_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                referral_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing referral info: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading referral information."
        )

async def subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data.replace("sub_", "")
    
    try:
        user = await db.get_user(user_id)
        if not user:
            await query.edit_message_text("❌ User not found. Please start the bot first.")
            return
        
        if action == "premium":
            await show_premium_menu(update, context, user)
        
        elif action == "referral":
            await show_referral_info(update, context, user)
        
        elif action == "check":
            await check_subscription_status(update, context, user_id)
        
        elif action.startswith("buy_"):
            await handle_premium_purchase(update, context, action, user)
        
        elif action == "copy_link":
            await handle_copy_referral_link(update, context, user)
        
        elif action == "share_link":
            await handle_share_referral_link(update, context, user)
        
        elif action == "stats":
            await show_premium_stats(update, context, user)
        
        elif action == "referral_stats":
            await show_referral_stats(update, context, user)
            
    except Exception as e:
        logger.error(f"Error in subscription callback: {e}")
        await query.edit_message_text(
            "❌ An error occurred while processing your request."
        )

async def check_subscription_status(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Check user's subscription status to required channels"""
    try:
        channels = await db.get_force_sub_channels()
        
        if not channels:
            await update.callback_query.edit_message_text(
                "✅ **No Subscription Required**\n\n"
                "You can use the bot without any restrictions!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")
                ]])
            )
            return
        
        not_subscribed = []
        
        for channel in channels:
            try:
                member = await context.bot.get_chat_member(channel.channel_id, user_id)
                if member.status in ['left', 'kicked']:
                    not_subscribed.append(channel)
            except Exception:
                # If we can't check, assume not subscribed
                not_subscribed.append(channel)
        
        if not_subscribed:
            channels_text = "🚫 **Subscription Required**\n\n"
            channels_text += "Please join these channels to use the bot:\n\n"
            
            keyboard = []
            for channel in not_subscribed:
                if channel.channel_username:
                    keyboard.append([InlineKeyboardButton(
                        f"📺 Join {channel.channel_name}",
                        url=f"https://t.me/{channel.channel_username.replace('@', '')}"
                    )])
                else:
                    keyboard.append([InlineKeyboardButton(
                        f"📺 Join {channel.channel_name}",
                        url=f"https://t.me/c/{channel.channel_id.replace('-100', '')}"
                    )])
            
            keyboard.append([InlineKeyboardButton("🔄 Check Again", callback_data="sub_check")])
            
            await update.callback_query.edit_message_text(
                channels_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.callback_query.edit_message_text(
                "✅ **Subscription Verified**\n\n"
                "Welcome! You can now use all bot features.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Main Menu", callback_data="start_main")
                ]])
            )
            
    except Exception as e:
        logger.error(f"Error checking subscription status: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while checking your subscription status."
        )

async def handle_premium_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, user: User):
    """Handle premium purchase requests"""
    try:
        duration_map = {
            "buy_1m": ("1 Month", "$4.99", 30),
            "buy_3m": ("3 Months", "$12.99", 90),
            "buy_6m": ("6 Months", "$22.99", 180),
            "buy_1y": ("1 Year", "$39.99", 365)
        }
        
        if action not in duration_map:
            await update.callback_query.edit_message_text("❌ Invalid purchase option.")
            return
        
        duration, price, days = duration_map[action]
        
        purchase_text = f"""
💳 **Premium Purchase**

**Package:** {duration}
**Price:** {price}
**Duration:** {days} days

⚠️ **Payment Instructions:**
This is a demo implementation. In a real bot, you would:
1. Integrate with payment providers (Stripe, PayPal, etc.)
2. Handle payment verification
3. Activate premium automatically

For now, contact an admin to upgrade your account.
        """
        
        keyboard = [
            [InlineKeyboardButton("💬 Contact Admin", url="https://t.me/YourAdminUsername")],
            [InlineKeyboardButton("⬅️ Back to Premium", callback_data="sub_premium")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            purchase_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error handling premium purchase: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while processing your purchase request."
        )

async def handle_copy_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Handle copy referral link request"""
    try:
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.referral_code}"
        
        await update.callback_query.edit_message_text(
            f"📋 **Referral Link Copied**\n\n"
            f"`{referral_link}`\n\n"
            f"Share this link with your friends to earn premium time!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Referral", callback_data="sub_referral")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error copying referral link: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while copying your referral link."
        )

async def handle_share_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Handle share referral link request"""
    try:
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.referral_code}"
        
        share_text = f"""
🤖 **Check out this amazing File Rename Bot!**

I've been using this bot to rename and process my files - it's incredible!

✨ **Features:**
• Rename files with custom templates
• Add custom thumbnails
• Process files up to 5GB
• Auto-rename functionality
• Premium features available

🎁 **Join using my referral link and get premium bonus:**
{referral_link}

Try it now! 🚀
        """
        
        await update.callback_query.edit_message_text(
            f"📤 **Share This Message**\n\n"
            f"Copy and share this message with your friends:\n\n"
            f"```\n{share_text}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Referral", callback_data="sub_referral")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error sharing referral link: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while preparing your referral message."
        )

async def show_premium_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Show premium user statistics"""
    try:
        # Get user's file processing stats
        file_records = await db.get_user_file_records(user.user_id, limit=1000)
        
        total_files = len(file_records)
        completed_files = len([r for r in file_records if r.processing_status == "completed"])
        failed_files = len([r for r in file_records if r.processing_status == "failed"])
        
        # Calculate total file size processed
        total_size = sum(r.file_size for r in file_records)
        
        stats_text = f"""
📊 **Your Premium Statistics**

🎯 **Processing Stats:**
• Total Files Processed: {total_files:,}
• Successfully Completed: {completed_files:,}
• Failed Processing: {failed_files:,}
• Success Rate: {(completed_files/total_files*100):.1f}% if total_files > 0 else 0%

💾 **Data Usage:**
• Total Data Processed: {format_file_size(total_size)}
• Average File Size: {format_file_size(total_size/total_files) if total_files > 0 else '0 B'}

💎 **Premium Status:**
• Status: {'✅ Active' if user.is_premium_active() else '❌ Inactive'}
• Valid Until: {user.premium_expires.strftime('%Y-%m-%d') if user.premium_expires else 'Lifetime'}
• Referrals Made: Calculating...

📈 **Recent Activity:**
• Files This Week: {len([r for r in file_records if (datetime.now() - r.created_at).days <= 7])}
• Files This Month: {len([r for r in file_records if (datetime.now() - r.created_at).days <= 30])}
        """
        
        keyboard = [
            [InlineKeyboardButton("📁 Recent Files", callback_data="sub_recent_files")],
            [InlineKeyboardButton("⬅️ Back to Premium", callback_data="sub_premium")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error showing premium stats: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading your statistics."
        )

async def show_referral_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Show detailed referral statistics"""
    try:
        # This would require additional database queries in a real implementation
        referral_stats_text = f"""
📊 **Detailed Referral Statistics**

🎯 **Referral Performance:**
• Total Referrals: 0
• Active Referrals: 0
• Premium Referrals: 0
• Referral Conversion Rate: 0%

💰 **Earnings:**
• Premium Days Earned: 0
• Current Premium Status: {'✅ Active' if user.is_premium_active() else '❌ Inactive'}
• Next Milestone: 1 referral for 30 days premium

📈 **Progress:**
• Progress to Next Reward: 0/1 referrals
• Progress to Lifetime Premium: 0/25 referrals

🎁 **Referral Rewards:**
• 1 Referral = 30 days premium
• 5 Referrals = 6 months premium
• 10 Referrals = 1 year premium
• 25 Referrals = Lifetime premium

**Your Referral Code:** `{user.referral_code}`
        """
        
        keyboard = [
            [InlineKeyboardButton("🔗 Get Referral Link", callback_data="sub_copy_link")],
            [InlineKeyboardButton("⬅️ Back to Referral", callback_data="sub_referral")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            referral_stats_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error showing referral stats: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred while loading your referral statistics."
        )

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"
