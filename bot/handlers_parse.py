import os, json, asyncio
from telegram import Update
from telegram.ext import ContextTypes
from services.extract import extract_event
from services.db import upsert_event

AWAIT_ANNOUNCEMENT = 1

REF_DATE = os.getenv("REF_DATE", "2025-08-11")
TZ = os.getenv("TZ", "America/Vancouver")

async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Okay! Send the announcement text (paste it in full). Send /cancel to abort."
    )
    return AWAIT_ANNOUNCEMENT

async def receive_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("I didn’t receive any text—try again or /cancel.")
        return AWAIT_ANNOUNCEMENT

    try:
        event_norm = await extract_event(
            announcement=text,
            ref_date=REF_DATE,
            tz_name=TZ,
        )
    except Exception as e:
        await update.message.reply_text(f"Parse failed:\n{e}")
        return AWAIT_ANNOUNCEMENT

    try:
        event_id = upsert_event(event_norm)
    except Exception as e:
        await update.message.reply_text(f"DB save failed:\n{e}")
        return AWAIT_ANNOUNCEMENT

    # Friendly confirmation (local time is included by extract_event msg)
    title = event_norm.get("title")
    start_local = event_norm.get("start_local")
    end_local = event_norm.get("end_local")
    loc = event_norm.get("location") or "—"
    when = f"{start_local}" if not end_local else f"{start_local}–{end_local}"

    await update.message.reply_text(
        f"Saved (id {event_id}):\n"
        f"{title}\n"
        f"{when}\n"
        f"{loc}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END
