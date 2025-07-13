"""
Text replacement functionality for file renaming
"""

import logging
import json
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.connection import db
from middleware.auth import require_auth
from middleware.subscription_check import subscription_required

logger = logging.getLogger(__name__)

@require_auth
@subscription_required
async def replace_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /replace command"""
    user_id = update.effective_user.id
    
    try:
        await show_replace_menu(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in replace command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading text replacement settings."
        )

@require_auth
@subscription_required
async def setreplace_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setreplace command"""
    user_id = update.effective_user.id
    
    try:
        if context.args and len(context.args) >= 2:
            # Direct command usage: /setreplace "old text" "new text"
            old_text = context.args[0]
            new_text = context.args[1]
            await add_replace_rule(update, context, user_id, old_text, new_text)
        else:
            # Show interactive menu
            await show_add_replace_rule(update, context, user_id)
    except Exception as e:
        logger.error(f"Error in setreplace command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while setting replacement rules."
        )

async def show_replace_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show text replacement main menu"""
    try:
        # Get current replacement rules
        settings = await db.get_user_settings(user_id)
        replace_rules = json.loads(getattr(settings, 'replace_rules', '[]'))
        
        message_text = "🔄 **Text Replacement Settings**\n\n"
        message_text += "Configure automatic text replacement in filenames.\n\n"
        
        if replace_rules:
            message_text += "**Active Rules:**\n"
            for i, rule in enumerate(replace_rules, 1):
                message_text += f"{i}. `{rule['old']}` → `{rule['new']}`\n"
        else:
            message_text += "**No replacement rules configured.**\n"
        
        message_text += "\n**Options:**\n"
        message_text += "• Add new replacement rule\n"
        message_text += "• Edit existing rules\n"
        message_text += "• Test replacement preview\n"
        message_text += "• Toggle replacement mode\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Rule", callback_data="replace_add")],
            [InlineKeyboardButton("📝 Edit Rules", callback_data="replace_edit")],
            [InlineKeyboardButton("🔄 Preview", callback_data="replace_preview")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="replace_settings")],
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
        logger.error(f"Error showing replace menu: {e}")
        await update.message.reply_text("❌ Error loading replacement settings.")

async def replace_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle replace callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        if data == "replace_add":
            await show_add_replace_rule(update, context, user_id)
        elif data == "replace_edit":
            await show_edit_replace_rules(update, context, user_id)
        elif data == "replace_preview":
            await show_replace_preview(update, context, user_id)
        elif data == "replace_settings":
            await show_replace_settings(update, context, user_id)
        elif data.startswith("replace_delete_"):
            rule_index = int(data.split("_")[2])
            await delete_replace_rule(update, context, user_id, rule_index)
        elif data.startswith("replace_toggle_"):
            rule_index = int(data.split("_")[2])
            await toggle_replace_rule(update, context, user_id, rule_index)
            
    except Exception as e:
        logger.error(f"Error handling replace callback: {e}")
        await query.edit_message_text("❌ Error processing replacement settings.")

async def show_add_replace_rule(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show add replacement rule interface"""
    try:
        add_text = "➕ **Add Replacement Rule**\n\n"
        add_text += "Create a new text replacement rule:\n\n"
        add_text += "**Format:** Send two messages:\n"
        add_text += "1. Text to replace (old text)\n"
        add_text += "2. Replacement text (new text)\n\n"
        add_text += "**Examples:**\n"
        add_text += "• Replace `.` with ` ` (spaces)\n"
        add_text += "• Replace `_` with ` ` (underscores to spaces)\n"
        add_text += "• Replace `HDTV` with `HD TV`\n"
        add_text += "• Replace `1080p` with `Full HD`\n\n"
        add_text += "**Quick Templates:**"
        
        keyboard = [
            [InlineKeyboardButton("📝 Custom Rule", callback_data="replace_custom")],
            [InlineKeyboardButton("🔹 . → (space)", callback_data="replace_quick_dot_space")],
            [InlineKeyboardButton("🔹 _ → (space)", callback_data="replace_quick_under_space")],
            [InlineKeyboardButton("🔹 Common Replacements", callback_data="replace_common")],
            [InlineKeyboardButton("🔙 Back", callback_data="replace_main")]
        ]
        
        await update.callback_query.edit_message_text(
            add_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing add replace rule: {e}")
        await update.callback_query.edit_message_text("❌ Error loading add rule interface.")

async def show_edit_replace_rules(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show edit replacement rules interface"""
    try:
        settings = await db.get_user_settings(user_id)
        replace_rules = json.loads(getattr(settings, 'replace_rules', '[]'))
        
        if not replace_rules:
            await update.callback_query.edit_message_text(
                "❌ No replacement rules found. Add some rules first!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Add Rule", callback_data="replace_add"),
                    InlineKeyboardButton("🔙 Back", callback_data="replace_main")
                ]])
            )
            return
        
        edit_text = "📝 **Edit Replacement Rules**\n\n"
        edit_text += "Select a rule to edit or delete:\n\n"
        
        keyboard = []
        for i, rule in enumerate(replace_rules):
            status = "✅" if rule.get('enabled', True) else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {rule['old']} → {rule['new']}", 
                    callback_data=f"replace_edit_{i}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="replace_main")])
        
        await update.callback_query.edit_message_text(
            edit_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing edit replace rules: {e}")
        await update.callback_query.edit_message_text("❌ Error loading edit interface.")

async def show_replace_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show replacement preview with examples"""
    try:
        settings = await db.get_user_settings(user_id)
        replace_rules = json.loads(getattr(settings, 'replace_rules', '[]'))
        
        if not replace_rules:
            await update.callback_query.edit_message_text(
                "❌ No replacement rules found. Add some rules first!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Add Rule", callback_data="replace_add"),
                    InlineKeyboardButton("🔙 Back", callback_data="replace_main")
                ]])
            )
            return
        
        preview_text = "🔄 **Replacement Preview**\n\n"
        preview_text += "Here's how your rules will transform filenames:\n\n"
        
        # Sample filenames for preview
        sample_files = [
            "Movie.Name.2024.1080p.BluRay.x264-GROUP",
            "TV_Show_S01E01_HDTV_720p",
            "Document.File.Name.with.dots.pdf",
            "Audio_Track_Name_192kbps.mp3"
        ]
        
        for sample in sample_files:
            transformed = apply_replace_rules(sample, replace_rules)
            preview_text += f"**Before:** `{sample}`\n"
            preview_text += f"**After:** `{transformed}`\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Test Custom", callback_data="replace_test_custom")],
            [InlineKeyboardButton("🔙 Back", callback_data="replace_main")]
        ]
        
        await update.callback_query.edit_message_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing replace preview: {e}")
        await update.callback_query.edit_message_text("❌ Error generating preview.")

async def show_replace_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show replacement settings"""
    try:
        settings = await db.get_user_settings(user_id)
        replace_enabled = getattr(settings, 'replace_enabled', True)
        case_sensitive = getattr(settings, 'replace_case_sensitive', False)
        
        settings_text = "⚙️ **Replacement Settings**\n\n"
        settings_text += "Configure how text replacement works:\n\n"
        
        settings_text += f"**Replacement Mode:** {'✅ Enabled' if replace_enabled else '❌ Disabled'}\n"
        settings_text += f"**Case Sensitive:** {'✅ Yes' if case_sensitive else '❌ No'}\n\n"
        
        settings_text += "**Options:**\n"
        settings_text += "• Toggle replacement on/off\n"
        settings_text += "• Enable/disable case sensitivity\n"
        settings_text += "• Clear all rules\n"
        
        keyboard = [
            [InlineKeyboardButton(
                "❌ Disable" if replace_enabled else "✅ Enable",
                callback_data="replace_toggle_enabled"
            )],
            [InlineKeyboardButton(
                "❌ Case Insensitive" if case_sensitive else "✅ Case Sensitive",
                callback_data="replace_toggle_case"
            )],
            [InlineKeyboardButton("🗑️ Clear All Rules", callback_data="replace_clear_all")],
            [InlineKeyboardButton("🔙 Back", callback_data="replace_main")]
        ]
        
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing replace settings: {e}")
        await update.callback_query.edit_message_text("❌ Error loading settings.")

async def add_replace_rule(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, old_text: str, new_text: str):
    """Add a new replacement rule"""
    try:
        settings = await db.get_user_settings(user_id)
        replace_rules = json.loads(getattr(settings, 'replace_rules', '[]'))
        
        # Check if rule already exists
        for rule in replace_rules:
            if rule['old'] == old_text:
                await update.message.reply_text(
                    f"❌ Rule for '{old_text}' already exists. Use edit to modify it."
                )
                return
        
        # Add new rule
        new_rule = {
            'old': old_text,
            'new': new_text,
            'enabled': True,
            'case_sensitive': False
        }
        replace_rules.append(new_rule)
        
        # Save to database
        await db.update_user_settings(user_id, {
            'replace_rules': json.dumps(replace_rules)
        })
        
        success_text = f"✅ **Replacement Rule Added**\n\n"
        success_text += f"**Replace:** `{old_text}`\n"
        success_text += f"**With:** `{new_text}`\n\n"
        success_text += "This rule will be applied to all future file uploads."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Preview", callback_data="replace_preview")],
            [InlineKeyboardButton("🏠 Back to Settings", callback_data="settings_main")]
        ]
        
        await update.message.reply_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} added replace rule: {old_text} → {new_text}")
        
    except Exception as e:
        logger.error(f"Error adding replace rule: {e}")
        await update.message.reply_text("❌ Error adding replacement rule.")

async def delete_replace_rule(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, rule_index: int):
    """Delete a replacement rule"""
    try:
        settings = await db.get_user_settings(user_id)
        replace_rules = json.loads(getattr(settings, 'replace_rules', '[]'))
        
        if 0 <= rule_index < len(replace_rules):
            deleted_rule = replace_rules.pop(rule_index)
            
            # Save to database
            await db.update_user_settings(user_id, {
                'replace_rules': json.dumps(replace_rules)
            })
            
            success_text = f"✅ **Rule Deleted**\n\n"
            success_text += f"Removed rule: `{deleted_rule['old']}` → `{deleted_rule['new']}`"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Rules", callback_data="replace_edit")]
            ]
            
            await update.callback_query.edit_message_text(
                success_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"User {user_id} deleted replace rule: {deleted_rule['old']} → {deleted_rule['new']}")
        else:
            await update.callback_query.edit_message_text("❌ Invalid rule index.")
            
    except Exception as e:
        logger.error(f"Error deleting replace rule: {e}")
        await update.callback_query.edit_message_text("❌ Error deleting rule.")

def apply_replace_rules(filename: str, replace_rules: List[Dict[str, Any]]) -> str:
    """Apply replacement rules to filename"""
    try:
        result = filename
        
        for rule in replace_rules:
            if not rule.get('enabled', True):
                continue
                
            old_text = rule['old']
            new_text = rule['new']
            case_sensitive = rule.get('case_sensitive', False)
            
            if case_sensitive:
                result = result.replace(old_text, new_text)
            else:
                # Case-insensitive replacement
                import re
                result = re.sub(re.escape(old_text), new_text, result, flags=re.IGNORECASE)
        
        return result
        
    except Exception as e:
        logger.error(f"Error applying replace rules: {e}")
        return filename

async def handle_replace_mode_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for replacement rules"""
    try:
        user_data = context.user_data
        
        if user_data.get('waiting_for_replace_old'):
            # First message - old text
            old_text = update.message.text.strip()
            user_data['replace_old_text'] = old_text
            user_data['waiting_for_replace_old'] = False
            user_data['waiting_for_replace_new'] = True
            
            await update.message.reply_text(
                f"✅ **Old text:** `{old_text}`\n\n"
                f"Now send the replacement text:"
            )
            
        elif user_data.get('waiting_for_replace_new'):
            # Second message - new text
            new_text = update.message.text.strip()
            old_text = user_data.get('replace_old_text', '')
            
            user_data['waiting_for_replace_new'] = False
            user_data.pop('replace_old_text', None)
            
            await add_replace_rule(update, context, update.effective_user.id, old_text, new_text)
            
    except Exception as e:
        logger.error(f"Error handling replace mode input: {e}")
        await update.message.reply_text("❌ Error processing replacement rule.")

def get_user_replace_rules(user_settings) -> List[Dict[str, Any]]:
    """Get user's replacement rules"""
    try:
        return json.loads(getattr(user_settings, 'replace_rules', '[]'))
    except:
        return []

def is_replace_mode_enabled(user_settings) -> bool:
    """Check if replacement mode is enabled"""
    return getattr(user_settings, 'replace_enabled', True)