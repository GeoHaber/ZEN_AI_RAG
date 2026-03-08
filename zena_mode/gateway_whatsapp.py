import logging
import asyncio
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from async_backend import backend
from config_system import config

logger = logging.getLogger("WhatsAppGateway")

app = Flask(__name__)

# --- Security: Whitelist ---
# Numbers should be in E.164 format: '+1234567890'
ALLOWED_NUMBERS = getattr(config, "whatsapp_whitelist", [])


async def get_zenai_response(query: str) -> str:
    """Helper to get non-streaming response for WhatsApp (MMS/SMS limit)."""
    full_response = ""
    try:
        async with backend:
            async for chunk in backend.send_message_async(query):
                full_response += chunk
        return full_response
    except Exception as e:
        logger.error(f"WhatsApp backend error: {e}")
        return f"❌ Backend Error: {str(e)}"


@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio."""
    from_number = request.values.get("From", "")
    incoming_msg = request.values.get("Body", "")

    # Check Whitelist
    if from_number not in ALLOWED_NUMBERS:
        logger.warning(f"⛔ Unauthorized WhatsApp from {from_number}")
        resp = MessagingResponse()
        resp.message("⛔ Unauthorized access. Please contact the administrator.")
        return str(resp)

    logger.info(f"📲 WhatsApp from {from_number}: {incoming_msg[:50]}...")

    # Since Flask is sync but backend is async, we run the loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response_text = loop.run_until_complete(get_zenai_response(incoming_msg))
    loop.close()

    # Twilio Response
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(response_text)

    return str(resp)


def run_whatsapp_gateway():
    """Start the Flask server for WhatsApp webhooks."""
    port = getattr(config, "whatsapp_port", 5001)
    # Ensure whitelist is refreshed from config
    global ALLOWED_NUMBERS
    ALLOWED_NUMBERS = getattr(config, "whatsapp_whitelist", [])

    logger.info(f"🚀 WhatsApp Gateway (Webhook) is running on port {port}...")
    logger.info(f"📋 Whitelist: {ALLOWED_NUMBERS}")
    app.run(port=port)


if __name__ == "__main__":
    run_whatsapp_gateway()
