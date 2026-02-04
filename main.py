"""
Main entry point - WhatsApp Insurance Agent webhook server.

This server handles incoming WhatsApp messages from YCloud and routes them to the insurance agent.
"""

import sys
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request

from config import PORT, validate_config
from insurance_agent import insurance_agent
from whatsapp_client import whatsapp_client


app = FastAPI(
    title="Insurance Agent WhatsApp Bot",
    description="WhatsApp bot for insurance policy queries",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Insurance WhatsApp Agent"}


@app.get("/webhook")
async def webhook_verification(hub_mode: str = None, hub_challenge: str = None, hub_verify_token: str = None):
    """
    Handle webhook verification from YCloud.
    This is used during webhook setup.
    """
    # YCloud may use this for verification
    if hub_challenge:
        return int(hub_challenge)
    return {"status": "ready"}


async def process_message(from_number: str, your_number: str, text_content: str):
    """Process a WhatsApp message in the background."""
    print(f"\nProcessing: {from_number} -> {text_content[:50]}...")
    sys.stdout.flush()

    try:
        # Get response from the insurance agent
        response_text = await insurance_agent.process_message(from_number, text_content)

        print(f"Response: {response_text[:100]}...")
        sys.stdout.flush()

        # Send response using split messages (handles --- delimiter)
        await whatsapp_client.send_split_messages(from_number, response_text, your_number)

        print(f"Response sent to {from_number}")

    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()
        try:
            await whatsapp_client.send_message(
                from_number,
                "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo.",
                your_number
            )
        except Exception as send_error:
            print(f"Failed to send error message: {send_error}")


@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming WhatsApp message webhooks from YCloud.
    Returns 200 immediately, processes message in background.
    """
    payload = await request.json()

    print(f"\nWebhook received at {datetime.now()}")
    print(f"Event: {payload.get('type')}")
    sys.stdout.flush()

    event_type = payload.get("type", "")

    if event_type == "whatsapp.inbound_message.received":
        message_data = payload.get("whatsappInboundMessage", {})

        from_number = message_data.get("from", "")
        your_number = message_data.get("to", "")
        message_type = message_data.get("type", "")

        print(f"From: {from_number}, To: {your_number}, Type: {message_type}")
        sys.stdout.flush()

        text_content = None

        if message_type == "text":
            text_content = message_data.get("text", {}).get("body", "")
            print(f"Text: {text_content}")
            sys.stdout.flush()

        elif message_type == "interactive":
            # Handle button/list responses
            interactive_data = message_data.get("interactive", {})
            interactive_type = interactive_data.get("type", "")

            if interactive_type == "list_reply":
                button_id = interactive_data.get("list_reply", {}).get("id", "")
                text_content = interactive_data.get("list_reply", {}).get("title", button_id)
                print(f"List selection: {text_content}")
                sys.stdout.flush()

            elif interactive_type == "button_reply":
                button_id = interactive_data.get("button_reply", {}).get("id", "")
                text_content = interactive_data.get("button_reply", {}).get("title", button_id)
                print(f"Button click: {text_content}")
                sys.stdout.flush()

        if text_content and from_number:
            # Process in background - return 200 immediately
            asyncio.create_task(process_message(from_number, your_number, text_content))

    return {"status": "received"}


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup."""
    try:
        validate_config()
        print("Configuration validated successfully")
        print(f"Server starting on port {PORT}")
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
