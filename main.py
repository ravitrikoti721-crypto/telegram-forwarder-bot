import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")

IS_TESTING = os.environ.get("TEST_MODE", "false").lower() == "true"

if IS_TESTING:
    SOURCE_CHATS = [int(i.strip()) for i in os.environ.get("SOURCE_TEST_ID", "").split(",") if i.strip()]
    TARGET = int(os.environ.get("TARGET_TEST_ID", "0"))
else:
    SOURCE_CHATS = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
    TARGET = -1001752144165 

START_TIME = datetime.now(timezone.utc)
DB_FILE = "bot_data.db"

# --- DB FUNCTIONS ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS mapping (src_id INTEGER PRIMARY KEY, tgt_id INTEGER, last_text TEXT)")
    conn.commit()
    conn.close()

def save_mapping(src_id, tgt_id, text):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR REPLACE INTO mapping VALUES (?, ?, ?)", (src_id, tgt_id, text))
    conn.commit()
    conn.close()

def get_mapping(src_id):
    conn = sqlite3.connect(DB_FILE)
    res = conn.execute("SELECT tgt_id, last_text FROM mapping WHERE src_id = ?", (src_id,)).fetchone()
    conn.close()
    return res if res else (None, None)

init_db()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# --- ADVANCED BLOCKING LOGIC ---
def is_blocked_content(msg):
    # Agar message text ya caption mein ye keywords hain toh block kar do
    text = (msg.text or "").lower()
    block_keywords = ["kapil verma", "sebi registered", "sg cash", "training group", "premium group"]
    
    for kw in block_keywords:
        if kw in text:
            return True
    return False

def clean_text(text):
    if not text: return ""
    
    # 1. Line Killer for "Hare Krishna"
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if "Hare Krishna" not in line]
    text = '\n'.join(cleaned_lines)
    
    # 2. Cleanup URLs & Usernames
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    # 3. Final Name Filter (Double safety)
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil", "Stock Precision"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    final = text.strip()
    return final + "\u2063" if final else ""

# --- MIRROR ENGINE ---
async def process_msg(msg):
    try:
        if msg.date < START_TIME: return
        
        # 🔥 Step 1: Check for Blocked Content (SG Cash etc.)
        if is_blocked_content(msg):
            logging.info(f"🚫 Blocked SG/SEBI Promo: {msg.id}")
            return

        tgt_id, last_text = get_mapping(msg.id)
        text = clean_text(msg.text)

        if not tgt_id:
            if not text and not msg.media: return
            
            # Media Handling
            if msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=text, link_preview=False)
                if os.path.exists(path): os.remove(path)
            else:
                sent = await client.send_message(TARGET, text, link_preview=False)

            if sent:
                save_mapping(msg.id, sent.id, text)

        elif last_text != text:
            await client.edit_message(TARGET, tgt_id, text, link_preview=False)
            save_mapping(msg.id, tgt_id, text)

    except Exception as e:
        logging.error(f"Error: {e}")

# --- HANDLERS ---
@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def h1(event): await process_msg(event.message)

@client.on(events.MessageEdited(chats=SOURCE_CHATS))
async def h2(event): await process_msg(event.message)

async def main():
    await client.start()
    logging.info("🚀 V66 SG-BLOCKER ACTIVE")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
