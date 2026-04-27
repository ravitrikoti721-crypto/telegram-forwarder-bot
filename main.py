import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 

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
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH, connection_retries=None, auto_reconnect=True)

def quick_clean(text):
    if not text: return ""
    # Links aur @usernames hatao (Logo block karne ke liye link_preview=False niche use kiya hai)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return text.strip()

# --- 1. NEW MESSAGE ---
@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def handler(event):
    try:
        msg = event.message
        if get_tgt_id(msg.id): return 
        
        cleaned_text = quick_clean(msg.text)
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            path = await client.download_media(msg)
            # link_preview=False ensures no external logos/previews appear
            sent_msg = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(path): os.remove(path)
        else:
            if not cleaned_text and not msg.text: return
            sent_msg = await client.send_message(TARGET, cleaned_text or msg.text, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Fast Mirror: {msg.id}")
    except Exception as e:
        logging.error(f"❌ Error: {e}")

# --- 2. EDIT HANDLER ---
@client.on(events.MessageEdited(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def edit_handler(event):
    try:
        tgt_id = get_tgt_id(event.message.id)
        if tgt_id:
            cleaned_text = quick_clean(event.message.text)
            await client.edit_message(TARGET, tgt_id, cleaned_text, link_preview=False)
            logging.info(f"✏️ Edited: {event.message.id}")
    except: pass

# --- 3. DELETE HANDLER ---
@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            tgt_id = get_tgt_id(msg_id)
            if tgt_id: 
                await client.delete_messages(TARGET, tgt_id)
                logging.info(f"🗑️ Deleted: {msg_id}")
    except: pass

async def main():
    await client.start()
    logging.info("--- V35 BALANCED MODE ONLINE ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
