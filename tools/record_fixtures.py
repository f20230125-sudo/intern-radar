"""Record small real samples of each feed into tests/fixtures, once. Tests then run without a network.

    python tools/record_fixtures.py

Each sample is cut down to a handful of postings (student roles in the UAE first), so the files stay small and
no employer's whole board is copied into the repository.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from radar.http import Client  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
STUDENT = re.compile(r"\bintern|graduate|trainee|launch program", re.I)
UAE = re.compile(r"dubai|abu dhabi|emirates|\bAE\b", re.I)


def keep(items: list, title, place, n: int = 6) -> list:
    """Student roles in the UAE first, then other UAE roles, then anything, up to n."""
    ranked = sorted(items, key=lambda j: (not (STUDENT.search(title(j)) and UAE.search(place(j))), not UAE.search(place(j))))
    return ranked[:n]


def save(name: str, doc) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", name)


def main() -> None:
    with Client() as c:
        d = c.get("https://boards-api.greenhouse.io/v1/boards/tamara/jobs")
        d["jobs"] = keep(d["jobs"], lambda j: j["title"], lambda j: j["location"]["name"])
        d["meta"] = {"total": len(d["jobs"])}
        save("greenhouse_tamara_list.json", d)
        first = next(j for j in d["jobs"] if STUDENT.search(j["title"]))
        save("greenhouse_tamara_job.json", c.get(f"https://boards-api.greenhouse.io/v1/boards/tamara/jobs/{first['id']}"))

        d = c.get("https://api.lever.co/v0/postings/ifm-us", params={"mode": "json"})
        save("lever_ifm.json", keep(d, lambda j: j["text"], lambda j: (j.get("categories") or {}).get("location") or "", 5))

        d = c.get("https://api.ashbyhq.com/posting-api/job-board/ziina", params={"includeCompensation": "true"})
        d["jobs"] = keep(d["jobs"], lambda j: j["title"], lambda j: j.get("location") or "", 4)
        save("ashby_ziina.json", d)

        d = c.get("https://apply.workable.com/api/v1/widget/accounts/bayutdubizzle", params={"details": "true"})
        d["jobs"] = keep(d["jobs"], lambda j: j["title"], lambda j: j.get("country") or "", 5)
        save("workable_bayut.json", d)

        url = "https://mastercard.wd1.myworkdayjobs.com/wday/cxs/mastercard/CorporateCareers"
        first = c.post(f"{url}/jobs", json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
        # Keep only the country filter, and within it a few countries: the full filter list is large.
        wanted = re.compile(r"United Arab Emirates|United States of America|^India$|Dubai")

        def prune(items: list) -> list:
            kept = []
            for item in items or []:
                children = prune(item.get("values") or [])
                if children or wanted.search(item.get("descriptor") or ""):
                    kept.append({**item, "values": children} if "values" in item else item)
            return kept

        first["facets"], first["jobPostings"] = prune(first.get("facets", [])), first.get("jobPostings", [])[:1]
        facets = first["facets"]
        save("workday_mastercard_first.json", first)
        from radar.sources.workday import _uae_facets

        applied = _uae_facets(facets)
        page = c.post(f"{url}/jobs", json={"appliedFacets": applied, "limit": 20, "offset": 0, "searchText": ""})
        page.pop("facets", None)
        save("workday_mastercard_page.json", page)
        intern = next(j for j in page["jobPostings"] if STUDENT.search(j["title"]))
        save("workday_mastercard_job.json", c.get(f"{url}{intern['externalPath']}"))

        d = c.get("https://www.amazon.jobs/en/search.json", params={"country": "ARE", "result_limit": 100, "offset": 0, "sort": "recent"})
        d["jobs"] = keep(d["jobs"], lambda j: j["title"], lambda j: "AE", 6)
        d["hits"] = len(d["jobs"])
        d.pop("facets", None)
        save("amazon_are.json", d)


if __name__ == "__main__":
    main()
