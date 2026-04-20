import os, logging, asyncio
from pyrogram import Client, filters

logging.basicConfig(level=logging.INFO)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_ID = -1001752144165  # Direct ID daal di hai taaki confusion na ho

def get_ids(var_name):
    raw = os.getenv(var_name, "")
    if not raw: return []
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids("SOURCE_PUBLIC_ID")

app = Client("market_precision_bot", api_id=int(API_ID), api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message(filters.chat(SOURCE_IDS))
async def mirror_messages(client, message):
    print(f"--> [DETECTED] New trade from {message.chat.id}", flush=True)
    try:
        # Copy attempt
        await message.copy(TARGET_ID)
        print(f"✅ SUCCESS: Mirrored to Market Precision", flush=True)
    except Exception as e:
        print(f"❌ ERROR: Cannot post to Target. Are you Admin? Error: {e}", flush=True)
        # Fallback text try
        try:
            if message.text:
                await client.send_message(TARGET_ID, message.text)
            elif message.caption:
                await message.copy(TARGET_ID)
            print("✅ SUCCESS: Mirrored via Fallback", flush=True)
        except Exception as e2:
            print(f"‼️ FATAL: Admin permission missing or Chat invalid: {e2}", flush=True)

async def main():
    await app.start()
    print(f"--- SYSTEM ONLINE | TARGET: {TARGET_ID} ---", flush=True)
    print(f"MONITORING SOURCES: {SOURCE_IDS}", flush=True)
    # Check if target is accessible
    try:
        await app.get_chat(TARGET_ID)
        print("✅ Target Channel Verified!", flush=True)
    except:
        print("⚠️ Target NOT found. Make sure you are Admin in Market Precision!", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
