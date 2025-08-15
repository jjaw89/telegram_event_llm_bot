# bot/handlers_admin.py
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from bot.services.db_list_events_sorted import list_events_sorted
# need to import the function to edit an event

LOCAL_TZ = ZoneInfo("America/Vancouver")


async def select_event_entry(update: Update, context: ContextTypes.DEFAULT_TYPE, pattern="quick", action="edit") -> None:
    """_summary_

    Args:
        update (Update): _description_
        context (ContextTypes.DEFAULT_TYPE): _description_
        pattern (str, optional): _description_. Defaults to "quick".
        action (str, optional): _description_. Defaults to "edit".
    
    This function is the entry point for selecting an event.
    The pattern parameter allows the user to choose the order they want to select the events by:
    eg: /edit_event gives the quick option. A menue with the first 5 events in each of the possible sort orders.
    eg: /edit_event date jumps to the first page of events sorted by start_ts asc.
    
    The action parameter allows this menu to be used for different actions. 
    Possible future actions could include:
    select an event a user wants to rsvp to or see the details of an event.
    """
    
    if pattern == "quick":
        # Quick select event
        await select_event_quick(update, context, action=action)
    if pattern == "date":
        # Select event by date
        await select_event_by_date(update, context, action=action, page_number=0)
    if pattern == "created":
        # Select event by created_at
        await select_event_by_created(update, context, action=action, page_number=0)
    if pattern == "updated":
        # Select event by updated_at
        await select_event_by_updated(update, context, action=action, page_number=0)

    
    
async def select_event_quick(update: Update, context: ContextTypes.DEFAULT_TYPE, action = "view"):
    """

    We use this menu system to allow a user to select an event so that they can interact with it.
    The user can choose to list the events in the database sorted by
    start_ts asc, created_at desc, or updated_at desc.
    The user will initally be presented with the first event in each of the possible sort orders
    with buttons to view the first 5 events in the order of their choice.
    """
    # Query the database for the events we will display
    select = ["id", "title", "start_ts"]
    events = [
        list_events_sorted(select = select, sort_by="start_ts", asc=True, limit=1, offset=0),
        list_events_sorted(select = select, sort_by="created_at", asc=False, limit=1, offset=0),
        list_events_sorted(select = select, sort_by="updated_at", asc=False, limit=1, offset=0)
    ]
    
    # Build buttons for each event
    buttons = []
    for i, event in enumerate(events):
        text = f"{event["title"]} ({event["start_ts"].astimezone(LOCAL_TZ).strftime('%m-%d')})"
        call_back_data = f"event:{event["id"]}:"
        buttons.append([InlineKeyboardButton(text, callback_data=call_back_data)])
        
    buttons.append([ 
        InlineKeyboardButton("Date", callback_data='date'),
        InlineKeyboardButton("Created", callback_data='created'),
        InlineKeyboardButton("Updated", callback_data='updated')
        ],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]) # Exits the selection process
        
    # Create the inline keyboard markup
    reply_markup = InlineKeyboardMarkup(buttons)
    # Send the message with the inline keyboard
    await update.message.reply_text("Select an event or choose a sort order:", reply_markup=reply_markup)
    
    # if the update is "event:<event_id>:" then we will call the apropriate action function
    if update.callback_query and update.callback_query.data.startswith("event:"):
        event_id = int(update.callback_query.data.split(":")[1])
        if action == "edit":
            # Call the edit function for the selected event
            await edit_event(update, context, event_id) # To be implemented
    
    # If the user selects a sort order, we will call the appropriate function
    elif update.callback_query and update.callback_query.data in ["date", "created", "updated"]:
        pattern = update.callback_query.data
        if pattern == "date":
            await select_event_by_date(update, context, action=action, page_number=0)
        elif pattern == "created":
            await select_event_by_created(update, context, action=action, page_number=0)
        elif pattern == "updated":
            await select_event_by_updated(update, context, action=action, page_number=0)
    
    # If the user selects cancel we will exit the selection process
    # Question: After a user edits an event, does the program come back to this point?
    # If so, we should always exit the selection process if the program reaches this point and we would not have an elif.
    
    
    
async def select_event_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE, action, page_number=0):

async def select_event_by_created(update: Update, context: ContextTypes.DEFAULT_TYPE, action, page_number=0):
    
async def select_event_by_updated(update: Update, context: ContextTypes.DEFAULT_TYPE, action, page_number=0):

