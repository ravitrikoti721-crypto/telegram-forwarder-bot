import os, logging, asyncio, re
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

    # 1. Skip strictly promotional content (Captions check)
    promo_keywords = [
        "Renew it Today", "PRIME plan", "Membership Is Expiring", 
        "Weekend Market Analysis", "Watch here", "new video", 
        "Finance with Sunil", "Sunil", "Sunit", "SG Options Training",
        "Registered RA", "Kapil Verma"
    ]
    
    # Agar text mein inme se kuch bhi hai, toh skip kar do
    if any(key.lower() in text.lower() for key in promo_keywords):
        return None

    # 2. Hatao saare Links
    text = re.sub(r'https?:\/\/(www\.)?(youtube\.com|youtu\.be|yt\.openinapp\.co|twitter\.com|x\.com|cosmofeed\.com|revlu\.in|revlu\.link|t\.me)\/\S+', '', text)
    
    # 3. Hatao Usernames
    text = re.sub(r'@\S+', '', text)

    # 4. Remove Specific Brand Names from text
    bad_words = [
        "Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision",
        "Finance with Sunil", "Sunil", "Sunit", "SG Options Training",
        "Ping", "Join our SEBI Registered", "guided advisory", 
        "Advanced Equity Trading Group", "REGISTERED RA"
    ]
    
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)

    # 5. Final Cleanup
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    
    return text

# --- HANDLERS ---

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    try:
        # Check both raw_text (normal) and caption
        original_text = event.raw_text
        cleaned_text = clean_message(original_text)
        
        # Agar promotional hai toh skip
        if cleaned_text is None:
            logging.info(f"⏭️ Message {event.id} skipped due to promotion.")
            return

        reply_to = reply_map.get(event.reply_to_msg_id) if event.reply_to_msg_id else None

        if event.media:
            # Agar image ke caption mein promotional text hai, tab bhi skip hoga
            sent_msg = await client.send_message(TARGET, cleaned_text, file=event.media, reply_to=reply_to)
        else:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to)
        
        reply_map[event.id] = sent_msg.id
        
    except Exception as e:
        logging.error(f"❌ Error in NewMessage: {e}")

@client.on(events.MessageEdited(chats=SOURCE_IDS))
async def edit_handler(event):
    try:
        target_msg_id = reply_map.get(event.id)
        if target_msg_id:
            cleaned_text = clean_message(event.raw_text)
            target_msg = await client.get_messages(TARGET, ids=target_msg_id)
            
            if cleaned_text and target_msg and target_msg.text != cleaned_text:
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
        logging.error(f"❌ Error in Delete: {e}")

async def main():
    await client.start()
    logging.info("--- SYSTEM ONLINE (SCREENSHOT FILTER ENABLED) ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
