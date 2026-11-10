"""Workday career sites. Each employer is a tenant with one or more sites: Mastercard's is tenant "mastercard",
host "wd1", site "CorporateCareers". These are the calls the site's own page makes, and the tenant's robots file
allows its public site paths.

A big employer has thousands of postings worldwide, so the listing asks for the UAE only: the first response
carries the site's filters, one of which is the country, and the UAE's id is read from it.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from radar import sources
from radar.http import Client, SourceError
from radar.models import Board, RawPosting

PAGE = 20
MAX_PAGES = 15
_UAE = re.compile(r"united\s+arab\s+emirates|^uae$", re.I)
_CITY = re.compile(r"dubai|abu\s*dhabi|sharjah", re.I)
_POSTED = re.compile(r"posted\s+(today|yesterday|(\d+)\+?\s+days?\s+ago)", re.I)


def _root(board: Board) -> str:
    return f"https://{board.slug}.{board.host}.myworkdayjobs.com"


def _api(board: Board) -> str:
    return f"{_root(board)}/wday/cxs/{board.slug}/{board.site}"


def _uae_facets(facets: list[dict]) -> dict[str, list[str]]:
    """Find the filter values that mean "in the UAE". Country first; cities only if there is no country filter."""
    country: dict[str, list[str]] = {}
    city: dict[str, list[str]] = {}

    def walk(items: list[dict], parameter: str | None) -> None:
        for item in items or []:
            param = item.get("facetParameter") or parameter
            name = item.get("descriptor") or ""
            if item.get("id") and param:
                if _UAE.search(name):
                    country.setdefault(param, []).append(item["id"])
                elif _CITY.search(name):
                    city.setdefault(param, []).append(item["id"])
            walk(item.get("values") or [], param)

    walk(facets, None)
    return country or city


def _posted(text: str | None, now: datetime) -> datetime | None:
    m = _POSTED.search(text or "")
    if not m:
        return None
    word = m.group(1).lower()
    days = 0 if word == "today" else 1 if word == "yesterday" else int(m.group(2))
    return (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)


def listing(client: Client, board: Board) -> list[RawPosting]:
    if not board.site or not board.host:
        raise SourceError("a Workday board needs a host and a site")
    url = f"{_api(board)}/jobs"
    first = client.post(url, json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    applied = _uae_facets(first.get("facets") or [])
    if not applied:
        raise SourceError("the site has no UAE filter")
    now = datetime.now(UTC)
    out: list[RawPosting] = []
    seen: set[str] = set()
    total = None
    for page in range(MAX_PAGES):
        data = client.post(url, json={"appliedFacets": applied, "limit": PAGE, "offset": page * PAGE, "searchText": ""})
        if total is None:
            total = data.get("total") or 0
        rows = data.get("jobPostings") or []
        for job in rows:
            path = job.get("externalPath") or ""
            ref = (job.get("bulletFields") or [None])[0] or path.rsplit("_", 1)[-1] or path
            if not path or ref in seen:
                continue
            seen.add(ref)
            out.append(
                RawPosting(
                    board=board,
                    native_id=str(ref),
                    title=(job.get("title") or "").strip(),
                    url=f"{_root(board)}/{board.site}{path}",
                    locations=[job.get("locationsText") or "United Arab Emirates"],
                    posted_at=_posted(job.get("postedOn"), now),
                    detail_ref=path,
                    extra={"uae_filter": True},
                )
            )
        if not rows or (page + 1) * PAGE >= total:
            break
    return out


def detail(client: Client, posting: RawPosting) -> None:
    data = client.get(f"{_api(posting.board)}{posting.detail_ref}")
    info = data.get("jobPostingInfo") or {}
    posting.html = info.get("jobDescription") or ""
    posting.employment_type = info.get("timeType")
    places = [info.get("location")] + list(info.get("additionalLocations") or [])
    places = [p for p in places if p]
    if places:
        posting.locations = places
    started = sources.parse_time(info.get("startDate"))
    if started:
        posting.posted_at = started
    if info.get("remoteType"):
        posting.workplace = info["remoteType"]
