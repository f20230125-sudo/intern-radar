"""Score the rules against postings whose answers were written out by reading each posting in full.

    python -m radar.eval            print the table, write site/public/eval.json
    python -m radar.eval --misses   also list every disagreement

Two files are needed:
  data/discovery/pool.jsonl   every UAE posting with its full text (tools/pool.py; not committed)
  data/labelled/labels.json   the expected answers, by posting id

Kind is scored on every labelled posting: is it a student role, and which kind. Facts are scored on the postings
labelled as student roles. For a fact, precision is how often a stated reading was right and recall is how often
a fact that the posting states was read. A fact the label says is not stated and the rules also leave out counts
for neither: it is the common case and would flatter both numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from radar import facts as fact_rules
from radar import kind as kind_rules

ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "data" / "discovery" / "pool.jsonl"
LABELS = ROOT / "data" / "labelled" / "labels.json"
OUT = ROOT / "site" / "public" / "eval.json"
FIRST = ROOT / "data" / "labelled" / "first_pass.json"

# What is compared for each fact: the category for facts that are categories, the wording for facts that are values.
BY_VALUE = ("eligibility", "stage", "mode")
BY_LABEL = ("duration", "start", "deadline")
FACT_NAMES = {
    "eligibility": "Who can apply",
    "start": "Start",
    "duration": "Length",
    "pay": "Pay",
    "stage": "Stage of study",
    "mode": "Where you work",
    "deadline": "Closing date",
}


def predicted(key: str, fact) -> str | None:
    if fact is None:
        return None
    if key == "pay":
        return "amount" if fact.value == "amount" else fact.value
    return fact.value if key in BY_VALUE else fact.label


def ratio(num: int, den: int) -> float | None:
    return round(num / den, 3) if den else None


def score(pool: dict[str, dict], labels: dict) -> tuple[list[dict], list[str]]:
    misses: list[str] = []
    kinds: dict[str, str | None] = labels["kinds"]
    tp = fp = fn = exact = 0
    for pid, expected in kinds.items():
        row = pool.get(pid)
        if row is None:
            continue
        got = kind_rules.classify(row["title"], row["text"], row.get("employment_type")).kind
        if expected and got:
            tp += 1
            exact += got == expected
            if got != expected:
                misses.append(f"kind  {row['employer']}: {row['title']!r} read as {got}, labelled {expected}")
        elif got and not expected:
            fp += 1
            misses.append(f"kind  {row['employer']}: {row['title']!r} read as {got}, labelled not a student role")
        elif expected and not got:
            fn += 1
            misses.append(f"kind  {row['employer']}: {row['title']!r} missed, labelled {expected}")
    scores = [
        {"name": "Is it a student role", "n": tp + fn, "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn)},
        {"name": "Which kind, when it is one", "n": tp, "precision": ratio(exact, tp), "recall": ratio(exact, tp)},
    ]

    fact_labels: dict[str, dict[str, str | None]] = labels["facts"]
    for key in FACT_NAMES:
        tp = fp = fn = 0
        for pid, expected_facts in fact_labels.items():
            row = pool.get(pid)
            if row is None or key not in expected_facts:
                continue
            found = fact_rules.read(row["title"], row["text"], workplace=row.get("workplace"))
            got, expected = predicted(key, found.get(key)), expected_facts[key]
            if expected is not None and got == expected:
                tp += 1
            else:
                if got is not None:
                    fp += 1
                if expected is not None:
                    fn += 1
                if got != expected:
                    misses.append(f"{key:11s} {row['employer']}: {row['title'][:50]!r} read {got!r}, labelled {expected!r}")
        scores.append({"name": FACT_NAMES[key], "n": tp + fn, "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn)})
    return scores, misses


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--misses", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    if not POOL.exists() or not LABELS.exists():
        print("needs data/discovery/pool.jsonl (python tools/pool.py) and data/labelled/labels.json")
        return 1
    pool = {row["id"]: row for row in map(json.loads, POOL.read_text(encoding="utf-8").splitlines())}
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    scores, misses = score(pool, labels)
    labelled = sum(1 for pid in labels["kinds"] if pid in pool)
    print(f"{labelled} labelled postings ({sum(1 for p in labels['facts'] if p in pool)} with facts labelled)\n")
    print(f"{'what is read':30s} {'applies':>8s} {'precision':>10s} {'recall':>8s}")
    for s in scores:
        fmt = lambda v: "n/a" if v is None else f"{v:.0%}"  # noqa: E731
        print(f"{s['name']:30s} {s['n']:8d} {fmt(s['precision']):>10s} {fmt(s['recall']):>8s}")
    if args.misses:
        print("\nDisagreements:")
        for m in misses:
            print(" ", m)
    if not args.no_write:
        first = json.loads(FIRST.read_text(encoding="utf-8"))["scores"] if FIRST.exists() else []
        report = {
            "labelled": labelled,
            "with_facts": sum(1 for p in labels["facts"] if p in pool),
            "date": labels["date"],
            "labelled_by": labels.get("labelled_by", ""),
            "scores": scores,
            "first_pass": first,
        }
        OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
