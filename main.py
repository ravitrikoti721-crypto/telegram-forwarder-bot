import os, logging, asyncio
from pyrogram import Client, filters

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment Variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET_ID = -1001752144165  # Market Precision

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    if not raw: return []
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID")

# Client Initialization
app = Client(
    "rt_final_copier",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
    in_memory=True
)

@app.on_message(filters.chat(SOURCE_IDS))
async def mirror_handler(client, message):
    logging.info(f"🎯 SIGNAL DETECTED from {message.chat.id}")
    try:
        # Step 1: Try Direct Copy
        await message.copy(TARGET_ID)
        logging.info("✅ SUCCESS: Mirrored to Market Precision")
    except Exception as e:
        logging.error(f"⚠️ Copy failed ({e}), trying Text Fallback...")
        try:
            # Step 2: Fallback for Restricted Channels
            if message.text:
                await client.send_message(TARGET_ID, message.text)
            elif message.caption:
                await client.send_message(TARGET_ID, message.caption)
            logging.info("✅ SUCCESS: Mirrored via Fallback")
        except Exception as e2:
            logging.error(f"❌ FATAL ERROR: {e2}")

@app.on_message(filters.me & filters.private)
async def test_self(client, message):
    if message.text == "ping":
        await message.reply("pong! System is alive. ✅")
        logging.info("PING-PONG Test successful!")

async def main():
    logging.info("Starting UserBot...")
    await app.start()
    
    # Syncing: Ye line IDs recognize karne mein madad karti hai
    logging.info("Syncing dialogues...")
    async for dialog in app.get_dialogs(limit=20):
        pass
    
    me = await app.get_me()
    logging.info(f"--- SYSTEM ONLINE ---")
    logging.info(f"User: {me.first_name} (@{me.username})")
    logging.info(f"Monitoring Sources: {SOURCE_IDS}")
    logging.info(f"Target ID: {TARGET_ID}")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
