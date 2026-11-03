"""Handlers for VPN client users and iOS/Android profiles management."""

import io
import json

from telegram import Update
from telegram.ext import ContextTypes

from telegrambot.core.config import check_authorization
from telegrambot.core.users_client import (
    execute_users_cmd,
    fetch_all_users,
    fetch_user,
    resolve_mobileconfig_bytes,
)
from telegrambot.ui.users_keyboards import (
    format_android_guide,
    format_user_card,
    make_user_delete_confirm_keyboard,
    make_user_detail_keyboard,
    make_users_list_keyboard,
)


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /users and /list commands."""
    if update.effective_user is None or not check_authorization(
        update.effective_user.id
    ):
        return
    users = await fetch_all_users()
    active_count = sum(1 for u in users if u.get("status") == "active")
    text = (
        f"👥 <b>VPN Client Users</b>\n"
        f"Active: <b>{active_count}</b> | Total: <b>{len(users)}</b>\n\n"
        f"Profile ရယူရန် သို့မဟုတ် ထိန်းချုပ်ရန် အသုံးပြုသူကို နှိပ်ပါ:\n"
        f"<i>(အသစ်ထည့်ရန်: <code>/adduser &lt;name&gt; [pass]</code>)</i>"
    )
    if update.message:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=make_users_list_keyboard(users)
        )


async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /adduser and /add commands."""
    if update.effective_user is None or not check_authorization(
        update.effective_user.id
    ):
        return
    args = context.args or []
    if not args:
        if update.message:
            await update.message.reply_text(
                "ℹ️ <b>အသုံးပြုပုံ:</b> <code>/adduser &lt;name&gt; [password]</code>\n"
                "သို့မဟုတ် <code>/add &lt;name&gt;</code>\n"
                "<i>ဥပမာ: <code>/adduser KyawKyaw</code></i>",
                parse_mode="HTML",
            )
        return

    uname, upass = args[0], (args[1] if len(args) > 1 else None)
    cmd = ["--user-add", uname] + ([upass] if upass else []) + ["--json"]
    out, err, code = await execute_users_cmd(cmd)

    if code != 0 or not out.strip():
        if update.message:
            await update.message.reply_text(
                f"❌ Failed to create user: {err or out}", parse_mode="HTML"
            )
        return

    try:
        user_info = json.loads(out).get("user", {})
    except Exception:
        user_info = {"username": uname, "status": "active"}

    msg_text = format_user_card(user_info)
    kb = make_user_detail_keyboard(
        user_info.get("username", uname),
        user_info.get("status") == "active",
    )
    if update.message:
        await update.message.reply_text(msg_text, parse_mode="HTML", reply_markup=kb)
        doc_bytes, filename = resolve_mobileconfig_bytes(user_info)
        bio = io.BytesIO(doc_bytes)
        bio.name = filename
        await update.message.reply_document(
            document=bio,
            filename=filename,
            caption=f"🍏 <b>iOS Profile for {user_info.get('username', uname)}</b>",
            parse_mode="HTML",
        )


async def _run_user_action_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE, flag: str, verb: str
) -> None:
    """Helper for simple username-targeted commands like pause, resume, del."""
    if update.effective_user is None or not check_authorization(
        update.effective_user.id
    ):
        return
    args = context.args or []
    if not args:
        if update.message:
            await update.message.reply_text(
                f"Usage: <code>/{verb} &lt;username&gt;</code>", parse_mode="HTML"
            )
        return
    out, err, code = await execute_users_cmd([flag, args[0]])
    if update.message:
        res = out.strip() or err.strip()
        await update.message.reply_text(
            f"{'✅' if code == 0 else '❌'} {res}", parse_mode="HTML"
        )


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pause command."""
    await _run_user_action_cmd(update, context, "--user-pause", "pause")


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resume command."""
    await _run_user_action_cmd(update, context, "--user-resume", "resume")


async def deluser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /deluser, /del, /remove commands."""
    await _run_user_action_cmd(update, context, "--user-del", "deluser")


async def getuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /get, /profile, /download commands."""
    if update.effective_user is None or not check_authorization(
        update.effective_user.id
    ):
        return
    args = context.args or []
    if not args:
        if update.message:
            await update.message.reply_text(
                "Usage: <code>/get &lt;username&gt;</code>", parse_mode="HTML"
            )
        return
    u = await fetch_user(args[0])
    if not u:
        if update.message:
            await update.message.reply_text(
                f"❌ User '{args[0]}' not found.", parse_mode="HTML"
            )
        return

    card = format_user_card(u)
    kb = make_user_detail_keyboard(
        u.get("username", args[0]), u.get("status") == "active"
    )
    if update.message:
        await update.message.reply_text(card, parse_mode="HTML", reply_markup=kb)
        doc_bytes, filename = resolve_mobileconfig_bytes(u)
        bio = io.BytesIO(doc_bytes)
        bio.name = filename
        await update.message.reply_document(
            document=bio,
            filename=filename,
            caption=f"🍏 <b>iOS Profile for {u.get('username', args[0])}</b>",
            parse_mode="HTML",
        )


async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for VPN user profiles."""
    query = update.callback_query
    if (
        query is None
        or update.effective_user is None
        or not check_authorization(update.effective_user.id)
    ):
        return

    try:
        await query.answer()
    except Exception:
        pass

    data = query.data or ""
    chat_id = query.message.chat_id if query.message else None
    if not chat_id:
        return

    if data in ["user_list", "user_refresh"]:
        users = await fetch_all_users()
        active = sum(1 for u in users if u.get("status") == "active")
        text = (
            f"👥 <b>VPN Client Users</b>\n"
            f"Active: <b>{active}</b> | Total: <b>{len(users)}</b>\n\n"
            f"Profile ရယူရန် သို့မဟုတ် ထိန်းချုပ်ရန် အသုံးပြုသူကို နှိပ်ပါ:\n"
            f"<i>(အသစ်ထည့်ရန်: <code>/adduser &lt;name&gt; [pass]</code>)</i>"
        )
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=make_users_list_keyboard(users)
        )

    elif data == "user_add_prompt" and query.message:
        await query.message.reply_text(
            "➕ <b>အသုံးပြုသူအသစ် ထည့်သွင်းရန်:</b>\n\n"
            "<code>/adduser &lt;name&gt; [password]</code>\n\n"
            "<i>ဥပမာ: <code>/adduser KyawKyaw</code>\n"
            "(Password မထည့်ပါက Bot မှ အလိုအလျောက် ထုတ်ပေးပါမည်)</i>",
            parse_mode="HTML",
        )

    elif data.startswith("user_view:"):
        uname = data.replace("user_view:", "")
        u = await fetch_user(uname)
        if not u:
            await query.edit_message_text(f"❌ User '{uname}' not found.")
            return
        kb = make_user_detail_keyboard(uname, u.get("status") == "active")
        await query.edit_message_text(
            format_user_card(u), parse_mode="HTML", reply_markup=kb
        )

    elif data.startswith("user_ios:"):
        uname = data.replace("user_ios:", "")
        u = await fetch_user(uname) or {"username": uname}
        doc_bytes, filename = resolve_mobileconfig_bytes(u)
        bio = io.BytesIO(doc_bytes)
        bio.name = filename
        url = u.get("url", f"https://connect.hhk.my.id/ios/{uname}.mobileconfig")
        await context.bot.send_document(
            chat_id=chat_id,
            document=bio,
            filename=filename,
            caption=f"🍏 <b>iOS Profile for {uname}</b>\nSafari Link: {url}",
            parse_mode="HTML",
        )

    elif data.startswith("user_android:") and query.message:
        uname = data.replace("user_android:", "")
        u = await fetch_user(uname) or {"username": uname}
        await query.message.reply_text(format_android_guide(u), parse_mode="HTML")

    elif data.startswith("user_pause:"):
        uname = data.replace("user_pause:", "")
        await execute_users_cmd(["--user-pause", uname])
        u = await fetch_user(uname) or {"username": uname, "status": "paused"}
        kb = make_user_detail_keyboard(uname, False)
        await query.edit_message_text(
            format_user_card(u), parse_mode="HTML", reply_markup=kb
        )

    elif data.startswith("user_resume:"):
        uname = data.replace("user_resume:", "")
        await execute_users_cmd(["--user-resume", uname])
        u = await fetch_user(uname) or {"username": uname, "status": "active"}
        kb = make_user_detail_keyboard(uname, True)
        await query.edit_message_text(
            format_user_card(u), parse_mode="HTML", reply_markup=kb
        )

    elif data.startswith("user_del_prompt:"):
        uname = data.replace("user_del_prompt:", "")
        kb = make_user_delete_confirm_keyboard(uname)
        await query.edit_message_text(
            f"⚠️ <b>User '{uname}' ကို အပြီးဖျက်ရန် သေချာပါသလား?</b>",
            parse_mode="HTML",
            reply_markup=kb,
        )

    elif data.startswith("user_del_confirm:"):
        uname = data.replace("user_del_confirm:", "")
        await execute_users_cmd(["--user-del", uname])
        users = await fetch_all_users()
        active = sum(1 for u in users if u.get("status") == "active")
        text = (
            f"🗑️ User <b>'{uname}'</b> ကို ဖျက်ပြီးပါပြီ။\n\n"
            f"Active: <b>{active}</b> | Total: <b>{len(users)}</b>"
        )
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=make_users_list_keyboard(users)
        )
