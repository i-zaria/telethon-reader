import os
import asyncio
import requests

from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel

def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is missing or empty")
    return value

API_ID = int(require_env("TG_API_ID"))
API_HASH = require_env("TG_API_HASH")
SESSION = os.environ.get("TG_SESSION", "/app/sessions/main")
CHANNEL = require_env("TG_CHANNEL")
N8N_WEBHOOK_URL = require_env("N8N_WEBHOOK_URL")

PROXY_HOST = require_env("PROXY_HOST")
PROXY_PORT = int(require_env("PROXY_PORT"))
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

_cached_channel_entity = None

async def get_channel_entity():
    global _cached_channel_entity
    if _cached_channel_entity is None:
        _cached_channel_entity = await client.get_entity(CHANNEL)
    return _cached_channel_entity

async def get_subscribers_count():
    try:
        channel_entity = await get_channel_entity()
        full = await client(GetFullChannelRequest(channel_entity))
        return getattr(full.full_chat, "participants_count", None)
    except Exception as e:
        print(f"[SUBSCRIBERS_ERROR] error={e}")
        return None

def build_message_link(channel_entity, message_id: int):
    try:
        if isinstance(channel_entity, Channel) and getattr(channel_entity, "username", None):
            return f"https://t.me/{channel_entity.username}/{message_id}"

        if isinstance(channel_entity, Channel):
            return f"https://t.me/c/{channel_entity.id}/{message_id}"

        return None
    except Exception as e:
        print(f"[MESSAGE_LINK_ERROR] message_id={message_id} error={e}")
        return None

def build_payload(event, event_type: str, subscribers_at_publish=None, message_link=None) -> dict:
    message = event.message

    return {
        "event_type": event_type,
        "source": "telethon",
        "channel": CHANNEL,
        "chat_id": event.chat_id,
        "message_id": message.id,
        "message_link": message_link,
        "date": message.date.isoformat() if message.date else None,
        "edit_date": message.edit_date.isoformat() if message.edit_date else None,
        "text": message.message or "",
        "raw_text": message.raw_text or "",
        "sender_id": message.sender_id,
        "post_author": message.post_author,
        "views": getattr(message, "views", None),
        "forwards": getattr(message, "forwards", None),
        "grouped_id": getattr(message, "grouped_id", None),
        "has_media": message.media is not None,
        "subscribers_at_publish": subscribers_at_publish,
    }

def send_webhook(payload: dict) -> None:
    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=(5, 30)
        )
        print(
            f"[WEBHOOK_OK] type={payload['event_type']} "
            f"message_id={payload['message_id']} "
            f"status={response.status_code}"
        )
    except requests.exceptions.Timeout:
        print(
            f"[WEBHOOK_TIMEOUT] type={payload['event_type']} "
            f"message_id={payload['message_id']}"
        )
    except requests.exceptions.RequestException as e:
        print(
            f"[WEBHOOK_ERROR] type={payload['event_type']} "
            f"message_id={payload['message_id']} error={e}"
        )
    except Exception as e:
        print(
            f"[UNEXPECTED_ERROR] type={payload['event_type']} "
            f"message_id={payload['message_id']} error={e}"
        )

@client.on(events.NewMessage(chats=CHANNEL))
async def on_new_message(event):
    channel_entity = await get_channel_entity()
    subscribers_count = await get_subscribers_count()
    message_link = build_message_link(channel_entity, event.message.id)

    payload = build_payload(
        event=event,
        event_type="message_new",
        subscribers_at_publish=subscribers_count,
        message_link=message_link
    )

    print(
        f"[NEW] chat_id={payload['chat_id']} "
        f"message_id={payload['message_id']} "
        f"subscribers_at_publish={payload['subscribers_at_publish']} "
        f"message_link={payload['message_link']} "
        f"text={payload['text'][:120]!r}"
    )

    send_webhook(payload)

@client.on(events.MessageEdited(chats=CHANNEL))
async def on_message_edited(event):
    channel_entity = await get_channel_entity()
    message_link = build_message_link(channel_entity, event.message.id)

    payload = build_payload(
        event=event,
        event_type="message_edited",
        subscribers_at_publish=None,
        message_link=message_link
    )

    print(
        f"[EDIT] chat_id={payload['chat_id']} "
        f"message_id={payload['message_id']} "
        f"message_link={payload['message_link']} "
        f"text={payload['text'][:120]!r}"
    )

    send_webhook(payload)

async def main():
    print("[START] Telethon reader starting")
    print(f"[CONFIG] channel={CHANNEL}")
    print(f"[CONFIG] session={SESSION}")
    print(f"[CONFIG] webhook_configured={bool(N8N_WEBHOOK_URL)}")
    print(f"[CONFIG] proxy_host={PROXY_HOST}:{PROXY_PORT}")

    await client.start()
    me = await client.get_me()

    print(
        f"[AUTH_OK] user_id={me.id} "
        f"username={me.username} "
        f"phone={me.phone}"
    )

    channel_entity = await get_channel_entity()
    print(
        f"[CHANNEL_OK] id={getattr(channel_entity, 'id', None)} "
        f"title={getattr(channel_entity, 'title', None)} "
        f"username={getattr(channel_entity, 'username', None)}"
    )

    print("[LISTENING] Waiting for new and edited channel posts")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
