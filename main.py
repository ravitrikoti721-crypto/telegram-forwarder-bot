import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_ID = -1001752144165 

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID")

app = Client("test_bot", api_id=int(API_ID), api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

# Sabse powerful filter: Saare messages detect karo
@app.on_message()
async def monitor_everything(client, message):
    # Ye line har message par log dikhayegi, chahe wo source ho ya na ho
    print(f"DEBUG: Message from {message.chat.id} | Text: {message.text[:20] if message.text else 'Media'}", flush=True)
    
    if message.chat.id in SOURCE_IDS:
        print(f"!!! MATCH !!! Copying to Target...", flush=True)
        try:
            await message.copy(TARGET_ID)
            print("✅ SUCCESS: Mirrored!", flush=True)
        except Exception as e:
            print(f"❌ Error: {e}", flush=True)

async def main():
    await app.start()
    print(f"--- TESTING MODE ONLINE ---", flush=True)
    print(f"Monitoring Sources: {SOURCE_IDS}", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
