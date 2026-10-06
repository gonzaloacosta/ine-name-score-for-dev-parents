"""Spanish phonetics helpers: syllable nuclei, stress position and a homophone key."""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

STRONG_VOWELS = set("aeoáéó")
ACCENTED_WEAK_VOWELS = set("íú")
WEAK_VOWELS = set("iuü") | ACCENTED_WEAK_VOWELS
VOWELS = STRONG_VOWELS | WEAK_VOWELS
ACCENTED_VOWELS = set("áéíóú")


class Stress(Enum):
    AGUDA = "aguda"  # stress on the last syllable
    LLANA = "llana"  # stress on the penultimate syllable
    ESDRUJULA = "esdrújula"  # stress on the antepenultimate (or earlier)


@dataclass(frozen=True)
class Syllabification:
    count: int
    stress: Stress
    ends_in_vowel: bool


def _forms_hiatus(prev: str, curr: str) -> bool:
    both_strong = prev in STRONG_VOWELS and curr in STRONG_VOWELS
    return both_strong or prev in ACCENTED_WEAK_VOWELS or curr in ACCENTED_WEAK_VOWELS


def _split_vowel_group(group: str) -> list[str]:
    """Split a run of vowels into nuclei (diphthongs stay together, hiatus splits)."""
    nuclei = [group[0]]
    for i in range(1, len(group)):
        prev, curr = group[i - 1], group[i]
        nxt = group[i + 1] if i + 1 < len(group) else ""
        # An unstressed weak vowel between two strong ones behaves like /j/ and
        # opens the next syllable: Na-ia, A-la-ia.
        consonantal_weak = curr in WEAK_VOWELS and prev in STRONG_VOWELS and nxt in STRONG_VOWELS
        if consonantal_weak or _forms_hiatus(prev, curr):
            nuclei.append(curr)
        else:
            nuclei[-1] += curr
    return nuclei


def _normalise_for_nuclei(word: str) -> str:
    w = word.lower()
    w = re.sub(r"([qg])u([eéií])", r"\1\2", w)  # silent u in que/qui/gue/gui
    w = w.replace("ch", "c").replace("h", "")  # h is silent and transparent
    w = re.sub(r"y(?![aeiouáéíóú])", "i", w)  # y acts as a vowel when not before one
    return w


def syllabify(word: str) -> Syllabification:
    """Count syllables and locate stress using standard Spanish orthography rules."""
    w = _normalise_for_nuclei(word)
    nuclei: list[str] = []
    for group in re.findall(r"[aeiouáéíóúü]+", w):
        nuclei.extend(_split_vowel_group(group))
    if not nuclei:
        raise ValueError(f"no vowels in {word!r}")

    accented = [i for i, n in enumerate(nuclei) if set(n) & ACCENTED_VOWELS]
    if accented:
        stressed = accented[-1]
    elif len(nuclei) > 1 and word.lower()[-1] in VOWELS | {"n", "s"}:
        stressed = len(nuclei) - 2
    else:
        stressed = len(nuclei) - 1

    from_end = len(nuclei) - 1 - stressed
    stress = {0: Stress.AGUDA, 1: Stress.LLANA}.get(from_end, Stress.ESDRUJULA)
    return Syllabification(
        count=len(nuclei),
        stress=stress,
        ends_in_vowel=word.lower()[-1] in VOWELS,
    )


def strip_accents(text: str) -> str:
    text = text.replace("ñ", "\0").replace("Ñ", "\1")
    stripped = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return stripped.replace("\0", "ñ").replace("\1", "Ñ")


# Ordered rewrite rules; digits are placeholders that later rules must not touch.
_KEY_RULES: list[tuple[str, str]] = [
    (r"PH", "F"),
    (r"TH", "T"),
    (r"SH", "S"),
    (r"CH(?=[LR])", "K"),  # Chloe, Christina
    (r"CH", "1"),
    (r"H", ""),
    (r"QU(?=[EI])", "K"),
    (r"GU(?=[EI])", "2"),  # hard g: Guiomar
    (r"C(?=[EI])", "S"),
    (r"[CQ]", "K"),
    (r"Z", "S"),  # seseo / ceceo
    (r"G(?=[EI])", "J"),
    (r"V", "B"),
    (r"W", "U"),
    (r"LL", "Y"),
    (r"Y(?![AEIOU])", "I"),
    (r"X", "KS"),
    (r"(.)\1+", r"\1"),  # Emma -> Ema
    (r"1", "CH"),
    (r"2", "G"),
]


def phonetic_key(name: str) -> str:
    """Collapse spellings that sound the same in Spanish (b/v, silent h, y/i, seseo...)."""
    key = re.sub(r"[^A-ZÑ]", "", strip_accents(name).upper())
    for pattern, replacement in _KEY_RULES:
        key = re.sub(pattern, replacement, key)
    return key
