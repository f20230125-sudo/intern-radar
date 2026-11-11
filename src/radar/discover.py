"""Finding which employers have a readable job board, and whether it lists roles in the UAE.

    python -m radar.discover                 probe every name in data/candidates.yaml, print what answers
    python -m radar.discover --write         also add the finds to data/companies.yaml
    python -m radar.discover --check         confirm every board already in companies.yaml still answers

A name is tried as a board id on Greenhouse, Lever, Ashby and Workable ("Property Finder" as propertyfinder and
property-finder). A Workday tenant is tried on the usual hosts; its robots file names its career sites, and each
site is asked whether it has a UAE filter. A board is kept only if it lists at least one role in the UAE today
(or --keep-empty is given), so the registry does not fill with boards that will never show anything.

This is run by hand, rarely. It is slow on purpose: one request a second per host.
"""

from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import yaml

from radar import reader, registry
from radar.http import USER_AGENT, Client, SourceError
from radar.models import Board
from radar.sources import ADAPTERS, workday

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / "data" / "candidates.yaml"
SLUG_SYSTEMS = ("greenhouse", "lever", "ashby", "workable")
WORKDAY_HOSTS = ("wd1", "wd3", "wd5", "wd12", "wd2", "wd103")
_SITE = re.compile(r"^(?:Allow|Sitemap):\s*(?:https?://[^/]+)?/([A-Za-z0-9_\-]+)/", re.I | re.M)


def variants(name: str) -> list[str]:
    """Board ids an employer called `name` is likely to use."""
    base = re.sub(r"[^a-z0-9 &-]", "", name.lower()).replace("&", " ").strip()
    words = base.split()
    out = ["".join(words), "-".join(words)]
    if len(words) > 1:
        out.append(words[0])
    seen: list[str] = []
    for v in out:
        if len(v) >= 2 and v not in seen:
            seen.append(v)
    return seen


def probe_slug(client: Client, system: str, slug: str, name: str) -> dict | None:
    board = Board(key=f"{system}:{slug}", system=system, slug=slug, name=name)
    try:
        postings = ADAPTERS[system].listing(client, board)
    except SourceError:
        return None
    except (KeyError, TypeError, AttributeError, ValueError):
        return None
    if not postings:
        return None
    uae = sum(1 for p in postings if reader.places_of(p)[0])
    return {"system": system, "slug": slug, "name": name, "postings": len(postings), "uae": uae}


def workday_sites(tenant: str, host: str) -> list[str]:
    """Career site names of a Workday tenant, read from its robots file."""
    url = f"https://{tenant}.{host}.myworkdayjobs.com/robots.txt"
    try:
        resp = httpx.get(url, timeout=15, headers={"User-Agent": USER_AGENT}, follow_redirects=False)
    except httpx.HTTPError:
        return []
    if resp.status_code != 200 or "text/html" in resp.headers.get("content-type", ""):
        return []
    sites: list[str] = []
    for site in _SITE.findall(resp.text):
        if site not in sites and site.lower() not in ("wday", "en-us"):
            sites.append(site)
    return sites


def probe_workday(client: Client, tenant: str, name: str) -> list[dict]:
    found: list[dict] = []
    for host in WORKDAY_HOSTS:
        sites = workday_sites(tenant, host)
        if not sites:
            continue
        for site in sites[:8]:
            board = Board(key=f"workday:{tenant}:{site}", system="workday", slug=tenant, name=name, host=host, site=site)
            try:
                postings = workday.listing(client, board)
            except SourceError:
                continue
            except (KeyError, TypeError, AttributeError, ValueError):
                continue
            if postings:
                found.append({"system": "workday", "slug": tenant, "host": host, "site": site, "name": name, "postings": len(postings), "uae": len(postings)})
        break  # a tenant lives on one host
    return found


def probe_name(client: Client, name: str, slugs: list[str] | None) -> list[dict]:
    hits: list[dict] = []
    for system in SLUG_SYSTEMS:
        tries = slugs or variants(name)
        if system == "workable":
            tries = tries[:1]  # Workable punishes many misses; one guess per employer
        for slug in tries:
            hit = probe_slug(client, system, slug, name)
            if hit:
                hits.append(hit)
                break  # the first id that answers is the board
    return hits


def entry(hit: dict) -> dict:
    keep = ("system", "slug", "host", "site", "name")
    return {k: hit[k] for k in keep if k in hit}


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="add finds to data/companies.yaml")
    parser.add_argument("--check", action="store_true", help="re-check the boards already in the registry")
    parser.add_argument("--keep-empty", action="store_true", help="keep boards with no UAE role today")
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--only", choices=("names", "workday"), help="probe only one kind of candidate")
    args = parser.parse_args(argv)

    boards, _ = registry.load()
    known = {b.key for b in boards}

    if args.check:
        bad = 0
        with Client() as client, ThreadPoolExecutor(max_workers=6) as pool:
            def one(b: Board) -> tuple[Board, str]:
                try:
                    return b, f"ok, {len(ADAPTERS[b.system].listing(client, b))} postings"
                except SourceError as exc:
                    return b, f"FAILED: {exc}"
            for b, result in pool.map(one, boards):
                bad += result.startswith("FAILED")
                print(f"{b.key:50s} {result}")
        return 1 if bad else 0

    doc = yaml.safe_load(args.candidates.read_text(encoding="utf-8")) or {}
    names: list[tuple[str, list[str] | None]] = []
    for item in doc.get("names") or []:
        if isinstance(item, dict):
            names.append((item["name"], item.get("slugs")))
        else:
            names.append((str(item), None))
    tenants: list[tuple[str, str]] = [(t["tenant"], t["name"]) for t in doc.get("workday") or []]

    hits: list[dict] = []
    with Client() as client, ThreadPoolExecutor(max_workers=8) as pool:
        jobs = []
        if args.only != "workday":
            jobs += [pool.submit(probe_name, client, name, slugs) for name, slugs in names]
        if args.only != "names":
            jobs += [pool.submit(probe_workday, client, tenant, name) for tenant, name in tenants]
        for done, job in enumerate(jobs, 1):
            hits.extend(job.result())
            if done % 25 == 0:
                print(f"  {done}/{len(jobs)} probed, {len(hits)} boards answer", flush=True)
        requests = client.requests

    def key(h: dict) -> str:
        return f"{h['system']}:{h['slug']}" + (f":{h['site']}" if h["system"] == "workday" else "")

    fresh = [h for h in hits if key(h) not in known and (h["uae"] > 0 or args.keep_empty)]
    fresh.sort(key=lambda h: (-h["uae"], h["name"].lower()))
    print(f"\n{requests} requests. {len(hits)} boards answer; {len(fresh)} are new and list UAE roles:")
    for h in fresh:
        print(f"  {h['uae']:4d} UAE of {h['postings']:5d}  {key(h):45s} {h['name']}")
    idle = [h for h in hits if h["uae"] == 0 and key(h) not in known]
    print(f"{len(idle)} more answer but list nothing in the UAE today.")

    if args.write and fresh:
        text = registry.DEFAULT.read_text(encoding="utf-8")
        marker = "\nnot_covered:"
        lines = "".join("  - " + yaml.safe_dump(entry(h), default_flow_style=True, width=1000, allow_unicode=True).strip() + "\n" for h in fresh)
        head, tail = text.split(marker, 1) if marker in text else (text, "")
        registry.DEFAULT.write_text(head.rstrip("\n") + "\n" + lines + (marker + tail if tail else ""), encoding="utf-8")
        print(f"added {len(fresh)} boards to {registry.DEFAULT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
