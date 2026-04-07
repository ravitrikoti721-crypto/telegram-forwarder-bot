import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# This helps us see errors in the Render logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# This looks for your token in the Render settings later
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Replace the numbers below with your target Channel ID (Must start with -100)
TARGET_CHANNEL_ID = -1001234567890 

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This checks if it's a message in a group or a post in a channel
    source = update.channel_post or update.message
    
    if source:
        try:
            # This copies the message to your destination channel
            await source.copy(chat_id=TARGET_CHANNEL_ID)
            print("Successfully copied a message!")
        except Exception as e:
            print(f"Error copying message: {e}")

async def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is missing in Environment Variables!")
        return

    # Build the bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Tell the bot to watch for EVERYTHING (text, photo, video)
    app.add_handler(MessageHandler(filters.ALL, handle_any_message))
    
    print("🚀 Bot is starting... I am watching your channels.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
