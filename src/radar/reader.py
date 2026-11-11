"""From one raw posting to one role: place, kind, facts, excerpt. No network, no clock."""

from __future__ import annotations

import hashlib
import re

from radar import facts, kind, place, skills
from radar.models import Place, RawPosting, Role
from radar.text import clip, sentences, slugify, to_text

_BOILER = re.compile(
    r"equal\s+opportunit|cookies?\b|privacy\s+(?:policy|notice)|we\s+are\s+an?\s+\w+\s+employer|about\s+(?:us|the\s+company)\s*:?$|^who\s+we\s+are|"
    r"^job\s+description\s*:?$|^overview\s*:?$|^about\s+the\s+role\s*:?$|^our\s+purpose|^position\s+summary",
    re.I,
)


_TITLE_ELIGIBILITY = re.compile(r"\s*[\(\[][^\)\]]*\b(?:uaen|uae\s+nationals?|emiratis?|emirati\s+nationals?|nationals?\s+only)\b[^\)\]]*[\)\]]", re.I)
_TITLE_PLACE = re.compile(
    r"\s*(?:[-–—,|:]\s*)+(?:(?:dubai|abu\s+dhabi|sharjah)\s*,\s*)?(?:dubai|abu\s+dhabi|sharjah|uae|u\.a\.e\.?|united\s+arab\s+emirates)\s*$",
    re.I,
)


def clean_title(title: str) -> str:
    """Titles often repeat what the row already shows: "... - Dubai, UAE (UAE Nationals Preferred)".
    The place and the nationality note are dropped from the displayed title; both are shown as facts instead,
    and the eligibility fact still quotes the employer's full title."""
    t = re.sub(r"\s+", " ", title).strip()
    for _ in range(3):
        before = t
        t = _TITLE_ELIGIBILITY.sub("", t).strip()
        t = _TITLE_PLACE.sub("", t).strip(" -–—,|:")
        if t == before:
            break
    return t if len(t) >= 6 else re.sub(r"\s+", " ", title).strip()


def fingerprint(raw: RawPosting) -> str:
    """Changes when the list entry changes, which is the cue to read the posting again."""
    stamp = raw.updated_at.isoformat() if raw.updated_at else ""
    basis = "|".join([raw.title, ";".join(sorted(raw.locations)), stamp, raw.employment_type or ""])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def places_of(raw: RawPosting) -> tuple[list[Place], int]:
    places, elsewhere = place.read(raw.locations)
    if not places and raw.extra.get("uae_filter"):
        # The source itself filtered on the UAE; its list text ("2 Locations") just does not name the place.
        return [Place(emirate="UAE", raw=raw.locations[0] if raw.locations else "United Arab Emirates")], 0
    return places, elsewhere


def body(raw: RawPosting) -> str:
    return to_text(raw.html) if raw.html else (raw.text or "").strip()


_ABOUT_ROLE = re.compile(
    r"\byou(?:'ll|’ll|\s+will|r)?\b|\bintern(?:s|ship)?\b|\bthe\s+role\b|\bthis\s+(?:role|position|program(?:me)?|opportunity)\b"
    r"|\bwe\s+are\s+(?:looking|seeking|hiring)\b|\blooking\s+for\b|\bresponsib|\bgraduates?\b|\bstudents?\b|\btrainee",
    re.I,
)


def excerpt(text: str) -> str:
    """Two sentences about the role itself. Company introductions and legal boilerplate are passed over; when
    nothing speaks about the role, the first plain sentences are used."""
    usable = [s for s in sentences(text) if len(s) >= 40 and not _BOILER.search(s)]
    about = [s for s in usable if _ABOUT_ROLE.search(s)]
    picked: list[str] = []
    for s in about or usable:
        picked.append(s)
        if len(" ".join(picked)) > 180 or len(picked) == 2:
            break
    return clip(" ".join(picked), 300)


def role_slug(employer: str, title: str, role_id: str) -> str:
    tail = hashlib.sha256(role_id.encode("utf-8")).hexdigest()[:6]
    return f"{slugify(employer, 30)}-{slugify(title, 50)}-{tail}"


def read(raw: RawPosting, *, now: str) -> Role | None:
    """Return the role, or None when the posting is not in the UAE or not a student role."""
    places, elsewhere = places_of(raw)
    if not places:
        return None
    text = body(raw)
    verdict = kind.classify(raw.title, text, raw.employment_type)
    if verdict.kind is None:
        return None
    return Role(
        id=raw.id,
        slug=role_slug(raw.board.name, raw.title, raw.id),
        employer=raw.board.name,
        board=raw.board.key,
        system=raw.board.system,
        title=clean_title(raw.title),
        url=raw.url,
        places=places,
        elsewhere=elsewhere,
        kind=verdict.kind,  # type: ignore[arg-type]
        kind_reason=verdict.reason,
        fields=facts.fields(raw.title, raw.department),
        skills=skills.read(raw.title, text),
        facts=facts.read(raw.title, text, workplace=raw.workplace),
        department=raw.department if raw.department and place.match(raw.department) is None else None,
        excerpt=excerpt(text),
        posted_at=raw.posted_at.isoformat() if raw.posted_at else None,
        first_seen=now,
        last_seen=now,
    )
