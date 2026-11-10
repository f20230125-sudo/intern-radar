"""Lever postings. A documented public API (github.com/lever/postings-api); its robots file asks for a one-second
gap, which the shared client already keeps."""

from __future__ import annotations

from radar import sources
from radar.http import Client
from radar.models import Board, RawPosting

BASE = "https://api.lever.co/v0/postings"


def listing(client: Client, board: Board) -> list[RawPosting]:
    data = client.get(f"{BASE}/{board.slug}", params={"mode": "json"})
    if not isinstance(data, list):
        return []
    out: list[RawPosting] = []
    for job in data:
        cats = job.get("categories") or {}
        locations = list(cats.get("allLocations") or [])
        if cats.get("location") and cats["location"] not in locations:
            locations.insert(0, cats["location"])
        parts = [job.get("descriptionPlain") or ""]
        for block in job.get("lists") or []:
            parts.append(block.get("text") or "")
            parts.append(block.get("content") or "")
        parts.append(job.get("additionalPlain") or "")
        out.append(
            RawPosting(
                board=board,
                native_id=str(job["id"]),
                title=(job.get("text") or "").strip(),
                url=job.get("hostedUrl") or f"https://jobs.lever.co/{board.slug}/{job['id']}",
                locations=locations,
                posted_at=sources.parse_time(job.get("createdAt")),
                html="\n".join(f"<p>{p}</p>" for p in parts if p),
                department=cats.get("team") or cats.get("department"),
                employment_type=cats.get("commitment"),
                workplace=job.get("workplaceType") if job.get("workplaceType") not in (None, "unspecified") else None,
            )
        )
    return out


def detail(client: Client, posting: RawPosting) -> None:  # the list call already carries the description
    return None
