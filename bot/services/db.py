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
  description TEXT,
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
INSERT INTO events (title, start_ts, end_ts, location, capacity, description, notes, raw, updated_at)
VALUES (%(title)s, %(start_ts)s, %(end_ts)s, %(location)s, %(capacity)s, %(description)s, %(notes)s, %(raw)s, now())
ON CONFLICT (lower(title), start_ts)
DO UPDATE SET
  end_ts      = EXCLUDED.end_ts,
  location    = EXCLUDED.location,
  capacity    = EXCLUDED.capacity,
  description = EXCLUDED.description,
  notes       = EXCLUDED.notes,
  raw         = EXCLUDED.raw,
  updated_at  = now()
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
                "description": n.get("description"),
                "notes": n.get("notes"),
                "raw": json.dumps(n.get("raw", {}), ensure_ascii=False),
            })
            row = cur.fetchone()
            conn.commit()
            return row["id"]
        
LIST_NEXT_SQL = """
SELECT
  id, title, location, description, notes,
  start_ts, end_ts   -- raw timestamptz; format in Python
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

def delete_all_events() -> int:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE events RESTART IDENTITY;")
            conn.commit()
            # TRUNCATE doesn't return rowcount; return 0 to indicate success
            return 0
        
def list_events_sorted(
    select: list = ["id", "title"],
    sort_by: str = "start_ts",
    asc: bool = True,
    limit: int = 5,
    offset: int = 0) -> list[dict]:
    """
    List events sorted by the specified field.
    :param sort_by: Field to sort by (e.g., 'start_ts', 'created_at', 'updated_at').
    :param limit: Number of events to return.
    :param offset: Offset for pagination. To be muultiplied by 'limit' in the SQL query.
    :return: List of events.
    """
    valid_sorts = ["start_ts", "created_at", "updated_at"]
    if sort_by not in valid_sorts:
        raise ValueError(f"Invalid sort_by value. Must be one of {valid_sorts}.")
    
    order = "ASC" if asc else "DESC"
    select_clause = ", ".join(select)
    sql = f"""
    SELECT {select_clause}
    FROM events
    ORDER BY {sort_by} {order}
    LIMIT %(limit)s OFFSET %(offset)s;
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"limit": limit, "offset": offset * limit})
            return cur.fetchall()   
        