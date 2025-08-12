# bot/main.py
import os
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters
)
from handlers_parse import start_add, receive_announcement, cancel, AWAIT_ANNOUNCEMENT
from handlers_list import list_next
from handlers_admin import delete_all

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is not set (see .env / docker-compose.yml).")

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", start_add)],
        states={ AWAIT_ANNOUNCEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_announcement)] },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="add_conversation",
        persistent=False,
    )
    app.add_handler(add_conv)

    app.add_handler(CommandHandler("list", list_next))
    app.add_handler(CommandHandler("deleteall", delete_all))

    async def _hi(update, context):
        await update.message.reply_text("Hi! Use /add to paste an announcement, or /list to see the next 5 events.")
    app.add_handler(CommandHandler("start", _hi))

    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
