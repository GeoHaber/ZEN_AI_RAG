use anyhow::{Result, Context};
use crate::async_backend::{backen};
use crate::config_system::{config};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static ALLOWED_USER_IDS: std::sync::LazyLock<getattr> = std::sync::LazyLock::new(|| Default::default());

/// Handle /start command.
pub async fn start(update: Update, context: ContextTypes::DEFAULT_TYPE) -> () {
    // Handle /start command.
    let mut user_id = update.effective_user.id;
    if !ALLOWED_USER_IDS.contains(&user_id) {
        update.message.reply_text(format!("⛔ Unauthorized access. User ID: {}", user_id)).await;
        return;
    }
    update.message.reply_text("🤖 ZenAI Gateway Online. Send me a question!".to_string()).await;
}

/// Route Telegram message to ZenAI Backend.
pub async fn handle_telegram_message(update: Update, context: ContextTypes::DEFAULT_TYPE) -> Result<()> {
    // Route Telegram message to ZenAI Backend.
    let mut user_id = update.effective_user.id;
    if !ALLOWED_USER_IDS.contains(&user_id) {
        update.message.reply_text("⛔ Unauthorized. Please contact the administrator.".to_string()).await;
        return;
    }
    let mut query = update.message.text;
    logger.info(format!("📲 Telegram query from {}: {}...", user_id, query[..50]));
    let mut status_msg = update.message.reply_text("🔎 Thinking...".to_string()).await;
    let mut full_response = "".to_string();
    // try:
    {
        let _ctx = backend;
        {
            // async for
            while let Some(chunk) = backend.send_message_async(query).next().await {
                full_response += chunk;
                if (full_response.len() % 100) == 0 {
                    // try:
                    {
                        context.bot.edit_message_text(/* chat_id= */ update.effective_chat.id, /* message_id= */ status_msg.message_id, /* text= */ (full_response + " ▌".to_string())).await;
                    }
                    // except Exception as _e:
                }
            }
        }
        if full_response {
            context.bot.edit_message_text(/* chat_id= */ update.effective_chat.id, /* message_id= */ status_msg.message_id, /* text= */ full_response).await;
        } else {
            context.bot.edit_message_text(/* chat_id= */ update.effective_chat.id, /* message_id= */ status_msg.message_id, /* text= */ "⚠️ Backend returned an empty response.".to_string()).await;
        }
    }
    // except Exception as e:
}

/// Blocking call to start the bot (used in a separate thread/process).
pub fn run_gateway() -> () {
    // Blocking call to start the bot (used in a separate thread/process).
    let mut token = /* getattr */ None;
    if !token {
        logger.warning("Telegram token missing. Gateway disabled.".to_string());
        return;
    }
    let mut app = ApplicationBuilder().token(token).build();
    app::add_handler(CommandHandler("start".to_string(), start));
    app::add_handler(MessageHandler((filters.TEXT & !filters.COMMAND), handle_telegram_message));
    logger.info("🚀 Telegram Gateway is running...".to_string());
    app::run_polling();
}
