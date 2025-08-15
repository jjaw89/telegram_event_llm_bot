from typing import Iterable, Sequence
from psycopg import sql

# Keep a single source of truth for allowed columns
ALLOWED_COLUMNS: set[str] = {
    "id", "title", "start_ts", "end_ts", "location",
    "capacity", "notes", "created_at", "updated_at", "description",
}

def list_events_sorted(
    select: Sequence[str] | None = None,
    *,
    sort_by: str = "start_ts",
    asc: bool = True,
    limit: int = 5,
    page: int = 0,
) -> list[dict]:
    """
    Return events sorted by a given field.

    Args:
        select: Columns to return. Defaults to ("id", "title").
        sort_by: Column to sort by (must be in ALLOWED_COLUMNS).
        asc: Sort ascending if True, descending if False.
        limit: Page size (number of rows).
        page: Zero-based page index (0 -> first page).

    Returns:
        List of dict rows.
    """
    if select is None:
        select = ("id", "title")

    # Validate identifiers
    invalid_select = [c for c in select if c not in ALLOWED_COLUMNS]
    if invalid_select:
        raise ValueError(f"Invalid select columns: {invalid_select}")

    if sort_by not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid sort_by value: {sort_by}")

    order = sql.SQL("ASC") if asc else sql.SQL("DESC")

    # Build identifier list safely
    select_identifiers = [sql.Identifier(c) for c in select]

    query = sql.SQL("""
        SELECT {cols}
        FROM events
        ORDER BY {sort_col} {order}
        LIMIT %s OFFSET %s
    """).format(
        cols=sql.SQL(", ").join(select_identifiers),
        sort_col=sql.Identifier(sort_by),
        order=order,
    )

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit, page * limit))
            return cur.fetchall()
