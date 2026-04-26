import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 

# --- DATABASE ---
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
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, connection_retries=None)

# --- STRICT CLEANING ---
def clean_message(text):
    if not text: return ""
    
    # 1. Exception for "Update Daily" (Taki zaroori signals na ruke)
    is_daily_update = "Update Daily" in text
    
    # 2. Block direct promos
    if not is_daily_update:
        if any(k.lower() in text.lower() for k in ["renew", "membership", "new video", "gift"]): return None

    # 3. Targeted Cleaning (Links, Usernames, specific branding)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    text = re.sub(r"(?i)Stock\s+Gainers\s+is\s+not\s+SEBI\s+registered.*", "", text)
    text = re.sub(r"(?i)For\s+Prime\s+Membership\s+ping\s+@sg\d+", "", text)
    
    # 4. Remove Logo/Platform names
    for word in ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "Sunil", "X (formerly Twitter)"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    final_text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    
    # AGAR SIRF LOGO YA KUCH NAHI BACHA TOH SKIP
    if not is_daily_update and len(final_text) < 5: return None
    
    return final_text

async def mirror_logic(msg):
    try:
        if get_tgt_id(msg.id): return 

        cleaned_text = clean_message(msg.text)
        if cleaned_text is None: return
        
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        # CRITICAL: link_preview=False will stop the logo box from appearing
        if msg.media:
            path = await client.download_media(msg)
            sent_msg = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(path): os.remove(path)
        else:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Clean Mirror: {msg.id}")
            
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID").split(",")]))
async def handler(event):
    await mirror_logic(event.message)

async def main():
    await client.start()
    logging.info("--- V17 LOGO-BLOCKER READY ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
