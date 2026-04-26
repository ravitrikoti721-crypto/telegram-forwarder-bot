import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 

# --- CLEAN SIGNATURE ---
# Message ke end mein 2 line ka gap aur fir sirf naam
SIGNATURE = "\n\nKritika" 

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
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, connection_retries=None)

# --- CLEANING + SIGNATURE LOGIC ---
def clean_and_sign(text):
    if not text: return ""
    
    # 1. Branding aur Ads saaf karo
    text = re.sub(r"(?i)For\s+Prime\s+Membership\s+ping\s+@sg\d+", "", text)
    text = re.sub(r"(?i)Stock\s+Gainers\s+is\s+not\s+SEBI\s+registered.*", "", text)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    for word in ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "Sunil"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    cleaned = text.strip()
    
    # 2. Add "Kritika" at the end (Sirf tab jab message khali na ho)
    if cleaned:
        return f"{cleaned}{SIGNATURE}"
    return cleaned

# --- HANDLERS ---
@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def handler(event):
    try:
        msg = event.message
        if get_tgt_id(msg.id): return 
        
        final_text = clean_and_sign(msg.text)
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            path = await client.download_media(msg)
            # link_preview=False taaki Twitter/External logos na aayein
            sent_msg = await client.send_file(TARGET, path, caption=final_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(path): os.remove(path)
        else:
            sent_msg = await client.send_message(TARGET, final_text, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Mirrored for Kritika: {msg.id}")
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.MessageEdited(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def edit_handler(event):
    try:
        tgt_id = get_tgt_id(event.message.id)
        if tgt_id:
            final_text = clean_and_sign(event.message.text)
            await client.edit_message(TARGET, tgt_id, final_text, link_preview=False)
    except: pass

@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            tgt_id = get_tgt_id(msg_id)
            if tgt_id: await client.delete_messages(TARGET, tgt_id)
    except: pass

async def main():
    await client.start()
    logging.info("--- V26 CLEAN KRITIKA ONLINE ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
