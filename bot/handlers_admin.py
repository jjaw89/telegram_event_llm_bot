# bot/handlers_admin.py
import os
from telegram import Update
from telegram.ext import ContextTypes
from services.db import delete_all_events

ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")  # set this in .env to your user id

async def delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Simple auth: only allow a specific user id
    # if ADMIN_ID and str(update.effective_user.id) != str(ADMIN_ID):
    #     await update.message.reply_text("Sorry, you’re not allowed to run this command.")
    #     return

    delete_all_events()
    await update.message.reply_text("All events deleted and IDs reset.")
