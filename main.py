import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 

# --- DB SETUP ---
DB_FILE = "bot_data.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS mapping (src_id INTEGER PRIMARY KEY, tgt_id INTEGER)")
    conn.commit()
    conn.close()

def save_id(src_id, tgt_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR REPLACE INTO mapping VALUES (?, ?)", (src_id, tgt_id))
    conn.commit()
    conn.close()

def get_tgt_id(src_id):
    conn = sqlite3.connect(DB_FILE)
    res = conn.execute("SELECT tgt_id FROM mapping WHERE src_id = ?", (src_id,)).fetchone()
    conn.close()
    return res[0] if res else None

init_db()

# Optimized for Paid Tier - Heavy Retry & Fast Reconnect
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, 
                        connection_retries=None, 
                        auto_reconnect=True,
                        request_retries=10,
                        retry_delay=1)

def minimal_clean(text):
    if not text: return ""
    # Sirf links aur @usernames hatao, baki Metal Focus wagera sab aane do
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    return text.strip()

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def handler(event):
    try:
        msg = event.message
        if get_tgt_id(msg.id): return 
        
        cleaned_text = minimal_clean(msg.text)
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            # Paid server speed - Download and Upload
            path = await client.download_media(msg)
            sent_msg = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(path): os.remove(path)
        else:
            final_msg = cleaned_text if cleaned_text else msg.text
            sent_msg = await client.send_message(TARGET, final_msg, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Instant Mirror: {msg.id}")
            
    except Exception as e:
        logging.error(f"❌ Error: {e}")

# Added Polling as a secondary backup because Paid server can handle it
async def backup_poll():
    while True:
        try:
            s_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
            for s_id in s_ids:
                async for msg in client.iter_messages(s_id, limit=3):
                    if not get_tgt_id(msg.id):
                        await handler(events.NewMessage.Event(msg))
            await asyncio.sleep(15) # 15 second gap is safe for Paid Tier
        except: await asyncio.sleep(20)

async def main():
    await client.start()
    logging.info("--- V29 PAID TIER OPTIMIZED ONLINE ---")
    client.loop.create_task(backup_poll())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
