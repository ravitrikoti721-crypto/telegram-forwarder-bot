import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")

# Target channel fixed
TARGET = -1001752144165 
# Public Source chats from env
SOURCE_CHATS = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]

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

# --- ADVANCED CLEANING & BLOCKING LOGIC ---
def clean_text(text):
    if not text: return ""
    lines = text.split('\n')
    # Filter out specific signatures and greetings
    cleaned_lines = [line for line in lines if "Hare Krishna" not in line and "Kapil Verma" not in line and "SEBI Registered" not in line]
    text = '\n'.join(cleaned_lines)
    
    # Remove Usernames
    text = re.sub(r'@\S+', '', text)
    
    # Text normalization
    final = text.strip()
    return final + "\u2063" if final else ""

def is_blocked(msg):
    text = (msg.text or "").lower()
    # 🔥 Twitter/X Link Restriction Logic (From Chat GPT)
    # Target exact patterns: twitter.com or x.com or t.co
    twitter_patterns = r'(?:twitter\.com|x\.com|t\.co)'
    if re.search(twitter_patterns, text):
        logging.info(f"🚫 Blocked Twitter Post: {msg.id}")
        return True
    
    # 🔥 New Smart SG Blocker: Check for Forward from problematic titles
    if msg.forward and msg.forward.chat:
        fwd_title = (msg.forward.chat.title or "").lower()
        # The image provided shows "SG Cash Training Group". We block keywords from this title.
        sg_block_kws = ["sg cash", "training group", "kapil verma", "sebi register"]
        if any(kw in fwd_title for kw in sg_block_kws):
            logging.info(f"🚫 Blocked SG Forward: {msg.id}")
            return True
            
    # Regular text blocking (Less strict to avoid false positives)
    block_kws = ["holding", "excellent stock"] # Only block extremely specific promo text
    if any(kw in text for kw in block_kws):
        return True
        
    return False

# --- MIRROR ENGINE ---
async def process_msg(msg):
    try:
        # Ignore old messages and blocked content
        if msg.date < START_TIME: return
        if is_blocked(msg): return

        tgt_id, last_text = get_mapping(msg.id)
        text = clean_text(msg.text)

        # Handle Reply (Tagging)
        reply_to = None
        if msg.reply_to_msg_id:
            reply_to, _ = get_mapping(msg.reply_to_msg_id)

        if not tgt_id:
            # Avoid sending blank messages after cleaning
            if not text and not msg.media: return
            
            if msg.media:
                # Mirror media with clean caption
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=text, reply_to=reply_to)
                if os.path.exists(path): os.remove(path)
            else:
                # Mirror text with link preview OFF
                sent = await client.send_message(TARGET, text, reply_to=reply_to, link_preview=False)

            if sent:
                save_mapping(msg.id, sent.id, text)
        
        elif last_text != text:
            # Preserve media on edit if possible, but edit_message primarily handles text
            await client.edit_message(TARGET, tgt_id, text, link_preview=False)
            save_mapping(msg.id, tgt_id, text)

    except Exception as e:
        logging.error(f"Error mirroring message: {e}")

# --- HANDLERS ---
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
                # Source deletion mirrors to target
                await client.delete_messages(TARGET, tgt_id)
                delete_mapping(msg_id)
            except Exception as e:
                logging.error(f"Error mirroring deletion: {e}")

async def main():
    await client.start()
    logging.info("🚀 V71 SMART-RESTRICT ONLINE")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
