import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
# This will read your mapping from Render's settings
SOURCE_ID = os.getenv("SOURCE_CHANNEL_ID")
TARGET_ID = os.getenv("TARGET_CHANNEL_ID")

async def handle_copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = update.channel_post or update.message
    if not source or not SOURCE_ID or not TARGET_ID:
        return

    # Check if the message is coming from the SEBI RA channel you specified
    if str(source.chat_id) == str(SOURCE_ID):
        try:
            # Clean copy: no "forwarded from" tag
            await context.bot.copy_message(
                chat_id=int(TARGET_ID),
                from_chat_id=source.chat_id,
                message_id=source.message_id
            )
            logging.info(f"✅ Trade copied to your channel!")
        except Exception as e:
            logging.error(f"❌ Copy failed: {e}")

async def main():
    if not BOT_TOKEN or not SOURCE_ID or not TARGET_ID:
        logging.error("❌ SETUP INCOMPLETE: Ensure BOT_TOKEN, SOURCE_CHANNEL_ID, and TARGET_CHANNEL_ID are set in Render.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_copy))
    
    logging.info(f"🚀 Bot starting. Monitoring: {SOURCE_ID} -> Sending to: {TARGET_ID}")
    
    # Use a simpler polling method that works better with Render's lifecycle
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Keep the bot running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logging.error(f"Fatal error: {e}")
