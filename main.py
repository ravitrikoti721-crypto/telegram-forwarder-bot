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

# --- RELAXED CLEANING LOGIC ---
def clean_message(text):
    if not text: return ""
    
    # Strictly promotional content block (Sirf renewals aur videos hatao)
    promo_keywords = ["Renew", "Membership Is Expiring", "new video", "Finance with Sunil"]
    if any(key.lower() in text.lower() for key in promo_keywords): 
        return None

    # Hatao Links aur @usernames (Twitter/YT links included)
    text = re.sub(r'https?:\/\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    
    # Hatao sirf Creator ke specific IDs/Names
    bad_words = ["Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision", "REGISTERED RA", "Advanced Trading Group"]
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    
    # Hatao hashtags jo gande lagte hain
    text = text.replace("#PRIMEPOWER", "").replace("#PRIME", "")
    
    return re.sub(r'\n\s*\n', '\n\n', text).strip()

async def mirror_logic(msg):
    try:
        if msg.id in reply_map: return 
        
        cleaned_text = clean_message(msg.text)
        if cleaned_text is None: return

        reply_to = reply_map.get(msg.reply_to_msg_id) if msg.reply_to_msg_id else None

        if msg.media:
            # Agar image ke sath caption hai toh cleaned_text jayega
            sent_msg = await client.send_message(TARGET, cleaned_text, file=msg.media, reply_to=reply_to)
        else:
            sent_msg = await client.send_message(TARGET, cleaned_text, reply_to=reply_to)
        
        reply_map[msg.id] = sent_msg.id
        logging.info(f"✅ Mirrored: {msg.id}")
    except Exception as e:
        logging.error(f"❌ Error: {e}")

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    await mirror_logic(event.message)

# Force Polling for Restricted Channels (Keeping it active)
async def poll_restricted_channels():
    while True:
        try:
            for s_id in SOURCE_IDS:
                async for msg in client.iter_messages(s_id, limit=5):
                    if msg.id not in reply_map:
                        await mirror_logic(msg)
            await asyncio.sleep(60) 
        except:
            await asyncio.sleep(60)

async def main():
    await client.start()
    logging.info("--- SYSTEM V8 BALANCED ONLINE ---")
    client.loop.create_task(poll_restricted_channels())
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
