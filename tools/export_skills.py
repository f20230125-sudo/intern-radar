"""Write the collector's skill list to site/src/lib/skills.json, so the site reads a pasted CV with the same rules.

    python tools/export_skills.py

A test fails if the two ever differ.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from radar import skills  # noqa: E402

OUT = ROOT / "site" / "src" / "lib" / "skills.json"

if __name__ == "__main__":
    OUT.write_text(json.dumps(skills.patterns(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(skills.NAMES)} skills -> {OUT.relative_to(ROOT)}")
