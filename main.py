import os, logging, asyncio
from pyrogram import Client

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET_ID = -1001752144165 

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID")

app = Client("rt_reset", api_id=API_ID, api_hash=API_HASH, session_string=SESSION, in_memory=True)

@app.on_message()
async def simple_test(client, message):
    # Duniya ka koi bhi message aayega toh ye line dikhni chahiye
    print(f"!!! MESSAGE DETECTED FROM: {message.chat.id} !!!", flush=True)
    
    if message.chat.id in SOURCE_IDS:
        try:
            await message.copy(TARGET_ID)
            print("✅ MIRROR SUCCESS", flush=True)
        except Exception as e:
            print(f"❌ MIRROR ERROR: {e}", flush=True)

async def main():
    await app.start()
    print(f"--- RESET COMPLETE | MONITORING: {SOURCE_IDS} ---", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
