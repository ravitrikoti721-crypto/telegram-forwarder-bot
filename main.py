import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

# Config
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET_ID = -1001752144165 # Market Precision

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID")

app = Client("rt_pro_copier", api_id=API_ID, api_hash=API_HASH, session_string=SESSION, in_memory=True)

@app.on_message()
async def final_mirror(client, message):
    # Debug: Har message ki ID log mein dikhegi
    logging.info(f"DEBUG: Message received from ID: {message.chat.id}")

    if message.chat.id in SOURCE_IDS:
        logging.info(f"🎯 MATCH FOUND! Source: {message.chat.id}")
        try:
            # 1. Try normal copy
            await message.copy(TARGET_ID)
            logging.info("✅ SUCCESS: Mirrored via Copy")
        except Exception as e:
            logging.warning(f"⚠️ Copy failed, trying Text fallback: {e}")
            try:
                # 2. Try sending as new message (For restricted channels)
                if message.text:
                    await client.send_message(TARGET_ID, message.text)
                elif message.caption:
                    await client.send_message(TARGET_ID, message.caption)
                logging.info("✅ SUCCESS: Mirrored via Text Fallback")
            except Exception as e2:
                logging.error(f"❌ FATAL: Both methods failed: {e2}")

async def main():
    await app.start()
    logging.info("--- BOT STARTED ---")
    # Dialogs sync taaki IDs recognize ho jayein
    async for dialog in app.get_dialogs(limit=20):
        pass
    logging.info(f"🚀 SYSTEM LIVE | MONITORING SOURCES: {SOURCE_IDS}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
