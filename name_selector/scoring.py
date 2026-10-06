"""Scoring criteria. Every criterion returns a float in [0, 1]; higher is better."""

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping

from name_selector.models import Candidate, ScoredName
from name_selector.phonetics import Stress, Syllabification, phonetic_key, syllabify

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


def rank(
    candidates: Iterable[Candidate],
    census: Mapping[str, int],
    weights: Mapping[str, float],
    ascii_only: bool = False,
) -> list[ScoredName]:
    pool = [c for c in candidates if not ascii_only or ascii_score(c.written)]
    if not pool:
        return []

    sound_totals = _sound_totals(census)
    freqs = [max(c.census_frequency, 1) for c in pool]
    births = [max(c.mean_births, 1) for c in pool]
    total_weight = sum(weights.values())

    scored = []
    for c in pool:
        syllables = syllabify(c.pronunciation)
        criteria = {
            "anonymity": log_scale(max(c.census_frequency, 1), min(freqs), max(freqs)),
            "ascii": ascii_score(c.written),
            "song": song_score(syllables),
            "spelling": spelling_score(c.key, census, sound_totals),
            "current": log_scale(max(c.mean_births, 1), min(births), max(births)),
            "systems": systems_score(c.written),
        }
        total = sum(weights[k] * v for k, v in criteria.items()) / total_weight
        scored.append(ScoredName(c, syllables, criteria, total))

    return sorted(scored, key=lambda s: (-s.total, s.candidate.key))
