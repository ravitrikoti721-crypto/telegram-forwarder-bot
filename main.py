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

def clean_message(text):
    if not text: return ""
    
    # 1. Check for Daily Updates (Always allow)
    is_daily_update = "Update Daily" in text or "Performance" in text
    
    # 2. Strict Promo Filter
    if not is_daily_update:
        if any(k.lower() in text.lower() for k in ["renew", "membership", "join prime"]): return None

    # 3. Clean Branding but Keep Message Context
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    # Remove specific brand names
    for word in ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "Sunil"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    return re.sub(r'\n\s*\n', '\n\n', text).strip()

async def mirror_logic(msg):
    try:
        if get_tgt_id(msg.id): return 

        cleaned_text = clean_message(msg.text)
        
        # Smart Check: Agar message khali hai aur media bhi nahi hai, toh skip
        if not cleaned_text and not msg.media: return
        
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        sent_msg = None
        # Agar asli media hai (Photo/Document), toh download karke upload karo
        if msg.media and not msg.web_preview:
            logging.info(f"📸 Genuine Media detected: {msg.id}")
            path = await client.download_media(msg)
            sent_msg = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(path): os.remove(path)
        # Agar sirf text bacha hai (ya link preview block kiya hai)
        elif cleaned_text or msg.text:
            final_to_send = cleaned_text if cleaned_text else "New Update (Link Removed)"
            sent_msg = await client.send_message(TARGET, final_to_send, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Mirrored: {msg.id}")
            
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID").split(",")]))
async def handler(event):
    await mirror_logic(event.message)

async def main():
    await client.start()
    logging.info("--- V18 SMART MEDIA FILTER ONLINE ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
