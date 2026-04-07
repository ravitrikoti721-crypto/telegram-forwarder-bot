import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        text = update.message.text
        print(f"📩 {text}")
        await update.message.reply_text(f"Received: {text}")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("🚀 Bot running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
