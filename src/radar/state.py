"""What the radar remembers between runs, and how one run's findings change it.

The memory answers three questions a single fetch cannot: when was this role first seen, has it changed, and has
it gone. It is one JSON file. Everything here is plain data in, plain data out, so it can be tested without a
network or a clock.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from radar.models import Role

KEEP_CLOSED_DAYS = 45
# A board that had roles and suddenly lists nothing is more often a fault than a mass closing. It is believed
# only after this many runs in a row.
EMPTY_RUNS_BEFORE_BELIEVED = 3


@dataclass
class Seen:
    """One UAE posting the radar has read. `role` is None when it is not a student role."""

    fingerprint: str
    rules: int
    role: dict | None = None


@dataclass
class BoardMemory:
    last_ok: str | None = None
    postings: int = 0
    uae: int = 0
    empty_runs: int = 0


@dataclass
class State:
    rules_version: int = 0
    postings: dict[str, Seen] = field(default_factory=dict)
    boards: dict[str, BoardMemory] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> State:
        if not path.exists():
            return cls()
        doc = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            rules_version=doc.get("rules_version", 0),
            postings={k: Seen(**v) for k, v in (doc.get("postings") or {}).items()},
            boards={k: BoardMemory(**v) for k, v in (doc.get("boards") or {}).items()},
        )

    def save(self, path: Path) -> None:
        doc = {
            "rules_version": self.rules_version,
            "postings": {k: vars(v) for k, v in sorted(self.postings.items())},
            "boards": {k: vars(v) for k, v in sorted(self.boards.items())},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        tmp.replace(path)


@dataclass
class BoardFinding:
    """What one board's fetch produced in this run."""

    key: str
    ok: bool
    error: str | None = None
    postings: int = 0  # everything on the board
    listed: dict[str, str] = field(default_factory=dict)  # id -> fingerprint, for every UAE posting listed
    read: dict[str, Role | None] = field(default_factory=dict)  # id -> role or None, for those read this run
    unread: set[str] = field(default_factory=set)  # UAE postings that needed reading but could not be (cap, error)


@dataclass
class Event:
    at: str
    kind: str  # new | changed | closed | reopened
    id: str
    employer: str
    title: str
    detail: str = ""

    def line(self) -> str:
        return json.dumps(vars(self), ensure_ascii=False)


_COMPARED = ("title", "url", "places", "kind", "fields", "skills", "facts", "department")


def _differs(old: dict, new: dict) -> list[str]:
    return [name for name in _COMPARED if old.get(name) != new.get(name)]


def needs_read(state: State, posting_id: str, fp: str, rules: int) -> bool:
    seen = state.postings.get(posting_id)
    return seen is None or seen.fingerprint != fp or seen.rules != rules


def apply(state: State, findings: list[BoardFinding], *, now: str, rules: int) -> list[Event]:
    """Fold one run into the state. Returns what happened, for the history log."""
    events: list[Event] = []
    for f in findings:
        memory = state.boards.setdefault(f.key, BoardMemory())
        if not f.ok:
            continue
        prefix = f.key + ":"
        known_here = [pid for pid in state.postings if pid.startswith(prefix)]
        had_open = any(
            (state.postings[pid].role or {}).get("status") == "open" for pid in known_here
        )
        if not f.listed and had_open and memory.empty_runs + 1 < EMPTY_RUNS_BEFORE_BELIEVED:
            memory.empty_runs += 1
            continue
        memory.empty_runs = 0
        memory.last_ok, memory.postings, memory.uae = now, f.postings, len(f.listed)

        for pid, fp in f.listed.items():
            seen = state.postings.get(pid)
            if pid in f.unread:
                # Not read this run. Keep whatever is known; an open role stays alive.
                if seen and seen.role and seen.role.get("status") == "open":
                    seen.role["last_seen"] = now
                continue
            if pid in f.read:
                role = f.read[pid]
                new = role.model_dump(mode="json") if role else None
                old = seen.role if seen else None
                if new is not None:
                    if old is not None:
                        new["first_seen"] = old["first_seen"]
                        new["changed_at"] = old.get("changed_at")
                        if old.get("status") == "closed":
                            events.append(Event(now, "reopened", pid, new["employer"], new["title"]))
                        else:
                            diff = _differs(old, new)
                            # A rule fix that reads the same posting differently is not a change by the employer.
                            if diff and seen is not None and seen.rules == rules:
                                new["changed_at"] = now
                                events.append(Event(now, "changed", pid, new["employer"], new["title"], ", ".join(diff)))
                    else:
                        events.append(Event(now, "new", pid, new["employer"], new["title"], new["kind"]))
                elif old is not None and old.get("status") == "open":
                    events.append(Event(now, "closed", pid, old["employer"], old["title"], "no longer a student role"))
                state.postings[pid] = Seen(fingerprint=fp, rules=rules, role=new)
            elif seen is not None and seen.role is not None:
                if seen.role.get("status") == "closed":
                    seen.role["status"], seen.role["closed_at"] = "open", None
                    events.append(Event(now, "reopened", pid, seen.role["employer"], seen.role["title"]))
                seen.role["last_seen"] = now

        for pid in known_here:
            if pid in f.listed:
                continue
            seen = state.postings[pid]
            if seen.role is None:
                del state.postings[pid]
            elif seen.role.get("status") == "open":
                seen.role["status"], seen.role["closed_at"] = "closed", now
                events.append(Event(now, "closed", pid, seen.role["employer"], seen.role["title"]))

    cutoff = (datetime.fromisoformat(now) - timedelta(days=KEEP_CLOSED_DAYS)).isoformat()
    for pid in [p for p, s in state.postings.items() if s.role and s.role.get("status") == "closed" and (s.role.get("closed_at") or "") < cutoff]:
        del state.postings[pid]
    state.rules_version = rules
    return events


def roles(state: State) -> list[Role]:
    out = [Role.model_validate(s.role) for s in state.postings.values() if s.role is not None]
    out.sort(key=lambda r: (r.status != "open", -(datetime.fromisoformat(r.posted_at or r.first_seen).timestamp()), r.id))
    return out
