"""Load the processed INE CSVs into candidates for ranking."""

import csv
from collections import defaultdict
from pathlib import Path

from name_selector.ine import births_csv, census_csv
from name_selector.lexicon import spelling_for
from name_selector.models import Candidate, Sex

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def load(
    data_dir: Path = DEFAULT_DATA_DIR,
    sex: Sex = Sex.FEMALE,
) -> tuple[list[Candidate], dict[str, int]]:
    """Candidates are names in any year's top-100 births; census covers every name."""
    census: dict[str, int] = {}
    ages: dict[str, float] = {}
    with open(data_dir / census_csv(sex), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            census[row["name"]] = int(row["frequency"])
            ages[row["name"]] = float(row["mean_age"])

    births: dict[str, dict[int, int]] = defaultdict(dict)
    with open(data_dir / births_csv(sex), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            births[row["name"]][int(row["year"])] = int(row["births"])

    candidates = []
    for key, by_year in sorted(births.items()):
        spelling = spelling_for(key, sex)
        candidates.append(
            Candidate(
                key=key,
                written=spelling.written,
                pronunciation=spelling.pronunciation,
                census_frequency=census.get(key, 0),
                census_mean_age=ages.get(key),
                births=by_year,
            ),
        )
    return candidates, census
