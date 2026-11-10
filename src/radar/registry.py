"""The list of employers being watched, kept in data/companies.yaml so a person can read and edit it."""

from __future__ import annotations

from pathlib import Path

import yaml

from radar.models import Board
from radar.sources import ADAPTERS

DEFAULT = Path(__file__).resolve().parents[2] / "data" / "companies.yaml"


class RegistryError(ValueError):
    pass


def board_from(entry: dict) -> Board:
    system = entry.get("system")
    slug = entry.get("slug")
    name = entry.get("name")
    if system not in ADAPTERS:
        raise RegistryError(f"unknown system {system!r} for {name!r}")
    if not slug or not name:
        raise RegistryError(f"an entry needs a slug and a name: {entry!r}")
    if system == "workday" and not (entry.get("host") and entry.get("site")):
        raise RegistryError(f"Workday entry {name!r} needs host and site")
    key = f"{system}:{slug}" + (f":{entry['site']}" if system == "workday" else "")
    return Board(key=key, system=system, slug=str(slug), name=str(name), site=entry.get("site"), host=entry.get("host"), home=entry.get("home"))


def load(path: Path = DEFAULT) -> tuple[list[Board], list[dict]]:
    """Return (boards, not_covered). Duplicate keys are an error, so one employer is never read twice."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    boards: list[Board] = []
    seen: set[str] = set()
    for entry in doc.get("boards") or []:
        board = board_from(entry)
        if board.key in seen:
            raise RegistryError(f"duplicate board {board.key}")
        seen.add(board.key)
        boards.append(board)
    not_covered = [
        {"name": str(item["name"]), "reason": str(item.get("reason", ""))} for item in doc.get("not_covered") or []
    ]
    return boards, not_covered
