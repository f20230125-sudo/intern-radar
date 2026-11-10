"""Ashby job boards, through the public posting API (developers.ashbyhq.com/docs/public-job-posting-api)."""

from __future__ import annotations

from radar import sources
from radar.http import Client
from radar.models import Board, RawPosting

BASE = "https://api.ashbyhq.com/posting-api/job-board"


def listing(client: Client, board: Board) -> list[RawPosting]:
    data = client.get(f"{BASE}/{board.slug}", params={"includeCompensation": "true"})
    out: list[RawPosting] = []
    for job in data.get("jobs", []):
        if job.get("isListed") is False:
            continue
        locations = [job.get("location") or ""]
        for other in job.get("secondaryLocations") or []:
            if other.get("location"):
                locations.append(other["location"])
        country = (((job.get("address") or {}).get("postalAddress")) or {}).get("addressCountry")
        if country and locations[0] and country.lower() not in locations[0].lower():
            locations[0] = f"{locations[0]}, {country}"
        workplace = job.get("workplaceType")
        if not workplace and job.get("isRemote"):
            workplace = "Remote"
        html = job.get("descriptionHtml") or ""
        summary = (job.get("compensation") or {}).get("compensationTierSummary")
        if summary:
            html += f"<p>Compensation: {summary}</p>"
        out.append(
            RawPosting(
                board=board,
                native_id=str(job["id"]),
                title=(job.get("title") or "").strip(),
                url=job.get("jobUrl") or f"https://jobs.ashbyhq.com/{board.slug}/{job['id']}",
                locations=[loc for loc in locations if loc],
                posted_at=sources.parse_time(job.get("publishedAt")),
                html=html,
                text=None if html else job.get("descriptionPlain"),
                department=job.get("department") or job.get("team"),
                employment_type=job.get("employmentType"),
                workplace=workplace,
            )
        )
    return out


def detail(client: Client, posting: RawPosting) -> None:
    return None
