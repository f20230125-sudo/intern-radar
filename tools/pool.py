"""Collect every UAE posting on the watched boards, with its full text, into data/discovery/pool.jsonl.

    python tools/pool.py

The pool is the raw material for the labelled set that the rules are scored against. It holds full posting
text, so it stays on this machine (data/discovery is not committed).
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from radar import reader, registry  # noqa: E402
from radar.http import Client, SourceError  # noqa: E402
from radar.sources import ADAPTERS  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "discovery" / "pool.jsonl"
CAP = 150  # descriptions per board


def board_rows(client: Client, board) -> list[dict]:
    adapter = ADAPTERS[board.system]
    try:
        postings = adapter.listing(client, board)
    except (SourceError, KeyError, TypeError, AttributeError, ValueError) as exc:
        print(f"  skipped {board.key}: {exc}", flush=True)
        return []
    rows = []
    fetched = 0
    for raw in postings:
        if not reader.places_of(raw)[0]:
            continue
        if raw.html is None and raw.text is None and raw.detail_ref:
            if fetched >= CAP:
                continue
            try:
                adapter.detail(client, raw)
                fetched += 1
            except (SourceError, KeyError, TypeError, AttributeError, ValueError):
                continue
        if not reader.places_of(raw)[0]:
            continue
        rows.append(
            {
                "id": raw.id,
                "employer": board.name,
                "title": raw.title,
                "employment_type": raw.employment_type,
                "workplace": raw.workplace,
                "department": raw.department,
                "locations": raw.locations,
                "url": raw.url,
                "text": reader.body(raw),
            }
        )
    return rows


def main() -> None:
    boards, _ = registry.load()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with Client() as client, ThreadPoolExecutor(max_workers=6) as pool:
        rows = [row for chunk in pool.map(lambda b: board_rows(client, b), boards) for row in chunk]
    with OUT.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{len(rows)} UAE postings from {len(boards)} boards -> {OUT}")


if __name__ == "__main__":
    main()
