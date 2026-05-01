import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 
START_TIME = datetime.now(timezone.utc)

# --- DB SETUP ---
DB_FILE = "bot_data.db"
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
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, connection_retries=None, auto_reconnect=True)

def strict_clean(text):
    if not text: return ""
    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com)\/\S+', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil", "Stock Precision"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return text.strip()

# --- DEEP SEARCH FOR OLD MESSAGES ---
async def find_target_msg_id(source_reply_id):
    # 1. Pehle database mein check karo
    tgt_id, _ = get_mapping(source_reply_id)
    if tgt_id: return tgt_id

    # 2. Agar DB mein nahi mila (Purana Trade), toh channel mein search karo
    try:
        source_msg = await client.get_messages(None, ids=source_reply_id) # Source se message uthao
        if source_msg and source_msg.text:
            search_text = strict_clean(source_msg.text)[:50] # Pehle 50 chars se search karo
            async for m in client.iter_messages(TARGET, limit=300): # Aapke channel mein pichle 300 msg dekho
                if m.text and search_text in m.text:
                    return m.id
    except: pass
    return None

async def process_msg(msg):
    try:
        if msg.date < START_TIME: return

        tgt_id, last_text = get_mapping(msg.id)
        cleaned_text = strict_clean(msg.text)

        if not cleaned_text and not msg.media: return

        if not tgt_id:
            # Smart Reply Finder
            reply_to = None
            if msg.reply_to_msg_id:
                reply_to = await find_target_msg_id(msg.reply_to_msg_id)

            if msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
                if os.path.exists(path): os.remove(path)
            else:
                sent = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
            
            if sent:
                save_mapping(msg.id, sent.id, cleaned_text)
                logging.info(f"✅ Processed with Tagging: {msg.id}")

        elif last_text != cleaned_text:
            await client.edit_message(TARGET, tgt_id, cleaned_text, link_preview=False)
            save_mapping(msg.id, tgt_id, cleaned_text)

    except Exception as e:
        if "Message ID is invalid" not in str(e):
            logging.error(f"Error: {e}")

# Handlers
@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def h1(event): await process_msg(event.message)

@client.on(events.MessageEdited(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def h2(event): await process_msg(event.message)

async def sync_poll():
    while True:
        try:
            s_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
            for s_id in s_ids:
                async for msg in client.iter_messages(s_id, limit=5):
                    await process_msg(msg)
            await asyncio.sleep(10)
        except: await asyncio.sleep(15)

async def main():
    await client.start()
    logging.info("--- V43 DEEP-SEARCH TAGGING ONLINE ---")
    client.loop.create_task(sync_poll())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
