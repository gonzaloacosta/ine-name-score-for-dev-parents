import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from name_selector.api import app

client = TestClient(app)
APP_JS = Path(__file__).resolve().parent.parent / "public" / "app.js"
PUBLIC_CACHE = "public, s-maxage=86400, stale-while-revalidate=604800"


def rank(**params):
    return client.get("/api/rank", params=params)


def excluded_names(body):
    return {e["name"] for e in body["excluded"]}


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_default_ranking_is_top_20_and_cacheable():
    res = rank()
    body = res.json()

    assert res.status_code == 200
    assert len(body["names"]) == 20
    assert [n["rank"] for n in body["names"]] == list(range(1, 21))
    assert body["excluded"] == []
    assert body["data"] == {"census_date": "2025-01-01", "birth_years": [2023, 2024]}
    assert res.headers["cache-control"] == PUBLIC_CACHE


def test_name_entry_shape():
    first = rank(top=1).json()["names"][0]

    assert set(first) == {
        "rank",
        "name",
        "total",
        "criteria",
        "syllables",
        "stress",
        "census_frequency",
        "births",
    }
    assert set(first["criteria"]) == {
        "anonymity",
        "ascii",
        "song",
        "spelling",
        "current",
        "systems",
    }
    assert first["total"] == round(first["total"], 3)


def test_surname_excludes_gala_for_gordo_and_is_not_cached():
    res = rank(surname1="Ordo")
    gala = next(e for e in res.json()["excluded"] if e["name"] == "Gala")

    assert {"handle": "gordo", "pattern": "n[0] + s1", "word": "gordo", "tier": "negative"} in gala[
        "reasons"
    ]
    assert "Gala" not in {n["name"] for n in res.json()["names"]}
    assert res.headers["cache-control"] == "no-store"


def test_ascii_only_drops_accented_names():
    names = {n["name"] for n in rank(top=200, ascii_only="true").json()["names"]}

    assert "Lucía" not in names
    assert "Julia" in names


def test_top_returns_whole_pool_when_larger():
    assert len(rank(top=200).json()["names"]) == 105


@pytest.mark.parametrize(
    "params",
    [
        {"top": 0},
        {"top": 201},
        {"surname1": "L0pez"},
        {"surname1": "<script>"},
        {"surname1": "a" * 41},
        {"surname2": "x--y"},
    ],
)
def test_invalid_input_is_422(params):
    assert rank(**params).status_code == 422


# Review focus
def test_accented_surname_is_normalised_in_handles():
    lucia = next(e for e in rank(surname1="Ocaña").json()["excluded"] if e["name"] == "Lucía")

    assert any(r["handle"] == "locana" and r["word"] == "loca" for r in lucia["reasons"])


def test_compound_surname_with_spaces_is_one_surname():
    res = rank(surname1="de la Fuente")

    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"


def test_whitespace_only_surname_counts_as_absent():
    res = rank(surname1="   ")

    assert res.status_code == 200
    assert res.json()["excluded"] == []
    assert res.headers["cache-control"] == PUBLIC_CACHE


def test_surname2_alone_is_used_not_dropped():
    assert "Gala" in excluded_names(rank(surname2="Ordo").json())


def test_ascii_only_also_filters_excluded_list():
    body = rank(surname1="Ocaña", ascii_only="true").json()

    assert "Lucía" not in excluded_names(body)


def test_unexpected_error_is_generic_500(monkeypatch):
    def boom(*_args):
        raise RuntimeError("secret detail")

    monkeypatch.setattr("name_selector.api._load_data", boom)
    res = TestClient(app, raise_server_exceptions=False).get("/api/rank")

    assert res.status_code == 500
    assert res.json() == {"detail": "internal error"}


def test_frontend_reads_only_fields_the_api_returns():
    """Contract: every API field app.js reads must exist in a real response."""
    body = rank(surname1="Ordo").json()
    reads = {
        "names": ["rank", "name", "total"],
        "excluded": ["name", "reasons"],
        "reasons": ["handle", "word"],
        "data": ["census_date", "birth_years"],
    }
    js = APP_JS.read_text(encoding="utf-8")

    for field in [f for fields in reads.values() for f in fields] + list(reads):
        assert re.search(rf"\.{field}\b", js), (
            f"app.js no longer reads .{field}; update the contract"
        )
    assert all(set(reads["names"]) <= set(n) for n in body["names"])
    assert all(set(reads["excluded"]) <= set(e) for e in body["excluded"])
    assert all(set(reads["reasons"]) <= set(r) for e in body["excluded"] for r in e["reasons"])
    assert set(reads["data"]) <= set(body["data"])


# Final review fixes
@pytest.mark.parametrize(
    "surname",
    [
        "O’Neill",  # iOS smart apostrophe
        "Peña",  # decomposed ñ (NFD), e.g. pasted on macOS
        "de  la   Fuente",  # repeated spaces
    ],
)
def test_real_world_surname_spellings_are_accepted(surname):
    assert rank(surname1=surname).status_code == 200


def test_decomposed_enye_matches_composed_enye():
    composed = rank(surname1="Ocaña").json()["excluded"]
    decomposed = rank(surname1="Ocaña").json()["excluded"]

    assert decomposed == composed


def test_submit_button_is_disabled_until_app_js_enables_it():
    """A native form GET before app.js loads would put surnames in the URL."""
    html = (APP_JS.parent / "index.html").read_text(encoding="utf-8")

    assert re.search(r'<button type="submit"[^>]*\bdisabled\b', html)
    assert "submitButton.disabled = false" in APP_JS.read_text(encoding="utf-8")


def test_python_version_pin_is_tracked_for_vercel():
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".python-version"],
        cwd=APP_JS.parent.parent,
        capture_output=True,
    )

    assert tracked.returncode == 0, (
        ".python-version is not committed; Vercel would use its default Python"
    )


# Boys and per-name explanation
def explain_name(**params):
    return client.get("/api/explain", params=params)


def test_rank_for_boys():
    body = rank(sex="male", top=200).json()
    names = {n["name"] for n in body["names"]}

    assert {"Hugo", "Martín", "Álvaro"} <= names
    assert "Lucía" not in names


def test_rank_rejects_unknown_sex():
    assert rank(sex="other").status_code == 422


def test_explain_pool_name_matches_ranking():
    first = rank(top=1).json()["names"][0]
    body = explain_name(name="paula").json()

    assert body["name"] == "Paula"
    assert body["rank"] == 1
    assert body["total"] == first["total"]
    assert body["criteria"] == first["criteria"]
    assert body["pool_size"] == 105
    assert body["handles"] == []
    assert body["excluded"] is False


def test_explain_name_outside_pool_with_typed_spelling():
    body = explain_name(name="Begoña").json()

    assert body["name"] == "Begoña"
    assert body["rank"] is None
    assert body["in_census"] is True
    assert body["census_frequency"] > 10_000
    assert body["census_mean_age"] > 40
    assert body["births"] == {}


def test_explain_boy():
    body = explain_name(name="Hugo", sex="male").json()

    assert body["sex"] == "male"
    assert body["rank"] is not None


def test_explain_lists_handles_and_flags_bad_ones_without_caching():
    res = explain_name(name="Gala", surname1="Ordo")
    body = res.json()
    gordo = next(h for h in body["handles"] if h["handle"] == "gordo")
    clean = next(h for h in body["handles"] if h["handle"] == "galaordo")

    assert gordo == {"handle": "gordo", "pattern": "n[0] + s1", "word": "gordo", "tier": "negative"}
    assert clean["word"] is None and clean["tier"] is None
    assert body["excluded"] is True
    assert res.headers["cache-control"] == "no-store"


def test_explain_without_surnames_is_cacheable():
    assert explain_name(name="Julia").headers["cache-control"] == PUBLIC_CACHE


@pytest.mark.parametrize(
    "params",
    [{}, {"name": ""}, {"name": "J0hn"}, {"name": "a" * 41}, {"name": "<b>"}],
)
def test_explain_rejects_invalid_names(params):
    assert explain_name(**params).status_code == 422
