import json
import logging
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

MAPPINGS_FILE = "channels.json"


def load_mappings():
    try:
        with open(MAPPINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_mappings(data):
    with open(MAPPINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# 👉 Add mapping
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        source = context.args[0]
        dest = context.args[1]

        mappings = load_mappings()
        mappings[source] = dest
        save_mappings(mappings)

        await update.message.reply_text(f"✅ Added: {source} → {dest}")
    except:
        await update.message.reply_text("❌ Usage: /add source_channel destination_channel")


# 👉 List mappings
async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mappings = load_mappings()
    if not mappings:
        await update.message.reply_text("No mappings found.")
        return

    text = "\n".join([f"{k} → {v}" for k, v in mappings.items()])
    await update.message.reply_text(text)


# 👉 Forward messages
async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mappings = load_mappings()

    chat_id = str(update.message.chat.username)

    if chat_id in mappings:
        dest = mappings[chat_id]

        await context.bot.forward_message(
            chat_id=dest,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(MessageHandler(filters.ALL, forward))

    print("🚀 Bot running...")
    app.run_polling()
