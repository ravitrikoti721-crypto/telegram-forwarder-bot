import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# This creates a dictionary of your Public and Private pairs
def get_mappings():
    mapping = {}
    # Pair 1: Public
    pub_source = os.getenv("SOURCE_PUBLIC_ID")
    pub_target = os.getenv("TARGET_PUBLIC_ID")
    if pub_source and pub_target:
        mapping[str(pub_source)] = int(pub_target)
    
    # Pair 2: Private
    priv_source = os.getenv("SOURCE_PRIVATE_ID")
    priv_target = os.getenv("TARGET_PRIVATE_ID")
    if priv_source and priv_target:
        mapping[str(priv_source)] = int(priv_target)
        
    return mapping

async def handle_copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = update.channel_post or update.message
    if not source:
        return

    # Get the latest mappings
    channel_map = get_mappings()
    source_id = str(source.chat_id)

    if source_id in channel_map:
        try:
            await context.bot.copy_message(
                chat_id=channel_map[source_id],
                from_chat_id=source.chat_id,
                message_id=source.message_id
            )
            logging.info(f"✅ Copied from {source_id} to {channel_map[source_id]}")
        except Exception as e:
            logging.error(f"❌ Copy failed: {e}")

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN missing!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_copy))
    
    logging.info("🚀 Multi-Channel Bot is Live!")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
