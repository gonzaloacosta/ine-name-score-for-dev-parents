"""HTTP API for the web frontend. Vercel loads ``name_selector.api:app``."""

import logging
import re
import unicodedata
from functools import cache
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from name_selector import dataset
from name_selector.handles import BadHandle, find_bad_handles, generate_handles
from name_selector.models import Candidate, ScoredName, Sex
from name_selector.scoring import DEFAULT_WEIGHTS, ascii_score, excluded_by_handles, explain, rank

log = logging.getLogger(__name__)

CENSUS_DATE = "2025-01-01"
MAX_TEXT_LENGTH = 40
# Unicode letters, words joined by a single space, hyphen or apostrophe ("de la Fuente", "O'Neill").
TEXT_RE = re.compile(r"[^\W\d_]+(?:[ '\-][^\W\d_]+)*")
PUBLIC_CACHE = "public, s-maxage=86400, stale-while-revalidate=604800"
# Typographic apostrophes (iOS types ’ by default) count as a plain apostrophe.
APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})

app = FastAPI(title="name-selector", docs_url=None, redoc_url=None, openapi_url=None)


@cache
def _load_data(sex: Sex) -> tuple[list[Candidate], dict[str, int], dict[str, float]]:
    candidates, census = dataset.load(sex=sex)
    return candidates, census, dataset.load_ages(sex=sex)


def _invalid(field: str, msg: str) -> HTTPException:
    return HTTPException(status_code=422, detail=[{"loc": ["query", field], "msg": msg}])


def _clean_text(field: str, value: str | None) -> str | None:
    """Normalise a typed name or surname; None when empty, 422 when not name-like."""
    # NFC: "n" + combining tilde (pasted on macOS) becomes "ñ"; then collapse whitespace.
    value = " ".join(unicodedata.normalize("NFC", value or "").translate(APOSTROPHES).split())
    if not value:
        return None
    if len(value) > MAX_TEXT_LENGTH or not TEXT_RE.fullmatch(value):
        raise _invalid(field, "letters, spaces, - and ' only (max 40)")
    return value


def _clean_surnames(surname1: str | None, surname2: str | None) -> list[str]:
    cleaned = (_clean_text("surname1", surname1), _clean_text("surname2", surname2))
    return [s for s in cleaned if s]


def _data_json(candidates: list[Candidate]) -> dict[str, Any]:
    return {
        "census_date": CENSUS_DATE,
        "birth_years": sorted({y for c in candidates for y in c.births}),
    }


def _name_json(position: int | None, s: ScoredName) -> dict[str, Any]:
    c = s.candidate
    return {
        "rank": position,
        "name": c.written,
        "total": round(s.total, 3),
        "criteria": {k: round(v, 3) for k, v in s.criteria.items()},
        "syllables": s.syllables.count,
        "stress": s.syllables.stress.value,
        "census_frequency": c.census_frequency,
        "births": {str(year): n for year, n in sorted(c.births.items())},
    }


def _reason_json(hit: BadHandle) -> dict[str, str]:
    return {"handle": hit.handle, "pattern": hit.pattern, "word": hit.word, "tier": hit.tier.value}


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Path only: the query string may contain surnames.
    log.error("unhandled %s on %s", type(exc).__name__, request.url.path)
    return JSONResponse({"detail": "internal error"}, status_code=500)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/rank")
def get_rank(
    response: Response,
    surname1: str | None = None,
    surname2: str | None = None,
    top: Annotated[int, Query(ge=1, le=200)] = 20,
    ascii_only: bool = False,
    sex: Sex = Sex.FEMALE,
) -> dict[str, Any]:
    surnames = _clean_surnames(surname1, surname2)
    candidates, census, _ = _load_data(sex)
    ranked = rank(candidates, census, DEFAULT_WEIGHTS, ascii_only, surnames or None)
    visible = [c for c in candidates if not ascii_only or ascii_score(c.written)]
    excluded = excluded_by_handles(visible, surnames) if surnames else []

    response.headers["Cache-Control"] = "no-store" if surnames else PUBLIC_CACHE
    return {
        "names": [_name_json(i, s) for i, s in enumerate(ranked[:top], start=1)],
        "excluded": [
            {"name": c.written, "reasons": [_reason_json(h) for h in hits]} for c, hits in excluded
        ],
        "data": _data_json(candidates),
    }


@app.get("/api/explain")
def get_explain(
    response: Response,
    name: str | None = None,
    surname1: str | None = None,
    surname2: str | None = None,
    sex: Sex = Sex.FEMALE,
) -> dict[str, Any]:
    """Score breakdown for any name (the web version of ``name-selector explain``)."""
    typed = _clean_text("name", name)
    if typed is None:
        raise _invalid("name", "a name is required")
    surnames = _clean_surnames(surname1, surname2)
    candidates, census, ages = _load_data(sex)
    result = explain(typed, candidates, census, DEFAULT_WEIGHTS, ages)
    c = result.scored.candidate

    bad = {h.handle: h for h in find_bad_handles(c.written, surnames)} if surnames else {}
    handles = [
        {
            "handle": h.text,
            "pattern": h.pattern,
            "word": bad[h.text].word if h.text in bad else None,
            "tier": bad[h.text].tier.value if h.text in bad else None,
        }
        for h in (generate_handles(c.written, surnames) if surnames else [])
    ]

    response.headers["Cache-Control"] = "no-store" if surnames else PUBLIC_CACHE
    return {
        **_name_json(result.position, result.scored),
        "sex": sex.value,
        "pool_size": result.pool_size,
        "in_census": result.in_census,
        "census_mean_age": c.census_mean_age,
        "ends_in_vowel": result.scored.syllables.ends_in_vowel,
        "handles": handles,
        "excluded": bool(bad),
        "data": _data_json(candidates),
    }
