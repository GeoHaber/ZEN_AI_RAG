import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from async_backend import backend
from config_system import config

logger = logging.getLogger("TelegramGateway")

# --- Security: Whitelist ---
# This should be populated from config or secrets.json
ALLOWED_USER_IDS = getattr(config, "telegram_whitelist", [])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text(f"⛔ Unauthorized access. User ID: {user_id}")
        return
    
    await update.message.reply_text("🤖 ZenAI Gateway Online. Send me a question!")

async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route Telegram message to ZenAI Backend."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Unauthorized. Please contact the administrator.")
        return

    query = update.message.text
    logger.info(f"📲 Telegram query from {user_id}: {query[:50]}...")

    # Notify user we are thinking
    status_msg = await update.message.reply_text("🔎 Thinking...")
    
    full_response = ""
    try:
        async with backend:
            async for chunk in backend.send_message_async(query):
                full_response += chunk
                
                # Update status message occasionally to show progress (throttled)
                if len(full_response) % 100 == 0:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=status_msg.message_id,
                            text=full_response + " ▌"
                        )
                    except Exception:
                        pass # Ignore frequent update errors

        # Final balanced response
        if full_response:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=full_response
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text="⚠️ Backend returned an empty response."
            )
            
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text=f"❌ Gateway Error: {str(e)}"
        )

def run_gateway():
    """Blocking call to start the bot (used in a separate thread/process)."""
    token = getattr(config, "telegram_token", None)
    if not token:
        logger.warning("Telegram token missing. Gateway disabled.")
        return

    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_telegram_message))
    
    logger.info("🚀 Telegram Gateway is running...")
    app.run_polling()

if __name__ == '__main__':
    # For standalone testing
    run_gateway()
