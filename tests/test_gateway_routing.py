import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

class TestTelegramGateway(unittest.IsolatedAsyncioTestCase):
    """TestTelegramGateway class."""
    def setUp(self):
        self.whitelist = [123456789] # Mock authorized User ID
        self.unauthorized_user = 987654321

    @patch('zena_mode.gateway_telegram.backend') # Mocking the global backend
    async def test_authorized_user_routing(self, mock_backend):
        """Verify that an authorized user's message is sent to the LLM."""
        from zena_mode.gateway_telegram import handle_telegram_message
        
        # Patch the whitelist inside the module for the test
        with patch('zena_mode.gateway_telegram.ALLOWED_USER_IDS', [123456789]):
            # Mock backend streaming response
            mock_gen = MagicMock()
            mock_gen.__aiter__.return_value = ["Hello ", "from ZenAI!"]
            mock_backend.send_message_async.return_value = mock_gen
            mock_backend.__aenter__.return_value = mock_backend
            
            # Mock Telegram Message/Update
            update = MagicMock()
            update.effective_user.id = 123456789
            update.message.text = "Tell me about the swarm."
            update.message.reply_text = AsyncMock()
            
            context = MagicMock()
            context.bot.send_message = AsyncMock()
            context.bot.edit_message_text = AsyncMock()

            await handle_telegram_message(update, context)
            
            # Check if backend was called
            mock_backend.send_message_async.assert_called_with("Tell me about the swarm.")

    async def test_unauthorized_user_rejection(self):
        """Ensure that users not in the whitelist are blocked."""
        from zena_mode.gateway_telegram import handle_telegram_message
        
        with patch('zena_mode.gateway_telegram.ALLOWED_USER_IDS', [123456789]):
            update = MagicMock()
            update.effective_user.id = 987654321 # Unauthorized
            update.message.text = "Hack me!"
            update.message.reply_text = AsyncMock()

            context = MagicMock()
            context.bot.send_message = AsyncMock()

            await handle_telegram_message(update, context)
            
            # Should have sent a rejection message
            args, kwargs = update.message.reply_text.call_args
            self.assertIn("Unauthorized", args[0])

if __name__ == "__main__":
    unittest.main()
