import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        print(update.message.text)
        await update.message.reply_text("Received")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("🚀 Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
