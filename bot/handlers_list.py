from telegram import Update
from telegram.ext import ContextTypes
from services.db import list_next_events
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

LOCAL_TZ = ZoneInfo("America/Vancouver")

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

async def list_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_next_events(limit=5)
    if not rows:
        await update.message.reply_text("No upcoming events found.")
        return

    blocks = []
    for r in rows:
        title = r["title"]
        loc   = r["location"] or "—"
        desc  = (r.get("description") or "").strip()

        # Convert to local tz
        s_local = r["start_ts"].astimezone(LOCAL_TZ)
        e_local = r["end_ts"].astimezone(LOCAL_TZ) if r["end_ts"] else None
        e_local = _roll_end_if_needed(s_local, e_local)

        # Build the when line
        if e_local is None:
            when = f"{s_local.strftime('%a %b %-d')} • {s_local.strftime('%-I:%M %p')}"
        else:
            if s_local.date() == e_local.date():
                when = _fmt_same_day_range(s_local, e_local)
            else:
                when = _fmt_cross_day_range(s_local, e_local)

        # Keep description short in the list view
        if len(desc) > 140:
            desc = desc[:137] + "…"

        block = f"{title}\n{when}\n{loc}"
        if desc:
            block += f"\n{desc}"
        blocks.append(block)

    await update.message.reply_text("\n\n".join(blocks))
