import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 

# --- PERSISTENT DATABASE ---
DB_FILE = "bot_data.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS mapping (src_id INTEGER PRIMARY KEY, tgt_id INTEGER)")
    conn.commit()
    conn.close()

def get_tgt_id(src_id):
    conn = sqlite3.connect(DB_FILE)
    res = conn.execute("SELECT tgt_id FROM mapping WHERE src_id = ?", (src_id,)).fetchone()
    conn.close()
    return res[0] if res else None

def save_id(src_id, tgt_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR REPLACE INTO mapping VALUES (?, ?)", (src_id, tgt_id))
    conn.commit()
    conn.close()

init_db()

# Connection optimization for faster response
client = TelegramClient(
    StringSession(SESSION), 
    API_ID, 
    API_HASH,
    connection_retries=None, # Infinite retries
    retry_delay=1            # Fast retry
)

def clean_message(text):
    if not text: return ""
    is_daily_update = "Update Daily" in text
    if not is_daily_update:
        if any(k.lower() in text.lower() for k in ["renew", "membership", "new video"]): return None

    # Targeted cleaning
    text = re.sub(r"(?i)For\s+Prime\s+Membership\s+ping\s+@sg\d+", "", text)
    text = re.sub(r"(?i)Stock\s+Gainers\s+is\s+not\s+SEBI\s+registered.*", "", text)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    for word in ["Stock Gainers", "Kapil Verma", "SEBI RA", "Stock Precision", "Sunil"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    return re.sub(r'\n\s*\n', '\n\n', text).strip()

async def mirror_logic(msg):
    try:
        if get_tgt_id(msg.id): return 
        
        cleaned_text = clean_message(msg.text)
        if cleaned_text is None: return
        
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            # Download/Upload bypass for protected chats
            path = await client.download_media(msg)
            sent_msg = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(path): os.remove(path)
        else:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Fast Mirrored: {msg.id}")
            
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID").split(",")]))
async def handler(event):
    await mirror_logic(event.message)

# Fast Polling fallback for restricted channels (Reduced to 10s)
async def fast_poll():
    while True:
        try:
            s_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID").split(",")]
            for s_id in s_ids:
                async for msg in client.iter_messages(s_id, limit=2):
                    await mirror_logic(msg)
            await asyncio.sleep(10) 
        except:
            await asyncio.sleep(15)

# Keep-Alive Ping
async def keep_awake():
    while True:
        logging.info("--- Keep-Alive Ping ---")
        await asyncio.sleep(300) # Ping every 5 mins

async def main():
    await client.start()
    logging.info("--- V16 BLAZING FAST ONLINE ---")
    client.loop.create_task(fast_poll())
    client.loop.create_task(keep_awake())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
