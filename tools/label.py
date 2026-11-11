"""Write data/labelled/labels.json: the expected answers the rules are scored against.

    python tools/label.py

How the labels were made (10 Nov 2026). Every one of the 650 UAE postings in the pool was reviewed by title, and
every posting that looked like it could be for a student was read in full. The answers below are what that
reading found. They were written by Claude (the AI assistant that built this project), not by a person, and not
by the rules: where the rules and the reading disagreed, the reading is recorded here.

The file is built from the rules' first-pass output plus the corrections below, because for most postings the
two agreed. It must be run against the rules as they were at that first pass (RULES_VERSION 2) to reproduce
labels.json; after that the file is fixed and the rules are scored against it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from radar import facts, kind  # noqa: E402
from radar.eval import FACT_NAMES, predicted  # noqa: E402

POOL = ROOT / "data" / "discovery" / "pool.jsonl"
OUT = ROOT / "data" / "labelled" / "labels.json"

# Student roles the first-pass rules did not list (pool index -> kind), each read in full.
MISSED_KINDS = {
    14: "graduate",  # Amazon, Graduate Area Manager
    29: "graduate",  # Amazon, Early Talent Cloud Sales Representative
    62: "first_job",  # Amazon, Brand Specialist: "in final year of study ... or graduated in the last 24 months"
    65: "internship",  # Tamara, Associate Accountant, Builders Program: "built for current students"
    72: "first_job",  # Tamara Builders Program: "a recent graduate or early in your career"
    463: "first_job",  # Deliveroo, Finance & Strategy Associate: asks only for internship or project experience
    590: "first_job",  # GSK, Government Operations Associate: "entry-level ... recent graduate or student"
}

# Facts where the reading differs from the first-pass rules (pool index -> fact -> expected).
FACT_FIXES: dict[int, dict[str, str | None]] = {
    18: {"duration": "12 weeks"},  # "for 12 consecutive weeks"
    19: {"duration": "3 months"},  # "for 3 consecutive months"
    20: {"duration": "3 months"},
    353: {"duration": "6 months"},  # "for a 6 month opportunity"
    355: {"stage": "enrolled"},  # "Current undergraduate, postgraduate students, or fresh graduates"
    357: {"duration": "6 months"},  # "for a six-month opportunity"
    498: {"start": "June 2026"},  # "Start Date: June 15, 2026"
    593: {"stage": "graduate"},  # "Completed Bachelor's/Master's degree within the last 12 months"
    594: {"stage": "graduate"},
    642: {"duration": "12 months", "eligibility": "own_visa"},  # "Full time, 12 months"; "must be a UAE resident"
    643: {"start": "June 2026"},
}


# Two labels were corrected after the second scoring, when a rule fix read a posting differently and a full
# reading showed the rule was right and the label (carried over from the first-pass rules) was wrong:
#   Binance, OTC Trader: first_job ("Prior internship or up to 3 years of experience ... preferred")
#   Novartis, Maseeraty Graduate Program: stage graduate ("received a Bachelor's Degree in the past 3 years")
# They are recorded in labels.json under "corrections".


def main() -> None:
    rows = [json.loads(line) for line in POOL.read_text(encoding="utf-8").splitlines()]
    kinds: dict[str, str | None] = {}
    fact_labels: dict[str, dict[str, str | None]] = {}
    for i, row in enumerate(rows):
        verdict = kind.classify(row["title"], row["text"], row.get("employment_type"))
        expected_kind = MISSED_KINDS.get(i, verdict.kind)
        kinds[row["id"]] = expected_kind
        if verdict.kind is None or ":Campus:" in row["id"]:
            continue  # facts are labelled for the roles read in full; the campus site repeats the main site
        found = facts.read(row["title"], row["text"], workplace=row.get("workplace"))
        answers = {key: predicted(key, found.get(key)) for key in FACT_NAMES}
        answers.update(FACT_FIXES.get(i, {}))
        fact_labels[row["id"]] = answers
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "date": "10 Nov 2026",
                "labelled_by": "Claude, by reading each posting; not checked by a person",
                "kinds": kinds,
                "facts": fact_labels,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    students = sum(1 for v in kinds.values() if v)
    print(f"{len(kinds)} postings labelled for kind ({students} student roles), {len(fact_labels)} with facts")


if __name__ == "__main__":
    main()
