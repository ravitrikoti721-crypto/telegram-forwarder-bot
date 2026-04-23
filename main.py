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

# --- UPDATED CLEANING LOGIC (V14) ---
def clean_message(text):
    if not text: return ""
    
    # 1. Agar message "Update Daily" wala hai, toh block nahi karna (Exception)
    is_daily_update = "Update Daily" in text
    
    # 2. General Promo Block (sirf tab jab Daily Update na ho)
    if not is_daily_update:
        promo_list = ["renew", "membership is expiring", "new video", "training"]
        if any(k.lower() in text.lower() for k in promo_list): 
            return None

    # 3. Hatao specific words jo aapne mana kiye hain
    # (a) "For Prime Membership ping @sg005"
    text = re.sub(r"(?i)For\s+Prime\s+Membership\s+ping\s+@sg\d+", "", text)
    # (b) "SEBI Registered RA" wala part
    text = re.sub(r"(?i)Stock\s+Gainers\s+is\s+not\s+SEBI\s+registered.*", "", text)
    text = re.sub(r"(?i)Stock\s+Gainers\s+SEBI\s+registered\s+RA", "", text)
    # (c) Baaki links aur usernames
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)

    # 4. Creator Brand Names
    bad_words = ["Stock Gainers", "Kapil Verma", "SEBI RA", "Stock Precision", "Sunil"]
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    final_text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return final_text if final_text else None

async def mirror_logic(msg):
    try:
        if get_tgt_id(msg.id): return 
        
        cleaned_text = clean_message(msg.text)
        if cleaned_text is None: return
        
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            media_path = await client.download_media(msg)
            sent_msg = await client.send_file(TARGET, media_path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(media_path): os.remove(media_path)
        elif cleaned_text:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Mirrored Daily Update/Signal: {msg.id}")
            
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def handler(event):
    await mirror_logic(event.message)

async def main():
    await client.start()
    logging.info("--- V14 DAILY UPDATE ENABLED ONLINE ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
