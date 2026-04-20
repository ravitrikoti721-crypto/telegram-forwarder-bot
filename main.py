import os, logging
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO)

# Config
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165

# IDs handle karna
def get_ids():
    raw = os.getenv("SOURCE_PUBLIC_ID", "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids()

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    logging.info(f"🎯 NEW MESSAGE DETECTED from {event.chat_id}")
    try:
        await client.send_message(TARGET, event.message)
        logging.info("✅ SUCCESS: Mirrored")
    except Exception as e:
        logging.error(f"❌ ERROR: {e}")

async def main():
    await client.start()
    print("--- TELETHON SYSTEM ONLINE ---")
    print(f"Monitoring: {SOURCE_IDS}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    from telethon.sessions import StringSession
    asyncio.run(main())
