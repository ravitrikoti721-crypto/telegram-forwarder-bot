import os
import logging
import asyncio
from pyrogram import Client, filters

# Setup logging to see the "Active" message in Render
logging.basicConfig(level=logging.INFO)

# These are pulled from your Render Environment Variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# This creates your "Bridge" between the channels
# It looks for the NEW keys you added to Render
MAPPINGS = {
    os.getenv("SOURCE_PUBLIC_ID"): os.getenv("TARGET_PUBLIC_ID"),
    os.getenv("SOURCE_PRIVATE_ID"): os.getenv("TARGET_PRIVATE_ID")
}

# Convert IDs to numbers so the UserBot understands them
CHANNELS_MAP = {int(k): int(v) for k, v in MAPPINGS.items() if k and v}

# Initialize your UserBot (acts as your account)
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
            # .copy() is the magic command for restricted content
            await message.copy(target_id)
            logging.info(f"✅ Message mirrored from {message.chat.id} to {target_id}")
        except Exception as e:
            logging.error(f"❌ Mirroring error: {e}")

if __name__ == "__main__":
    if not SESSION_STRING:
        logging.error("❌ ERROR: SESSION_STRING is missing in Render Environment!")
    else:
        logging.info(f"🚀 UserBot is active! Monitoring {len(CHANNELS_MAP)} pairs.")
        app.run()
