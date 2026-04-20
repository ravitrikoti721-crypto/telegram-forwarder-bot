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

    # 1. Skip messages that are purely promotional (Screenshot 4 logic)
    promo_keywords = ["Renew it Today", "PRIME plan", "Membership Is Expiring", "BE PART OF PRIME"]
    if any(key.lower() in text.lower() for key in promo_keywords):
        logging.info("🚫 Skipping purely promotional message.")
        return None

    # 2. Hatao Twitter aur X links (Screenshot 2 & 3)
    text = re.sub(r'https?:\/\/(www\.)?(twitter\.com|x\.com)\/\S+', '', text)
    
    # 3. Hatao Payment links (Cosmofeed, Revlu)
    text = re.sub(r'https?:\/\/(cosmofeed\.com|revlu\.in|revlu\.link)\/\S+', '', text)
    
    # 4. Hatao generic Telegram links aur usernames (Ping @SG005 logic)
    text = re.sub(r'https?:\/\/t\.me\/\S+', '', text)
    text = re.sub(r'@\S+', '', text)

    # 5. Specific Bad Words Removal (Kapil Verma, Stock Gainers, etc.)
    bad_words = [
        "Kapil Verma", "SEBI RA", "Stock Gainers", "Stock Precision",
        "Twitter", "X (formerly Twitter)", "Prime Membership", 
        "PRIME plan", "Ping", "Renew it Today", "Join our SEBI Registered",
        "guided advisory", "Advanced Equity Trading Group"
    ]
    
    for word in bad_words:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)

    # 6. Final Cleanup (Extra symbols aur empty lines)
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    
    # Agar cleaning ke baad sirf emojis ya junk bacha hai, toh None bhejenge
    if len(text) < 3 and not any(char.isalnum() for char in text):
        return None
        
    return text

@client.on(events.NewMessage(chats=SOURCE_IDS))
async def handler(event):
    logging.info(f"🎯 NEW SIGNAL from {event.chat_id}")
    try:
        original_text = event.raw_text
        cleaned_text = clean_message(original_text)
        
        # Agar clean_message ne None diya, toh matlab message skip karna hai
        if cleaned_text is None:
            logging.info("⏭️ Message filtered out completely.")
            return

        if event.media:
            await client.send_message(TARGET, cleaned_text, file=event.media)
        else:
            await client.send_message(TARGET, cleaned_text)
            
        logging.info("✅ SUCCESS: Professional Clean & Mirror")
    except Exception as e:
        logging.error(f"❌ ERROR: {e}")

async def main():
    await client.start()
    logging.info("--- 24/7 ELITE CLEANER ONLINE ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
