import os
import logging
import asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

# These come from your Render Environment Variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# This creates your "Bridge" between the channels
MAPPINGS = {
    os.getenv("SOURCE_PUBLIC_ID"): os.getenv("TARGET_PUBLIC_ID"),
    os.getenv("SOURCE_PRIVATE_ID"): os.getenv("TARGET_PRIVATE_ID")
}

# Convert IDs to numbers for the code to understand
CHANNELS_MAP = {int(k): int(v) for k, v in MAPPINGS.items() if k and v}

# Initialize your UserBot account
app = Client(
    "my_userbot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.chat(list(CHANNELS_MAP.keys())))
async def mirror_messages(client, message):
    target_id = CHANNELS_MAP.get(message.chat.id)
    if target_id:
        try:
            # .copy() is the "Secret Sauce" - it bypasses "Restricted Forwarding"
            await message.copy(target_id)
            logging.info(f"✅ Message mirrored to {target_id}")
        except Exception as e:
            logging.error(f"❌ Mirroring error: {e}")

if __name__ == "__main__":
    logging.info(f"🚀 UserBot is active! Monitoring {len(CHANNELS_MAP)} channels.")
    app.run()
