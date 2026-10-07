"""Scoring criteria. Every criterion returns a float in [0, 1]; higher is better."""

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from name_selector.handles import BadHandle, find_bad_handles
from name_selector.models import Candidate, ScoredName
from name_selector.phonetics import Stress, Syllabification, phonetic_key, strip_accents, syllabify

DEFAULT_WEIGHTS: dict[str, float] = {
    "anonymity": 0.25,  # many namesakes -> hard to single out via OSINT
    "ascii": 0.20,  # survives every IT system without mangling
    "song": 0.20,  # fits "Cumpleaños feliz"
    "spelling": 0.15,  # only one way to write what you hear
    "current": 0.10,  # normal among babies born today
    "systems": 0.10,  # no reserved words, sane length, no spaces/hyphens
}

# Values that collide with "missing"/test sentinels in software.
RESERVED_WORDS = {
    "NULL", "NONE", "NIL", "NAN", "NA", "TRUE", "FALSE", "TEST", "ADMIN",
    "ROOT", "UNDEFINED", "VOID", "USER", "UNKNOWN", "NAME", "EMPTY",
}  # fmt: skip

# Graphemes that are not native Spanish and invite misspellings.
FOREIGN_GRAPHEMES = re.compile(r"K|W|PH|TH|SH|CH(?=[LR])|Y(?![AEIOU])|(?!LL|RR)([A-Z])\1")

SYLLABLE_FIT = {1: 0.4, 2: 1.0, 3: 1.0, 4: 0.6}
STRESS_FIT = {Stress.LLANA: 1.0, Stress.AGUDA: 0.6, Stress.ESDRUJULA: 0.4}


def ascii_score(written: str) -> float:
    return 1.0 if written.isascii() and written.isalpha() else 0.0


def systems_score(written: str) -> float:
    if written.upper() in RESERVED_WORDS:
        return 0.0
    score = 1.0
    if not written.isalpha():  # spaces, hyphens, apostrophes break form validation
        score *= 0.5
    if len(written) < 3:  # rejected by naive "min length" validators
        score *= 0.6
    if len(written) > 12:  # truncated on cards, tickets and badges
        score *= 0.7
    return score


def song_score(syllables: Syllabification) -> float:
    """The name lands on the climax of the 3rd line: strong beat on its penultimate
    syllable, then a held note. Ideal: 2-3 syllables, llana, ending in a vowel."""
    fit = SYLLABLE_FIT.get(syllables.count, 0.3)
    fit *= STRESS_FIT[syllables.stress]
    if not syllables.ends_in_vowel:
        fit *= 0.85
    return fit


def spelling_score(
    key: str,
    census: Mapping[str, int],
    sound_totals: Mapping[str, int] | None = None,
) -> float:
    """Share of people with this *sound* who also use this *spelling*.

    Pass precomputed ``sound_totals`` when scoring many names: building them is O(census).
    """
    sound_totals = sound_totals if sound_totals is not None else _sound_totals(census)
    same_sound = sound_totals.get(phonetic_key(key), 0)
    share = census.get(key, 0) / same_sound if same_sound else 1.0
    return share * (0.85 if FOREIGN_GRAPHEMES.search(key) else 1.0)


def log_scale(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0
    value = min(max(value, lo), hi)
    return (math.log10(value) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))


def parse_weights(spec: str | None) -> dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)
    for item in filter(None, (spec or "").split(",")):
        name, _, raw = item.partition("=")
        name = name.strip()
        if name not in weights:
            raise ValueError(f"unknown criterion {name!r}; valid: {', '.join(weights)}")
        value = float(raw)
        if value < 0:
            raise ValueError(f"weight for {name!r} must be >= 0")
        weights[name] = value
    if not any(weights.values()):
        raise ValueError("at least one weight must be > 0")
    return weights


def _sound_totals(census: Mapping[str, int]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for name, freq in census.items():
        totals[phonetic_key(name)] += freq
    return totals


def excluded_by_handles(
    candidates: Iterable[Candidate],
    surnames: list[str],
) -> list[tuple[Candidate, list[BadHandle]]]:
    """Candidates whose future email/username with these surnames spells a bad word."""
    hits = ((c, find_bad_handles(c.written, surnames)) for c in candidates)
    return [(c, bad) for c, bad in hits if bad]


@dataclass(frozen=True)
class _Ranges:
    """Min/max of census frequency and births over a pool: the scale for log_scale()."""

    freq: tuple[float, float]
    births: tuple[float, float]

    @classmethod
    def of(cls, pool: list[Candidate]) -> "_Ranges":
        freqs = [max(c.census_frequency, 1) for c in pool]
        births = [max(c.mean_births, 1) for c in pool]
        return cls((min(freqs), max(freqs)), (min(births), max(births)))


def _score(
    c: Candidate,
    census: Mapping[str, int],
    sound_totals: Mapping[str, int],
    ranges: _Ranges,
    weights: Mapping[str, float],
) -> ScoredName:
    syllables = syllabify(c.pronunciation)
    criteria = {
        # Names outside the pool can fall below its minimum: score 0, never negative.
        "anonymity": log_scale(max(c.census_frequency, 1), *ranges.freq)
        if c.census_frequency
        else 0.0,
        "ascii": ascii_score(c.written),
        "song": song_score(syllables),
        "spelling": spelling_score(c.key, census, sound_totals),
        "current": log_scale(max(c.mean_births, 1), *ranges.births) if c.births else 0.0,
        "systems": systems_score(c.written),
    }
    total = sum(weights[k] * v for k, v in criteria.items()) / sum(weights.values())
    return ScoredName(c, syllables, criteria, total)


def rank(
    candidates: Iterable[Candidate],
    census: Mapping[str, int],
    weights: Mapping[str, float],
    ascii_only: bool = False,
    surnames: list[str] | None = None,
) -> list[ScoredName]:
    candidates = list(candidates)
    excluded = {c.key for c, _ in excluded_by_handles(candidates, surnames)} if surnames else set()
    pool = [
        c
        for c in candidates
        if c.key not in excluded and (not ascii_only or ascii_score(c.written))
    ]
    if not pool:
        return []

    sound_totals = _sound_totals(census)
    ranges = _Ranges.of(pool)
    scored = [_score(c, census, sound_totals, ranges, weights) for c in pool]
    return sorted(scored, key=lambda s: (-s.total, s.candidate.key))


@dataclass(frozen=True)
class Explanation:
    scored: ScoredName
    position: int | None  # place in the default ranking; None when outside the top-100 pool
    pool_size: int
    in_census: bool


def name_key(name: str) -> str:
    """INE form of a typed name: uppercase, no accents, single spaces."""
    return " ".join(strip_accents(name).upper().split())


def explain(
    name: str,
    candidates: Iterable[Candidate],
    census: Mapping[str, int],
    weights: Mapping[str, float],
    ages: Mapping[str, float] | None = None,
) -> Explanation:
    """Score any name. Pool names reuse their ranking entry; others use the typed spelling
    and are measured on the same scale as the pool."""
    candidates = list(candidates)
    key = name_key(name)
    ranked = rank(candidates, census, weights)
    for position, scored in enumerate(ranked, start=1):
        if scored.candidate.key == key:
            return Explanation(scored, position, len(ranked), key in census)

    written = " ".join(word[:1].upper() + word[1:].lower() for word in name.split())
    candidate = Candidate(
        key=key,
        written=written,
        pronunciation=written,
        census_frequency=census.get(key, 0),
        census_mean_age=(ages or {}).get(key),
        births={},
    )
    scored = _score(candidate, census, _sound_totals(census), _Ranges.of(candidates), weights)
    return Explanation(scored, None, len(ranked), key in census)
