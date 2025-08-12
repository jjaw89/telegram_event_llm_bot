from telegram import Update
from telegram.ext import ContextTypes
from services.db import list_next_events

async def list_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_next_events(limit=5)
    if not rows:
        await update.message.reply_text("No upcoming events found.")
        return

    lines = []
    for r in rows:
        title = r["title"]
        start_local = r["start_local"]
        end_local = r["end_local"]
        when = f"{start_local}" if end_local is None else f"{start_local}–{end_local}"
        loc = r["location"] or "—"
        desc = (r["notes"] or "").strip()
        if len(desc) > 140:
            desc = desc[:137] + "…"
        lines.append(f"{title}\n{when}\n{loc}\n{desc}".strip())

    await update.message.reply_text("\n\n".join(lines))
