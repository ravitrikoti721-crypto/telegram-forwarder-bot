import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

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

app = Client(
    "rt_final_clean",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
    in_memory=True  # Isse purani database ka chakkar khatam ho jayega
)

@app.on_message(filters.chat(SOURCE_IDS))
async def mirror_logic(client, message):
    try:
        # Copy attempt
        await message.copy(TARGET_ID)
        logging.info(f"✅ SUCCESS: Mirrored from {message.chat.id}")
    except Exception as e:
        logging.error(f"⚠️ Copy failed: {e}")
        # Fallback for restricted content
        try:
            if message.text:
                await client.send_message(TARGET_ID, message.text)
            elif message.caption:
                await message.copy(TARGET_ID)
            logging.info("✅ SUCCESS: Mirrored via Fallback")
        except Exception as e2:
            logging.error(f"❌ Final Failure: {e2}")

async def main():
    logging.info("Starting Bot...")
    await app.start()
    
    # --- FORCE SYNC CHANNELS ---
    logging.info("Syncing channels to prevent 'Peer ID Invalid'...")
    try:
        async for dialog in app.get_dialogs(limit=30):
            pass
        logging.info("✅ Sync Complete")
    except Exception as e:
        logging.error(f"Sync Warning: {e}")

    logging.info(f"🚀 SYSTEM LIVE | MONITORING: {SOURCE_IDS}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
