import os, logging, asyncio, re
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO)

# Config
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165

def get_ids():
    raw = os.getenv("SOURCE_PUBLIC_ID", "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# Mapping: {source_msg_id: target_msg_id}
reply_map = {}

def clean_message(text):
    if not text: return ""
    promo_keywords = ["Renew it Today", "PRIME plan", "Membership Is Expiring", "Watch here", "new video", "Finance with Sunil"]
    if any(key.lower() in text.lower() for key in promo_keywords): return None

    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    bad_words = ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "Sunil", "Sunit"]
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return re.sub(r'\n\s*\n', '\n\n', text).strip()

# 1. Naya Message Handler
@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    try:
        cleaned_text = clean_message(event.raw_text)
        if cleaned_text is None: return

        reply_to = reply_map.get(event.reply_to_msg_id) if event.reply_to_msg_id else None

        if event.media:
            sent_msg = await client.send_message(TARGET, cleaned_text, file=event.media, reply_to=reply_to)
        else:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to)
        
        reply_map[event.id] = sent_msg.id
    except Exception as e:
        logging.error(f"Error in NewMessage: {e}")

# 2. Edit Message Handler
@client.on(events.MessageEdited(chats=SOURCE_IDS))
async def edit_handler(event):
    try:
        target_msg_id = reply_map.get(event.id)
        if target_msg_id:
            cleaned_text = clean_message(event.raw_text)
            if cleaned_text:
                await client.edit_message(TARGET, target_msg_id, cleaned_text)
                logging.info(f"✅ Message {event.id} edited in Target.")
    except Exception as e:
        logging.error(f"Error in Edit: {e}")

# 3. Delete Message Handler
@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            target_msg_id = reply_map.get(msg_id)
            if target_msg_id:
                await client.delete_messages(TARGET, target_msg_id)
                logging.info(f"🗑️ Message {msg_id} deleted from Target.")
                del reply_map[msg_id]
    except Exception as e:
        logging.error(f"Error in Delete: {e}")

async def main():
    await client.start()
    logging.info("--- FULL SYNC (EDIT/DELETE/REPLY) ONLINE ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
