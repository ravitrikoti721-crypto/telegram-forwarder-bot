import os, logging, asyncio, re, sqlite3
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")

SOURCE_CHATS = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]
TARGET = -1001752144165 

START_TIME = datetime.now(timezone.utc)

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

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# --- CLEAN TEXT ---
def clean_text(text):
    if not text:
        return ""

    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com|t\.co)\/\S+', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text)

    return text.strip() + "\u2063"

# --- REMOVE PREVIEW COMPLETELY ---
def has_link(msg):
    if msg.raw_text:
        if re.search(r'https?:\/\/', msg.raw_text):
            return True
    if msg.entities:
        return True
    return False

# --- MAIN ---
async def process_msg(msg):
    try:
        if msg.date < START_TIME:
            return

        tgt_id, last_text = get_mapping(msg.id)
        text = clean_text(msg.text)

        if not tgt_id:

            reply_to = get_mapping(msg.reply_to_msg_id)[0] if msg.reply_to_msg_id else None

            # 🔥 CASE 1: MESSAGE WITH LINK → SEND ONLY TEXT (NO MEDIA)
            if has_link(msg):
                sent = await client.send_message(
                    TARGET,
                    text,
                    reply_to=reply_to,
                    link_preview=False,
                    parse_mode=None
                )

            # 🔥 CASE 2: PURE MEDIA (NO LINK)
            elif msg.media:
                path = await client.download_media(msg)

                sent = await client.send_file(
                    TARGET,
                    path,
                    caption=text,
                    reply_to=reply_to,
                    link_preview=False,
                    parse_mode=None,
                    force_document=True  # 🔥 KEY LINE
                )

                if os.path.exists(path):
                    os.remove(path)

            else:
                sent = await client.send_message(
                    TARGET,
                    text,
                    reply_to=reply_to,
                    link_preview=False,
                    parse_mode=None
                )

            if sent:
                save_mapping(msg.id, sent.id, text)

        elif last_text != text:
            await client.edit_message(
                TARGET,
                tgt_id,
                text,
                link_preview=False,
                parse_mode=None
            )
            save_mapping(msg.id, tgt_id, text)

    except Exception as e:
        logging.error(e)

# --- HANDLERS ---
@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def new_handler(event):
    await process_msg(event.message)

@client.on(events.MessageEdited(chats=SOURCE_CHATS))
async def edit_handler(event):
    await process_msg(event.message)

@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            tgt_id, _ = get_mapping(msg_id)
            if tgt_id:
                await client.delete_messages(TARGET, tgt_id)
    except:
        pass

# --- MAIN ---
async def main():
    await client.start()
    print("🚀 BOT RUNNING (NO LOGO MODE)")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
