import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Install these on Render (pip install Pillow pytesseract)
try:
    from PIL import Image
    import pytesseract
except ImportError:
    logging.warning("Please add Pillow and pytesseract to requirements.txt")

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

# --- IMAGE TEXT SCANNER (The OCR Fix) ---
def is_image_blocked(image_path):
    try:
        # 1. Image open karo aur resize karo scan speed ke liye
        img = Image.open(image_path).convert('L') # Convert to grayscale for better OCR
        
        # 2. Image ke andar ka text padho
        text_in_image = pytesseract.image_to_string(img).lower()
        
        # 3. Restricted Keywords
        # Stock Gainers/Precision ke logo aur promo text
        block_keywords = [
            "sg options", "training group", "kapil verma", "stock gainers", 
            "stock precision", "sebi registered", "prime day", "membership is expiring"
        ]
        
        if any(word in text_in_image for word in block_keywords):
            logging.info(f"🚫 Image Blocked by OCR Scanner: Found restricted keywords inside image.")
            return True
            
        return False
    except Exception as e:
        logging.error(f"OCR Error: {e}. If this happens on Render, Tesseract might not be installed.")
        return False

# --- TEXT CLEANING ---
def clean_message_text(text):
    if not text: return ""
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    # Remove obvious source names from captions
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Stock Precision Learning"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return text.strip()

@client.on(events.NewMessage(chats=[int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]))
async def handler(event):
    try:
        msg = event.message
        if get_tgt_id(msg.id): return 
        
        cleaned_text = clean_message_text(msg.text)
        reply_to = get_tgt_id(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            # Paid server memory optimization - Download to process
            path = await client.download_media(msg)
            
            # --- CRITICAL IMAGE SCAN ---
            # Agar image ke andar "SG Options" wagera mila toh message ko wahi drop karo
            if is_image_blocked(path):
                logging.info(f"🚫 Blocked image with internal branding: {msg.id}")
                if os.path.exists(path): os.remove(path)
                return 

            sent_msg = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
            if os.path.exists(path): os.remove(path)
        else:
            # Normal text processing
            if not cleaned_text and not msg.text: return
            sent_msg = await client.send_message(TARGET, cleaned_text or msg.text, reply_to=reply_to, link_preview=False)
        
        if sent_msg:
            save_id(msg.id, sent_msg.id)
            logging.info(f"✅ Instant Mirror: {msg.id}")
            
    except Exception as e:
        logging.error(f"❌ Error: {e}")

# High-Speed Backup Polling for Paid Tier
async def backup_poll():
    while True:
        try:
            s_ids = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
            for s_id in s_ids:
                async for msg in client.iter_messages(s_id, limit=3):
                    if not get_tgt_id(msg.id):
                        await handler(events.NewMessage.Event(msg))
            await asyncio.sleep(15) 
        except: await asyncio.sleep(20)

async def main():
    await client.start()
    logging.info("--- V32 OCR PROTECTED ONLINE (No Filters) ---")
    client.loop.create_task(backup_poll())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
