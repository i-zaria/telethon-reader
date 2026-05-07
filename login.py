import os
import asyncio
from telethon import TelegramClient

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ.get("TG_SESSION", "/app/sessions/main")

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

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH, proxy=proxy)
    await client.start()
    me = await client.get_me()
    print(f"Login successful: id={me.id}, username={me.username}, phone={me.phone}")
    await client.disconnect()

asyncio.run(main())
