import asyncio
import json
import os
import logging

from telethon import TelegramClient, events
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPINGS_FILE = os.path.join(BASE_DIR, "channels.json")
SESSION_FILE = os.path.join(BASE_DIR, "userbot_session")


def load_mappings() -> dict:
    try:
        with open(MAPPINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_mappings(data: dict) -> None:
    with open(MAPPINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


mappings: dict = load_mappings()


# ── Commands ──────────────────────────────────────────────────────────────────


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        source = context.args[0]
        dest = context.args[1]
    except (IndexError, TypeError):
        await update.message.reply_text("Usage: /add @source @destination")
        return

    if not source.startswith("@") or not dest.startswith("@"):
        await update.message.reply_text(
            "Both channels must start with @ (e.g. @channelname)"
        )
        return

    mappings[source] = dest
    save_mappings(mappings)
    await update.message.reply_text(f"✅ Added: {source} → {dest}")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        source = context.args[0]
    except (IndexError, TypeError):
        await update.message.reply_text("Usage: /remove @source")
        return

    if source in mappings:
        del mappings[source]
        save_mappings(mappings)
        await update.message.reply_text(f"✅ Removed: {source}")
    else:
        await update.message.reply_text(f"Not found: {source}")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not mappings:
        await update.message.reply_text(
            "No channel mappings configured.\n\nUse /add @source @destination to add one."
        )
    else:
        lines = [f"• {src} → {dst}" for src, dst in mappings.items()]
        text = "Current channel mappings:\n\n" + "\n".join(lines)
        await update.message.reply_text(text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Telegram Channel Forwarder\n\n"
        "Commands:\n"
        "/add @source @destination — Forward messages from source to destination\n"
        "/remove @source — Stop forwarding from a source channel\n"
        "/list — Show all active mappings\n"
        "/help — Show this message"
    )
    await update.message.reply_text(text)


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

    @client.on(events.NewMessage)
    async def forwarder(event: events.NewMessage.Event) -> None:
        try:
            chat = await event.get_chat()
            username = getattr(chat, "username", None)
            if username and f"@{username}" in mappings:
                dest = mappings[f"@{username}"]
                await client.send_message(dest, event.message)
                logger.info("Forwarded message from @%s to %s", username, dest)
        except Exception as exc:
            logger.error("Error forwarding message: %s", exc)

    # Start the Telethon userbot (reads session file; no interactive prompt)
    await client.start()

    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        try:
            chat = await event.get_chat()
            username = getattr(chat, "username", None)

            print("Incoming message from:", username)

            if username:
                for src, dest in mappings.items():
                    if username == src.replace("@", ""):
                        print(f"Forwarding from {src} to {dest}")
                        await client.forward_messages(dest, event.message)

        except Exception as e:
            print("Error:", e)

    me = await client.get_me()
    logger.info("Userbot signed in as %s (@%s)", me.first_name, me.username)

    # Build the PTB bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("help", cmd_help))

    async with app:
        await app.start()

        await app.updater.start_polling()
        logger.info("Bot is running. Commands: /add /remove /list /help")

        # Keep both running until Telethon disconnects
        await client.run_until_disconnected()

        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
