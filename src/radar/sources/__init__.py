"""One adapter per career system. Each has the same two calls:

  listing(client, board) -> list[RawPosting]   everything open on the board, one cheap request where the system allows
  detail(client, posting) -> None              fill in the description, for systems whose list call leaves it out

A run calls detail only for postings that are in the UAE and that it has not read before.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from radar.sources import amazon, ashby, greenhouse, lever, workable, workday

ADAPTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workable": workable,
    "workday": workday,
    "amazon": amazon,
}


def parse_time(value: Any) -> datetime | None:
    """Sources send ISO strings, epoch milliseconds, or nothing."""
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=UTC)
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, OverflowError, OSError):
        return None
