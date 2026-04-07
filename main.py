import asyncio
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# This will store your mappings in the bot's memory
# Format: { "Source_ID": "Target_ID" }
mappings = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Forwarder Bot Active! Use /map [SourceID] [TargetID] to link channels.")

async def map_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Command usage: /map -100111 -100222
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /map <Source_Channel_ID> <Target_Channel_ID>")
        return
    
    source = context.args[0]
    target = int(context.args[1])
    mappings[source] = target
    await update.message.reply_text(f"✅ Linked! Messages from {source} will now copy to {target}")

async def handle_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = update.channel_post or update.message
    if not source:
        return

    source_id = str(source.chat_id)

    if source_id in mappings:
        target_id = mappings[source_id]
        try:
            await context.bot.copy_message(
                chat_id=target_id,
                from_chat_id=source.chat_id,
                message_id=source.message_id
            )
            logging.info(f"Copied from {source_id} to {target_id}")
        except Exception as e:
            logging.error(f"Error: {e}")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("map", map_channels))
    app.add_handler(MessageHandler(filters.ALL, handle_posts))
    
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
