import json
import re
from pathlib import Path

import pytest

from radar import skills

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Experience using SQL to pull data and build dashboards in Power BI.", ["SQL", "Power BI", "Dashboards and reporting"]),
        ("Strong programming skills in Python and experience with PyTorch and large language models.", ["Python", "LLMs and NLP", "PyTorch or TensorFlow"]),
        ("Proficiency in R, Python or SAS.", ["Python", "R"]),
        ("Familiarity with JavaScript and React.", ["JavaScript", "React"]),
        ("Fluent in Arabic and English.", ["Arabic"]),
    ],
)
def test_skills_are_read_from_the_words_used(text, expected):
    assert skills.read("Intern", text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "You will support our R&D team and our research partners.",
        "We react quickly to customers and go the extra mile.",
        "Javanese coffee is served daily; our culture is built on trust.",
        "Rust-proof coatings for offshore structures.",
    ],
)
def test_skills_are_not_read_from_lookalike_words(text):
    assert skills.read("Site Engineer", text) == []


def test_the_site_reads_a_cv_with_the_same_list():
    on_site = json.loads((ROOT / "site" / "src" / "lib" / "skills.json").read_text(encoding="utf-8"))
    assert on_site == skills.patterns(), "run: python tools/export_skills.py"


def test_every_pattern_is_one_javascript_can_run():
    # The site compiles these in the browser. Python-only syntax would break it there.
    for item in skills.patterns():
        assert not re.search(r"\(\?P<|\(\?[aiLmsux]+\)", item["pattern"]), item["name"]
        assert item["flags"] in ("", "i")
