"""HTTP API for the web frontend. Vercel loads ``name_selector.api:app``."""

import logging
import re
from functools import cache
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from name_selector import dataset
from name_selector.handles import BadHandle
from name_selector.models import Candidate, ScoredName
from name_selector.scoring import DEFAULT_WEIGHTS, ascii_score, excluded_by_handles, rank

log = logging.getLogger(__name__)

CENSUS_DATE = "2025-01-01"
MAX_SURNAME_LENGTH = 40
# Unicode letters, words joined by a single space, hyphen or apostrophe ("de la Fuente", "O'Neill").
SURNAME_RE = re.compile(r"[^\W\d_]+(?:[ '\-][^\W\d_]+)*")
PUBLIC_CACHE = "public, s-maxage=86400, stale-while-revalidate=604800"

app = FastAPI(title="name-selector", docs_url=None, redoc_url=None, openapi_url=None)


@cache
def _load_data() -> tuple[list[Candidate], dict[str, int]]:
    return dataset.load()


def _clean_surname(field: str, value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    if len(value) > MAX_SURNAME_LENGTH or not SURNAME_RE.fullmatch(value):
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["query", field], "msg": "letters, spaces, - and ' only (max 40)"}],
        )
    return value


def _name_json(position: int, s: ScoredName) -> dict[str, Any]:
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
) -> dict[str, Any]:
    surnames = [
        s for s in (_clean_surname("surname1", surname1), _clean_surname("surname2", surname2)) if s
    ]
    candidates, census = _load_data()
    ranked = rank(candidates, census, DEFAULT_WEIGHTS, ascii_only, surnames or None)
    visible = [c for c in candidates if not ascii_only or ascii_score(c.written)]
    excluded = excluded_by_handles(visible, surnames) if surnames else []

    response.headers["Cache-Control"] = "no-store" if surnames else PUBLIC_CACHE
    return {
        "names": [_name_json(i, s) for i, s in enumerate(ranked[:top], start=1)],
        "excluded": [
            {"name": c.written, "reasons": [_reason_json(h) for h in hits]} for c, hits in excluded
        ],
        "data": {
            "census_date": CENSUS_DATE,
            "birth_years": sorted({y for c in candidates for y in c.births}),
        },
    }
