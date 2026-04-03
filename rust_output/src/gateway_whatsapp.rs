use anyhow::{Result, Context};
use crate::async_backend::{backen};
use crate::config_system::{config};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static APP: std::sync::LazyLock<Flask> = std::sync::LazyLock::new(|| Default::default());

pub static ALLOWED_NUMBERS: std::sync::LazyLock<getattr> = std::sync::LazyLock::new(|| Default::default());

/// Helper to get non-streaming response for WhatsApp (MMS/SMS limit).
pub async fn get_zenai_response(query: String) -> Result<String> {
    // Helper to get non-streaming response for WhatsApp (MMS/SMS limit).
    let mut full_response = "".to_string();
    // try:
    {
        let _ctx = backend;
        {
            // async for
            while let Some(chunk) = backend.send_message_async(query).next().await {
                full_response += chunk;
            }
        }
        full_response
    }
    // except Exception as e:
}

/// Handle incoming WhatsApp messages from Twilio.
pub fn whatsapp_webhook() -> () {
    // Handle incoming WhatsApp messages from Twilio.
    let mut from_number = request.values.get(&"From".to_string()).cloned().unwrap_or("".to_string());
    let mut incoming_msg = request.values.get(&"Body".to_string()).cloned().unwrap_or("".to_string());
    if !ALLOWED_NUMBERS.contains(&from_number) {
        logger.warning(format!("⛔ Unauthorized WhatsApp from {}", from_number));
        let mut resp = MessagingResponse();
        resp.message("⛔ Unauthorized access. Please contact the administrator.".to_string());
        resp.to_string()
    }
    logger.info(format!("📲 WhatsApp from {}: {}...", from_number, incoming_msg[..50]));
    let mut r#loop = asyncio.new_event_loop();
    asyncio.set_event_loop(r#loop);
    let mut response_text = r#loop.run_until_complete(get_zenai_response(incoming_msg));
    r#loop.close();
    let mut resp = MessagingResponse();
    let mut msg = resp.message();
    msg.body(response_text);
    resp.to_string()
}

/// Start the Flask server for WhatsApp webhooks.
pub fn run_whatsapp_gateway() -> () {
    // Start the Flask server for WhatsApp webhooks.
    let mut port = /* getattr */ 5001;
    // global/nonlocal ALLOWED_NUMBERS
    let mut ALLOWED_NUMBERS = /* getattr */ vec![];
    logger.info(format!("🚀 WhatsApp Gateway (Webhook) is running on port {}...", port));
    logger.info(format!("📋 Whitelist: {}", ALLOWED_NUMBERS));
    app::run(/* port= */ port);
}
