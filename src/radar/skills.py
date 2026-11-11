"""The skills a posting names, from a fixed list.

Used for one thing: letting a reader paste their CV and see which roles name the same skills. The list is
deliberately plain (tools, languages, methods, subjects). A skill counts only when the posting uses the word;
nothing is inferred from the job title's field.
"""

from __future__ import annotations

import re

_I = re.I

# name -> pattern. Order is the order shown. Patterns use word boundaries so "R" does not match "our".
_SKILLS: list[tuple[str, str]] = [
    ("Python", r"\bpython\b"),
    ("SQL", r"\bsql\b|\bpostgres(?:ql)?\b|\bmysql\b"),
    ("Excel", r"\bexcel\b|\bspreadsheets?\b|\bgoogle\s+sheets\b"),
    ("Power BI", r"\bpower\s?bi\b"),
    ("Tableau", r"\btableau\b"),
    ("Looker", r"\blooker\b"),
    ("R", r"(?<![\w&/.-])R(?![\w&/.-])(?=\s*(?:,|\)|/|or\b|and\b|programming|studio))|\brstudio\b"),
    ("Java", r"\bjava\b(?!\s*script)"),
    ("JavaScript", r"\bjavascript\b|\bnode\.?js\b"),
    ("TypeScript", r"\btypescript\b"),
    ("React", r"\bReact(?:\.?js|\s+Native)?\b|\bNext\.?js\b|\breactjs\b"),
    ("C++", r"\bc\+\+"),
    ("C#", r"\bc#|\b\.net\b"),
    ("Go", r"\bgolang\b|\bgo\s+(?:lang|programming)\b"),
    ("Rust", r"\bRust\b(?![\s-]*(?:proof|prevent|resist))"),
    ("Swift or Kotlin", r"\bswift\b|\bkotlin\b|\bios\s+develop|\bandroid\s+develop"),
    ("HTML and CSS", r"\bhtml\b|\bcss\b"),
    ("Git", r"\bgit(?:hub|lab)?\b"),
    ("Linux", r"\blinux\b|\bunix\b|\bbash\b"),
    ("Docker and Kubernetes", r"\bdocker\b|\bkubernetes\b|\bk8s\b|\bcontainers?\b"),
    ("Cloud (AWS, Azure, GCP)", r"\baws\b|\bazure\b|\bgcp\b|\bgoogle\s+cloud\b|\bcloud\s+(?:computing|platform|infrastructure|services)\b"),
    ("APIs", r"\bapis?\b|\brest(?:ful)?\b|\bgraphql\b"),
    ("Machine learning", r"\bmachine\s+learning\b|\bml\b|\bdeep\s+learning\b|\bneural\s+networks?\b"),
    ("LLMs and NLP", r"\bllms?\b|\blarge\s+language\s+models?\b|\bnlp\b|\bnatural\s+language\b|\bgenerative\s+ai\b|\bgenai\b|\bprompt"),
    ("Computer vision", r"\bcomputer\s+vision\b|\bimage\s+(?:processing|recognition)\b"),
    ("PyTorch or TensorFlow", r"\bpytorch\b|\btensorflow\b|\bkeras\b|\bscikit"),
    ("Data analysis", r"\bdata\s+analy(?:sis|tics|st)\b|\banaly[sz]e\s+data\b|\bdata[\s-]driven\b"),
    ("Statistics", r"\bstatistic(?:s|al)\b|\bregression\b|\bhypothesis\s+test|\ba/b\s+test"),
    ("Data engineering", r"\bdata\s+(?:pipelines?|engineering|warehous)|\betl\b|\bspark\b|\bairflow\b|\bdbt\b"),
    ("Dashboards and reporting", r"\bdashboards?\b|\bdata\s+visuali[sz]ation\b|\b(?:management|financial|regular|weekly|monthly)\s+report(?:s|ing)\b|\breporting\s+(?:tools?|skills)\b"),
    ("Financial modelling", r"\bfinancial\s+model|\bvaluation\b|\bdcf\b|\bforecast(?:ing|s)?\b"),
    ("Accounting", r"\baccounting\b|\bifrs\b|\bgaap\b|\bbookkeeping\b|\breconciliation"),
    ("Audit and risk", r"\baudit(?:ing|s)?\b|\brisk\s+(?:management|assessment|analysis)\b|\binternal\s+controls?\b"),
    ("Compliance and AML", r"\bcompliance\b|\baml\b|\bkyc\b|\bsanctions\b|\bregulatory\b"),
    ("Trading and markets", r"\btrading\b|\bfinancial\s+markets\b|\bcapital\s+markets\b|\bequit(?:y|ies)\b|\bderivatives\b"),
    ("Crypto and blockchain", r"\bcrypto(?:currency|currencies)?\b|\bblockchain\b|\bweb3\b|\bdigital\s+assets?\b"),
    ("Sales", r"\bsales\b|\bbusiness\s+development\b|\blead\s+generation\b|\bprospecting\b"),
    ("CRM", r"\bcrm\b|\bsalesforce\b|\bhubspot\b"),
    ("Marketing", r"\bmarketing\b|\bcampaigns?\b|\bbrand(?:ing)?\b"),
    ("Social media and content", r"\bsocial\s+media\b|\bcontent\s+(?:creation|writing|marketing)\b|\bcopywriting\b"),
    ("SEO and paid media", r"\bseo\b|\bsem\b|\bpaid\s+media\b|\bgoogle\s+ads\b|\bperformance\s+marketing\b"),
    ("Public relations", r"\bpublic\s+relations\b|\bpress\s+releases?\b|\bmedia\s+relations\b"),
    ("Design tools", r"\bfigma\b|\badobe\b|\bphotoshop\b|\billustrator\b|\bafter\s+effects\b|\bcanva\b"),
    ("UX research and design", r"\bux\b|\buser\s+(?:research|experience)\b|\bwirefram|\bprototyp"),
    ("Animation and video", r"\banimation\b|\bmotion\s+graphics\b|\bvideo\s+editing\b"),
    ("Product management", r"\bproduct\s+(?:management|roadmap|strategy|requirements)\b|\buser\s+stories\b"),
    ("Project management", r"\bproject\s+management\b|\bpmp\b|\bstakeholder\s+management\b|\bproject\s+plans?\b"),
    ("Agile", r"\bagile\b|\bscrum\b|\bjira\b|\bkanban\b"),
    ("Operations and logistics", r"\blogistics\b|\bsupply\s+chain\b|(?<!data\s)(?<!sql\s)\bwarehouse\b(?!\s+in\s+duckdb)|\binventory\b|\bfulfil+ment\b"),
    ("Process improvement", r"\bprocess\s+improvement\b|\blean\b|\bsix\s+sigma\b|\bkaizen\b|\bcontinuous\s+improvement\b"),
    ("Procurement", r"\bprocurement\b|\bsourcing\b|\bvendor\s+management\b"),
    ("Customer service", r"\bcustomer\s+(?:service|support|success|experience)\b"),
    # "Recruitment" and "onboarding" appear in nearly every posting's small print, so they do not count.
    ("HR and recruiting", r"\bhuman\s+resources\s+(?:management|operations|practices|processes|degree)\b|\bhr\s+(?:operations|processes|policies|administration|generalist)\b|\bsourcing\s+candidates\b|\bscreening\s+(?:cvs|resumes|candidates)\b|\bpayroll\b"),
    ("Research and writing", r"\bresearch\s+(?:skills|reports?|papers?)\b|\breport\s+writing\b|\bliterature\s+review"),
    ("Presentations", r"\bpowerpoint\b|\bpresentations?\b|\bpitch\s+decks?\b"),
    ("Mechanical engineering", r"\bmechanical\s+engineering\b|\bhvac\b|\bcad\b|\bsolidworks\b|\bautocad\b"),
    ("Electrical engineering", r"\belectrical\s+engineering\b|\bpower\s+systems\b|\bplc\b|\bcircuit"),
    ("Civil and construction", r"\bcivil\s+engineering\b|\bconstruction\b|\bstructural\b|\bquantity\s+survey"),
    ("Data centres", r"\bdata\s+cent(?:er|re)s?\b"),
    ("Networking and security", r"\bnetwork(?:ing|s)?\s+(?:security|engineering|protocols)\b|\bcyber\s?security\b|\binformation\s+security\s+(?:analyst|engineer|principles|practices|standards|degree)\b|\bfirewalls?\b"),
    ("Regulatory affairs and pharma", r"\bregulatory\s+affairs\b|\bpharma(?:cy|ceutical)\b|\bclinical\b|\bgmp\b"),
    ("Legal research", r"\blegal\s+(?:research|drafting)\b|\bcontracts?\s+(?:review|drafting)\b|\bparalegal\b"),
    ("Arabic", r"\barabic\b"),
    ("French", r"\bfrench\b"),
    ("Hindi or Urdu", r"\bhindi\b|\burdu\b"),
]
# These three are told from ordinary words by their capital letter, so they are matched with case.
_CASED = {"R", "React", "Rust"}
_COMPILED = [(name, re.compile(pattern, 0 if name in _CASED else _I)) for name, pattern in _SKILLS]
NAMES = [name for name, _ in _SKILLS]


def read(title: str, text: str, limit: int = 14) -> list[str]:
    """Skills named in the posting, in list order, at most `limit`."""
    hay = f"{title}\n{text}"
    return [name for name, pattern in _COMPILED if pattern.search(hay)][:limit]


def patterns() -> list[dict[str, str]]:
    """The same list as data, so the site can match a pasted CV with the identical rules."""
    return [{"name": name, "pattern": pattern, "flags": "" if name in _CASED else "i"} for name, pattern in _SKILLS]
