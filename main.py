import os, logging, asyncio, re, sqlite3, cv2, numpy as np
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timezone

# Install easyocr locally: pip install easyocr
import easyocr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
TARGET = -1001752144165 
SOURCE_CHATS = [int(i.strip()) for i in os.getenv("SOURCE_PUBLIC_ID", "").split(",") if i.strip()]

# Initialize OCR Reader (English)
reader = easyocr.Reader(['en'])

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

def clean_text(text):
    if not text: return ""
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if "Hare Krishna" not in line]
    text = '\n'.join(cleaned_lines)
    text = re.sub(r'https?:\/\/\S+|@\S+', '', text)
    for word in ["Kapil Verma", "Stock Gainers", "SEBI Registered", "Sunil"]:
        text = re.compile(re.escape(word), re.IGNORECASE).sub("", text)
    return text.strip() + "\u2063"

# 🔥 NEW: Function to read text FROM IMAGE
async def is_image_blocked(photo_path):
    try:
        results = reader.readtext(photo_path)
        full_image_text = " ".join([res[1].lower() for res in results])
        
        block_keywords = ["sg cash", "sebi", "kapil verma", "training group", "premium"]
        for kw in block_keywords:
            if kw in full_image_text:
                logging.info(f"🚫 OCR BLOCKED: Found '{kw}' in image.")
                return True
        return False
    except Exception as e:
        logging.error(f"OCR Error: {e}")
        return False

async def process_msg(msg):
    try:
        # 1. Check caption first
        caption = (msg.text or "").lower()
        if any(kw in caption for kw in ["kapil verma", "sebi registered", "sg cash"]):
            return

        # 2. If it's a photo, scan the content INSIDE the photo
        if msg.photo:
            path = await client.download_media(msg)
            if await is_image_blocked(path):
                if os.path.exists(path): os.remove(path)
                return
            
            # If photo is clean, mirror it
            cleaned_caption = clean_text(msg.text)
            await client.send_file(TARGET, path, caption=cleaned_caption)
            if os.path.exists(path): os.remove(path)
            
        elif msg.text:
            cleaned_text = clean_text(msg.text)
            if cleaned_text:
                await client.send_message(TARGET, cleaned_text)

    except Exception as e:
        logging.error(f"Error: {e}")

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def h1(event): await process_msg(event.message)

async def main():
    await client.start()
    logging.info("🚀 V67 IMAGE-SCANNER ACTIVE")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
