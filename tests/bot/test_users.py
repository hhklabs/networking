"""Unit tests for Telegram Bot VPN user management handlers and UI."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegrambot.handlers.users import (
    adduser_command,
    deluser_command,
    getuser_command,
    pause_command,
    resume_command,
    users_callback,
    users_command,
)
from telegrambot.ui.users_keyboards import (
    format_android_guide,
    format_user_card,
    make_user_delete_confirm_keyboard,
    make_user_detail_keyboard,
    make_users_list_keyboard,
)


class TestTelegramBotUsers(unittest.IsolatedAsyncioTestCase):
    def test_keyboards_and_formatters(self):
        sample_users = [
            {"username": "KyawKyaw", "status": "active", "server": "connect.test.id"},
            {"username": "MgMg", "status": "paused", "server": "connect.test.id"},
        ]
        kb_list = make_users_list_keyboard(sample_users)
        self.assertEqual(len(kb_list.inline_keyboard), 3)
        self.assertEqual(
            kb_list.inline_keyboard[0][0].callback_data, "user_view:KyawKyaw"
        )
        self.assertEqual(kb_list.inline_keyboard[1][0].callback_data, "user_view:MgMg")

        kb_detail_act = make_user_detail_keyboard("KyawKyaw", True)
        self.assertIn(
            "user_pause:KyawKyaw", kb_detail_act.inline_keyboard[1][0].callback_data
        )

        kb_detail_pause = make_user_detail_keyboard("KyawKyaw", False)
        self.assertIn(
            "user_resume:KyawKyaw", kb_detail_pause.inline_keyboard[1][0].callback_data
        )

        kb_del = make_user_delete_confirm_keyboard("KyawKyaw")
        self.assertEqual(
            kb_del.inline_keyboard[0][0].callback_data, "user_del_confirm:KyawKyaw"
        )

        card = format_user_card(sample_users[0])
        self.assertIn("KyawKyaw", card)
        self.assertIn("connect.test.id", card)

        guide = format_android_guide(sample_users[0])
        self.assertIn("IKEv2/IPSec MSCHAPv2", guide)
        self.assertIn("KyawKyaw", guide)

    @patch("telegrambot.handlers.users.check_authorization", return_value=True)
    @patch("telegrambot.core.users_client.run_hotspot_command")
    async def test_users_command(self, mock_run, mock_auth):
        mock_run.return_value = (
            json.dumps([{"username": "Alice", "status": "active"}]),
            "",
            0,
        )
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await users_command(update, context)

        update.message.reply_text.assert_called_once()
        text, kwargs = (
            update.message.reply_text.call_args[0][0],
            update.message.reply_text.call_args[1],
        )
        self.assertIn("VPN Client Users", text)
        self.assertIsNotNone(kwargs.get("reply_markup"))

    @patch("telegrambot.handlers.users.check_authorization", return_value=True)
    @patch("telegrambot.core.users_client.run_hotspot_command")
    async def test_adduser_command(self, mock_run, mock_auth):
        user_record = {
            "username": "Bob",
            "password": "Pass@1234",
            "server": "connect.test.id",
            "status": "active",
            "url": "https://connect.test.id/ios/Bob.mobileconfig",
        }
        mock_run.return_value = (
            json.dumps({"success": True, "user": user_record}),
            "",
            0,
        )
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()
        context = MagicMock()
        context.args = ["Bob", "Pass@1234"]

        await adduser_command(update, context)

        update.message.reply_text.assert_called_once()
        update.message.reply_document.assert_called_once()
        doc_kwargs = update.message.reply_document.call_args[1]
        self.assertEqual(doc_kwargs["filename"], "Bob.mobileconfig")

    @patch("telegrambot.handlers.users.check_authorization", return_value=True)
    @patch("telegrambot.core.users_client.run_hotspot_command")
    async def test_pause_and_resume_command(self, mock_run, mock_auth):
        mock_run.return_value = ("User 'Bob' paused successfully", "", 0)
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["Bob"]

        await pause_command(update, context)
        update.message.reply_text.assert_called_once()
        self.assertIn("paused", update.message.reply_text.call_args[0][0])

        mock_run.return_value = ("User 'Bob' resumed successfully", "", 0)
        update.message.reply_text.reset_mock()
        await resume_command(update, context)
        update.message.reply_text.assert_called_once()
        self.assertIn("resumed", update.message.reply_text.call_args[0][0])

    @patch("telegrambot.handlers.users.check_authorization", return_value=True)
    @patch("telegrambot.core.users_client.run_hotspot_command")
    async def test_deluser_command(self, mock_run, mock_auth):
        mock_run.return_value = ("User 'Bob' deleted successfully", "", 0)
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.args = ["Bob"]

        await deluser_command(update, context)
        update.message.reply_text.assert_called_once()
        self.assertIn("deleted", update.message.reply_text.call_args[0][0])

    @patch("telegrambot.handlers.users.check_authorization", return_value=True)
    @patch("telegrambot.core.users_client.run_hotspot_command")
    async def test_getuser_command(self, mock_run, mock_auth):
        mock_run.return_value = (
            json.dumps({"username": "Bob", "password": "pwd", "status": "active"}),
            "",
            0,
        )
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()
        context = MagicMock()
        context.args = ["Bob"]

        await getuser_command(update, context)
        update.message.reply_text.assert_called_once()
        update.message.reply_document.assert_called_once()

    @patch("telegrambot.handlers.users.check_authorization", return_value=True)
    @patch("telegrambot.core.users_client.run_hotspot_command")
    async def test_users_callback(self, mock_run, mock_auth):
        mock_run.return_value = (
            json.dumps({"username": "Bob", "status": "active"}),
            "",
            0,
        )
        update = MagicMock()
        update.effective_user.id = 12345
        query = MagicMock()
        query.data = "user_view:Bob"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message.chat_id = 9999
        update.callback_query = query
        context = MagicMock()

        await users_callback(update, context)
        query.edit_message_text.assert_called_once()
        self.assertIn("Bob", query.edit_message_text.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
