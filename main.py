import os, logging, asyncio, re
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 

def get_ids():
    raw = os.getenv("SOURCE_PUBLIC_ID", "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
reply_map = {}

# --- CLEANING LOGIC ---
def clean_message(text):
    if not text: return ""
    # Agar message mein yeh keywords hain toh pura skip kar do
    promo_keywords = ["Renew", "PRIME", "Membership", "Watch here", "new video", "Sunil", "Kapil Verma", "SG Options"]
    if any(key.lower() in text.lower() for key in promo_keywords): 
        return None

    # Hatao Links aur Usernames
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    # Hatao Creator ke names
    bad_words = ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "REGISTERED RA", "Advanced Trading Group"]
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    return re.sub(r'\n\s*\n', '\n\n', text).strip()

# --- HANDLERS ---

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    logging.info(f"📩 Message from {event.chat_id} detected.")
    try:
        cleaned_text = clean_message(event.raw_text)
        if cleaned_text is None: return

        # REPLY TRACKING
        reply_to = reply_map.get(event.reply_to_msg_id) if event.reply_to_msg_id else None

        # SENDING (No Delay for speed)
        if event.media:
            sent_msg = await client.send_message(TARGET, cleaned_text, file=event.media, reply_to=reply_to)
        else:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to)
        
        reply_map[event.id] = sent_msg.id
        logging.info(f"✅ SUCCESS: Mirrored msg {event.id}")
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.MessageEdited(chats=SOURCE_IDS))
async def edit_handler(event):
    try:
        target_msg_id = reply_map.get(event.id)
        if target_msg_id:
            cleaned_text = clean_message(event.raw_text)
            if cleaned_text:
                await client.edit_message(TARGET, target_msg_id, cleaned_text)
    except Exception as e: pass

@client.on(events.MessageDeleted())
async def delete_handler(event):
    try:
        for msg_id in event.deleted_ids:
            target_msg_id = reply_map.get(msg_id)
            if target_msg_id:
                await client.delete_messages(TARGET, target_msg_id)
                del reply_map[msg_id]
    except Exception as e: pass

async def main():
    await client.start()
    logging.info("--- SYSTEM V6 ONLINE (FAST MODE) ---")
    
    # Stock Precision restricted sync
    for s_id in SOURCE_IDS:
        try:
            e = await client.get_entity(s_id)
            logging.info(f"✅ Sync Successful: {e.title}")
        except: pass

    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
