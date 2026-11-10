"""Is this posting in the UAE, and in which emirate?

Sources write places every way there is: "Dubai", "AE - Dubai", "Dubai, United Arab Emirates", "Abu Dhabi (ADGM)",
"United Arab Emirates", "Remote - EMEA". Only a place that names the country or one of its cities counts.
"""

from __future__ import annotations

import re

from radar.models import Place

# Order matters: the first match names the emirate.
_EMIRATES: list[tuple[str, re.Pattern[str]]] = [
    ("Abu Dhabi", re.compile(r"\babu\s*dhabi\b|\badgm\b|\bmasdar\s+city\b|\bal\s*ain\b|\byas\s+island\b|\bal\s+reem\b|\bmussafah\b|\bruwais\b", re.I)),
    ("Dubai", re.compile(r"\bdubai\b|\bdifc\b|\bjebel\s+ali\b|\bjafza\b|\bdeira\b|\bbusiness\s+bay\b|\bjlt\b|\bdxb\b", re.I)),
    ("Sharjah", re.compile(r"\bsharjah\b", re.I)),
    ("Ajman", re.compile(r"\bajman\b", re.I)),
    ("Ras Al Khaimah", re.compile(r"\bras\s+al[\s-]*kha[iy]mah\b|\brak\s+(?:city|free)", re.I)),
    ("Fujairah", re.compile(r"\bfujairah\b", re.I)),
    ("Umm Al Quwain", re.compile(r"\bumm\s+al[\s-]*qu?wain\b", re.I)),
]
_COUNTRY = re.compile(
    r"\bunited\s+arab\s+emirates\b|\bu\.?a\.?e\.?\b|\bemirates\b(?!\s+(?:airline|group|nbd|post|stadium))"
    r"|(?:^|[\s,(/-])AE(?:$|[\s,)/-])|\bARE\b",
)
_COUNTRY_I = re.compile(r"\bunited\s+arab\s+emirates\b|\bu\.a\.e\.?\b|\buae\b", re.I)
_SPLIT = re.compile(r"\s*(?:;|\||\s/\s|\bor\b|\band\b|&|\n)\s*", re.I)


def match(raw: str) -> Place | None:
    """Return the UAE place a single location string names, or None."""
    s = raw.strip()
    if not s:
        return None
    for emirate, pattern in _EMIRATES:
        if pattern.search(s):
            return Place(emirate=emirate, raw=s)
    if _COUNTRY_I.search(s) or _COUNTRY.search(s):
        return Place(emirate="UAE", raw=s)
    return None


def split(raw: str) -> list[str]:
    """Some sources put several places in one string: "Riyadh; Dubai" or "Dubai / Abu Dhabi"."""
    return [part.strip(" ,") for part in _SPLIT.split(raw) if part.strip(" ,")]


def read(locations: list[str]) -> tuple[list[Place], int]:
    """Return (UAE places, count of places elsewhere) for a posting's location strings."""
    places: list[Place] = []
    elsewhere = 0
    seen: set[str] = set()
    for loc in locations:
        if not loc:
            continue
        whole = match(loc)
        parts = split(loc)
        if whole is not None and len(parts) <= 1:
            parts = [loc]
        for part in parts:
            place = match(part)
            if place is None:
                elsewhere += 1
            elif place.emirate not in seen:
                seen.add(place.emirate)
                places.append(place)
    # "Dubai" and "UAE" on the same posting is one place, not two.
    if len(places) > 1:
        places = [p for p in places if p.emirate != "UAE"] or places[:1]
    return places, elsewhere
