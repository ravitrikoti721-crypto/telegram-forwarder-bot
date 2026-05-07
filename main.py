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

# --- CLEANING & BLOCKING LOGIC ---
def clean_text(text):
    if not text: return ""
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if "Hare Krishna" not in line]
    text = '\n'.join(cleaned_lines)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil", "Stock Precision"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return text.strip() + "\u2063"

def is_blocked(msg):
    text = (msg.text or "").lower()
    # Twitter Link check (If post has twitter/x link, block it)
    if re.search(r'twitter\.com|x\.com|t\.co', text): return True
    # SG Ads keywords
    block_kws = ["holding", "short term", "excellent stock", "sebi", "kapil", "sg cash", "gain so far"]
    if any(kw in text for kw in block_kws): return True
    # If forwarded from SEBI/SG channel
    if msg.forward and msg.forward.chat:
        title = (msg.forward.chat.title or "").lower()
        if "sebi" in title or "stock" in title: return True
    return False

# --- MIRROR ENGINE ---
async def process_msg(msg):
    try:
        if msg.date < START_TIME: return
        if is_blocked(msg): return

        tgt_id, last_text = get_mapping(msg.id)
        text = clean_text(msg.text)

        # FIND REPLY TAG
        reply_to = None
        if msg.reply_to_msg_id:
            reply_to, _ = get_mapping(msg.reply_to_msg_id)

        if not tgt_id:
            if not text and not msg.media: return
            
            if msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=text, reply_to=reply_to)
                if os.path.exists(path): os.remove(path)
            else:
                sent = await client.send_message(TARGET, text, reply_to=reply_to, link_preview=False)

            if sent:
                save_mapping(msg.id, sent.id, text)
        
        elif last_text != text:
            await client.edit_message(TARGET, tgt_id, text, link_preview=False)
            save_mapping(msg.id, tgt_id, text)

    except Exception as e:
        logging.error(f"Error: {e}")

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def h1(event): await process_msg(event.message)

@client.on(events.MessageEdited(chats=SOURCE_CHATS))
async def h2(event): await process_msg(event.message)

async def main():
    await client.start()
    logging.info("🚀 V69 ULTIMATE-FAST ONLINE")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
