# bot/handlers_parse.py
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from services.extract import extract_event
from services.db import upsert_event
import asyncio

AWAIT_ANNOUNCEMENT = 1

REF_DATE = os.getenv("REF_DATE", "2025-08-11")
TZ = os.getenv("TZ", "America/Vancouver")
LOCAL_TZ = ZoneInfo(TZ)

def _fmt_same_day_range(s: datetime, e: datetime) -> str:
    date_str = s.strftime("%a %b %-d")
    return f"{date_str} • {s.strftime('%-I:%M %p')}–{e.strftime('%-I:%M %p')}"

def _fmt_cross_day_range(s: datetime, e: datetime) -> str:
    left  = f"{s.strftime('%a %b %-d')}, {s.strftime('%-I:%M %p')}"
    right = f"{e.strftime('%a %b %-d')}, {e.strftime('%-I:%M %p')}"
    return f"{left} → {right}"

def _roll_end_if_needed(s_local: datetime, e_local: datetime | None) -> datetime | None:
    if e_local is None:
        return None
    if e_local <= s_local:
        return e_local + timedelta(days=1)
    return e_local

async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Okay! Send the announcement text (paste it in full). Send /cancel to abort."
    )
    return AWAIT_ANNOUNCEMENT

# async def receive_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     text = (update.message.text or "").strip()
#     if not text:
#         await update.message.reply_text("I didn’t receive any text—try again or /cancel.")
#         return AWAIT_ANNOUNCEMENT

#     tz = ZoneInfo("America/Vancouver")
#     ref_date = datetime.now(tz).date().isoformat()  # e.g., "2025-08-13"
    
#     try:
#         event_norm = await extract_event(
#             announcement=text,
#             ref_date=ref_date,
#             tz_name="America/Vancouver",
#         )
#     except Exception as e:
#         await update.message.reply_text("Parse failed:\n" + str(e))
#         return AWAIT_ANNOUNCEMENT

#     try:
#         event_id = upsert_event(event_norm)
#     except Exception as e:
#         await update.message.reply_text("DB save failed:\n" + str(e))
#         return AWAIT_ANNOUNCEMENT

#     title = (event_norm.get("title") or "Untitled event").strip()
#     loc   = (event_norm.get("location") or "—").strip()
#     desc  = (event_norm.get("description") or "").strip()

#     s_utc_iso = event_norm.get("start_ts_utc")
#     e_utc_iso = event_norm.get("end_ts_utc")

#     s_local = datetime.fromisoformat(s_utc_iso).astimezone(LOCAL_TZ)
#     e_local = datetime.fromisoformat(e_utc_iso).astimezone(LOCAL_TZ) if e_utc_iso else None
#     e_local = _roll_end_if_needed(s_local, e_local)

#     if e_local is None:
#         when = s_local.strftime("%a %b %-d") + " • " + s_local.strftime("%-I:%M %p")
#     else:
#         when = (_fmt_same_day_range(s_local, e_local)
#                 if s_local.date() == e_local.date()
#                 else _fmt_cross_day_range(s_local, e_local))

#     parts = [f"Saved (id {event_id}):", title, when, loc]
#     if desc:
#         parts.append(desc)

#     await update.message.reply_text("\n".join(parts))
#     return ConversationHandler.END

BUFFER_DURATION = 3  # seconds to wait for additional message parts

async def receive_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if "announcement_buffer" not in context.chat_data:
        context.chat_data["announcement_buffer"] = {}
    
    buffer = context.chat_data["announcement_buffer"].setdefault(user_id, [])
    message = (update.message.text or "").strip()

    if not message:
        await update.message.reply_text("I didn’t receive any text—try again or /cancel.")
        return AWAIT_ANNOUNCEMENT

    buffer.append(message)

    # Store the latest time we saw a message
    context.chat_data["announcement_last_seen"] = datetime.now()

    # Wait a moment to see if more messages come in
    await asyncio.sleep(BUFFER_DURATION)

    # If nothing new was seen during the wait, proceed
    if datetime.now() - context.chat_data["announcement_last_seen"] < timedelta(seconds=BUFFER_DURATION - 1):
        return AWAIT_ANNOUNCEMENT  # more messages still arriving

    # Combine the buffered parts
    full_announcement = "\n".join(buffer)
    context.chat_data["announcement_buffer"].pop(user_id, None)

    # --- proceed with extract/save as before ---
    try:
        event_norm = await extract_event(
            announcement=full_announcement,
            ref_date=datetime.now(ZoneInfo(TZ)).date().isoformat(),
            tz_name=TZ,
        )
    except Exception as e:
        await update.message.reply_text("Parse failed:\n" + str(e))
        return AWAIT_ANNOUNCEMENT

    try:
        event_id = upsert_event(event_norm)
    except Exception as e:
        await update.message.reply_text("DB save failed:\n" + str(e))
        return AWAIT_ANNOUNCEMENT

    # Format and send response
    title = (event_norm.get("title") or "Untitled event").strip()
    loc   = (event_norm.get("location") or "—").strip()
    desc  = (event_norm.get("description") or "").strip()

    s_utc_iso = event_norm.get("start_ts_utc")
    e_utc_iso = event_norm.get("end_ts_utc")

    s_local = datetime.fromisoformat(s_utc_iso).astimezone(LOCAL_TZ)
    e_local = datetime.fromisoformat(e_utc_iso).astimezone(LOCAL_TZ) if e_utc_iso else None
    e_local = _roll_end_if_needed(s_local, e_local)

    if e_local is None:
        when = s_local.strftime("%a %b %-d") + " • " + s_local.strftime("%-I:%M %p")
    else:
        when = (_fmt_same_day_range(s_local, e_local)
                if s_local.date() == e_local.date()
                else _fmt_cross_day_range(s_local, e_local))

    parts = [f"Saved (id {event_id}):", title, when, loc]
    if desc:
        parts.append(desc)

    await update.message.reply_text("\n".join(parts))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END
