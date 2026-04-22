import os, logging, asyncio, re
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 # Market Precision Target

def get_ids():
    raw = os.getenv("SOURCE_PUBLIC_ID", "")
    return [int(i.strip()) for i in raw.split(",") if i.strip()]

SOURCE_IDS = get_ids()
client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# Memory to store IDs for replies
reply_map = {}

# --- CLEANING LOGIC ---
def clean_message(text):
    if not text: return ""
    
    # 1. Skip Promotional Posts
    promo_keywords = ["Renew", "Membership", "new video", "Subscribe", "Training"]
    if any(key.lower() in text.lower() for key in promo_keywords): 
        return None

    # 2. Disclaimer Removal (Finance With Sunil & Others)
    # Yeh pattern specifically SEBI disclaimer waale pure block ko uda dega
    disclaimer_pattern = r"(Disclaimer\s*[:-].*?SEBI Registered RA.*?advisor before taking any trade)"
    text = re.sub(disclaimer_pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    # 3. Clean Links & Usernames
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    # 4. Remove Brand Names
    bad_words = [
        "Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", 
        "Finance with Sunil", "Sunil", "Sunit", "REGISTERED RA", "Advanced Trading Group"
    ]
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    return re.sub(r'\n\s*\n', '\n\n', text).strip()

async def mirror_logic(msg):
    try:
        # Avoid duplicate mirroring
        if msg.id in reply_map: return 
        
        cleaned_text = clean_message(msg.text)
        final_text = cleaned_text if cleaned_text else ""

        # --- REPLY HANDLING ---
        # Bot restart hone par purani mapping memory se nikal jati hai
        reply_to = reply_map.get(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            sent_msg = await client.send_message(TARGET, final_text, file=msg.media, reply_to=reply_to)
        elif cleaned_text:
            sent_msg = await client.send_message(TARGET, final_text, reply_to=reply_to)
        else:
            # If no text left and no media, skip
            return

        # Store for future replies in current session
        reply_map[msg.id] = sent_msg.id
        logging.info(f"✅ Mirrored: {msg.id}")
        
    except Exception as e:
        logging.error(f"❌ Error in mirror_logic: {e}")

# Real-time event handler
@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    await mirror_logic(event.message)

# Background Polling for Restricted Channels
async def poll_restricted_channels():
    while True:
        try:
            for s_id in SOURCE_IDS:
                # Fetching latest 10 messages to ensure nothing is missed
                async for msg in client.iter_messages(s_id, limit=10):
                    if msg.id not in reply_map:
                        await mirror_logic(msg)
            await asyncio.sleep(45) 
        except Exception as e:
            logging.error(f"Polling Error: {e}")
            await asyncio.sleep(60)

async def main():
    await client.start()
    logging.info("--- SYSTEM V10 (FAST REPLY & CLEANER) ONLINE ---")
    
    # Run polling in the background
    client.loop.create_task(poll_restricted_channels())
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
