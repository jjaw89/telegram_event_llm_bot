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
    notes: str | None = None

SCHEMA = {
  "type":"object","properties":{
    "title":{"type":"string"},
    "start_iso":{"type":"string"},
    "end_iso":{"type":"string","nullable":True},
    "location":{"type":"string","nullable":True},
    "capacity":{"type":"integer","nullable":True},
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
        f"Reference date for resolving missing year / relative dates: {ref_date}. "
        "Title: use the explicit event name; if multiple, pick the one nearest the 'When:' line; do not invent. "
        "Times: if a range like '7:00 PM - 9:00 PM' appears, set start_iso and end_iso; else end_iso=null. "
        "Location: prefer 'venue (details), address, city, province, country' if present. "
        "Capacity: convert written numbers to integers if unambiguous; else null. "
        "Notes: <= 280 chars; deduplicate repeated sentences; omit marketing fluff."
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role":"system","content": system},
            {"role":"user","content": f"Schema:\n{json.dumps(SCHEMA)}\n\nAnnouncement:\n{announcement}"}
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
        "notes": evt.notes,
        "raw": data
    }
