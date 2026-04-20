import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_ID = int(os.getenv("TARGET_PUBLIC_ID").strip())

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

# Saari source IDs yahan hain
SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID") + get_ids("SOURCE_PRIVATE_ID")

app = Client("multi_userbot_final", api_id=int(API_ID), api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message() # Sabhi messages detect karo pehle
async def mirror_messages(client, message):
    # Logs mein dikhao ki koi message aaya hai
    print(f"--> [EVENT] Message received from: {message.chat.id}", flush=True)
    
    if message.chat.id in SOURCE_IDS:
        print(f"!!! MATCH !!! Copying from {message.chat.id} to {TARGET_ID}", flush=True)
        try:
            await message.copy(TARGET_ID)
            print("✅ SUCCESS: Copied!", flush=True)
        except Exception as e:
            print(f"⚠️ Copy failed, trying Text fallback: {e}", flush=True)
            try:
                if message.text:
                    await client.send_message(TARGET_ID, message.text)
                elif message.caption:
                    await message.copy(TARGET_ID)
                print("✅ SUCCESS: Copied via Fallback", flush=True)
            except Exception as e2:
                print(f"❌ FATAL: {e2}", flush=True)

async def main():
    await app.start()
    print(f"--- SYSTEM ONLINE | MONITORING {len(SOURCE_IDS)} SOURCES ---", flush=True)
    print(f"Sources: {SOURCE_IDS}", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Event loop warning fix
    asyncio.run(main())
