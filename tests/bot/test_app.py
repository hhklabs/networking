"""Unit tests for bot application creation and handler registration."""

import unittest
from unittest.mock import patch


class TestTelegramBotAppCreation(unittest.TestCase):
    """Test building application and registering handlers."""

    def test_create_application(self):
        with patch("telegrambot.bot.BOT_TOKEN", "123456:FAKE_TOKEN_FOR_TESTING"):
            from telegrambot.bot import create_application

            app = create_application()
            self.assertIsNotNone(app)
            # Verify handlers are registered
            handlers_count = sum(len(handlers) for handlers in app.handlers.values())
            self.assertGreater(handlers_count, 15)

    def test_switch_pattern_routes_submenus(self):
        with patch("telegrambot.bot.BOT_TOKEN", "123456:FAKE_TOKEN_FOR_TESTING"):
            from telegrambot.bot import create_application

            app = create_application()
            switch_handlers = [
                h
                for group in app.handlers.values()
                for h in group
                if getattr(h, "callback", None).__name__ == "switch_vpn_callback"
            ]
            self.assertTrue(len(switch_handlers) > 0)
            pattern = switch_handlers[0].pattern
            for target in [
                "menu_switch",
                "menu_vless",
                "menu_awg",
                "menu_ovpn",
                "switch_reality_1",
                "switch_reality_2",
                "switch_sing0",
                "switch_awg0",
                "switch_tun0",
                "switch_wg0",
                "switch_auto",
            ]:
                self.assertIsNotNone(
                    pattern.match(target),
                    f"Pattern failed to match: {target}",
                )


class TestTelegramBotErrorHandler(unittest.IsolatedAsyncioTestCase):
    """Test global error handler resilience against network errors."""

    async def test_error_handler_network_error_suppresses_traceback(self):
        from telegram.error import NetworkError
        from telegrambot.bot import _error_handler

        mock_context = unittest.mock.MagicMock()
        mock_context.error = NetworkError("Bad Gateway")

        with patch("telegrambot.bot.logger") as mock_logger:
            await _error_handler(None, mock_context)
            mock_logger.warning.assert_called_once()
            self.assertIn(
                "Telegram network error encountered",
                mock_logger.warning.call_args[0][0],
            )
            mock_logger.error.assert_not_called()

    async def test_error_handler_generic_error_logs_exception(self):
        from telegrambot.bot import _error_handler

        mock_context = unittest.mock.MagicMock()
        mock_context.error = RuntimeError("Unexpected crash")

        with patch("telegrambot.bot.logger") as mock_logger:
            await _error_handler(None, mock_context)
            mock_logger.error.assert_called_once()
            mock_logger.warning.assert_not_called()


if __name__ == "__main__":
    unittest.main()
