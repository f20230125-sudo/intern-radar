"""Reading the facts a student needs out of a posting.

Every fact comes with the sentence it was read from, so a reader can check it. A posting that does not say
something gets no fact for it: the site then shows "not stated". Nothing here guesses.

Facts:
  eligibility  who may apply (UAE nationals only / preferred, open to all, needs own visa)
  pay          paid, unpaid, or an amount
  duration     how long the placement runs
  start        when it starts
  stage        what stage of study it is for
  mode         on site, hybrid or remote
  deadline     when applications close
"""

from __future__ import annotations

import re

from radar.models import Fact
from radar.text import clip, sentences

_I = re.I
_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_SEASON = r"(?:summer|winter|spring|fall|autumn)"
_NUMWORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
_N = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"


_LIMIT = 260


def _fact(value: str, label: str, sentence: str, source: str = "text", mark: str | None = None) -> Fact:
    """`mark` is the exact run of words that decided the fact; the site underlines it inside the sentence.
    A long sentence is cut to a window around the mark, so the deciding words are never clipped away."""
    sentence = re.sub(r"\s+", " ", sentence).strip()
    mark = re.sub(r"\s+", " ", mark).strip() if mark else None
    if mark and mark not in sentence:
        mark = None
    if len(sentence) > _LIMIT and mark:
        at = sentence.index(mark)
        begin = max(0, min(at - 80, len(sentence) - _LIMIT))
        if begin > 0:
            space = sentence.find(" ", begin)
            begin = space + 1 if 0 <= space < at else begin
        piece = sentence[begin : begin + _LIMIT]
        if begin + _LIMIT < len(sentence):
            cut = piece.rfind(" ")
            piece = (piece[:cut] if cut > at - begin + len(mark) else piece).rstrip(" ,;:-") + "…"
        evidence = ("…" if begin > 0 else "") + piece
    else:
        evidence = clip(sentence, _LIMIT)
    if mark and mark not in evidence:
        mark = None
    return Fact(value=value, label=label, evidence=evidence, source=source, mark=mark)  # type: ignore[arg-type]


def _n(s: str) -> int:
    return _NUMWORD.get(s.lower(), int(s) if s.isdigit() else 0)


# ---------------------------------------------------------------- eligibility

_NATIONAL = r"(?:uae\s+nationals?|u\.a\.e\.?\s+nationals?|emirati(?:s)?(?:\s+nationals?)?|uaen|uae\s+citizens?|emirati\s+citizens?|local\s+emirati)"
_ONLY = re.compile(
    rf"\b(?:only|exclusively|strictly|must\s+be|limited\s+to|restricted\s+to|reserved\s+for|open\s+to|for|designed\s+for|dedicated\s+to|eligible)\b[^.\n]{{0,40}}{_NATIONAL}"
    rf"|{_NATIONAL}\s*(?:only|\(only\)|are\s+eligible|are\s+invited|candidates?\s+only|program(?:me)?|graduates?\b|talent\s+program)"
    r"|\bemirati[sz]ation\b|\bnafis\b|\btawteen\b|\bfamily\s+book\b|\bkhulasat\s+al\s+qaid\b",
    _I,
)
_PREFERRED = re.compile(
    rf"{_NATIONAL}[^.\n]{{0,40}}\b(?:preferred|preference|encouraged|priority|are\s+welcome|will\s+be\s+given)\b"
    rf"|\b(?:preference|priority)\b[^.\n]{{0,40}}{_NATIONAL}|\b(?:preferred|encourage[sd]?)\b[^.\n]{{0,30}}{_NATIONAL}",
    _I,
)
_NATIONAL_ANY = re.compile(_NATIONAL, _I)
_OPEN = re.compile(
    r"\b(?:all|any)\s+nationalit(?:y|ies)\b|\bopen\s+to\s+(?:all\s+)?(?:international|expat(?:riate)?)\b|\binternational\s+students?\s+(?:are\s+)?(?:welcome|eligible|may\s+apply)"
    r"|\bvisa\s+sponsorship\s+(?:is\s+)?(?:provided|available|offered)\b|\bwe\s+(?:will\s+)?(?:sponsor|provide)\s+(?:your\s+)?(?:visa|work\s+permit)\b"
    r"|\bregardless\s+of\s+nationality\b",
    _I,
)
_OWN_VISA = re.compile(
    r"\b(?:must|should|need\s+to|required\s+to)\s+(?:already\s+)?(?:have|hold|possess|be\s+on)\b[^.\n]{0,40}\b(?:valid\s+)?(?:uae\s+)?(?:residen(?:ce|cy)|visa|work\s+permit|student\s+visa)\b"
    r"|\b(?:own|spouse|parent|father|family|husband|student|university)[\s'’s-]*(?:sponsor(?:ed|ship)?|visa)\b"
    r"|\bvisa\s+sponsorship\s+(?:is\s+|will\s+)?not\b|\bno\s+visa\s+sponsorship\b|\b(?:unable|not\s+able)\s+to\s+(?:sponsor|provide\s+(?:a\s+)?visa)"
    r"|\bcurrently\s+(?:based|residing|living)\s+in\s+(?:the\s+)?(?:uae|dubai|abu\s+dhabi)\b|\bmust\s+be\s+(?:based|resident|residing)\s+in\s+(?:the\s+)?(?:uae|dubai)"
    r"|\bmust\s+be\s+an?\s+(?:uae|dubai|abu\s+dhabi)\s+resident\b|\b(?:uae|dubai)\s+residents?\s+only\b"
    r"|\bno\s+objection\s+(?:certificate|letter)\b|\bnoc\b\s+from",
    _I,
)
_PROGRAMME = re.compile(r"\bemirati[sz]ation\b|\bnafis\b|\btawteen\b|\bfamily\s+book\b", _I)
_TITLE_NATIONAL = re.compile(r"\buaen\b|\buae\s+nationals?\b|\bemiratis?\b|\bnational\s+graduates?\b", _I)
_TITLE_PREFERRED = re.compile(r"preferred|preference", _I)


def eligibility(title: str, sents: list[str]) -> Fact | None:
    m = _TITLE_NATIONAL.search(title)
    if m:
        if _TITLE_PREFERRED.search(title):
            return _fact("nationals_preferred", "UAE nationals preferred", title, "title", m.group(0))
        return _fact("nationals_only", "UAE nationals only", title, "title", m.group(0))
    preferred: Fact | None = None
    for s in sents:
        m = _PREFERRED.search(s)
        if m:
            preferred = preferred or _fact("nationals_preferred", "UAE nationals preferred", s, mark=m.group(0))
            continue
        m = _ONLY.search(s)
        if m and _NATIONAL_ANY.search(s):
            return _fact("nationals_only", "UAE nationals only", s, mark=m.group(0))
        m = _PROGRAMME.search(s)
        if m:
            return _fact("nationals_only", "UAE nationals only", s, mark=m.group(0))
    if preferred:
        return preferred
    for s in sents:
        m = _OPEN.search(s)
        if m:
            return _fact("open", "Open to all nationalities", s, mark=m.group(0))
    for s in sents:
        m = _OWN_VISA.search(s)
        if m:
            return _fact("own_visa", "Needs your own UAE visa", s, mark=m.group(0))
    return None


# ------------------------------------------------------------------------ pay

_CUR = r"(?:aed|dhs?\.?|dirhams?|usd|us\$|\$|sar|eur|€|gbp|£)"
_AMOUNT = re.compile(
    rf"(?:{_CUR})\s?(\d{{1,3}}(?:[,\s]\d{{3}})+|\d{{3,6}})(?:\s?(?:-|–|to)\s?(?:{_CUR}\s?)?(\d{{1,3}}(?:[,\s]\d{{3}})+|\d{{3,6}}))?"
    rf"|(\d{{1,3}}(?:[,\s]\d{{3}})+|\d{{3,6}})(?:\s?(?:-|–|to)\s?(\d{{1,3}}(?:[,\s]\d{{3}})+|\d{{3,6}}))?\s?({_CUR})\b",
    _I,
)
_PER = re.compile(r"\b(?:per|a|/|each)\s*(month|year|annum|week|hour|day)|\b(monthly|annual(?:ly)?|yearly|weekly|hourly)\b|/\s?(mo|yr|hr)\b", _I)
_PAY_CUE = re.compile(r"\b(?:stipend|salary|compensation|allowance|pay|paid|remuneration|wage|package|earn)\b", _I)
_UNPAID = re.compile(r"\bunpaid\b|\bnon[\s-]?paid\b|\bno\s+(?:stipend|salary|remuneration|compensation)\b|\bwithout\s+(?:pay|stipend|salary)\b|\bvoluntary\s+(?:internship|position|role)\b|\bnot\s+a\s+paid\b", _I)
_PAID = re.compile(r"\bpaid\s+(?:internship|intern|placement|position|program(?:me)?|traineeship|opportunity)\b|\b(?:monthly\s+)?stipend\b|\binternship\s+is\s+paid\b|\bfully\s+paid\b|\bcompetitive\s+(?:salary|stipend|pay|compensation)\b|\bmonthly\s+allowance\b", _I)
_CUR_NAME = {"aed": "AED", "dh": "AED", "dhs": "AED", "dirham": "AED", "dirhams": "AED", "usd": "USD", "us$": "USD", "$": "USD", "sar": "SAR", "eur": "EUR", "€": "EUR", "gbp": "GBP", "£": "GBP"}
_PERIOD = {"month": "month", "monthly": "month", "mo": "month", "year": "year", "annum": "year", "annual": "year", "annually": "year", "yearly": "year", "yr": "year", "week": "week", "weekly": "week", "hour": "hour", "hourly": "hour", "hr": "hour", "day": "day"}


def _digits(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def pay(sents: list[str]) -> Fact | None:
    for s in sents:
        m = _UNPAID.search(s)
        if m:
            return _fact("unpaid", "Unpaid", s, mark=m.group(0))
    for s in sents:
        if not _PAY_CUE.search(s):
            continue
        m = _AMOUNT.search(s)
        if not m:
            continue
        low = m.group(1) or m.group(3)
        high = m.group(2) or m.group(4)
        cur_raw = (m.group(5) or re.match(_CUR, m.group(0), _I).group(0)).lower().rstrip(".")  # type: ignore[union-attr]
        cur = _CUR_NAME.get(cur_raw, cur_raw.upper())
        lo = _digits(low)
        if lo < 100:
            continue
        per = _PER.search(s)
        period = _PERIOD.get(next(g for g in per.groups() if g).lower(), "") if per else ""
        amount = f"{cur} {lo:,}" + (f" to {_digits(high):,}" if high else "") + (f" a {period}" if period else "")
        return _fact("amount", amount, s, mark=m.group(0))
    for s in sents:
        m = _PAID.search(s)
        if m:
            return _fact("paid", "Paid, amount not stated", s, mark=m.group(0))
    return None


# ------------------------------------------------------------------- duration

_SPAN = re.compile(rf"\b{_N}\s*(?:\+\s*)?(?:(?:-|–|—|to|or)\s*{_N}\s*)?[\s-]*(?:consecutive\s+|full\s+|calendar\s+)?(weeks?|months?|years?)\b", _I)
_DUR_CUE = re.compile(
    r"\b(?:duration|internship|intern\b|placement|program(?:me)?|traineeship|contract|fixed[\s-]term|period\s+of|available\s+(?:to\s+work\s+)?(?:for|full)|commit(?:ment)?|"
    r"long\b|lasting|lasts|runs?\s+for|minimum\s+of|for\s+a\s+(?:minimum|period)|opportunity|full[\s-]?time)\b",
    _I,
)
_DUR_NOT = re.compile(r"\bexperience\b|\bprobation|\bnotice\s+period|\bwithin\b|\bgraduat(?:ed|ing|ion)\b|\bold\b|\bissued\b|\bvalid\b|\bago\b|\bevery\b|\bleave\b", _I)


def duration(title: str, sents: list[str]) -> Fact | None:
    for source, items in (("title", [title]), ("text", sents)):
        for s in items:
            if source == "text" and (not _DUR_CUE.search(s)):
                continue
            for m in _SPAN.finditer(s):
                window = s[max(0, m.start() - 60) : m.end() + 40]
                if source == "text" and _DUR_NOT.search(window):
                    continue
                low, high, unit = _n(m.group(1)), _n(m.group(2)) if m.group(2) else 0, m.group(3).lower().rstrip("s")
                if low == 0 or (unit == "year" and low > 3) or (unit == "month" and low > 36) or (unit == "week" and low > 104):
                    continue
                if unit == "year" and source == "text" and not re.search(r"program|scheme|rotation|contract|placement", s, _I):
                    continue
                span = f"{low} to {high}" if high and high != low else f"{low}"
                plural = "" if (not high and low == 1) else "s"
                return _fact(f"{low}-{high or low}-{unit}", f"{span} {unit}{plural}", s, source, m.group(0))
    return None


# ---------------------------------------------------------------------- start

_START_CUE = re.compile(
    r"(?<![\w-])(?:start(?:s|ing)?(?:\s+date)?|commenc(?:es?|ing)|begin(?:s|ning)?|joining(?:\s+date)?|intakes?|cohorts?)\b(?![\s-]?ups?\b)",
    _I,
)
_WHEN_TOKEN = re.compile(rf"\b({_MONTH}|{_SEASON})\b\.?", _I)
_YEAR_AFTER = re.compile(r"\s*(?:\d{1,2}(?:st|nd|rd|th)?\s*,?)?\s*,?\s*(20\d\d)\b")
_SEASON_YEAR = re.compile(rf"\b({_SEASON}\s+20\d\d|{_MONTH}\.?\s+20\d\d|20\d\d\s+{_SEASON})\b", _I)
_IMMEDIATE = re.compile(r"\b(?:immediate(?:ly)?\s+(?:start|joiner|joining|available|availability)|start\s+(?:immediately|asap)|available\s+to\s+(?:start|join)\s+immediately|immediate\s+joiners?)\b", _I)
_START_NOT = re.compile(r"\bgraduat|\bfounded|\bestablished|\bsince\b|\bdeadline|\bapply\s+by|\bclos(?:e|ing)", _I)
_SEASONS = ("summer", "winter", "spring", "fall", "autumn")
_MONTH_NAME = {"jan": "January", "feb": "February", "mar": "March", "apr": "April", "may": "May", "jun": "June", "jul": "July", "aug": "August", "sep": "September", "oct": "October", "nov": "November", "dec": "December"}


def _when_word(token: str) -> str:
    t = token.lower().rstrip(".")
    return t.capitalize() if t in _SEASONS else _MONTH_NAME.get(t[:3], t.capitalize())


def _when(window: str) -> tuple[str, int] | None:
    """Read the time out of the words after a start cue: "on 1st March or 1st September 2027",
    "an internship between January and December 2027", "mid-June 2027", "in summer 2027"."""
    tokens = list(_WHEN_TOKEN.finditer(window))
    if not tokens or tokens[0].start() > 34:
        return None
    first = tokens[0]
    words = [_when_word(first.group(1))]
    end = first.end()
    joiner = ""
    if len(tokens) > 1 and tokens[1].start() - first.end() <= 16:
        between = window[first.end() : tokens[1].start()].lower()
        lead = window[: first.start()].lower()
        if "between" in lead or re.search(r"\bto\b|\bthrough\b|\buntil\b|–|\s-\s", between):
            joiner = "to"
        elif re.search(r"\bor\b|/", between):
            joiner = "or"
        elif re.search(r"\band\b|&|,", between):
            joiner = "and"
        if joiner:
            words.append(_when_word(tokens[1].group(1)))
            end = tokens[1].end()
    year = _YEAR_AFTER.match(window[end:])
    text = f" {joiner} ".join(words)
    if year:
        return f"{text} {year.group(1)}", end + year.end()
    return text, end


def start(title: str, sents: list[str]) -> Fact | None:
    m = _SEASON_YEAR.search(title)
    if m:
        label = " ".join(p if p.isdigit() else _when_word(p) for p in m.group(1).split())
        return _fact("when", label, title, "title", m.group(1))
    for s in sents:
        m = _IMMEDIATE.search(s)
        if m:
            return _fact("immediate", "Immediate start", s, mark=m.group(0))
    for s in sents:
        for cue in _START_CUE.finditer(s):
            if _START_NOT.search(s[max(0, cue.start() - 40) : cue.end() + 14]):
                continue
            found = _when(s[cue.end() : cue.end() + 90])
            if found:
                return _fact("when", found[0], s, mark=s[cue.start() : cue.end() + found[1]])
    return None


# ---------------------------------------------------------------------- stage

_STAGES: list[tuple[str, str, re.Pattern[str]]] = [
    ("penultimate", "Penultimate-year students", re.compile(r"\bpenultimate[\s-]+year\b|\bsecond[\s-]+to[\s-]+last\s+year\b|\bthird[\s-]year\s+(?:student|undergraduate)", _I)),
    ("final", "Final-year students", re.compile(r"\bfinal[\s-]+(?:year|semester|term)\b|\blast\s+(?:year|semester)\s+of\s+(?:study|studies|university|a|an|the|your)\b|\bgraduating\s+(?:in|by|between)\b", _I)),
    ("enrolled", "Current students", re.compile(r"\bcurrently\s+(?:enrolled|pursuing|studying|completing)\b|\benrolled\s+in\b|\bpursuing\s+a\b|\b(?:university|college)\s+students?\b|\bundergraduate\s+students?\b|\bstudents?\s+(?:who|in\s+their|from)\b", _I)),
    ("graduate", "Recent graduates", re.compile(r"\b(?:recent|fresh|new)(?:ly)?\s+grad(?:uate)?s?\b|\brecently\s+(?:graduated|completed)\b|\bgraduated\s+(?:within|in\s+the\s+last)\b|\bcompleted\s+(?:a|your)\s+(?:bachelor|degree)"
        r"|\b(?:completed|received|obtained|earned)\b[^.\n]{0,60}\bdegree\b[^.\n]{0,20}\b(?:within|in)\s+the\s+(?:last|past)\b", _I)),
]
_LEVELS: list[tuple[str, re.Pattern[str]]] = [
    ("Bachelor's", re.compile(r"\bbachelor(?:'|’)?s?\b|\bundergraduate\b|\bb\.?(?:sc|tech|eng|e|a|com|ba)\b\.?|\bbs\b", _I)),
    ("Master's", re.compile(r"\bmaster(?:'|’)?s?\b|\bpostgraduate\b|\bm\.?(?:sc|tech|eng|ba)\b\.?|\bmba\b|\bms\b", _I)),
    ("PhD", re.compile(r"\bph\.?\s?d\b|\bdoctora(?:l|te)\b", _I)),
]


def stage(sents: list[str]) -> Fact | None:
    for value, label, pattern in _STAGES:
        for s in sents:
            m = pattern.search(s)
            if m:
                levels = [name for name, p in _LEVELS if p.search(s)]
                return _fact(value, label + (f" ({', '.join(levels)})" if levels else ""), s, mark=m.group(0))
    for s in sents:
        if re.search(r"\bdegree\b|\bstudents?\b|\bqualification", s, _I):
            found = [(name, p.search(s)) for name, p in _LEVELS]
            levels = [name for name, m in found if m]
            if levels:
                return _fact("degree", " or ".join(levels) + " degree", s, mark=next(m.group(0) for _, m in found if m))
    return None


# ----------------------------------------------------------------------- mode

_MODES = [
    ("hybrid", "Hybrid", re.compile(r"\bhybrid\b", _I)),
    ("remote", "Remote", re.compile(r"\b(?:fully|100%)\s+remote\b|\bremote[\s-](?:first|only|role|position|internship|work\b)|\bwork\s+from\s+home\b|\bthis\s+(?:role|position)\s+is\s+remote\b", _I)),
    # "On site" appears in many sentences that are not about where the role is done ("contractors working on site"),
    # so it only counts when the sentence is about the role, the work pattern, or reporting to the office.
    (
        "onsite",
        "On site",
        re.compile(
            r"\b(?:role|position|internship|job|program(?:me)?|intern)\b[^.\n]{0,40}\b(?:on[\s-]?site|in[\s-]office|in[\s-]person|office[\s-]based)\b"
            r"|\b(?:on[\s-]?site|in[\s-]person|office[\s-]based)\s+(?:role|position|internship|only|presence|work\s+model|in\s+(?:our|the))\b"
            r"|\breport\s+to\s+(?:work|the\s+office)\b[^.\n]{0,20}\b(?:on[\s-]?site|daily|every\s+day)"
            r"|\b(?:five|5)\s+days\s+(?:a|per)\s+week\s+(?:in|at|from)\s+(?:the|our)\s+office\b"
            r"|^(?:work\s+(?:model|arrangement|mode|type|pattern)|workplace(?:\s+type)?|location\s+type)\s*[:\-]?\s*(?:on[\s-]?site|in[\s-]office|office)\b",
            _I,
        ),
    ),
]


def mode(feed: str | None, sents: list[str]) -> Fact | None:
    if feed:
        f = feed.lower().replace("_", "").replace("-", "").replace(" ", "")
        for value, label, _ in _MODES:
            if value in f:
                return _fact(value, label, f'The employer files it as "{feed}".', "feed")
    for value, label, pattern in _MODES:
        for s in sents:
            m = pattern.search(s)
            if m:
                return _fact(value, label, s, mark=m.group(0))
    return None


# ------------------------------------------------------------------- deadline

_DATE = rf"(\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\.?(?:,?\s+20\d\d)?|{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+20\d\d)?|\d{{1,2}}[/.-]\d{{1,2}}[/.-]20\d\d|20\d\d-\d\d-\d\d)"
_DEADLINE = re.compile(
    rf"\b(?:deadline|apply\s+(?:by|before)|applications?\s+(?:close[sd]?|due|deadline|must\s+be\s+(?:received|submitted))|closing\s+date|last\s+date|submit\s+(?:by|before))\b[^.\n]{{0,50}}?{_DATE}",
    _I,
)


def deadline(sents: list[str]) -> Fact | None:
    for s in sents:
        m = _DEADLINE.search(s)
        if m:
            return _fact("date", re.sub(r"\s+", " ", m.group(1)).strip(), s, mark=m.group(0))
    return None


# --------------------------------------------------------------------- fields

_FIELDS: list[tuple[str, re.Pattern[str]]] = [
    ("AI and machine learning", re.compile(r"\b(?:ai|a\.i\.|ml|machine\s+learning|deep\s+learning|artificial\s+intelligence|llms?|nlp|computer\s+vision|genai|generative|data\s+scien(?:ce|tist)|research\s+scientist|applied\s+scientist)\b", _I)),
    ("Data and analytics", re.compile(r"\b(?:data\s+(?:analy|engineer|platform|governance|management)|analytics|business\s+intelligence|\bbi\b|insights?|statistic|quantitative|quant\b|reporting\s+analyst)", _I)),
    ("Software engineering", re.compile(r"\b(?:software|developer|engineer(?:ing)?\s+intern|full[\s-]?stack|front[\s-]?end|back[\s-]?end|mobile|ios|android|devops|sre|cloud|platform\s+engineer|web\s+develop|qa\b|quality\s+assurance|test\s+engineer|sde|programmer|technical\s+program)", _I)),
    ("IT, cloud and security", re.compile(r"\b(?:cyber|security\s+(?:analyst|engineer|operations)|infosec|information\s+security|it\s+support|help\s?desk|network|system\s+admin|infrastructure|data\s+cent(?:er|re))", _I)),
    ("Product and design", re.compile(r"\b(?:product\s+(?:manage|design|owner|operations|analyst)|ux|ui\b|user\s+experience|designer|graphic|creative|visual|animator|motion|content\s+design)", _I)),
    ("Finance and accounting", re.compile(r"\b(?:financ|account(?:ing|ant)|audit|tax\b|treasury|investment|banking|equity|credit|risk|actuar|fp&a|wealth|trading|trader|valuation|m&a)", _I)),
    ("Marketing and communications", re.compile(r"\b(?:marketing|brand|social\s+media|content|communications?|public\s+relations|\bpr\b|seo|growth|campaign|copywrit|editorial|journalis)", _I)),
    ("Sales and business development", re.compile(r"\b(?:sales|business\s+development|account\s+(?:manage|executive)|partnerships?|commercial|merchant|customer\s+success|client\s+(?:service|relations))", _I)),
    ("Operations and supply chain", re.compile(r"\b(?:operations?|supply\s+chain|logistics|procurement|warehouse|fulfil+ment|program\s+manage|project\s+(?:manage|coordinat)|facilities|planning)", _I)),
    ("Engineering", re.compile(r"\b(?:mechanical|electrical|civil|chemical|process\s+engineer|structural|hvac|mep\b|manufactur|aerospace|robotics|hardware|electronics|petroleum|energy|sustainab|environment|architect(?:ure)?\b|construction|site\s+engineer)", _I)),
    ("People and HR", re.compile(r"\b(?:human\s+resources|\bhr\b|people\s+(?:operations|team|partner)|talent|recruit|learning\s+(?:and|&)\s+development)", _I)),
    ("Legal and compliance", re.compile(r"\b(?:legal|counsel|paralegal|compliance|regulatory|governance|policy)\b", _I)),
    ("Consulting and strategy", re.compile(r"\b(?:consult|strategy|strategic|advisory|business\s+analyst|management\s+trainee|transformation)", _I)),
    ("Hospitality and retail", re.compile(r"\b(?:hospitality|hotel|housekeeping|front\s+office|guest|culinary|kitchen|food\s+(?:and|&)\s+beverage|f&b|retail|store|merchandis|restaurant|chef)", _I)),
    ("Science and health", re.compile(r"\b(?:laborator|biolog|chemist|pharma|clinical|medical|health|nurs|research\s+(?:assistant|intern|fellow))", _I)),
]


def fields(title: str, department: str | None) -> list[str]:
    """Up to two fields, from the title first and the department second."""
    found: list[str] = []
    for source in (title, department or ""):
        for name, pattern in _FIELDS:
            if name not in found and pattern.search(source):
                found.append(name)
        if found:
            break
    return found[:2] or ["Other"]


# ----------------------------------------------------------------------- read


def read(title: str, text: str, *, workplace: str | None = None) -> dict[str, Fact]:
    sents = sentences(text)
    found = {
        "eligibility": eligibility(title, sents),
        "pay": pay(sents),
        "duration": duration(title, sents),
        "start": start(title, sents),
        "stage": stage(sents),
        "mode": mode(workplace, sents),
        "deadline": deadline(sents),
    }
    return {k: v for k, v in found.items() if v is not None}
