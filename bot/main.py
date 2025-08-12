import json
import os
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import config
from event_admin import get_eventadmin_handlers
import event_admin.data_manager
from rsvp import (
    rsvp_callback,
    cancel_rsvp_callback,
    cancel_waitlist_callback,
    confirm_cancel_rsvp_callback,
    keep_rsvp_callback,
    confirm_cancel_waitlist_callback,
    keep_waitlist_callback    
)
from telegram import Update
from telegram.ext import ContextTypes
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update, context):
    """Respond to /start command with a friendly greeting."""
    await update.message.reply_text("Hello! I am the Victoria Pups Bot. How can I help you today?")

async def help_command(update, context):
    """Respond to /help command with a list of available commands."""
    help_text = (
        "Available commands:\n"
        "/start - Start interacting with the bot.\n"
        "/help - Show this help message.\n"
        "/rules - Post a summary of the rules. If posted in your private chat with the bot you can explore the full rules.\n"
        "/rulesadmin - From your own private chat with the bot you may post a full rule to the group chat.\n"
        "/postrule n - Posts full rule n (1 <= n <= 6).\n"
        "/admins - Show the group admin rolls.\n"
        "/links - Show some useful links.\n"
        "/debug - Print userID and chatID in the terminal."
    )
    await update.message.reply_text(help_text)

async def edit_event_start_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    print(f"Debug Info: Chat ID: {chat_id}, User ID: {user_id}")
    await update.message.reply_text("Debug info printed to terminal.")
    
async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A command to debug chat info and print it in the terminal."""
    chat = update.effective_chat
    chat_id = chat.id
    chat_type = chat.type
    chat_title = chat.title or "N/A"
    user = update.effective_user
    user_id = user.id if user else "N/A"
    user_name = user.full_name if user else "N/A"

    # Print chat details to the terminal
    print(f"[DEBUG] Chat ID: {chat_id}")
    print(f"[DEBUG] Chat Type: {chat_type}")
    print(f"[DEBUG] Chat Title: {chat_title}")
    print(f"[DEBUG] User ID: {user_id}")
    print(f"[DEBUG] User Name: {user_name}")

    # Try fetching more information about the chat
    try:
        chat_info = await context.bot.get_chat(chat_id)
        print(f"[DEBUG] Full chat info: {chat_info}")
    except Exception as e:
        print(f"[DEBUG] Could not fetch detailed chat info: {e}")

    # Reply with a simple acknowledgment
    await update.message.reply_text("Debug info printed to terminal.")

def main():
    # Initialize the application
    token = config.token
    app = Application.builder().token(token).build()

    # Ensure data directory and file exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Move up one level to get the project root directory
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    data_file = os.path.join(data_dir, "bot_data.json")

    if not os.path.exists(data_file):
        # Create empty data file
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump({"events": []}, f, ensure_ascii=False, indent=4)

    # Load data into bot_data
    with open(data_file, 'r', encoding='utf-8') as f:
        app.bot_data = json.load(f)  # e.g. {"events": [...]}

    # Add eventadmin handlers (the conversation handler)
    app.add_handler(get_eventadmin_handlers())
    app.add_handler(CallbackQueryHandler(rsvp_callback, pattern=r"^rsvp:\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_rsvp_callback, pattern=r"^cancelrsvp:\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_cancel_rsvp_callback, pattern=r"^confirmcancelrsvp:\d+$"))
    app.add_handler(CallbackQueryHandler(keep_rsvp_callback, pattern=r"^keeprsvp:\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_waitlist_callback, pattern=r"^cancelwaitlist:\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_cancel_waitlist_callback, pattern=r"^confirmcancelwaitlist:\d+$"))
    app.add_handler(CallbackQueryHandler(keep_waitlist_callback, pattern=r"^keepwaitlist:\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_waitlist_callback, pattern=r"^cancelwaitlist:\d+$"))
    
    app.add_handler(CommandHandler("debug", debug_command))
    # Start polling after all handlers are registered
    app.run_polling()

if __name__ == "__main__":
    main()