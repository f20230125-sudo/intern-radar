"""The shapes that move through a run: what a source returns, and what the site reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

System = Literal["greenhouse", "lever", "ashby", "workable", "workday", "amazon"]
Kind = Literal["internship", "graduate", "first_job"]


@dataclass(frozen=True)
class Board:
    """One employer's job board on one career system."""

    key: str  # stable id, e.g. "greenhouse:tamara"
    system: str
    slug: str
    name: str
    site: str | None = None  # Workday: the site name inside the tenant
    host: str | None = None  # Workday: e.g. "wd1"
    home: str | None = None  # the employer's careers page, for people


@dataclass
class RawPosting:
    """A posting as its source gave it, before any reading."""

    board: Board
    native_id: str
    title: str
    url: str
    locations: list[str]
    posted_at: datetime | None = None
    updated_at: datetime | None = None
    html: str | None = None  # description as HTML, when the list call already carries it
    text: str | None = None  # description as plain text
    department: str | None = None
    employment_type: str | None = None
    workplace: str | None = None
    detail_ref: str | None = None  # what the adapter needs to fetch the description later
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.board.key}:{self.native_id}"


class Fact(BaseModel):
    """One thing read from a posting, with the sentence it was read from."""

    model_config = ConfigDict(extra="forbid")

    value: str
    label: str
    evidence: str
    source: Literal["text", "title", "feed"] = "text"
    mark: str | None = None  # the words inside `evidence` that decided it


class Place(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emirate: str  # "Dubai", "Abu Dhabi", ... or "UAE" when the posting names only the country
    raw: str


class Role(BaseModel):
    """A student role as published in the snapshot."""

    model_config = ConfigDict(extra="forbid")

    id: str
    slug: str
    employer: str
    board: str
    system: str
    title: str
    url: str
    places: list[Place]
    elsewhere: int  # how many non-UAE locations the same posting also lists
    kind: Kind
    kind_reason: str
    fields: list[str]
    skills: list[str] = []
    facts: dict[str, Fact]
    department: str | None = None
    excerpt: str = ""
    posted_at: str | None = None  # the source's own date
    first_seen: str
    last_seen: str
    changed_at: str | None = None
    status: Literal["open", "closed"] = "open"
    closed_at: str | None = None


class BoardStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    system: str
    home: str | None = None
    ok: bool
    checked_at: str
    last_ok: str | None = None
    error: str | None = None
    postings: int = 0  # everything on the board
    uae: int = 0  # located in the UAE
    student: int = 0  # UAE and a student role


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    rules_version: int
    generated_at: str
    started_at: str
    roles: list[Role]
    boards: list[BoardStatus]
    not_covered: list[dict]
