import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Apna target channel ID yahan likhein (Example: -1001234567890)
TARGET_CHANNEL_ID = -1001234567890 

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = update.channel_post or update.message
    if source:
        try:
            await source.copy(chat_id=TARGET_CHANNEL_ID)
            logging.info("Message copied successfully!")
        except Exception as e:
            logging.error(f"Error copying message: {e}")

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is missing!")
        return

    # Build the application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handler
    application.add_handler(MessageHandler(filters.ALL, handle_any_message))
    
    # Start the bot
    logging.info("🚀 Bot starting...")
    
    # Ye part Render ke liye sabse best hai
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        # Bot ko chalta rakhne ke liye infinite loop
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        # Direct asyncio.run ki jagah hum manually loop handle kar rahe hain
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        pass
