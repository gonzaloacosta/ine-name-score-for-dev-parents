from pathlib import Path

import openpyxl
import pytest

from name_selector.ine import parse_births, parse_census
from name_selector.lexicon import LEXICON


def write_census_fixture(path: Path) -> None:
    wb = openpyxl.Workbook()
    wb.active.title = "Hombres"
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


def test_parse_census_fails_loudly_on_unexpected_layout(tmp_path):
    path = tmp_path / "bad.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Mujeres"
    wb.save(path)

    with pytest.raises(ValueError, match="header"):
        parse_census(path)


def test_lexicon_keys_are_ine_style_uppercase_ascii():
    for key in LEXICON:
        assert key == key.upper()
        assert key.isascii() and key.isalpha()
