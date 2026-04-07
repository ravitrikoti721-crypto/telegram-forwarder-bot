import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"


# 👉 Message handler (jo bhi message aayega, ye chalega)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text

        # print in logs
        print(f"📩 Message received: {text}")

        # reply back (optional)
        await update.message.reply_text(f"Received: {text}")

    except Exception as e:
        print("Error:", e)


# 👉 Main bot function
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # handler add karo
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("🚀 Bot running...")

    # start bot
    await app.run_polling()


# 👉 Entry point (IMPORTANT FIX)
if __name__ == "__main__":
    asyncio.run(main())
