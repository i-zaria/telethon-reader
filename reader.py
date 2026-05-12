import os
import asyncio
import requests
from telethon import TelegramClient, events

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ.get("TG_SESSION", "/app/sessions/main")
CHANNEL = os.environ["TG_CHANNEL"]

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")
if not N8N_WEBHOOK_URL:
    raise RuntimeError("N8N_WEBHOOK_URL is missing or empty")

PROXY_HOST = os.environ["PROXY_HOST"]
PROXY_PORT = int(os.environ["PROXY_PORT"])
PROXY_USER = os.environ.get("PROXY_USER")
PROXY_PASS = os.environ.get("PROXY_PASS")

proxy = {
    "proxy_type": "socks5",
    "addr": PROXY_HOST,
    "port": PROXY_PORT,
    "username": PROXY_USER,
    "password": PROXY_PASS,
    "rdns": True,
}

client = TelegramClient(SESSION, API_ID, API_HASH, proxy=proxy)

@client.on(events.NewMessage(chats=CHANNEL))
async def handler(event):
    message = event.message

    payload = {
        "source": "telethon",
        "channel": CHANNEL,
        "chat_id": event.chat_id,
        "message_id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "text": message.message or "",
        "raw_text": message.raw_text or "",
        "sender_id": message.sender_id,
        "post_author": message.post_author,
        "views": getattr(message, "views", None),
        "forwards": getattr(message, "forwards", None),
    }

    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
        print(f"Webhook sent: status={response.status_code}, message_id={message.id}")
    except Exception as e:
        print(f"Webhook send failed for message_id={message.id}: {e}")

async def main():
    await client.start()
    print(f"Telethon started for channel: {CHANNEL}")
    await client.run_until_disconnected()

asyncio.run(main())
