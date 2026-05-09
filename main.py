import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")

# Switching Logic
IS_TESTING = os.environ.get("TEST_MODE", "false").lower() == "true"

if IS_TESTING:
    SOURCE_CHATS = [int(i.strip()) for i in os.environ.get("SOURCE_TEST_ID", "").split(",") if i.strip()]
    TARGET = int(os.environ.get("TARGET_TEST_ID", "0"))
    logging.info("🛠️ MODE: TESTING")
else:
    SOURCE_CHATS = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
    TARGET = -1001752144165 
    logging.info("🚀 MODE: PRODUCTION")

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
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# --- ADVANCED BLOCKING LOGIC ---
def is_blocked(msg):
    text = (msg.text or "").lower()
    
    # 1. Promo & Link Keywords (YouTube, WhatsApp, Payment, TinyURL)
    promo_patterns = r'(twitter\.com|x\.com|t\.co|youtube\.com|youtu\.be|tinyurl\.com|wa\.me|\+91)'
    if re.search(promo_patterns, text): return True
    
    # 2. Advisory & Sales Keywords
    sales_kws = ["advisory", "discount", "offer", "link to join", "limited seats", "premium group", "kapil verma", "sg cash"]
    if any(kw in text for kw in sales_kws): return True
    
    # 3. Forward Header Block (For SG/Kapil Images)
    if msg.forward and msg.forward.chat:
        fwd_title = (msg.forward.chat.title or "").lower()
        if any(x in fwd_title for x in ["sg cash", "sebi", "kapil", "stock gainers"]): return True
            
    return False

def clean_text(text):
    if not text: return ""
    lines = text.split('\n')
    # Filter signatures
    cleaned_lines = [line for line in lines if "Hare Krishna" not in line and "Finance With Sunil" not in line]
    text = '\n'.join(cleaned_lines)
    text = re.sub(r'@\S+', '', text)
    return text.strip() + "\u2063" if text.strip() else ""

# --- MIRROR ENGINE ---
async def process_msg(msg):
    try:
        if msg.chat_id not in SOURCE_CHATS: return
        if is_blocked(msg): return

        tgt_id, last_text = get_mapping(msg.id)
        text = clean_text(msg.text)

        # Tagging logic
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
                sent = await client.send_message(TARGET, text, link_preview=False, reply_to=reply_to)

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
    logging.info("🚀 V77 ULTIMATE STABILITY ONLINE")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
