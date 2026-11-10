"""Amazon's own careers site, which answers searches as JSON. Its robots file blocks only /internal paths."""

from __future__ import annotations

from datetime import UTC, datetime

from radar.http import Client
from radar.models import Board, RawPosting

URL = "https://www.amazon.jobs/en/search.json"
PAGE = 100
MAX_PAGES = 10


def _date(value: str | None) -> datetime | None:
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(" ".join((value or "").split()), fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def listing(client: Client, board: Board) -> list[RawPosting]:
    out: list[RawPosting] = []
    for page in range(MAX_PAGES):
        data = client.get(URL, params={"country": "ARE", "result_limit": PAGE, "offset": page * PAGE, "sort": "recent"})
        jobs = data.get("jobs") or []
        for job in jobs:
            parts = [job.get("description"), job.get("basic_qualifications"), job.get("preferred_qualifications")]
            place = job.get("normalized_location") or job.get("location") or ""
            if job.get("country_code") == "ARE" and "emirates" not in place.lower():
                place = f"{place}, United Arab Emirates".strip(", ")
            out.append(
                RawPosting(
                    board=board,
                    native_id=str(job.get("id_icims") or job.get("id")),
                    title=(job.get("title") or "").strip(),
                    url="https://www.amazon.jobs" + (job.get("job_path") or ""),
                    locations=[place],
                    posted_at=_date(job.get("posted_date")),
                    html="\n".join(f"<p>{p}</p>" for p in parts if p),
                    department=job.get("job_category") or job.get("business_category"),
                    employment_type=job.get("job_schedule_type"),
                )
            )
        if len(jobs) < PAGE or (page + 1) * PAGE >= (data.get("hits") or 0):
            break
    return out


def detail(client: Client, posting: RawPosting) -> None:
    return None
