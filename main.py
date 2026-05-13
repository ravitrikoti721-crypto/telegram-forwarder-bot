import os, logging, asyncio, re, sqlite3, time
from telethon import TelegramClient, events
from telethon.sessions import StringSession

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

DB_FILE = "bot_data.db"
recent_processed = {}

# --- DB FUNCTIONS ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS mapping (src_id INTEGER PRIMARY KEY, tgt_id INTEGER, last_text TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS blocked_msgs (src_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def save_mapping(src_id, tgt_id, text):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR REPLACE INTO mapping VALUES (?, ?, ?)", (src_id, tgt_id, text))
    conn.commit()
    conn.close()

def save_blocked(src_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR REPLACE INTO blocked_msgs VALUES (?)", (src_id,))
    conn.commit()
    conn.close()

def is_parent_blocked(src_id):
    if not src_id: return False
    conn = sqlite3.connect(DB_FILE)
    res = conn.execute("SELECT src_id FROM blocked_msgs WHERE src_id = ?", (src_id,)).fetchone()
    conn.close()
    return True if res else False

def get_mapping(src_id):
    conn = sqlite3.connect(DB_FILE)
    res = conn.execute("SELECT tgt_id, last_text FROM mapping WHERE src_id = ?", (src_id,)).fetchone()
    conn.close()
    return res if res else (None, None)

def delete_mapping(src_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM mapping WHERE src_id = ?", (src_id,))
    conn.execute("DELETE FROM blocked_msgs WHERE src_id = ?", (src_id,))
    conn.commit()
    conn.close()

init_db()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# --- SMART CLEANING ---
def clean_text(text):
    if not text: return ""
    lines = text.split('\n')
    unwanted = ["hare krishna", "finance with sunil", "stock gainers", "sebi registered", "prime membership"]
    cleaned = [l for l in lines if not any(p in l.lower() for p in unwanted)]
    text = re.sub(r'@\S+', '', '\n'.join(cleaned))
    return text.strip() + "\u2063" if text.strip() else ""

# --- UPDATED BLOCKING (Hidden Link Proof) ---
def is_blocked(msg):
    # Agar ye kisi blocked message ka reply hai toh block karo
    if msg.reply_to_msg_id and is_parent_blocked(msg.reply_to_msg_id): return True
    
    # 🎯 FIX: Sirf visible text links scan karega, hidden/formatted links ko aane dega
    text = (msg.text or "").lower()
    promo_patterns = r'(twitter\.com|x\.com|t\.co|youtube\.com|youtu\.be|openinapp\.co|tinyurl\.com|bit\.ly|wa\.me|\+91)'
    if re.search(promo_patterns, text): return True
    
    promo_kws = ["advisory", "limited seats", "kapil verma", "sg cash", "discount offer"]
    if any(kw in text for kw in promo_kws): return True
    
    if msg.forward and msg.forward.chat:
        fwd_title = (msg.forward.chat.title or "").lower()
        if any(x in fwd_title for x in ["sg cash", "sebi", "kapil"]): return True
    return False

# --- MIRROR ENGINE ---
async def process_msg(msg, is_edit=False):
    try:
        if msg.chat_id not in SOURCE_CHATS: return
        
        # Check database first to prevent duplicates
        tgt_id, last_text = get_mapping(msg.id)

        # Duplicate check for New Messages only
        if not is_edit and not tgt_id:
            msg_key = f"{msg.chat_id}_{msg.id}"
            if msg_key in recent_processed and (time.time() - recent_processed[msg_key]) < 5: return
            recent_processed[msg_key] = time.time()

        if is_blocked(msg):
            save_blocked(msg.id)
            return

        text = clean_text(msg.text)
        reply_to = None
        if msg.reply_to_msg_id:
            reply_to, _ = get_mapping(msg.reply_to_msg_id)

        # 🎯 Logic: Agar ID nahi hai toh Naya Message, warna Edit
        if not tgt_id:
            if not text and not msg.media: return
            if msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=text, reply_to=reply_to)
                if os.path.exists(path): os.remove(path)
            else:
                sent = await client.send_message(TARGET, text, link_preview=False, reply_to=reply_to)
            if sent: save_mapping(msg.id, sent.id, text)
        
        elif last_text != text:
            # HAMESHA edit karega agar database mein ID mil gayi
            try:
                await client.edit_message(TARGET, tgt_id, text, link_preview=False)
                save_mapping(msg.id, tgt_id, text)
            except Exception as e:
                logging.error(f"Edit Failed: {e}")

    except Exception as e:
        logging.error(f"Error: {e}")

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def h1(event): await process_msg(event.message, is_edit=False)

@client.on(events.MessageEdited(chats=SOURCE_CHATS))
async def h2(event): await process_msg(event.message, is_edit=True)

@client.on(events.MessageDeleted())
async def delete_handler(event):
    for msg_id in event.deleted_ids:
        tgt_id, _ = get_mapping(msg_id)
        if tgt_id:
            try:
                await client.delete_messages(TARGET, tgt_id)
                delete_mapping(msg_id)
            except: pass

async def main():
    await client.start()
    logging.info("🚀 V84 STABLE - Hidden Links & Double Mirror Fixed")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
