import os, json
import psycopg
from psycopg.rows import dict_row

PG_DSN = os.getenv("PG_DSN", "postgresql://app:app@db:5432/eventsdb")

DDL = """
CREATE TABLE IF NOT EXISTS events (
  id SERIAL PRIMARY KEY,
  title     TEXT NOT NULL,
  start_ts  TIMESTAMPTZ NOT NULL,
  end_ts    TIMESTAMPTZ,
  location  TEXT,
  capacity  INT,
  notes     TEXT,
  raw       JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_events_title_start ON events (lower(title), start_ts);
"""

def _conn():
    return psycopg.connect(PG_DSN, row_factory=dict_row)

# Initialize schema once on import
with _conn() as c:
    with c.cursor() as cur:
        cur.execute(DDL)
        c.commit()

UPSERT_SQL = """
INSERT INTO events (title, start_ts, end_ts, location, capacity, notes, raw, updated_at)
VALUES (%(title)s, %(start_ts)s, %(end_ts)s, %(location)s, %(capacity)s, %(notes)s, %(raw)s, now())
ON CONFLICT (lower(title), start_ts)
DO UPDATE SET
  end_ts   = EXCLUDED.end_ts,
  location = EXCLUDED.location,
  capacity = EXCLUDED.capacity,
  notes    = EXCLUDED.notes,
  raw      = EXCLUDED.raw,
  updated_at = now()
RETURNING id;
"""

def upsert_event(n: dict) -> int:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(UPSERT_SQL, {
                "title": n["title"],
                "start_ts": n["start_ts_utc"],
                "end_ts": n["end_ts_utc"],
                "location": n.get("location"),
                "capacity": n.get("capacity"),
                "notes": n.get("notes"),
                "raw": json.dumps(n.get("raw", {}), ensure_ascii=False),
            })
            row = cur.fetchone()
            conn.commit()
            return row["id"]

LIST_NEXT_SQL = """
SELECT
  id, title, location, notes,
  (start_ts AT TIME ZONE 'America/Vancouver') AS start_local,
  CASE WHEN end_ts IS NULL THEN NULL
       ELSE (end_ts AT TIME ZONE 'America/Vancouver') END AS end_local
FROM events
WHERE start_ts >= now()
ORDER BY start_ts
LIMIT %(limit)s;
"""

def list_next_events(limit: int = 5) -> list[dict]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(LIST_NEXT_SQL, {"limit": limit})
            return cur.fetchall()
