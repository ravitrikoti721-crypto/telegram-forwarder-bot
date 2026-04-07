import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# Logging helps you see what's happening on Render
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Put your own Public or Private Channel ID here (Must start with -100)
# You can change this ID later when you move to your Private channel
TARGET_CHANNEL_ID = -100XXXXXXXXXX 

async def handle_new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Detect if the message is from a channel or a group
    source = update.channel_post or update.message
    
    if source:
        try:
            # 'copy_message' is the secret—it sends a fresh copy with NO "forwarded" tag
            await context.bot.copy_message(
                chat_id=TARGET_CHANNEL_ID,
                from_chat_id=source.chat_id,
                message_id=source.message_id
            )
            logging.info(f"✅ Clean copy sent to your channel!")
        except Exception as e:
            logging.error(f"❌ Failed to copy: {e}")

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is missing in Render Environment Variables!")
        return

    # Build the bot app
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # This handler watches for EVERYTHING (text, images, videos, documents)
    app.add_handler(MessageHandler(filters.ALL, handle_new_post))
    
    logging.info("🚀 Forwarder Bot is Active and Watching...")
    
    # 'allowed_updates' ensures the bot sees channel posts immediately
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
