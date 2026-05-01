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

# --- THE INVISIBLE SHIELD CLEANER ---
def shield_clean(text):
    if not text: return ""
    
    # 1. Sabse pehle Twitter/X/T.co links ko jadd se mitao
    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com|t\.co)\/\S+', '', text)
    
    # 2. Baki saare general links uda do
    text = re.sub(r'https?:\/\/\S+', '', text)
    
    # 3. Hidden Character Injection (Invisible Shield)
    # Hum text ke har word ke beech ek invisible character daal denge taaki Telegram media fetch na kar sake
    if text:
        text = text.replace(" ", "\u200B ") # Zero-width space adds a layer of protection
    
    # 4. Branding removal
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil", "Stock Precision"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    return text.strip()

async def process_msg(msg):
    try:
        if msg.date < START_TIME: return
        tgt_id, last_text = get_mapping(msg.id)
        cleaned_text = shield_clean(msg.text)

        if not tgt_id:
            if not cleaned_text and not msg.media: return
            reply_to = get_mapping(msg.reply_to_msg_id)[0] if msg.reply_to_msg_id else None
            
            # FORCE PREVIEW OFF + SEND
            if msg.media:
                path = await client.download_media(msg)
                sent = await client.send_file(TARGET, path, caption=cleaned_text, reply_to=reply_to, link_preview=False)
                if os.path.exists(path): os.remove(path)
            else:
                sent = await client.send_message(TARGET, cleaned_text, reply_to=reply_to, link_preview=False)
            
            if sent:
                save_mapping(msg.id, sent.id, cleaned_text)
                # DOUBLE KILL: Edit message immediately to ensure no preview
                await asyncio.sleep(0.3)
                try:
                    await client.edit_message(TARGET, sent.id, cleaned_text, link_preview=False)
                except: pass

        elif last_text != cleaned_text:
            await client.edit_message(TARGET, tgt_id, cleaned_text, link_preview=False)
            save_mapping(msg.id, tgt_id, cleaned_text)
            
    except Exception as e:
        logging.error(f"Error: {e}")

# --- HANDLERS ---
@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def h1(event): await process_msg(event.message)

@client.on(events.MessageEdited(chats=SOURCE_CHATS))
async def h2(event): await process_msg(event.message)

@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            tgt_id, _ = get_mapping(msg_id)
            if tgt_id: await client.delete_messages(TARGET, tgt_id)
    except: pass

async def light_poll():
    while True:
        try:
            for s_id in SOURCE_CHATS:
                async for msg in client.iter_messages(s_id, limit=5):
                    await process_msg(msg)
            await asyncio.sleep(15)
        except: await asyncio.sleep(20)

async def main():
    await client.start()
    logging.info(f"--- V50 INVISIBLE-SHIELD ONLINE (Testing: {IS_TESTING}) ---")
    client.loop.create_task(light_poll())
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
