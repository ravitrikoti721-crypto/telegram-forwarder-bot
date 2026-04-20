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

# --- ADVANCED CLEANING LOGIC ---
def clean_message(text):
    if not text:
        return ""

    # 1. Skip messages that are purely promotional or YouTube alerts
    promo_keywords = [
        "Renew it Today", "PRIME plan", "Membership Is Expiring", 
        "Weekend Market Analysis", "Watch here", "new video", "LIVE!",
        "Finance with Sunil", "Sunit", "Sunil"
    ]
    if any(key.lower() in text.lower() for key in promo_keywords):
        logging.info("🚫 Skipping promotional/YouTube alert.")
        return None

    # 2. Hatao YouTube aur baaki social links
    text = re.sub(r'https?:\/\/(www\.)?(youtube\.com|youtu\.be|yt\.openinapp\.co)\/\S+', '', text)
    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com)\/\S+', '', text)
    
    # 3. Hatao Payment links (Cosmofeed, Revlu)
    text = re.sub(r'https?:\/\/(cosmofeed\.com|revlu\.in|revlu\.link)\/\S+', '', text)
    
    # 4. Hatao generic Telegram links aur usernames
    text = re.sub(r'https?:\/\/t\.me\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)

    # 5. Specific Bad Words Removal (Including new ones)
    bad_words = [
        "Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision",
        "Finance with Sunil", "Sunil", "Sunit", "Weekend Market Analysis",
        "Watch here", "new video", "PRIME plan", "Ping", "Join our SEBI Registered",
        "guided advisory", "Advanced Equity Trading Group"
    ]
    
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)

    # 6. Final Cleanup
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    
    # Check if anything meaningful is left
    if not text or (len(text) < 5 and not any(char.isalnum() for char in text)):
        return None
        
    return text

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    logging.info(f"🎯 NEW SIGNAL from {event.chat_id}")
    try:
        original_text = event.raw_text
        cleaned_text = clean_message(original_text)
        
        if cleaned_text is None:
            logging.info("⏭️ Message skipped (Promotion/YouTube).")
            return

        if event.media:
            # Video thumbnails ya promotional posters ko skip karne ke liye check
            await client.send_message(TARGET, cleaned_text, file=event.media)
        else:
            await client.send_message(TARGET, cleaned_text)
            
        logging.info("✅ SUCCESS: Professional Clean & Mirror")
    except Exception as e:
        logging.error(f"❌ ERROR: {e}")

async def main():
    await client.start()
    logging.info("--- 24/7 SURGICAL CLEANER ONLINE ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
