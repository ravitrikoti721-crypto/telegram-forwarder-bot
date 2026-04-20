import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

# Config
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_ID = -1001752144165  # Forcefully set target ID

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    if not raw: return []
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID")

app = Client(
    "final_v7",
    api_id=int(API_ID),
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

@app.on_message()
async def catch_all(client, message):
    # Har message par ye line log mein aani chahiye!
    logging.info(f"RECEIVED: Chat ID {message.chat.id} | From: {message.from_user.first_name if message.from_user else 'Channel'}")
    
    if message.chat.id in SOURCE_IDS:
        logging.info(f"🎯 MATCH FOUND! Copying to {TARGET_ID}...")
        try:
            await message.copy(TARGET_ID)
            logging.info("✅ SUCCESS: Mirrored!")
        except Exception as e:
            logging.error(f"❌ COPY ERROR: {e}")
            # Fallback text
            try:
                if message.text:
                    await client.send_message(TARGET_ID, message.text)
                logging.info("✅ SUCCESS: Mirrored via Text Fallback")
            except Exception as e2:
                logging.error(f"❌ FATAL: {e2}")

async def main():
    logging.info("Starting Client...")
    await app.start()
    
    # Check Connection
    me = await app.get_me()
    logging.info(f"--- SYSTEM LIVE | USER: {me.first_name} (@{me.username}) ---")
    
    # Verify Target
    try:
        chat = await app.get_chat(TARGET_ID)
        logging.info(f"✅ TARGET VERIFIED: {chat.title}")
    except Exception as e:
        logging.error(f"❌ TARGET NOT FOUND: {e}")

    logging.info(f"MONITORING SOURCES: {SOURCE_IDS}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
