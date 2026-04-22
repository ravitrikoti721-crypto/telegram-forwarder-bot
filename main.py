import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 

# --- DATABASE SETUP ---
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
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# --- ADVANCED CLEANING ---
def clean_message(text):
    if not text: return ""
    if any(k.lower() in text.lower() for k in ["renew", "membership", "new video"]): return None
    
    # Remove SEBI Disclaimer specifically
    text = re.sub(r"Disclaimer\s*[:-].*?SEBI Registered RA.*?advisor before taking any trade", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"Disclaimer\s*[:-].*?SEBI Registered.*", "", text, flags=re.IGNORECASE | re.DOTALL)
    
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    for word in ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "Sunil"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    return text.strip()

async def mirror_logic(msg):
    try:
        if get_tgt_id(msg.id): return 

        cleaned_text = clean_message(msg.text)
        final_text = cleaned_text if cleaned_text else ""
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        sent_msg = None
        if msg.media:
            # 🚀 PROTECTED CONTENT BYPASS: Download first, then upload
            logging.info(f"📥 Downloading media from protected chat: {msg.id}")
            media_path = await client.download_media(msg)
            sent_msg = await client.send_file(TARGET, media_path, caption=final_text, reply_to=reply_to)
            if os.path.exists(media_path):
                os.remove(media_path) # Clean up file after upload
        elif cleaned_text:
            sent_msg = await client.send_message(TARGET, final_text, reply_to=reply_to)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Mirrored & Logged: {msg.id}")
        
    except Exception as e:
        logging.error(f"❌ Bypass Error: {e}")

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def handler(event):
    await mirror_logic(event.message)

async def poll_restricted():
    while True:
        try:
            source_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
            for s_id in source_ids:
                async for msg in client.iter_messages(s_id, limit=5):
                    await mirror_logic(msg)
            await asyncio.sleep(60)
        except:
            await asyncio.sleep(60)

async def main():
    await client.start()
    logging.info("--- V12 PROTECTED BYPASS ONLINE ---")
    client.loop.create_task(poll_restricted())
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
