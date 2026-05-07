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

def delete_mapping(src_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM mapping WHERE src_id = ?", (src_id,))
    conn.commit()
    conn.close()

init_db()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# --- CLEANING LOGIC (Updated with Line Killer) ---
def clean_text(text):
    if not text: return ""
    
    # 1. First, split into lines and remove any line containing "Hare Krishna"
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if "Hare Krishna" not in line]
    text = '\n'.join(cleaned_lines)
    
    # 2. Remove Twitter/X/URLs
    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com|t\.co)\/\S+', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text)
    
    # 3. Remove Usernames (@SG005 etc)
    text = re.sub(r'@\S+', '', text)
    
    # 4. Filter specific names
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil", "Stock Precision"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    final = text.strip()
    # Adding invisible character to preserve formatting
    return final + "\u2063" if final else ""

# --- UPDATED LINK DETECTION ---
def has_restricted_content(msg):
    if msg.text and re.search(r'https?:\/\/', msg.text): return True
    if msg.text and re.search(r'@\S+', msg.text): return True
    if msg.entities: return True
    return False

async def find_target_msg_id(source_reply_id):
    tgt_id, _ = get_mapping(source_reply_id)
    if tgt_id: return tgt_id
    try:
        source_msg = await client.get_messages(None, ids=source_reply_id)
        if source_msg and source_msg.text:
            cleaned = clean_text(source_msg.text)
            if not cleaned: return None
            search_text = cleaned[:50]
            async for m in client.iter_messages(TARGET, limit=100):
                if m.text and search_text in m.text: return m.id
    except: pass
    return None

# --- MIRROR ENGINE ---
async def process_msg(msg):
    try:
        if msg.date < START_TIME: return
        tgt_id, last_text = get_mapping(msg.id)
        text = clean_text(msg.text)

        if not tgt_id:
            if not text and not msg.media: return
            reply_to = await find_target_msg_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

            if has_restricted_content(msg):
                if not text: return
                sent = await client.send_message(TARGET, text, reply_to=reply_to, link_preview=False, parse_mode=None)
            elif msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=text, reply_to=reply_to, link_preview=False, parse_mode=None)
                if os.path.exists(path): os.remove(path)
            else:
                sent = await client.send_message(TARGET, text, reply_to=reply_to, link_preview=False, parse_mode=None)

            if sent:
                save_mapping(msg.id, sent.id, text)

        elif last_text != text:
            await client.edit_message(TARGET, tgt_id, text, link_preview=False, parse_mode=None)
            save_mapping(msg.id, tgt_id, text)

    except Exception as e:
        logging.error(f"Error: {e}")

# --- EVENT HANDLERS ---
@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def h1(event): await process_msg(event.message)

@client.on(events.MessageEdited(chats=SOURCE_CHATS))
async def h2(event): await process_msg(event.message)

@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            tgt_id, _ = get_mapping(msg_id)
            if tgt_id:
                await client.delete_messages(TARGET, tgt_id)
                delete_mapping(msg_id)
    except: pass

# --- SEQUENCE SYNC ---
async def speed_sync():
    while True:
        try:
            for s_id in SOURCE_CHATS:
                msgs = await client.get_messages(s_id, limit=10)
                for msg in reversed(msgs):
                    await process_msg(msg)
            await asyncio.sleep(5)
        except: await asyncio.sleep(10)

async def main():
    await client.start()
    logging.info(f"🚀 V64 PRECISE-CLEAN ONLINE")
    client.loop.create_task(speed_sync())
    await
