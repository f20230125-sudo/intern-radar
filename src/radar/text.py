"""Turning a posting's HTML into sentences a rule can read and a person can check."""

from __future__ import annotations

import html
import re

_BLOCK = re.compile(r"<\s*(?:/?(?:p|div|li|ul|ol|h[1-6]|tr|table|section|article|blockquote)|br\s*/?)\b[^>]*>", re.I)
_DROP = re.compile(r"<\s*(script|style)\b.*?<\s*/\s*\1\s*>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t ​‌‍﻿]+")
# A full stop ends a sentence when what follows starts a new one. "e.g." and "3.5" stay whole.
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")
_BULLET = re.compile(r"^\s*(?:[-*•●◦▪‣⁃·]|\d{1,2}[.)])\s+")


def to_text(markup: str | None) -> str:
    """HTML (possibly escaped once, as Greenhouse sends it) to plain text with one block per line."""
    if not markup:
        return ""
    s = markup
    if "&lt;" in s and "<" not in s:
        s = html.unescape(s)
    s = _DROP.sub(" ", s)
    s = _BLOCK.sub("\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    lines = [_WS.sub(" ", line).strip() for line in s.splitlines()]
    return "\n".join(line for line in lines if line)


def sentences(text: str) -> list[str]:
    """Split text into sentences. A line break always ends one, so list items stay separate."""
    out: list[str] = []
    for line in text.splitlines():
        line = _BULLET.sub("", line.strip())
        if not line:
            continue
        for part in _SPLIT.split(line):
            part = part.strip()
            if part:
                out.append(part)
    return out


def clip(s: str, limit: int = 240) -> str:
    """Shorten for display without cutting a word in half."""
    s = _WS.sub(" ", s).strip()
    if len(s) <= limit:
        return s
    cut = s[: limit + 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > limit * 0.6 else cut[:limit]).rstrip(" ,;:-") + "…"


def slugify(s: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:limit].strip("-") or "role"
