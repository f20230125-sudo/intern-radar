"""Memory across runs: new, changed, closed, reopened; and a whole run against the stand-in internet."""

import json
from datetime import UTC, datetime, timedelta

import httpx

from radar import RULES_VERSION, run
from radar import state as memory
from radar.models import Place, Role

T0 = "2026-11-10T08:00:00+00:00"
T1 = "2026-11-10T09:00:00+00:00"
T2 = "2026-11-10T10:00:00+00:00"


def role(pid: str, title: str = "Data Intern", *, now: str = T0, **changes) -> Role:
    base = dict(
        id=pid, slug=pid.replace(":", "-"), employer="Acme", board="greenhouse:acme", system="greenhouse", title=title,
        url="https://example.test/job", places=[Place(emirate="Dubai", raw="Dubai")], elsewhere=0, kind="internship",
        kind_reason='title says "Intern"', fields=["Data and analytics"], facts={}, first_seen=now, last_seen=now,
    )
    base.update(changes)
    return Role(**base)


def finding(listed: dict, read: dict | None = None, **kw) -> memory.BoardFinding:
    return memory.BoardFinding(key="greenhouse:acme", ok=True, postings=len(listed), listed=listed, read=read or {}, **kw)


A = "greenhouse:acme:1"
B = "greenhouse:acme:2"


def test_first_sight_is_new_and_remembered():
    state = memory.State()
    events = memory.apply(state, [finding({A: "f1", B: "f2"}, {A: role(A), B: None})], now=T0, rules=1)
    assert [(e.kind, e.id) for e in events] == [("new", A)]
    assert state.postings[A].role["first_seen"] == T0
    assert state.postings[B].role is None  # read, not a student role, and not read again
    assert not memory.needs_read(state, B, "f2", 1)
    assert memory.needs_read(state, B, "f2-changed", 1)
    assert memory.needs_read(state, B, "f2", 2)


def test_a_quiet_hour_changes_nothing_but_last_seen():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    events = memory.apply(state, [finding({A: "f1"})], now=T1, rules=1)
    assert events == []
    assert state.postings[A].role["first_seen"] == T0
    assert state.postings[A].role["last_seen"] == T1


def test_an_edit_by_the_employer_is_a_change_and_keeps_first_seen():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    events = memory.apply(state, [finding({A: "f2"}, {A: role(A, "Data Science Intern", now=T1)})], now=T1, rules=1)
    assert [(e.kind, e.detail) for e in events] == [("changed", "title")]
    r = state.postings[A].role
    assert (r["first_seen"], r["changed_at"], r["title"]) == (T0, T1, "Data Science Intern")


def test_a_rule_fix_is_not_reported_as_the_employer_changing_the_posting():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    events = memory.apply(state, [finding({A: "f1"}, {A: role(A, fields=["AI and machine learning"], now=T1)})], now=T1, rules=2)
    assert events == []
    assert state.postings[A].role["changed_at"] is None
    assert state.postings[A].role["fields"] == ["AI and machine learning"]
    assert state.rules_version == 2


def test_a_posting_that_disappears_is_closed_and_one_that_returns_is_reopened():
    state = memory.State()
    memory.apply(state, [finding({A: "f1", B: "f2"}, {A: role(A), B: role(B, "Ops Intern")})], now=T0, rules=1)
    events = memory.apply(state, [finding({B: "f2"})], now=T1, rules=1)
    assert [(e.kind, e.id) for e in events] == [("closed", A)]
    assert state.postings[A].role["status"] == "closed" and state.postings[A].role["closed_at"] == T1
    events = memory.apply(state, [finding({A: "f1", B: "f2"})], now=T2, rules=1)
    assert [(e.kind, e.id) for e in events] == [("reopened", A)]
    assert state.postings[A].role["status"] == "open" and state.postings[A].role["first_seen"] == T0


def test_a_failed_board_closes_nothing():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    events = memory.apply(state, [memory.BoardFinding(key="greenhouse:acme", ok=False, error="HTTP 503")], now=T1, rules=1)
    assert events == [] and state.postings[A].role["status"] == "open"


def test_a_board_that_suddenly_lists_nothing_is_doubted_before_it_is_believed():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    for _ in range(memory.EMPTY_RUNS_BEFORE_BELIEVED - 1):
        assert memory.apply(state, [finding({})], now=T1, rules=1) == []
        assert state.postings[A].role["status"] == "open"
    events = memory.apply(state, [finding({})], now=T2, rules=1)
    assert [e.kind for e in events] == ["closed"]


def test_an_unread_posting_stays_as_it_was():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    events = memory.apply(state, [finding({A: "f9", B: "f2"}, unread={A, B})], now=T1, rules=1)
    assert events == []
    assert state.postings[A].fingerprint == "f1" and state.postings[A].role["last_seen"] == T1
    assert B not in state.postings  # still to be read next run
    assert memory.needs_read(state, A, "f9", 1)


def test_a_role_that_stops_being_a_student_role_is_closed():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    events = memory.apply(state, [finding({A: "f2"}, {A: None})], now=T1, rules=1)
    assert [(e.kind, e.detail) for e in events] == [("closed", "no longer a student role")]
    assert state.postings[A].role is None


def test_closed_roles_are_forgotten_after_the_keep_window():
    state = memory.State()
    memory.apply(state, [finding({A: "f1"}, {A: role(A)})], now=T0, rules=1)
    memory.apply(state, [finding({B: "f2"}, {B: role(B, now=T1)})], now=T1, rules=1)
    later = (datetime.fromisoformat(T1) + timedelta(days=memory.KEEP_CLOSED_DAYS + 1)).isoformat()
    memory.apply(state, [finding({B: "f2"})], now=later, rules=1)
    assert A not in state.postings and B in state.postings


def test_state_survives_a_round_trip(tmp_path):
    state = memory.State()
    memory.apply(state, [finding({A: "f1", B: "f2"}, {A: role(A), B: None})], now=T0, rules=1)
    path = tmp_path / "state.json"
    state.save(path)
    again = memory.State.load(path)
    assert again.postings.keys() == state.postings.keys()
    assert again.postings[A].role == state.postings[A].role
    assert again.boards["greenhouse:acme"].uae == 2
    assert memory.State.load(tmp_path / "missing.json").postings == {}


def test_roles_are_ordered_open_first_then_newest():
    state = memory.State()
    old = role(A, posted_at="2026-09-01T00:00:00+00:00")
    new = role(B, "Ops Intern", posted_at="2026-11-09T00:00:00+00:00")
    memory.apply(state, [finding({A: "f1", B: "f2"}, {A: old, B: new})], now=T0, rules=1)
    assert [r.id for r in memory.roles(state)] == [B, A]
    memory.apply(state, [finding({A: "f1"})], now=T1, rules=1)
    assert [(r.id, r.status) for r in memory.roles(state)] == [(A, "open"), (B, "closed")]


# ------------------------------------------------------------------ a run


def test_a_whole_run_then_a_quiet_run_then_a_closing(tmp_path, client, web, boards):
    watched = list(boards.values())
    t0 = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
    snap, events, problems = run.run(watched, [{"name": "talabat", "reason": "not read"}], data=tmp_path, client=client, now=t0, workers=1)
    assert problems == []
    assert all(b.ok for b in snap.boards)
    open_roles = [r for r in snap.roles if r.status == "open"]
    assert {r.system for r in open_roles} == {"greenhouse", "lever", "workable", "workday", "amazon"}
    assert len(events) == len(open_roles) and {e.kind for e in events} == {"new"}
    assert snap.rules_version == RULES_VERSION and snap.not_covered[0]["name"] == "talabat"
    on_disk = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert len(on_disk["roles"]) == len(snap.roles)
    assert (tmp_path / "history" / "2026-11.jsonl").read_text(encoding="utf-8").count("\n") == len(events)

    # An hour later nothing has changed: no events, no descriptions fetched again.
    calls_before = len(web.calls)
    snap2, events2, _ = run.run(watched, [], data=tmp_path, client=client, now=t0 + timedelta(hours=1), workers=1)
    assert events2 == []
    detail_calls = [c for c in web.calls[calls_before:] if c[0] == "GET" and ("/jobs/" in c[1] or "/job/" in c[1])]
    assert detail_calls == []
    assert [r.first_seen for r in snap2.roles] == [r.first_seen for r in snap.roles]

    # Then Workable's board loses its roles. Doubted twice, believed the third time.
    web.overrides["apply.workable.com"] = httpx.Response(200, json={"name": "x", "jobs": []})
    kinds = []
    for hour in (2, 3, 4):
        _, ev, _ = run.run(watched, [], data=tmp_path, client=client, now=t0 + timedelta(hours=hour), workers=1)
        kinds.append(sorted({e.kind for e in ev}))
    assert kinds == [[], [], ["closed"]]


def test_one_board_failing_does_not_stop_the_run(tmp_path, client, web, boards):
    web.overrides["api.lever.co"] = httpx.Response(500)
    snap, _, problems = run.run(list(boards.values()), [], data=tmp_path, client=client, now=datetime(2026, 11, 10, 8, tzinfo=UTC), workers=1)
    assert problems == []
    failed = [b for b in snap.boards if not b.ok]
    assert [(b.key, b.error) for b in failed] == [("lever:ifm-us", "HTTP 500")]
    assert any(r.status == "open" for r in snap.roles)


def test_a_feed_that_changes_shape_is_reported_not_crashed(tmp_path, client, web, boards):
    web.overrides["boards-api.greenhouse.io"] = httpx.Response(200, json={"jobs": [{"title": "no id here"}]})
    snap, _, problems = run.run([boards["greenhouse"], boards["amazon"]], [], data=tmp_path, client=client, now=datetime(2026, 11, 10, 8, tzinfo=UTC), workers=1)
    assert problems == []
    assert [b.error for b in snap.boards if not b.ok] == ["unexpected feed shape (KeyError)"]


def test_nothing_is_published_when_every_board_fails(tmp_path, client, web, boards):
    for host in ("greenhouse", "lever", "ashby", "workable", "workday", "amazon"):
        web.overrides[host] = httpx.Response(503)
    _, _, problems = run.run(list(boards.values()), [], data=tmp_path, client=client, now=datetime(2026, 11, 10, 8, tzinfo=UTC), workers=1)
    assert problems == ["no board could be read"]
    assert not (tmp_path / "snapshot.json").exists() and not (tmp_path / "state.json").exists()
