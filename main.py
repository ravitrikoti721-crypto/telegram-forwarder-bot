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

# --- STRICT CLEANING LOGIC ---
def clean_message(text):
    if not text: return ""
    
    # 1. Direct Promo/Ad Block
    promo_list = ["renew", "membership", "new video", "gift", "comment wins", "join prime"]
    if any(k.lower() in text.lower() for k in promo_list): 
        return None

    # 2. Remove Links (Twitter/X/Web) aur Usernames
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)

    # 3. Remove SEBI & Brand Disclaimers
    bad_patterns = [
        r"Disclaimer.*SEBI Registered RA.*trade",
        r"Disclaimer.*SEBI Registered.*",
        r"Stock precision learning.*",
        r"Finance with Sunil.*"
    ]
    for pattern in bad_patterns:
        text = re.compile(pattern, re.IGNORECASE | re.DOTALL).sub("", text)

    # 4. Remove Specific Names/Brands
    for word in ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "Sunil", "X (formerly Twitter)"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    final_text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    
    # Agar sirf hashtags ya 2-3 shabd bache hain toh block kar do (Logo prevent karne ke liye)
    if len(final_text) < 10 and "#" in final_text: return None
    
    return final_text

async def mirror_logic(msg):
    try:
        if get_tgt_id(msg.id): return 

        cleaned_text = clean_message(msg.text)
        # Agar text None hai toh matlab promo/brand hai, skip media too.
        if cleaned_text is None: return
        
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        sent_msg = None
        # Link preview disable karne ke liye link_preview=False use karenge
        if msg.media:
            logging.info(f"📥 Downloading protected media: {msg.id}")
            media_path = await client.download_media(msg)
            sent_msg = await client.send_file(TARGET, media_path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(media_path): os.remove(media_path)
        elif cleaned_text:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Mirrored: {msg.id}")
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def handler(event):
    await mirror_logic(event.message)

async def poll_restricted():
    while True:
        try:
            source_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
            for s_id in source_ids:
                # Limit=1 taaki deploy pe purana kachra na aaye
                async for msg in client.iter_messages(s_id, limit=1):
                    await mirror_logic(msg)
            await asyncio.sleep(45)
        except:
            await asyncio.sleep(60)

async def main():
    await client.start()
    logging.info("--- V13 LOGO & PREVIEW BLOCKER ONLINE ---")
    client.loop.create_task(poll_restricted())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
