# bot/main.py
import os
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters
)
from handlers_parse import start_add, receive_announcement, cancel, AWAIT_ANNOUNCEMENT
from handlers_list import list_next
from handlers_admin import delete_all

# Load token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is not set (see .env / docker-compose.yml).")

# Parse admin IDs from env
ADMIN_IDS = [int(x) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()]

def restrict_to_admins(func):
    """Decorator to restrict handler use to admins."""
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    # Add conversation with admin restriction
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", restrict_to_admins(start_add))],
        states={
            AWAIT_ANNOUNCEMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, restrict_to_admins(receive_announcement))
            ],
        },
        fallbacks=[CommandHandler("cancel", restrict_to_admins(cancel))],
        name="add_conversation",
        persistent=False,
    )
    app.add_handler(add_conv)

    # Restricted commands
    app.add_handler(CommandHandler("list", restrict_to_admins(list_next)))
    app.add_handler(CommandHandler("deleteall", restrict_to_admins(delete_all)))

    @restrict_to_admins
    async def _hi(update, context):
        await update.message.reply_text("Hi! Use /add to paste an announcement, or /list to see the next 5 events.")

    app.add_handler(CommandHandler("start", _hi))

    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
