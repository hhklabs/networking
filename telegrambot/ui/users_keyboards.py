"""Inline keyboard builders and formatters for VPN client users management."""

from typing import Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def format_user_card(u: dict[str, Any]) -> str:
    """Format rich HTML card for a VPN user."""
    uname = u.get("username", "Unknown")
    status = u.get("status", "active")
    badge = "🟢" if status == "active" else "⏸️"
    server = u.get("server", "connect.hhk.my.id")
    pwd = u.get("password", "")
    url = u.get("url", f"https://{server}/ios/{uname}.mobileconfig")

    return (
        f"👤 <b>VPN User: {uname}</b>\n"
        f"───────────────────────\n"
        f"🌐 <b>Server:</b> <code>{server}</code>\n"
        f"🔑 <b>Protocol:</b> <code>IKEv2 (MSCHAPv2 / EAP)</code>\n"
        f"👤 <b>Username:</b> <code>{uname}</code>\n"
        f"🔒 <b>Password:</b> <code>{pwd}</code>\n"
        f"📊 <b>Status:</b> {badge} {status.title()}\n"
        f"🔗 <b>Safari URL:</b> {url}\n"
        f"───────────────────────\n"
        f"🍏 <b>iOS:</b> <code>.mobileconfig</code> ဖိုင်ကို နှိပ်၍ သွင်းပါ\n"
        f"🤖 <b>Android:</b> Settings > VPN မှ Copy ရိုက်ထည့်၍ ချိတ်ပါ"
    )


def format_android_guide(u: dict[str, Any]) -> str:
    """Format copy-friendly Android setup instructions."""
    uname = u.get("username", "Unknown")
    server = u.get("server", "connect.hhk.my.id")
    pwd = u.get("password", "")
    return (
        f"🤖 <b>Android VPN တပ်ဆင်နည်း ({uname})</b>\n"
        f"───────────────────────\n"
        f"ဖုန်း <b>Settings > VPN</b> သို့သွားပြီး <b>+</b> နှိပ်ပါ:\n\n"
        f"• <b>Name:</b> <code>GoodWifi ({uname})</code>\n"
        f"• <b>Type:</b> <code>IKEv2/IPSec MSCHAPv2</code>\n"
        f"• <b>Server:</b> <code>{server}</code>\n"
        f"• <b>IPSec identifier:</b> <code>{server}</code>\n"
        f"• <b>Username:</b> <code>{uname}</code>\n"
        f"• <b>Password:</b> <code>{pwd}</code>\n\n"
        f"<i>(စာသားများကို တစ်ချက်နှိပ်ရုံဖြင့် Copy ကူးနိုင်ပါသည်)</i>\n"
        f"ပြီးပါက <b>Save</b> နှိပ်ပြီး ချက်ချင်း စတင်သုံးနိုင်ပါပြီ!"
    )


def make_users_list_keyboard(users: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Build keyboard listing all registered VPN users."""
    buttons: list[list[InlineKeyboardButton]] = []
    for u in users:
        uname = u.get("username", "Unknown")
        status = u.get("status", "active")
        badge = "🟢" if status == "active" else "⏸️"
        label = (
            f"{badge} {uname}" if status == "active" else f"{badge} {uname} (Paused)"
        )
        buttons.append(
            [InlineKeyboardButton(label, callback_data=f"user_view:{uname}")]
        )

    buttons.append(
        [
            InlineKeyboardButton("➕ Add User", callback_data="user_add_prompt"),
            InlineKeyboardButton("🔄 Refresh", callback_data="user_refresh"),
        ]
    )
    return InlineKeyboardMarkup(buttons)


def make_user_detail_keyboard(username: str, is_active: bool) -> InlineKeyboardMarkup:
    """Build action keyboard for a single user."""
    pause_btn = (
        InlineKeyboardButton("⏸️ Pause User", callback_data=f"user_pause:{username}")
        if is_active
        else InlineKeyboardButton(
            "▶️ Resume User", callback_data=f"user_resume:{username}"
        )
    )
    buttons = [
        [
            InlineKeyboardButton(
                "🍏 iOS Profile", callback_data=f"user_ios:{username}"
            ),
            InlineKeyboardButton(
                "🤖 Android Setup", callback_data=f"user_android:{username}"
            ),
        ],
        [pause_btn],
        [
            InlineKeyboardButton(
                "🗑️ Delete User", callback_data=f"user_del_prompt:{username}"
            ),
            InlineKeyboardButton("⬅️ All Users", callback_data="user_list"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def make_user_delete_confirm_keyboard(username: str) -> InlineKeyboardMarkup:
    """Build confirmation keyboard before deleting a user."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚠️ Yes, Delete", callback_data=f"user_del_confirm:{username}"
                ),
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"user_view:{username}"
                ),
            ]
        ]
    )
