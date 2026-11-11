"""One run of the radar: read every board, fold the result into memory, write the snapshot.

    python -m radar.run                     all boards in data/companies.yaml
    python -m radar.run --only greenhouse   one system
    python -m radar.run --board lever:ifm-us

Exit code 1 means the run is not fit to publish: nothing could be read, or the snapshot failed its own checks.
One board failing is normal and does not stop a run; it shows on the site.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from radar import RULES_VERSION, kind, reader, registry
from radar import state as memory
from radar.http import Client, SourceError
from radar.models import Board, BoardStatus, RawPosting, Snapshot
from radar.sources import ADAPTERS

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DETAIL_CAP = 60  # descriptions fetched per board per run; the rest wait for the next run


def read_board(client: Client, board: Board, state: memory.State, *, now: str, rules: int = RULES_VERSION) -> memory.BoardFinding:
    adapter = ADAPTERS[board.system]
    try:
        postings: list[RawPosting] = adapter.listing(client, board)
    except SourceError as exc:
        return memory.BoardFinding(key=board.key, ok=False, error=str(exc))
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        return memory.BoardFinding(key=board.key, ok=False, error=f"unexpected feed shape ({type(exc).__name__})")

    finding = memory.BoardFinding(key=board.key, ok=True, postings=len(postings))
    todo: list[RawPosting] = []
    for raw in postings:
        places, _ = reader.places_of(raw)
        if not places:
            continue
        fp = reader.fingerprint(raw)
        finding.listed[raw.id] = fp
        if memory.needs_read(state, raw.id, fp, rules):
            todo.append(raw)

    # Likely student roles first, so a cap never delays an internship behind a hundred senior postings.
    todo.sort(key=lambda r: not kind.looks_student(r.title, r.employment_type))
    fetched = 0
    for raw in todo:
        needs_detail = raw.html is None and raw.text is None and raw.detail_ref is not None
        if needs_detail:
            if fetched >= DETAIL_CAP:
                finding.unread.add(raw.id)
                continue
            try:
                adapter.detail(client, raw)
                fetched += 1
            except SourceError:
                finding.unread.add(raw.id)
                continue
            except (KeyError, TypeError, AttributeError, ValueError):
                finding.unread.add(raw.id)
                continue
        finding.read[raw.id] = reader.read(raw, now=now)
    return finding


def dedupe(roles: list) -> list:
    """An employer with two career sites (a main one and a campus one) lists the same role on both. One is kept:
    an open copy before a closed one, then the one seen first."""
    best: dict[tuple, object] = {}
    for role in roles:
        key = (role.employer.lower(), role.title.lower(), tuple(sorted(p.emirate for p in role.places)))
        held = best.get(key)
        if held is None or (role.status == "open", held.first_seen) > (held.status == "open", role.first_seen):
            best[key] = role
    kept = {id(r) for r in best.values()}
    return [r for r in roles if id(r) in kept]


def build_snapshot(state: memory.State, boards: list[Board], findings: list[memory.BoardFinding], not_covered: list[dict], *, started: str, now: str) -> Snapshot:
    roles = dedupe(memory.roles(state))
    by_board: dict[str, int] = {}
    for role in roles:
        if role.status == "open":
            by_board[role.board] = by_board.get(role.board, 0) + 1
    found = {f.key: f for f in findings}
    statuses: list[BoardStatus] = []
    for board in boards:
        f = found.get(board.key)
        mem = state.boards.get(board.key, memory.BoardMemory())
        statuses.append(
            BoardStatus(
                key=board.key,
                name=board.name,
                system=board.system,
                home=board.home,
                ok=bool(f.ok) if f else mem.last_ok is not None,
                checked_at=now if f else (mem.last_ok or now),
                last_ok=mem.last_ok,
                error=f.error if f else None,
                postings=mem.postings,
                uae=mem.uae,
                student=by_board.get(board.key, 0),
            )
        )
    statuses.sort(key=lambda s: (-s.student, -s.uae, s.name.lower()))
    return Snapshot(rules_version=RULES_VERSION, generated_at=now, started_at=started, roles=roles, boards=statuses, not_covered=not_covered)


def check(snapshot: Snapshot, findings: list[memory.BoardFinding]) -> list[str]:
    """Reasons this snapshot must not be published. Empty means fine."""
    problems: list[str] = []
    if findings and not any(f.ok for f in findings):
        problems.append("no board could be read")
    ids = [r.id for r in snapshot.roles]
    if len(ids) != len(set(ids)):
        problems.append("duplicate role ids")
    slugs = [r.slug for r in snapshot.roles]
    if len(slugs) != len(set(slugs)):
        problems.append("duplicate role slugs")
    for role in snapshot.roles:
        if not role.url.startswith("https://"):
            problems.append(f"{role.id}: link is not https")
        if not role.places:
            problems.append(f"{role.id}: no UAE place")
    return problems


def run(boards: list[Board], not_covered: list[dict], *, data: Path = DATA, client: Client | None = None, now: datetime | None = None, workers: int = 6) -> tuple[Snapshot, list[memory.Event], list[str]]:
    started = (now or datetime.now(UTC)).replace(microsecond=0)
    stamp = started.isoformat()
    state = memory.State.load(data / "state.json")
    own = client is None
    client = client or Client()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            findings = list(pool.map(lambda b: read_board(client, b, state, now=stamp), boards))
    finally:
        if own:
            client.close()
    events = memory.apply(state, findings, now=stamp, rules=RULES_VERSION)
    finished = stamp if now else datetime.now(UTC).replace(microsecond=0).isoformat()
    snapshot = build_snapshot(state, boards, findings, not_covered, started=stamp, now=finished)
    problems = check(snapshot, findings)
    if not problems:
        state.save(data / "state.json")
        (data / "snapshot.json").write_text(snapshot.model_dump_json(indent=1), encoding="utf-8")
        if events:
            log = data / "history" / f"{stamp[:7]}.jsonl"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as fh:
                fh.writelines(e.line() + "\n" for e in events)
    return snapshot, events, problems


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="read only boards on this system")
    parser.add_argument("--board", help="read only this board key")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--registry", type=Path, default=registry.DEFAULT)
    args = parser.parse_args(argv)

    boards, not_covered = registry.load(args.registry)
    if args.only:
        boards = [b for b in boards if b.system == args.only]
    if args.board:
        boards = [b for b in boards if b.key == args.board]
    if not boards:
        print("no boards match")
        return 1

    with Client() as client:
        snapshot, events, problems = run(boards, not_covered, data=args.data, client=client)
        requests = client.requests

    open_roles = [r for r in snapshot.roles if r.status == "open"]
    failed = [b for b in snapshot.boards if not b.ok]
    print(f"{len(boards)} boards, {requests} requests, {len(open_roles)} open student roles, {len(failed)} boards failed")
    for kind_name in ("internship", "graduate", "first_job"):
        print(f"  {kind_name:11s} {sum(1 for r in open_roles if r.kind == kind_name)}")
    for event in events[:40]:
        print(f"  {event.kind:9s} {event.employer}: {event.title}")
    if len(events) > 40:
        print(f"  ... and {len(events) - 40} more")
    for b in failed:
        print(f"  FAILED {b.key}: {b.error}")
    for p in problems:
        print(f"  NOT PUBLISHED: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
