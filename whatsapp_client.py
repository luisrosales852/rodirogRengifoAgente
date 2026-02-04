"""YCloud WhatsApp Client for sending messages."""

import httpx
from config import YCLOUD_API_KEY, YCLOUD_API_BASE_URL


class YCloudWhatsAppClient:
    """Client for interacting with YCloud WhatsApp API."""

    def __init__(self):
        self.api_key = YCLOUD_API_KEY
        self.base_url = YCLOUD_API_BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def send_message(self, to_number: str, message: str, from_number: str) -> dict:
        """
        Send a WhatsApp text message to a recipient.

        Args:
            to_number: The recipient's phone number (with country code)
            message: The text message to send
            from_number: The sender's WhatsApp business number

        Returns:
            dict: The API response
        """
        url = f"{self.base_url}/whatsapp/messages"

        payload = {
            "from": from_number,
            "to": to_number,
            "type": "text",
            "text": {
                "body": message
            }
        }

        print(f"Sending message...")
        print(f"   From: {from_number}")
        print(f"   To: {to_number}")
        print(f"   Message: {message[:100]}{'...' if len(message) > 100 else ''}")

        client = await self._get_client()
        response = await client.post(url, json=payload)

        print(f"   Response: {response.status_code}")

        if response.status_code != 200:
            print(f"   Error: {response.text}")
        else:
            print(f"   Success!")

        response.raise_for_status()
        return response.json()

    async def send_message_with_delay(self, to_number: str, messages: list[str], from_number: str, delay_seconds: float = 0.5) -> list[dict]:
        """
        Send multiple messages with a delay between them for natural conversation flow.

        Args:
            to_number: The recipient's phone number
            messages: List of message parts to send
            from_number: The sender's WhatsApp business number
            delay_seconds: Delay between messages (default 0.5s)

        Returns:
            list[dict]: List of API responses
        """
        import asyncio

        print(f"Sending {len(messages)} message(s) with {delay_seconds}s delays...")

        responses = []
        for i, message in enumerate(messages):
            print(f"   [{i+1}/{len(messages)}] Sending: {message[:50]}{'...' if len(message) > 50 else ''}")
            response = await self.send_message(to_number, message, from_number)
            responses.append(response)

            # Don't delay after the last message
            if i < len(messages) - 1:
                await asyncio.sleep(delay_seconds)

        return responses

    async def send_split_messages(self, to_number: str, ai_response: str, from_number: str) -> list[str]:
        """
        Split AI response by '---' delimiter and send as multiple messages with delays.

        Args:
            to_number: The recipient's phone number
            ai_response: Full AI response (may contain --- delimiters)
            from_number: The sender's WhatsApp business number

        Returns:
            list[str]: List of individual messages that were sent
        """
        # Split by the --- delimiter
        messages = [msg.strip() for msg in ai_response.split('---') if msg.strip()]

        if not messages:
            messages = [ai_response]

        await self.send_message_with_delay(to_number, messages, from_number, delay_seconds=0.5)

        return messages


# Singleton instance
whatsapp_client = YCloudWhatsAppClient()
