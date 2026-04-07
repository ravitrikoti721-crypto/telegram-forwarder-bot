import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# 1. ADD LOGGING (Crucial for Render)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = "YOUR_ACTUAL_TOKEN_HERE"
TARGET_CHANNEL_ID = -1001234567890  # Replace with your destination channel ID

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This will copy any message (text, photo, video, doc) to the target channel
    if update.channel_post:
        await update.channel_post.copy(chat_id=TARGET_CHANNEL_ID)
    elif update.message:
        await update.message.copy(chat_id=TARGET_CHANNEL_ID)

async def main():
    # Build the application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handler to capture everything (Messages and Channel Posts)
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    
    print("🚀 Bot is starting...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
