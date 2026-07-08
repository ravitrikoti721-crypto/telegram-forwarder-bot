import os, logging, asyncio, re, sqlite3, time
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# 🆕 NEW: libraries needed to "read" text written inside images (OCR)
import pytesseract
from PIL import Image

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

# 🆕 NEW: Database now lives on the persistent disk mounted at /data,
# so it survives restarts and deploys instead of being wiped every time.
# Falls back to the old local path if /data doesn't exist yet (e.g. before the disk is attached).
DB_FILE = "/data/bot_data.db" if os.path.isdir("/data") else "bot_data.db"

# 🔥 HARD LOCK SYSTEM: Ek message ID ko ek baar mein ek hi baar process karne ke liye
active_locks = set()

# 🆕 NEW: Words to look for INSIDE images (screenshots). Add/remove words here anytime.
# Keep everything in lowercase - the checker converts image text to lowercase before comparing.
OCR_BLOCKED_KEYWORDS = [
    "kapil verma",
    "sg options",
    "sg cash",
    "sebi registered ra",
]

# --- DB FUNCTIONS ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS mapping (src_id INTEGER PRIMARY KEY, tgt_id INTEGER, last_text TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS blocked_msgs (src_id INTEGER PRIMARY KEY)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mapping_src_id ON mapping(src_id)")
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
    return text.strip()

# --- UPDATED BLOCKING ---
def is_blocked(msg):
    if msg.reply_to_msg_id and is_parent_blocked(msg.reply_to_msg_id): return True

    text = (msg.text or "").lower()
    promo_patterns = r'(twitter\.com|x\.com|t\.co|youtube\.com|youtu\.be|openinapp\.co|tinyurl\.com|bit\.ly|wa\.me|\+91)'
    if re.search(promo_patterns, text): return True

    promo_kws = ["advisory", "limited seats", "kapil verma", "sg cash", "discount offer"]
    if any(kw in text for kw in promo_kws): return True

    if msg.forward and msg.forward.chat:
        fwd_title = (msg.forward.chat.title or "").lower()
        if any(x in fwd_title for x in ["sg cash", "sebi", "kapil"]): return True
    return False

# 🆕 NEW: Reads the text written INSIDE a photo and checks it against OCR_BLOCKED_KEYWORDS.
# Only works on actual image files (screenshots/photos), not videos or PDFs.
def image_has_blocked_text(path):
    try:
        img = Image.open(path)
        extracted_text = pytesseract.image_to_string(img).lower()
        for keyword in OCR_BLOCKED_KEYWORDS:
            if keyword in extracted_text:
                logging.info(f"🛡️ OCR blocked image - found keyword: '{keyword}'")
                return True
        return False
    except Exception as e:
        # If OCR itself fails for any reason, we do NOT block the image just because of that -
        # we log the error and let the image through, so a broken OCR never silently kills your channel's mirroring.
        logging.error(f"OCR check failed (image was still allowed through): {e}")
        return False

# --- FIXED MIRROR ENGINE ---
async def process_msg(msg, is_edit=False):
    if msg.chat_id not in SOURCE_CHATS: return

    # 🔥 GLOBAL LOCK CHECK: Agar ye message ID abhi process ho rahi hai, toh turant drop karo
    if msg.id in active_locks:
        logging.info(f"🛡️ Duplicate network signal dropped for ID: {msg.id}")
        return

    # Lock lagao
    active_locks.add(msg.id)

    downloaded_path = None
    try:
        # DB check sabse pehle taaki lock ke andar confirmation ho sake
        tgt_id, last_text = get_mapping(msg.id)

        # Agar NewMessage event hai par DB mein entry mil gayi, toh isko edit ghoshit karo
        if not is_edit and tgt_id is not None:
            is_edit = True

        if is_blocked(msg):
            save_blocked(msg.id)
            return

        text = clean_text(msg.text)
        reply_to = None
        if msg.reply_to_msg_id:
            reply_to, _ = get_mapping(msg.reply_to_msg_id)

        # 🆕 NEW: If this message is a photo, download it first and OCR-check it
        # BEFORE deciding whether to send. If it contains a blocked name/brand, we
        # treat it exactly like a blocked text message (skip + remember it's blocked).
        if msg.media and msg.photo:
            downloaded_path = await client.download_media(msg)
            if downloaded_path and image_has_blocked_text(downloaded_path):
                save_blocked(msg.id)
                return

        # 🎯 CASE 1: NAYA MESSAGE
        if tgt_id is None and not is_edit:
            if not text and not msg.media: return

            if msg.media:
                # Reuse the download from the OCR step above if we already have it (photos),
                # otherwise download now (videos, documents, etc).
                path = downloaded_path or await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=text, reply_to=reply_to)
                if path and os.path.exists(path): os.remove(path)
                downloaded_path = None  # already cleaned up
            else:
                sent = await client.send_message(TARGET, text, link_preview=False, reply_to=reply_to)

            if sent:
                save_mapping(msg.id, sent.id, text)

        # 🎯 CASE 2: EDIT MESSAGE
        elif tgt_id is not None:
            last_text_str = last_text if last_text is not None else ""
            if last_text_str != text:
                try:
                    await client.edit_message(TARGET, tgt_id, text, link_preview=False)
                    save_mapping(msg.id, tgt_id, text)
                except Exception as e:
                    logging.error(f"Edit Failed: {e}")

    except Exception as e:
        logging.error(f"Error in engine: {e}")
    finally:
        # Clean up any leftover downloaded file (e.g. if it was blocked and never sent)
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
            except Exception:
                pass
        # 🔥 Network lag handle karne ke liye lock ko 4 second baad hi kholenge
        await asyncio.sleep(4)
        active_locks.discard(msg.id)

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def h1(event):
    await process_msg(event.message, is_edit=False)

@client.on(events.MessageEdited(chats=SOURCE_CHATS))
async def h2(event):
    await process_msg(event.message, is_edit=True)

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
    logging.info("🚀 V90 OCR-BLOCKADE ONLINE")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
