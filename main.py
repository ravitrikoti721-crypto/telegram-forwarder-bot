import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_ID = int(os.getenv("TARGET_PUBLIC_ID").strip())

# Ye line multiple IDs ko handle karegi
def get_ids(var_name):
    raw = os.getenv(var_name, "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

# Saari source IDs ko ek list mein jama karo
SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID") + get_ids("SOURCE_PRIVATE_ID")

app = Client("multi_userbot", api_id=int(API_ID), api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message(filters.chat(SOURCE_IDS))
async def mirror_messages(client, message):
    try:
        # Restricted content check fallback
        await message.copy(TARGET_ID)
        logging.info(f"✅ Mirrored from {message.chat.id} to {TARGET_ID}")
    except Exception as e:
        logging.warning(f"⚠️ Copy failed, trying Text fallback: {e}")
        try:
            if message.text:
                await client.send_message(TARGET_ID, message.text)
            elif message.caption:
                await message.copy(TARGET_ID)
            logging.info(f"✅ Mirrored via Fallback")
        except Exception as e2:
            logging.error(f"❌ Final Error: {e2}")

async def start_bot():
    await app.start()
    logging.info("Syncing and Checking Sources...")
    for s_id in SOURCE_IDS:
        try:
            chat = await app.get_chat(s_id)
            logging.info(f"✅ Monitoring: {chat.title}")
        except:
            logging.error(f"❌ Could not find ID: {s_id}")
    
    logging.info(f"🚀 Bot Active! Monitoring {len(SOURCE_IDS)} sources.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_bot())
