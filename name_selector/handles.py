"""Detect future email addresses / usernames that spell something unfortunate.

Example: Gonzalo + Ordo -> ``gordo@empresa.com`` (first initial + surname).
"""

import re
from dataclasses import dataclass
from enum import Enum
from functools import cache
from importlib.resources import files

from name_selector.phonetics import strip_accents


class Tier(Enum):
    OFFENSIVE = "offensive"  # matched anywhere in the handle
    NEGATIVE = "negative"  # matched only at the start or end of the handle


@dataclass(frozen=True)
class Handle:
    text: str
    pattern: str  # human-readable recipe, e.g. "n[0] + s1"
    name_span: tuple[int, int]  # [start, end) of the characters that come from the first name


@dataclass(frozen=True)
class BadHandle:
    handle: str
    pattern: str
    word: str
    tier: Tier


def slug(text: str) -> str:
    """What an email/username system keeps: lowercase a-z only."""
    return re.sub(r"[^a-z]", "", strip_accents(text).lower().replace("ñ", "n").replace("ç", "c"))


@cache
def load_words(tier: Tier) -> frozenset[str]:
    raw = files("name_selector.wordlists").joinpath(f"{tier.value}.txt").read_text("utf-8")
    lines = (line.strip() for line in raw.splitlines())
    return frozenset(line for line in lines if line and not line.startswith("#"))


def _join(*parts: tuple[str, bool]) -> tuple[str, tuple[int, int]]:
    """Concatenate (text, is_name) parts and return the text plus the name's span."""
    text, start, end = "", -1, -1
    for part, is_name in parts:
        if is_name:
            start, end = len(text), len(text) + len(part)
        text += part
    return text, (start, end)


def generate_handles(name: str, surnames: list[str]) -> list[Handle]:
    """Usual corporate / webmail patterns (separators dropped: ``ana.lopez`` reads ``analopez``)."""
    n = slug(name)
    s = [slug(x) for x in surnames if slug(x)]
    if not n or not s:
        return []
    s1 = s[0]
    recipes: dict[str, tuple[tuple[str, bool], ...]] = {
        "n + s1": ((n, True), (s1, False)),
        "n[0] + s1": ((n[0], True), (s1, False)),
        "n + s1[0]": ((n, True), (s1[0], False)),
        "s1 + n": ((s1, False), (n, True)),
        "s1 + n[0]": ((s1, False), (n[0], True)),
    }
    if len(s) > 1:
        s2 = s[1]
        recipes |= {
            "n + s1 + s2": ((n, True), (s1, False), (s2, False)),
            "n[0] + s1 + s2": ((n[0], True), (s1, False), (s2, False)),
            "n[0] + s1 + s2[0]": ((n[0], True), (s1, False), (s2[0], False)),
            "n + s2": ((n, True), (s2, False)),
            "initials": ((n[0], True), (s1[0], False), (s2[0], False)),
        }
    handles = {}
    for pattern, parts in recipes.items():
        text, span = _join(*parts)
        handles.setdefault(text, Handle(text, pattern, span))
    return list(handles.values())


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _created_by_combination(span: tuple[int, int], name: tuple[int, int]) -> bool:
    """The word straddles the name/surname join (g|ordo), or is exactly the name."""
    inside_name = name[0] <= span[0] and span[1] <= name[1]
    return span == name or (_overlaps(span, name) and not inside_name)


def _matches(handle: Handle, word: str, tier: Tier) -> bool:
    text = handle.text
    if tier is Tier.NEGATIVE:
        spans = []
        if text.startswith(word):
            spans.append((0, len(word)))
        if text.endswith(word):
            spans.append((len(text) - len(word), len(text)))
        # Short teasing words inside a longer name (Fátima -> "fat") are not read as such.
        return any(_created_by_combination(span, handle.name_span) for span in spans)
    spans = [(m.start(), m.start() + len(word)) for m in re.finditer(re.escape(word), text)]
    # A word sitting wholly inside the surname hits every name alike: not the name's fault.
    return any(_overlaps(span, handle.name_span) for span in spans)


def find_bad_handles(name: str, surnames: list[str]) -> list[BadHandle]:
    hits = []
    for handle in generate_handles(name, surnames):
        for tier in Tier:
            for word in sorted(load_words(tier)):
                if _matches(handle, word, tier):
                    hits.append(BadHandle(handle.text, handle.pattern, word, tier))
    return hits
