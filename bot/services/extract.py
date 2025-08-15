import os, json
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ValidationError
from dateutil import parser as dp
import httpx

OLLAMA = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
MODEL  = os.getenv("LLM_MODEL", "gemma3:4b-it-qat")

class EventOut(BaseModel):
    title: str
    start_iso: str
    end_iso: str | None = None
    location: str | None = None
    capacity: int | None = None
    description: str | None = None 
    notes: str | None = None

SCHEMA = {
  "type":"object","properties":{
    "title":{"type":"string"},
    "start_iso":{"type":"string"},
    "end_iso":{"type":"string","nullable":True},
    "location":{"type":"string","nullable":True},
    "capacity":{"type":"integer","nullable":True},
    "description":{"type":"string","nullable":True},
    "notes":{"type":"string","nullable":True}
  },"required":["title","start_iso"]
}

def _to_utc(iso_str: str | None):
    if not iso_str: return None
    return dp.isoparse(iso_str).astimezone(timezone.utc).isoformat()

def _roll_end_if_needed(start_iso: str, end_iso: str | None, tz_name: str):
    if not end_iso: return None
    tz = ZoneInfo(tz_name)
    s_local = dp.isoparse(start_iso).astimezone(tz)
    e_local = dp.isoparse(end_iso).astimezone(tz)
    if e_local <= s_local:
        e_local = e_local + timedelta(days=1)
    return e_local.astimezone(timezone.utc).isoformat()

def _fmt_local(iso_str: str | None, tz_name: str) -> str | None:
    if not iso_str: return None
    tz = ZoneInfo(tz_name)
    dt = dp.isoparse(iso_str).astimezone(tz)
    # Example: Sun Jan 5, 1:00 PM
    return dt.strftime("%a %b %-d, %-I:%M %p")

async def extract_event(announcement: str, ref_date: str, tz_name: str = "America/Vancouver") -> dict:
    system = (
        "Return ONLY one JSON object matching the schema. If a field is unknown, use null. "
        f"Timezone: assume {tz_name} if missing and include the offset in all ISO times. "
        f"Reference date: {ref_date}. All decisions MUST be made relative to this date. "
        "If the announcement includes a month and day but no year, ALWAYS assume the reference year. "
        "If multiple date/time mentions exist, return the one that is NEXT or UPCOMING relative to the reference date. "
        "NEVER return a date in the past. This is critical. "
        "Title: use the explicit event name; if multiple, pick the one nearest the 'When:' line; do not invent. "
        "Ignore usernames or social media handles. Remove trailing handles, hashtags, or location tags like 'yyj'. "
        "Times: Extract both start_iso and end_iso if a time range appears — including informal formats such as '5:30 PM – 6:15 PM', '5 - 7pm', '5–7 PM', or 'between 5 and 7 PM'. Do not ignore ranges due to punctuation, formatting, or spacing. If only one time is present, set end_iso to null. "
        "Treat ranges like '5:30 PM – 6:15 PM' as same-day unless there's clear evidence of an overnight event (e.g. ending after midnight)."
        "If multiple times or time ranges appear, prefer the one that: (1) includes both start and end time, (2) is more specific, and (3) occurs in the future relative to the reference date."
        "For recurring events or if the date is missing, infer the next future date and time using context (e.g. weekday + time).""Location: prefer 'venue (name), address, city, province, country' if present. "
        "Location: Always include at least a venue name or hosting group name—never return just the city. If a city is not explicitly mentioned, default to 'Victoria, British Columbia, Canada'. If no venue is mentioned, use 'hosting group (name), city, province, country'. If location is vague or partial, append the default city information."
        "Capacity: convert written numbers to integers if unambiguous; else null. "
        "Description: Return EXACTLY ONE sentence (≤140 chars) summarizing the event’s *main activities* and vibe. "
        "Include whether it’s a dance party, workshop, social, etc. Highlight anything sensory, queer, or kink-related. "
        "Do NOT repeat the date/time/venue.\n"
        "Notes: Return up to 280 characters. Include extra details that didn’t fit in the description, like dress code, accessibility, theme, ticket info, or performances. "
        "If relevant, include safety policies (e.g. 'Consent required', '19+', 'Kink/fetish positive'). "
        "Deduplicate repeated sentences. Skip marketing fluff."
    )


    user_content = f"Schema:\n{json.dumps(SCHEMA)}\n\nAnnouncement:\n{announcement}"
    payload = {
        "model": MODEL,
        "messages": [
            {"role":"system","content": system},
            {"role":"user","content": user_content}
        ],
        "options": {"temperature": 0, "num_predict": 256, "num_ctx": 4096},
        "format": "json",
        "stream": False
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA}/api/chat", json=payload)
        r.raise_for_status()
        data = json.loads(r.json()["message"]["content"])

    # validate and normalize
    evt = EventOut.model_validate(data)
    start_utc = _to_utc(evt.start_iso)
    end_utc = _roll_end_if_needed(evt.start_iso, evt.end_iso, tz_name)

    # also compute display-local strings
    start_local = _fmt_local(evt.start_iso, tz_name)
    end_local = _fmt_local(evt.end_iso, tz_name) if end_utc else None

    return {
        "title": evt.title.strip(),
        "start_ts_utc": start_utc,
        "end_ts_utc": end_utc,
        "start_local": start_local,
        "end_local": end_local,
        "location": evt.location,
        "capacity": evt.capacity,
        "description": evt.description,
        "notes": evt.notes,
        "raw": data
    }
