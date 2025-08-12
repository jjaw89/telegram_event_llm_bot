import os
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters
)
from handlers_parse import start_add, receive_announcement, cancel, AWAIT_ANNOUNCEMENT
from handlers_list import list_next

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is not set (see .env / docker-compose.yml).")

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    # /add → wait for next message as announcement
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", start_add)],
        states={
            AWAIT_ANNOUNCEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_announcement)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="add_conversation",
        persistent=False,
    )
    app.add_handler(add_conv)

    # /list → show next 5 events
    app.add_handler(CommandHandler("list", list_next))

    # sanity /start
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Hi! Use /add to paste an announcement, or /list to see the next 5 events.")))

    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()