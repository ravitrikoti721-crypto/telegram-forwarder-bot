import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
# MUST start with -100 for channels!
TARGET_CHANNEL_ID = -1002233445566 

async def handle_copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This checks BOTH standard messages and channel posts
    source = update.channel_post or update.message
    
    if source:
        try:
            # We use copy_message to keep it looking clean
            await context.bot.copy_message(
                chat_id=TARGET_CHANNEL_ID,
                from_chat_id=source.chat_id,
                message_id=source.message_id
            )
            logging.info(f"✅ Successfully copied from {source.chat_id}")
        except Exception as e:
            logging.error(f"❌ Error copying: {e}")

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is missing!")
        return

    # 'allowed_updates' ensures the bot listens to channel posts specifically
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handler for everything (Text, Media, etc.)
    app.add_handler(MessageHandler(filters.ALL, handle_copy))
    
    logging.info("🚀 Bot is live and watching...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
