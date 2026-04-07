import os
import logging
import asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

MAPPINGS = {
    os.getenv("SOURCE_PUBLIC_ID"): os.getenv("TARGET_PUBLIC_ID"),
    os.getenv("SOURCE_PRIVATE_ID"): os.getenv("TARGET_PRIVATE_ID")
}

CHANNELS_MAP = {int(k): int(v) for k, v in MAPPINGS.items() if k and v}

app = Client(
    "my_userbot",
    api_id=int(API_ID) if API_ID else None,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.chat(list(CHANNELS_MAP.keys())))
async def mirror_messages(client, message):
    target_id = CHANNELS_MAP.get(message.chat.id)
    if target_id:
        try:
            await message.copy(target_id)
            logging.info(f"✅ Mirrored to {target_id}")
        except Exception as e:
            logging.error(f"❌ Error: {e}")

async def start_bot():
    logging.info("Checking connection...")
    await app.start()
    
    # --- THIS PART FIXES THE 'PEER ID INVALID' ERROR ---
    logging.info("Syncing channels to prevent 'Peer ID Invalid'...")
    async for dialog in app.get_dialogs():
        # This forces the bot to 'meet' every channel you are in
        pass 
    # ---------------------------------------------------
    
    logging.info(f"🚀 UserBot is synced and active! Monitoring {len(CHANNELS_MAP)} pairs.")
    await asyncio.Event().wait() # Keep it running

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
