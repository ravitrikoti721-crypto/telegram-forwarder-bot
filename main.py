import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

# Config
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET_ID = -1001752144165 

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    if not raw: return []
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID")

# Client setup (Simplified)
app = Client(
    "rt_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION
)

@app.on_message(filters.chat(SOURCE_IDS))
async def mirror(client, message):
    try:
        await message.copy(TARGET_ID)
        logging.info(f"✅ Mirrored from {message.chat.id}")
    except Exception as e:
        logging.error(f"❌ Error: {e}")

async def main():
    await app.start()
    logging.info(f"🚀 SYSTEM LIVE | MONITORING: {SOURCE_IDS}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
