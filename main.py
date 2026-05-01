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

def strict_clean(text):
    if not text: return ""
    # Hard remove Twitter/X links to kill the logo preview
    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com)\/\S+', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil", "Stock Precision"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return text.strip()

async def find_target_msg_id(source_reply_id):
    tgt_id, _ = get_mapping(source_reply_id)
    if tgt_id: return tgt_id
    try:
        source_msg = await client.get_messages(None, ids=source_reply_id)
        if source_msg and source_msg.text:
            search_text = strict_clean(source_msg.text)[:50]
            async for m in client.iter_messages(TARGET, limit=200):
                if m.text and search_text in m.text: return m.id
    except: pass
    return None

# --- MAIN PROCESSOR ---
async def process_msg(msg):
    try:
        if msg.date < START_TIME: return
        tgt_id, last_text = get_mapping(msg.id)
        cleaned_text = strict_clean(msg.text)

        if not tgt_id:
            reply_to = None
            if msg.reply_to_msg_id:
                reply_to = await find_target_msg_id(msg.reply_to_msg_id)
            
            if msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
                if os.path.exists(path): os.remove(path)
            else:
                if not cleaned_text: return
                sent = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
            
            if sent: save_mapping(msg.id, sent.id, cleaned_text)
        elif last_text != cleaned_text:
            await client.edit_message(TARGET, tgt_id, cleaned_text, link_preview=False)
            save_mapping(msg.id, tgt_id, cleaned_text)
    except Exception: pass

# --- GLOBAL SYNC (EDITS & DELETES) ---
async def global_sync():
    while True:
        try:
            s_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
            for s_id in s_ids:
                # Get latest 10 messages from source
                current_msgs = await client.get_messages(s_id, limit=10)
                current_ids = [m.id for m in current_msgs]

                # Check our DB for messages from this source that might have been deleted
                conn = sqlite3.connect(DB_FILE)
                # Hum sirf unhi IDs ko check karenge jo bot ke start hone ke baad ki hain
                recorded = conn.execute("SELECT src_id, tgt_id FROM mapping").fetchall()
                conn.close()

                for src_id, tgt_id in recorded:
                    # Agar ID latest messages mein nahi hai aur source se gayab hai toh delete
                    if src_id not in current_ids:
                        try:
                            # Verify if it's actually deleted from source
                            check_msg = await client.get_messages(s_id, ids=src_id)
                            if not check_msg or isinstance(check_msg, events.MessageDeleted):
                                await client.delete_messages(TARGET, tgt_id)
                                delete_mapping(src_id)
                                logging.info(f"🗑️ Deleted Sync: {src_id}")
                        except: pass
                
                # Process New/Edited messages
                for msg in current_msgs:
                    await process_msg(msg)
            
            await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"Sync Error: {e}")
            await asyncio.sleep(15)

async def main():
    await client.start()
    logging.info("--- V44 ABSOLUTE SYNC ONLINE ---")
    client.loop.create_task(global_sync())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
