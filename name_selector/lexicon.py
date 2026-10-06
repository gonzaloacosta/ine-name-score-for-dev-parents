"""Curated spelling data the INE files cannot give us.

INE publishes names upper-cased and without accents (``LUCIA``), so the real written
form (``Lucía``) and its pronunciation must come from here. Names absent from this
table are assumed to be written as plain title case (``JULIA`` -> ``Julia``).
"""

from typing import NamedTuple


class Spelling(NamedTuple):
    written: str
    pronunciation: str | None = None  # only when Spanish stress rules misread `written`


LEXICON: dict[str, Spelling] = {
    # Written with a tilde in standard Spanish.
    "AFRICA": Spelling("África"),
    "ANGELA": Spelling("Ángela"),
    "FATIMA": Spelling("Fátima"),
    "INES": Spelling("Inés"),
    "LIA": Spelling("Lía"),
    "LUCIA": Spelling("Lucía"),
    "MARIA": Spelling("María"),
    "ROCIO": Spelling("Rocío"),
    "SOFIA": Spelling("Sofía"),
    # Usually registered without a tilde, but not pronounced the way it is written.
    "MIA": Spelling("Mia", pronunciation="Mía"),
    "YASMIN": Spelling("Yasmin", pronunciation="Yasmín"),
    "CHLOE": Spelling("Chloe", pronunciation="Cloe"),
    "NOUR": Spelling("Nour", pronunciation="Nur"),
}


def spelling_for(key: str) -> Spelling:
    spelling = LEXICON.get(key) or Spelling(key.title())
    return Spelling(spelling.written, spelling.pronunciation or spelling.written)
