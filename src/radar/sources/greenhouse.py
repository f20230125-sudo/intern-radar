"""Greenhouse job boards. Public by design: "Job Board data is publicly available, so authentication is not
required for any GET endpoints" (developers.greenhouse.io/job-board.html)."""

from __future__ import annotations

from radar import sources
from radar.http import Client
from radar.models import Board, RawPosting

BASE = "https://boards-api.greenhouse.io/v1/boards"


def listing(client: Client, board: Board) -> list[RawPosting]:
    data = client.get(f"{BASE}/{board.slug}/jobs")
    out: list[RawPosting] = []
    for job in data.get("jobs", []):
        locations = [(job.get("location") or {}).get("name") or ""]
        for office in job.get("offices") or []:
            for value in (office.get("location"), office.get("name")):
                if value and value not in locations:
                    locations.append(value)
        departments = [d.get("name") for d in job.get("departments") or [] if d.get("name")]
        out.append(
            RawPosting(
                board=board,
                native_id=str(job["id"]),
                title=(job.get("title") or "").strip(),
                url=job.get("absolute_url") or f"https://boards.greenhouse.io/{board.slug}/jobs/{job['id']}",
                locations=[loc for loc in locations if loc],
                posted_at=sources.parse_time(job.get("first_published")),
                updated_at=sources.parse_time(job.get("updated_at")),
                department=departments[0] if departments else None,
                detail_ref=str(job["id"]),
            )
        )
    return out


def detail(client: Client, posting: RawPosting) -> None:
    job = client.get(f"{BASE}/{posting.board.slug}/jobs/{posting.detail_ref}")
    posting.html = job.get("content") or ""
    for item in job.get("metadata") or []:
        name, value = (item.get("name") or "").lower(), item.get("value")
        if isinstance(value, str) and value and ("employment" in name or "type" in name):
            posting.employment_type = posting.employment_type or value
