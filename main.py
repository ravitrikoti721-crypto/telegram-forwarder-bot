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

def delete_mapping(src_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM mapping WHERE src_id = ?", (src_id,))
    conn.commit()
    conn.close()

init_db()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, connection_retries=None, auto_reconnect=True)

# --- STACK CLEANER (Strict Logo Removal) ---
def final_clean(text):
    if not text: return ""
    # Sabse pehle Twitter links udao
    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com)\/\S+', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil", "Stock Precision"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return text.strip()

# --- MIRROR ENGINE ---
async def process_msg(msg):
    try:
        # Purane messages ko ignore karo (Flood Protection)
        if msg.date < START_TIME: return

        tgt_id, last_text = get_mapping(msg.id)
        cleaned_text = final_clean(msg.text)

        if not tgt_id:
            if not cleaned_text and not msg.media: return
            
            # Smart Tagging logic
            reply_to = None
            if msg.reply_to_msg_id:
                reply_to, _ = get_mapping(msg.reply_to_msg_id)

            if msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
                if os.path.exists(path): os.remove(path)
            else:
                sent = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
            
            if sent:
                save_mapping(msg.id, sent.id, cleaned_text)
                logging.info(f"✅ Live: {msg.id}")

        elif last_text != cleaned_text:
            # Edit Sync
            await client.edit_message(TARGET, tgt_id, cleaned_text, link_preview=False)
            save_mapping(msg.id, tgt_id, cleaned_text)
            logging.info(f"✏️ Edited: {msg.id}")

    except Exception: pass

# --- THE SYNC ENGINE (Fixed Delete Loop) ---
async def global_sync():
    while True:
        try:
            s_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
            for s_id in s_ids:
                # 1. Check for New & Edited
                async for msg in client.iter_messages(s_id, limit=10):
                    await process_msg(msg)

                # 2. Check for Deleted (Mapping cleanup)
                conn = sqlite3.connect(DB_FILE)
                # Hum pichle 20 mappings check karenge active session mein
                recorded = conn.execute("SELECT src_id, tgt_id FROM mapping ORDER BY src_id DESC LIMIT 20").fetchall()
                conn.close()

                for s_msg_id, t_msg_id in recorded:
                    try:
                        # Message exist karta hai ya nahi?
                        res = await client.get_messages(s_id, ids=s_msg_id)
                        if not res or isinstance(res, events.MessageDeleted) or res.id == 0:
                            await client.delete_messages(TARGET, t_msg_id)
                            delete_mapping(s_msg_id)
                            logging.info(f"🗑️ Deleted Successfully: {s_msg_id}")
                    except: pass
            
            await asyncio.sleep(12)
        except: await asyncio.sleep(15)

async def main():
    await client.start()
    logging.info("--- V45 STABLE SYNC ONLINE ---")
    client.loop.create_task(global_sync())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
