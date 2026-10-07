from pathlib import Path

import openpyxl
import pytest

from name_selector import dataset
from name_selector.ine import parse_births, parse_census
from name_selector.lexicon import LEXICONS, spelling_for
from name_selector.models import Sex


def write_census_fixture(path: Path) -> None:
    wb = openpyxl.Workbook()
    men = wb.active
    men.title = "Hombres"
    men.append(["Orden", "Nombre", "Frecuencia", "Edad Media (*)"])
    men.append([1, "JOSE ANTONIO", 400000, 55.0])
    men.append([2, "HUGO", 90000, 12.4])
    men.append([None, None, None, None])
    ws = wb.create_sheet("Mujeres")
    ws.append(["Frecuencias de nombres femeninos"])
    ws.append([None])
    ws.append(["Orden", "Nombre", "Frecuencia", "Edad Media (*)"])
    ws.append([1, "MARIA CARMEN", 618622, 62.6])
    ws.append([2, "MARIA", 543083, 48.3])
    ws.append([3, "JULIA", 120000, 30.1])
    ws.append([None, None, None, None])
    ws.append(["Fuente: INE"])
    wb.save(path)


def write_births_fixture(path: Path) -> None:
    wb = openpyxl.Workbook()
    wb.active.title = "Año 2024"
    ws = wb.create_sheet("TOTAL")
    ws.append(["Total Nacional"])
    ws.append([None])
    ws.append([None, "NIÑOS", None, None, "NIÑAS"])
    ws.append(["TOTAL", 163732, None, "TOTAL", 154273])
    ws.append(["MATEO", 3289, None, "SOFIA", 3325])
    ws.append(["HUGO", 2734, None, "JULIA", 2071])
    ws.append([None, None, None, None, None])
    wb.save(path)


def test_parse_census_keeps_simple_names_only(tmp_path):
    path = tmp_path / "census.xlsx"
    write_census_fixture(path)

    rows = parse_census(path)

    assert rows == [("MARIA", 543083, 48.3), ("JULIA", 120000, 30.1)]


def test_parse_births_reads_girls_column(tmp_path):
    path = tmp_path / "nomnac24.xlsx"
    write_births_fixture(path)

    assert parse_births(path) == [("SOFIA", 3325), ("JULIA", 2071)]


def test_parse_census_reads_men_sheet_for_male(tmp_path):
    path = tmp_path / "census.xlsx"
    write_census_fixture(path)

    assert parse_census(path, Sex.MALE) == [("HUGO", 90000, 12.4)]


def test_parse_births_reads_boys_column_for_male(tmp_path):
    path = tmp_path / "nomnac24.xlsx"
    write_births_fixture(path)

    assert parse_births(path, Sex.MALE) == [("MATEO", 3289), ("HUGO", 2734)]


def test_parse_census_fails_loudly_on_unexpected_layout(tmp_path):
    path = tmp_path / "bad.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Mujeres"
    wb.save(path)

    with pytest.raises(ValueError, match="header"):
        parse_census(path)


def test_lexicon_keys_are_ine_style_uppercase_ascii():
    for lexicon in LEXICONS.values():
        for key in lexicon:
            assert key == key.upper()
            assert key.isascii() and key.isalpha()


def test_spelling_is_looked_up_per_sex():
    assert spelling_for("MARTIN", Sex.MALE).written == "Martín"
    assert spelling_for("ALVARO", Sex.MALE).written == "Álvaro"
    assert spelling_for("LUCIA", Sex.FEMALE).written == "Lucía"
    assert spelling_for("HUGO", Sex.MALE).written == "Hugo"


@pytest.mark.parametrize("sex", list(Sex))
def test_every_pool_name_has_a_stress_pattern_spanish_rules_can_read(sex):
    """Guards the lexicon: names like Oliver or Iker need a pronunciation override."""
    from name_selector.phonetics import Stress, syllabify

    candidates, _ = dataset.load(sex=sex)
    agudas_without_accent = {
        c.key
        for c in candidates
        if syllabify(c.pronunciation).stress is Stress.AGUDA
        and c.pronunciation == c.written
        and c.written[-1].lower() not in "aeiouns"
        and not set(c.written.lower()) & set("áéíóú")  # a written accent is authoritative
    }
    assert agudas_without_accent <= ALLOWED_CONSONANT_AGUDAS[sex]


ALLOWED_CONSONANT_AGUDAS = {
    # Genuinely stressed on the last syllable in Spanish.
    Sex.FEMALE: {"ABRIL", "ISABEL", "MAR", "NOUR"},
    Sex.MALE: {
        "AMIR",
        "ASIER",
        "DAVID",
        "GABRIEL",
        "ISAAC",
        "ISMAEL",
        "JOEL",
        "LUIS",
        "MANUEL",
        "MOHAMED",
        "POL",
        "RAFAEL",
        "SAMUEL",
        "ADAY",
        "MAX",
        "NIL",
        "ELIAS",
        "ERIC",
        "ERIK",
        "ARAN",
        "AXEL",
        "BIEL",
        "GAEL",
        "JAN",
        "KAI",
        "LIAM",
        "MARC",
        "PAU",
        "RAYAN",
        "ALEIX",
        "DANIEL",
        "MIGUEL",
        "SAUL",
        "AITOR",
        "JAVIER",
    },
}


def test_load_male_pool_uses_boys_data():
    candidates, census = dataset.load(sex=Sex.MALE)
    keys = {c.key for c in candidates}

    assert {"HUGO", "MATEO", "MARTIN"} <= keys
    assert "LUCIA" not in keys
    assert census["HUGO"] > 10_000
