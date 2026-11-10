"""Workable careers pages, through the widget feed Workable publishes for embedding a job list on a site.

One GET returns every open job with its description, so a board costs one request. The busier search endpoint
behind apply.workable.com rate-limits hard (a burst earns a day-long block), so it is not used.
"""

from __future__ import annotations

from radar import sources
from radar.http import Client
from radar.models import Board, RawPosting

BASE = "https://apply.workable.com/api/v1/widget/accounts"


def _place(loc: dict) -> str:
    return ", ".join(str(p) for p in (loc.get("city"), loc.get("region") or loc.get("state"), loc.get("country")) if p)


def listing(client: Client, board: Board) -> list[RawPosting]:
    data = client.get(f"{BASE}/{board.slug}", params={"details": "true"})
    out: list[RawPosting] = []
    for job in data.get("jobs", []):
        locations = [_place(loc) for loc in job.get("locations") or [] if isinstance(loc, dict) and not loc.get("hidden")]
        if not locations:
            locations = [_place(job)]
        remote = str(job.get("telecommuting", "")).lower() == "true"
        experience = job.get("experience") or ""
        code = str(job.get("shortcode") or "")
        if not code:
            continue
        out.append(
            RawPosting(
                board=board,
                native_id=code,
                title=(job.get("title") or "").strip(),
                url=job.get("url") or f"https://apply.workable.com/j/{code}",
                locations=[loc for loc in locations if loc],
                posted_at=sources.parse_time(job.get("published_on") or job.get("created_at")),
                html=job.get("description") or "",
                department=job.get("function") or job.get("department"),
                # "Internship" in the experience field is the employer's own filing of the role.
                employment_type=experience if "intern" in experience.lower() else job.get("employment_type"),
                workplace="remote" if remote else None,
            )
        )
    return out


def detail(client: Client, posting: RawPosting) -> None:
    return None
