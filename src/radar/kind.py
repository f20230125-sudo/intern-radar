"""Is this posting a student role, and which kind?

Three kinds, decided mostly from the title because that is where employers say it:
  internship  a placement for someone still studying (intern, trainee, working student, co-op, placement)
  graduate    a programme for people finishing or just finished (graduate programme, new grad, campus hire)
  first_job   an ordinary job that asks for a year of experience or less

Anything else is not a student role and is left out of the snapshot. The reason is kept with the answer so the
site can show why a role is listed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_I = re.I

# People who run student programmes are staff, not students: "Early Careers Recruiter", "Internship Programme Manager".
_STAFF = re.compile(
    r"\b(?:campus|university|graduate|early[\s-]*careers?|emerging\s+talent|intern(?:ship)?s?)\b[\s,/&-]*"
    r"(?:and\s+\w+\s+)?(?:program(?:me)?s?\s+|recruit(?:ing|ment)\s+|relations\s+|talent\s+|hiring\s+|experience\s+)*"
    r"(?:manager|lead|leader|director|head|coordinator|co-ordinator|recruiter|partner|specialist|advisor|adviser|officer|executive|consultant)\b"
    r"|\b(?:recruiter|talent\s+acquisition|head|director|manager|lead)\b[^,;|]{0,40}\b(?:campus|university\s+(?:relations|recruit)|early[\s-]*careers?|emerging\s+talent|graduate\s+(?:program|recruit|admission))",
    _I,
)
_SENIOR = re.compile(
    r"\b(?:senior|sr\.?|lead|principal|staff|head|director|vp|vice\s+president|chief|manager|supervisor|expert|architect|"
    r"specialist\s+ii+|iii|level\s*[3-9])\b",
    _I,
)

_INTERN = re.compile(
    r"\bintern(?:s|ship|ships)?\b|\binterne?e\b|\bworking\s+student\b|\bco-?op\b(?!\s*erat)|\bindustrial\s+(?:placement|train(?:ee|ing))\b"
    r"|\bplacement\s+(?:student|year)\b|\byear\s+in\s+industry\b|\bsummer\s+(?:analyst|associate|student|trainee)\b"
    r"|\bstudent\s+(?:researcher|assistant|trainee|worker|placement|program)|\bapprentice(?:ship)?\b|\bstagiaire\b|\bwerkstudent\b"
    r"|\b(?:winter|spring|summer|fall|autumn)\s+(?:20\d\d\s+)?internship\b|\bthesis\s+student\b",
    _I,
)
_TRAINEE = re.compile(r"\btrainee\b", _I)
_GRADUATE = re.compile(
    r"\bgraduate\s+(?:program(?:me)?|scheme|trainee|development|rotation|intake|opportunit|engineer|analyst|developer|consultant|"
    r"associate|accountant|surveyor|architect|designer|scientist|technician|planner|trader|economist|auditor|role|position|hire)"
    r"|\bgraduates?\b\s*(?:20\d\d|[-–(,]|$)|\bnew\s+grad(?:uate)?s?\b|\bfresh\s+grad(?:uate)?s?\b|\brecent\s+grad(?:uate)?s?\b"
    r"|\b(?:uae\s+)?national\s+graduates?\b|\bcampus\s+hire\b|\buniversity\s+(?:graduate|hire)\b|\bclass\s+of\s+20\d\d\b"
    r"|\bmanagement\s+trainee\b|\bgraduate\s+management\b|\brotational\s+(?:program|analyst|associate)|\blaunch\s+program(?:me)?\b"
    r"|\bearly[\s-]*careers?\b|\bemerging\s+talent\b|\banalyst\s+program(?:me)?\b|\bassociate\s+program(?:me)?\b|\bfuture\s+leaders?\b"
    r"|\bgraduate\b[^,;|]{0,30}\b20\d\d\b",
    _I,
)
_JUNIOR = re.compile(r"\bjunior\b|\bjr\.?\b|\bentry[\s-]*level\b|\btrainee\b|\bassociate\b|\bassistant\b|\banalyst\s+i\b|\blevel\s*1\b|\bgraduate\b", _I)

# "2+ years of experience", "0-1 years", "minimum of three years' experience", "at least 1 year".
_NUM = r"(\d{1,2}|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
_YEARS = re.compile(
    rf"{_NUM}\s*(?:\+|plus)?\s*(?:(?:-|–|—|to)\s*{_NUM}\s*)?\+?\s*(?:years?|yrs?)\b[^.\n]{{0,60}}?\b(?:experience|exp\b|background|track\s+record)"
    rf"|\bexperience\b[^.\n]{{0,40}}?{_NUM}\s*(?:\+|plus)?\s*(?:(?:-|–|—|to)\s*{_NUM}\s*)?\+?\s*(?:years?|yrs?)\b",
    _I,
)
_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_NO_EXPERIENCE = re.compile(
    r"\bno\s+(?:prior\s+|previous\s+|work\s+)?experience\s+(?:is\s+)?(?:required|needed|necessary)\b|\bfresh\s+graduates?\s+(?:are\s+)?(?:welcome|encouraged|can\s+apply|may\s+apply)"
    r"|\b(?:open\s+to|suitable\s+for|ideal\s+for|welcome)\s+(?:fresh|recent|new)\s+graduates?\b|\b(?:recent|fresh|new)\s+graduates?\s+(?:with|who|looking)\b",
    _I,
)


@dataclass(frozen=True)
class Verdict:
    kind: str | None
    reason: str


def _num(s: str) -> int:
    return _WORDS.get(s.lower(), int(s) if s.isdigit() else 99)


def min_years(text: str) -> tuple[int, str] | None:
    """The lowest "years of experience" a posting asks for, with the matched words. None if it never says."""
    best: tuple[int, str] | None = None
    for m in _YEARS.finditer(text):
        groups = [g for g in m.groups() if g]
        if not groups:
            continue
        low = _num(groups[0])
        if low > 40:
            continue
        if best is None or low < best[0]:
            best = (low, re.sub(r"\s+", " ", m.group(0)).strip())
    return best


def classify(title: str, text: str = "", employment_type: str | None = None) -> Verdict:
    t = re.sub(r"\s+", " ", title).strip()
    if _STAFF.search(t):
        return Verdict(None, "runs a student programme, not a student role")

    feed_says_intern = bool(employment_type and re.search(r"\bintern", employment_type, _I))
    m = _INTERN.search(t)
    if m:
        return Verdict("internship", f'title says "{m.group(0)}"')
    m = _GRADUATE.search(t)
    if m and not _SENIOR.search(_GRADUATE.sub(" ", t)):
        return Verdict("graduate", f'title says "{m.group(0).strip()}"')
    if feed_says_intern and not _SENIOR.search(t):
        return Verdict("internship", f'the employer files it as "{employment_type}"')
    m = _TRAINEE.search(t)
    if m and not _SENIOR.search(t):
        return Verdict("internship", 'title says "trainee"')

    if _SENIOR.search(t):
        return Verdict(None, "senior title")
    years = min_years(text) if text else None
    junior = _JUNIOR.search(t)
    if years is not None:
        if years[0] <= 1 and (junior or _NO_EXPERIENCE.search(text)):
            return Verdict("first_job", f'asks for "{years[1]}"')
        if years[0] == 0:
            return Verdict("first_job", f'asks for "{years[1]}"')
        return Verdict(None, f'asks for "{years[1]}"')
    m = _NO_EXPERIENCE.search(text) if text else None
    if m:
        return Verdict("first_job", f'says "{re.sub(r"\s+", " ", m.group(0))}"')
    if junior and re.search(r"\bjunior\b|\bjr\.?\b|\bentry[\s-]*level\b|\bgraduate\b", t, _I) and text:
        return Verdict("first_job", f'title says "{junior.group(0)}" and no experience is asked for')
    return Verdict(None, "no sign of a student role")


def looks_student(title: str, employment_type: str | None = None) -> bool:
    """A cheap title-only check, used to decide whether a posting's description is worth fetching."""
    t = title
    if _STAFF.search(t):
        return False
    if _INTERN.search(t) or _GRADUATE.search(t) or _TRAINEE.search(t):
        return True
    if employment_type and re.search(r"\bintern", employment_type, _I):
        return True
    return bool(_JUNIOR.search(t)) and not _SENIOR.search(t)
