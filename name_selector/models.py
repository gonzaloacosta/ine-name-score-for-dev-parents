from dataclasses import dataclass, field

from name_selector.phonetics import Syllabification


@dataclass(frozen=True)
class Candidate:
    key: str  # INE form: uppercase, no accents
    written: str  # correct Spanish spelling (what goes on the birth certificate)
    pronunciation: str  # spelling that makes Spanish stress rules give the real stress
    census_frequency: int  # women in Spain with exactly this (simple) name
    census_mean_age: float | None
    births: dict[int, int] = field(default_factory=dict)  # year -> newborn girls

    @property
    def mean_births(self) -> float:
        return sum(self.births.values()) / len(self.births) if self.births else 0.0


@dataclass(frozen=True)
class ScoredName:
    candidate: Candidate
    syllables: Syllabification
    criteria: dict[str, float]
    total: float
