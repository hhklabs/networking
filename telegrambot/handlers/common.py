"""Common handlers: /start and /help commands."""

from telegram import Update
from telegram.ext import ContextTypes

from telegrambot.constants.emojis import (
    TG_EMOJI_ADGUARD,
    TG_EMOJI_GLOBE,
    TG_EMOJI_IPV6,
    TG_EMOJI_RPI,
)
from telegrambot.core.config import check_authorization
from telegrambot.ui.main_keyboard import MAIN_KEYBOARD


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None:
        return

    if not check_authorization(update.effective_user.id):
        if update.message is not None:
            await update.message.reply_text(
                "⛔️ <b>Access Denied</b>\n\n"
                f"Your Telegram User ID is <code>{update.effective_user.id}</code>.\n"
                "To control this hotspot, add your User ID to "
                "<code>TELEGRAM_ALLOWED_USERS</code> in your <code>.env</code> file.",
                parse_mode="HTML",
            )
        return

    help_text = (
        f"<b>{TG_EMOJI_RPI} GoodWifi Hotspot Manager</b>\n\n"
        f"<b>Available Commands:</b>\n"
        f"• <code>status</code> - Show hotspot and VPN status\n"
        f"• <code>switch_vpn &lt;sing0|awg0|tun0|wg0|auto&gt;</code> - "
        f"Switch active VPN backend\n"
        f"• {TG_EMOJI_GLOBE} <code>country &lt;sg|jp|direct&gt;</code> - "
        f"Switch exit country\n"
        f"• {TG_EMOJI_IPV6} <code>ipv6 &lt;drop|reject|off&gt;</code> - "
        f"Configure IPv6 leak protection\n"
        f"• {TG_EMOJI_ADGUARD} <code>adguard &lt;on|off|restart&gt;</code> - "
        f"Toggle AdGuard Home service\n"
        f"• <code>restart</code> - Restart hotspot services\n"
        f"• <code>restart_vpn</code> - Restart VPN connection\n"
        f"• <code>fix</code> - Auto-fix common issues\n"
        f"• <code>clients</code> - Show connected clients\n"
        f"• <code>users</code> - Manage VPN profiles (iOS & Android)\n"
        f"• <code>adduser &lt;name&gt; [pass]</code> - Add client profile\n"
        f"• <code>pause / resume &lt;name&gt;</code> - Pause/resume client access\n"
        f"• <code>deluser &lt;name&gt;</code> - Delete client profile\n"
        f"• <code>get &lt;name&gt;</code> - Redownload client profile\n"
        f"• <code>help</code> - Show this help message\n\n"
        f"<b>Usage:</b> Send command as plain text (no / needed)"
    )

    if update.message is not None:
        await update.message.reply_text(
            help_text, reply_markup=MAIN_KEYBOARD, parse_mode="HTML"
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for /start command."""
    if update.effective_user is None:
        return
    await help_command(update, context)
