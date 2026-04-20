import os, logging, asyncio
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
    session_string=SESSION_STRING,
    in_memory=True # Purana kachra saaf rakhne ke liye
)

@app.on_message(filters.chat(list(CHANNELS_MAP.keys())))
async def mirror_messages(client, message):
    target_id = CHANNELS_MAP.get(message.chat.id)
    if target_id:
        try:
            # Restricted content bypass: Try copy first
            await message.copy(target_id)
            logging.info(f"✅ Mirrored to {target_id}")
        except Exception as e:
            logging.warning(f"⚠️ Copy failed (Restricted?), trying Text/Media send: {e}")
            try:
                # Agar copy fail ho toh manual message bhejo
                if message.text:
                    await client.send_message(target_id, message.text)
                elif message.caption:
                    await message.copy(target_id) # Media restricted bypass try
                logging.info(f"✅ Mirrored via fallback to {target_id}")
            except Exception as e2:
                logging.error(f"❌ Final Error: {e2}")

async def start_bot():
    logging.info("Checking connection...")
    await app.start()
    
    logging.info("Syncing channels and checking membership...")
    # Har channel ko check karega ki aap uske member ho ya nahi
    for source_id in CHANNELS_MAP.keys():
        try:
            chat = await app.get_chat(source_id)
            logging.info(f"✅ Found Source: {chat.title}")
        except Exception as e:
            logging.error(f"❌ Source ID {source_id} Not Found! Make sure your account is a member. Error: {e}")
    
    logging.info(f"🚀 UserBot is active! Monitoring {len(CHANNELS_MAP)} pairs.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
