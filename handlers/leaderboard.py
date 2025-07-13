"""
Leaderboard functionality for tracking user statistics
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from middleware.auth import require_auth
from utils.helpers import format_file_size

logger = logging.getLogger(__name__)

@require_auth
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard command"""
    user_id = update.effective_user.id
    
    try:
        await show_leaderboard_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in leaderboard command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading leaderboard."
        )

async def show_leaderboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show leaderboard menu"""
    try:
        message_text = "🏆 **Leaderboard**\n\n"
        message_text += "View rankings and statistics:\n\n"
        
        message_text += "**Available Rankings:**\n"
        message_text += "• 📊 Files Processed\n"
        message_text += "• 🔗 Referrals Made\n"
        message_text += "• 💎 Premium Users\n"
        message_text += "• 📈 Most Active Users\n"
        message_text += "• 🎯 Top Contributors\n\n"
        
        message_text += "**Time Periods:**\n"
        message_text += "• All Time\n"
        message_text += "• This Month\n"
        message_text += "• This Week\n"
        message_text += "• Today\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Files Processed", callback_data="leaderboard_files")],
            [InlineKeyboardButton("🔗 Referrals", callback_data="leaderboard_referrals")],
            [InlineKeyboardButton("💎 Premium Users", callback_data="leaderboard_premium")],
            [InlineKeyboardButton("📈 Most Active", callback_data="leaderboard_active")],
            [InlineKeyboardButton("👤 My Stats", callback_data="leaderboard_mystats")],
            [InlineKeyboardButton("🏠 Back", callback_data="start_menu")]
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
        logger.error(f"Error showing leaderboard menu: {e}")
        await update.message.reply_text("❌ Error loading leaderboard.")

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leaderboard callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data == "leaderboard_files":
            await show_files_leaderboard(update, context, user_id)
        elif data == "leaderboard_referrals":
            await show_referrals_leaderboard(update, context, user_id)
        elif data == "leaderboard_premium":
            await show_premium_leaderboard(update, context, user_id)
        elif data == "leaderboard_active":
            await show_active_leaderboard(update, context, user_id)
        elif data == "leaderboard_mystats":
            await show_user_stats(update, context, user_id)
        elif data.startswith("leaderboard_period_"):
            period = data.split("_")[2]
            category = data.split("_")[3]
            await show_period_leaderboard(update, context, user_id, period, category)
            
    except Exception as e:
        logger.error(f"Error handling leaderboard callback: {e}")
        await query.edit_message_text("❌ Error processing leaderboard.")

async def show_files_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show files processed leaderboard"""
    try:
        # Get top users by files processed
        top_users = await get_top_users_by_files()
        
        leaderboard_text = "📊 **Files Processed Leaderboard**\n\n"
        
        if not top_users:
            leaderboard_text += "No data available yet.\n"
            leaderboard_text += "Start processing files to appear on the leaderboard!"
        else:
            leaderboard_text += "**Top 10 Users by Files Processed:**\n\n"
            
            for i, user_data in enumerate(top_users[:10], 1):
                rank_emoji = get_rank_emoji(i)
                username = user_data.get('username', f"User{user_data['user_id']}")
                files_count = user_data.get('total_files_processed', 0)
                
                leaderboard_text += f"{rank_emoji} **{i}.** {username}\n"
                leaderboard_text += f"   Files: {files_count:,}\n\n"
        
        # Show user's position
        user_position = await get_user_position_files(user_id)
        if user_position:
            leaderboard_text += f"**Your Position:** #{user_position['position']}\n"
            leaderboard_text += f"**Your Files:** {user_position['files']:,}\n"
        
        keyboard = [
            [InlineKeyboardButton("📅 This Month", callback_data="leaderboard_period_month_files")],
            [InlineKeyboardButton("📅 This Week", callback_data="leaderboard_period_week_files")],
            [InlineKeyboardButton("📅 Today", callback_data="leaderboard_period_today_files")],
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ]
        
        await update.callback_query.edit_message_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing files leaderboard: {e}")
        await update.callback_query.edit_message_text("❌ Error loading files leaderboard.")

async def show_referrals_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show referrals leaderboard"""
    try:
        # Get top users by referrals
        top_referrers = await get_top_users_by_referrals()
        
        leaderboard_text = "🔗 **Referrals Leaderboard**\n\n"
        
        if not top_referrers:
            leaderboard_text += "No referrals yet.\n"
            leaderboard_text += "Share your referral link to earn premium time!"
        else:
            leaderboard_text += "**Top 10 Referrers:**\n\n"
            
            for i, user_data in enumerate(top_referrers[:10], 1):
                rank_emoji = get_rank_emoji(i)
                username = user_data.get('username', f"User{user_data['user_id']}")
                referral_count = user_data.get('referral_count', 0)
                premium_earned = referral_count * 3  # 3 hours per referral
                
                leaderboard_text += f"{rank_emoji} **{i}.** {username}\n"
                leaderboard_text += f"   Referrals: {referral_count}\n"
                leaderboard_text += f"   Premium Earned: {premium_earned}h\n\n"
        
        # Show user's referral stats
        user_referrals = await get_user_referral_stats(user_id)
        if user_referrals:
            leaderboard_text += f"**Your Referrals:** {user_referrals['count']}\n"
            leaderboard_text += f"**Premium Earned:** {user_referrals['count'] * 3}h\n"
        
        keyboard = [
            [InlineKeyboardButton("🔗 Get Referral Link", callback_data="referral_link")],
            [InlineKeyboardButton("📊 My Referrals", callback_data="my_referrals")],
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ]
        
        await update.callback_query.edit_message_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing referrals leaderboard: {e}")
        await update.callback_query.edit_message_text("❌ Error loading referrals leaderboard.")

async def show_premium_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show premium users leaderboard"""
    try:
        # Get premium users
        premium_users = await get_premium_users()
        
        leaderboard_text = "💎 **Premium Users**\n\n"
        
        if not premium_users:
            leaderboard_text += "No premium users yet.\n"
            leaderboard_text += "Upgrade to premium for exclusive features!"
        else:
            leaderboard_text += f"**Total Premium Users:** {len(premium_users)}\n\n"
            leaderboard_text += "**Recent Premium Users:**\n\n"
            
            for i, user_data in enumerate(premium_users[:10], 1):
                username = user_data.get('username', f"User{user_data['user_id']}")
                premium_since = user_data.get('premium_since', 'Unknown')
                
                leaderboard_text += f"💎 **{i}.** {username}\n"
                leaderboard_text += f"   Premium Since: {premium_since}\n\n"
        
        # Show user's premium status
        user = await db.get_user(user_id)
        if user and user.is_premium_active():
            expires = user.premium_expires.strftime("%Y-%m-%d %H:%M") if user.premium_expires else "Never"
            leaderboard_text += f"**Your Status:** 💎 Premium\n"
            leaderboard_text += f"**Expires:** {expires}\n"
        else:
            leaderboard_text += f"**Your Status:** 🆓 Free User\n"
        
        keyboard = [
            [InlineKeyboardButton("💎 Upgrade Premium", callback_data="premium_upgrade")],
            [InlineKeyboardButton("🔗 Refer Friends", callback_data="referral_link")],
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ]
        
        await update.callback_query.edit_message_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing premium leaderboard: {e}")
        await update.callback_query.edit_message_text("❌ Error loading premium leaderboard.")

async def show_active_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show most active users leaderboard"""
    try:
        # Get most active users (by recent activity)
        active_users = await get_most_active_users()
        
        leaderboard_text = "📈 **Most Active Users**\n\n"
        
        if not active_users:
            leaderboard_text += "No activity data available.\n"
        else:
            leaderboard_text += "**Most Active Users (Last 7 Days):**\n\n"
            
            for i, user_data in enumerate(active_users[:10], 1):
                rank_emoji = get_rank_emoji(i)
                username = user_data.get('username', f"User{user_data['user_id']}")
                activity_score = user_data.get('activity_score', 0)
                last_activity = user_data.get('last_activity', 'Unknown')
                
                leaderboard_text += f"{rank_emoji} **{i}.** {username}\n"
                leaderboard_text += f"   Activity Score: {activity_score}\n"
                leaderboard_text += f"   Last Active: {last_activity}\n\n"
        
        # Show user's activity
        user_activity = await get_user_activity_score(user_id)
        if user_activity:
            leaderboard_text += f"**Your Activity Score:** {user_activity['score']}\n"
            leaderboard_text += f"**Your Rank:** #{user_activity['rank']}\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Activity Details", callback_data="activity_details")],
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ]
        
        await update.callback_query.edit_message_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing active leaderboard: {e}")
        await update.callback_query.edit_message_text("❌ Error loading active users leaderboard.")

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show user's personal statistics"""
    try:
        # Get user data
        user = await db.get_user(user_id)
        user_stats = await get_detailed_user_stats(user_id)
        
        if not user or not user_stats:
            await update.callback_query.edit_message_text("❌ Unable to load your statistics.")
            return
        
        stats_text = f"👤 **Your Statistics**\n\n"
        
        # Basic info
        username = user.username or f"User{user_id}"
        stats_text += f"**Username:** {username}\n"
        stats_text += f"**Member Since:** {user.join_date.strftime('%Y-%m-%d')}\n"
        stats_text += f"**Premium Status:** {'💎 Premium' if user.is_premium_active() else '🆓 Free'}\n\n"
        
        # File statistics
        stats_text += "📊 **File Statistics:**\n"
        stats_text += f"• Total Files: {user_stats['total_files']:,}\n"
        stats_text += f"• This Month: {user_stats['files_this_month']:,}\n"
        stats_text += f"• This Week: {user_stats['files_this_week']:,}\n"
        stats_text += f"• Today: {user_stats['files_today']:,}\n\n"
        
        # Referral statistics
        stats_text += "🔗 **Referral Statistics:**\n"
        stats_text += f"• Total Referrals: {user_stats['referrals']:,}\n"
        stats_text += f"• Premium Earned: {user_stats['referrals'] * 3}h\n"
        stats_text += f"• Referred By: {user_stats['referred_by'] or 'None'}\n\n"
        
        # Rankings
        stats_text += "🏆 **Your Rankings:**\n"
        stats_text += f"• Files Processed: #{user_stats['files_rank']}\n"
        stats_text += f"• Referrals: #{user_stats['referrals_rank']}\n"
        stats_text += f"• Activity: #{user_stats['activity_rank']}\n\n"
        
        # Recent activity
        if user_stats['recent_files']:
            stats_text += "📋 **Recent Files:**\n"
            for file_info in user_stats['recent_files'][:3]:
                stats_text += f"• {file_info['name']} ({file_info['date']})\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Export Stats", callback_data="export_stats")],
            [InlineKeyboardButton("🔗 Share Stats", callback_data="share_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="leaderboard_main")]
        ]
        
        await update.callback_query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing user stats: {e}")
        await update.callback_query.edit_message_text("❌ Error loading your statistics.")

def get_rank_emoji(rank: int) -> str:
    """Get emoji for rank position"""
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    elif rank <= 10:
        return "🏆"
    else:
        return "📊"

async def get_top_users_by_files() -> List[Dict[str, Any]]:
    """Get top users by files processed"""
    try:
        # This would query the database for top users
        # For now, return mock data structure
        return []
    except Exception as e:
        logger.error(f"Error getting top users by files: {e}")
        return []

async def get_top_users_by_referrals() -> List[Dict[str, Any]]:
    """Get top users by referrals"""
    try:
        # This would query the database for top referrers
        return []
    except Exception as e:
        logger.error(f"Error getting top users by referrals: {e}")
        return []

async def get_premium_users() -> List[Dict[str, Any]]:
    """Get premium users"""
    try:
        # This would query the database for premium users
        return []
    except Exception as e:
        logger.error(f"Error getting premium users: {e}")
        return []

async def get_most_active_users() -> List[Dict[str, Any]]:
    """Get most active users"""
    try:
        # This would query the database for most active users
        return []
    except Exception as e:
        logger.error(f"Error getting most active users: {e}")
        return []

async def get_user_position_files(user_id: int) -> Dict[str, Any]:
    """Get user's position in files leaderboard"""
    try:
        user = await db.get_user(user_id)
        if user:
            return {
                'position': 1,  # This would be calculated from database
                'files': user.total_files_processed
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user position: {e}")
        return None

async def get_user_referral_stats(user_id: int) -> Dict[str, Any]:
    """Get user's referral statistics"""
    try:
        # This would query the database for user's referral stats
        return {'count': 0}
    except Exception as e:
        logger.error(f"Error getting user referral stats: {e}")
        return {'count': 0}

async def get_user_activity_score(user_id: int) -> Dict[str, Any]:
    """Get user's activity score"""
    try:
        # This would calculate activity score based on recent usage
        return {'score': 0, 'rank': 1}
    except Exception as e:
        logger.error(f"Error getting user activity score: {e}")
        return {'score': 0, 'rank': 1}

async def get_detailed_user_stats(user_id: int) -> Dict[str, Any]:
    """Get detailed user statistics"""
    try:
        user = await db.get_user(user_id)
        if not user:
            return None
        
        # Calculate various statistics
        stats = {
            'total_files': user.total_files_processed,
            'files_this_month': 0,  # Would be calculated from database
            'files_this_week': 0,   # Would be calculated from database
            'files_today': 0,       # Would be calculated from database
            'referrals': 0,         # Would be calculated from database
            'referred_by': None,    # Would be from user.referred_by
            'files_rank': 1,        # Would be calculated from database
            'referrals_rank': 1,    # Would be calculated from database
            'activity_rank': 1,     # Would be calculated from database
            'recent_files': []      # Would be from recent file records
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting detailed user stats: {e}")
        return None