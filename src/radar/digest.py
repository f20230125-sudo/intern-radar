"""The day's new roles as a short Markdown note, for the daily digest issue.

    python -m radar.digest --out digest.md

Writes nothing when no role appeared today (UAE time), so the workflow posts nothing on a quiet day. Employer
text is escaped: a posting title must not be able to add a link or mention anyone in the issue.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from radar.run import DATA

UAE = timezone(timedelta(hours=4))
_KIND = {"internship": "Internship", "graduate": "Graduate programme", "first_job": "First job"}
_ORDER = ("eligibility", "start", "duration", "pay", "stage")


def plain(text: str) -> str:
    """Make employer text inert in Markdown: no links, no mentions, no formatting."""
    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r"([\\`*_{}\[\]()<>#|!~])", r"\\\1", text)
    return text.replace("@", "@​")


def build(snapshot: dict, *, now: datetime, site: str = "") -> str | None:
    today = now.astimezone(UAE).date()
    fresh = [
        r
        for r in snapshot["roles"]
        if r["status"] == "open" and datetime.fromisoformat(r["first_seen"]).astimezone(UAE).date() == today
    ]
    if not fresh:
        return None
    fresh.sort(key=lambda r: (r["employer"].lower(), r["title"].lower()))
    lines = [f"{len(fresh)} student role{'s' if len(fresh) != 1 else ''} first seen today at UAE employers.", ""]
    for r in fresh:
        facts = [r["facts"][k]["label"] for k in _ORDER if k in r["facts"]]
        places = ", ".join(p["emirate"] for p in r["places"])
        link = f"{site}/role/{r['slug']}" if site else r["url"]
        detail = " · ".join([_KIND[r["kind"]], places, *facts])
        lines.append(f"- **{plain(r['employer'])}**: [{plain(r['title'])}]({link})  \n  {plain(detail)}")
    lines += ["", "Read from the employers' own career systems. Check the posting itself before you apply."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--site", default="")
    args = parser.parse_args(argv)
    snapshot = json.loads((args.data / "snapshot.json").read_text(encoding="utf-8"))
    text = build(snapshot, now=datetime.now(UTC), site=args.site.rstrip("/"))
    if text is None:
        args.out.unlink(missing_ok=True)
        print("no new roles today; no digest")
        return 0
    args.out.write_text(text, encoding="utf-8")
    print(f"digest written: {text.count(chr(10) + '- ') + text.startswith('- ')} roles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
