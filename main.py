import os, logging, asyncio, re, random
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165  # Market Precision

def get_ids():
    raw = os.getenv("SOURCE_PUBLIC_ID", "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# Mapping for replies/edits/deletes
reply_map = {}

# --- CLEANING LOGIC ---
def clean_message(text):
    if not text:
        return ""

    # Skip strictly promotional content
    promo_keywords = [
        "Renew it Today", "PRIME plan", "Membership Is Expiring", 
        "Weekend Market Analysis", "Watch here", "new video", 
        "Finance with Sunil", "Kapil Verma", "SG Options Training"
    ]
    if any(key.lower() in text.lower() for key in promo_keywords):
        return None

    # 1. Hatao saare Links (Twitter, YouTube, Payment, etc.)
    text = re.sub(r'https?:\/\/(www\.)?(youtube\.com|youtu\.be|yt\.openinapp\.co|twitter\.com|x\.com|cosmofeed\.com|revlu\.in|revlu\.link|t\.me)\/\S+', '', text)
    
    # 2. Hatao Usernames (@username)
    text = re.sub(r'@\S+', '', text)

    # 3. Specific Brand Names Removal
    bad_words = [
        "Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision",
        "Finance with Sunil", "Sunil", "Sunit", "PRIME plan", "SG Options Training",
        "REGISTERED RA", "Advanced Trading Group"
    ]
    
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)

    # 4. Final Cleanup
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return text

# --- HANDLERS ---

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    logging.info(f"🎯 New message detected from {event.chat_id}")
    try:
        cleaned_text = clean_message(event.raw_text)
        if cleaned_text is None:
            return

        # --- STEALTH DELAY (10 to 30 seconds) ---
        await asyncio.sleep(random.randint(10, 30))

        reply_to = reply_map.get(event.reply_to_msg_id) if event.reply_to_msg_id else None

        if event.media:
            sent_msg = await client.send_message(TARGET, cleaned_text, file=event.media, reply_to=reply_to)
        else:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to)
        
        reply_map[event.id] = sent_msg.id
        logging.info(f"✅ Mirrored msg {event.id}")
        
    except Exception as e:
        logging.error(f"❌ Error in NewMessage: {e}")

@client.on(events.MessageEdited(chats=SOURCE_IDS))
async def edit_handler(event):
    try:
        target_msg_id = reply_map.get(event.id)
        if target_msg_id:
            cleaned_text = clean_message(event.raw_text)
            if cleaned_text:
                await client.edit_message(TARGET, target_msg_id, cleaned_text)
    except Exception as e:
        if "message was not modified" not in str(e):
            logging.error(f"❌ Error in Edit: {e}")

@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            target_msg_id = reply_map.get(msg_id)
            if target_msg_id:
                await client.delete_messages(TARGET, target_msg_id)
                del reply_map[msg_id]
    except Exception as e:
        pass

# --- STARTUP SYNC & RUN ---
async def main():
    await client.start()
    logging.info("--- GHOST SYSTEM V4 ONLINE | SYNCING SOURCES ---")
    
    # Forceful Sync for Restricted Channels
    for s_id in SOURCE_IDS:
        try:
            entity = await client.get_entity(s_id)
            # Fetch last 1 message just to keep the connection alive
            async for msg in client.iter_messages(entity, limit=1):
                pass
            logging.info(f"✅ Successfully synced with: {entity.title}")
        except Exception as e:
            logging.warning(f"⚠️ Could not sync with ID {s_id}: {e}")

    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
