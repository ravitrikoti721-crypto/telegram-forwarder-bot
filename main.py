import os, logging, asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Logging
logging.basicConfig(level=logging.INFO)

# Config
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165

# Source IDs
def get_ids():
    raw = os.getenv("SOURCE_PUBLIC_ID", "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids()

# Client Setup
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    logging.info(f"🎯 NEW MESSAGE from {event.chat_id}")
    try:
        await client.send_message(TARGET, event.message)
        logging.info("✅ SUCCESS: Mirrored")
    except Exception as e:
        logging.error(f"❌ ERROR: {e}")

async def main():
    await client.start()
    logging.info("--- TELETHON SYSTEM ONLINE ---")
    logging.info(f"Monitoring: {SOURCE_IDS}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except Exception as e:
        logging.error(f"FATAL: {e}")
