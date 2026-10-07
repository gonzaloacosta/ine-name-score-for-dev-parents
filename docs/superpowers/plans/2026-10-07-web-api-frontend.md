# Web API + Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the name ranking as a FastAPI API plus a static bilingual frontend on Vercel (free Hobby).

**Architecture:** `name_selector/api.py` is a thin FastAPI layer over the existing, unchanged scoring code,
loaded by Vercel via `[tool.vercel] entrypoint`. `public/` holds plain HTML/CSS/JS served by the Vercel CDN.
`vercel.json` sets security headers and trims the function bundle; a GitHub workflow smoke-tests production.

**Tech Stack:** Python 3.11–3.13, FastAPI, uv, pytest + httpx `TestClient`, vanilla JS (ES modules), Vercel.

**Spec:** `docs/superpowers/specs/2026-10-07-web-api-frontend-design.md`

## Global Constraints

- Python runtime on Vercel: 3.13 (`.python-version`); CI keeps 3.11, 3.12, 3.13.
- Entrypoint: `[tool.vercel] entrypoint = "name_selector.api:app"`.
- `surname1` / `surname2`: optional, 1–40 chars after trimming, Unicode letters, single space, `-`, `'` only.
- `top`: int 1–200, default 20. `ascii_only`: bool, default false.
- Cache: no surnames → `public, s-maxage=86400, stale-while-revalidate=604800`; with surnames → `no-store`.
- Surnames are never logged, stored or cached by our code.
- Palette tokens exactly: `--white #F7F9FC`, `--sky #CFE6FA`, `--pink #F8D7E3`, `--lilac #E3D7F7`,
  `--coral #FF9F8A`, `--navy #1F2544`; bar gradient `#8EC5F0 → #C3A8EE → #F4A9C4`; button text navy.
- UI strings in ES (default) and EN; API data inserted with DOM APIs / `textContent`, never `innerHTML`.
- No framework, no JS build step, no external network requests from the page (fonts self-hosted).
- Commit messages: conventional commits, no AI attribution lines.

## Review Focus

1. Surname with accents/ñ (`Peña`, `Ocaña`) → accepted (200), handles normalised (`locana`).
2. Compound surname with spaces (`de la Fuente`) → accepted, treated as one surname.
3. Whitespace-only surname (`"   "`) → treated as absent (200, cached response headers), not 422.
4. `surname2` without `surname1` → `surname2` is used as the only surname rather than silently dropped
   (deviation from spec wording "ignored": dropping user input silently is worse). Spec updated.
5. `ascii_only=true` together with surnames → `excluded` lists only names that `ascii_only` would show.

Each item has a test in Task 1.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `name_selector/api.py` | create | FastAPI app: validation, JSON shaping, cache headers, error handler |
| `tests/test_api.py` | create | API behaviour + frontend contract tests |
| `pyproject.toml` | modify | `fastapi` dep; `httpx`, `uvicorn` dev deps; `[tool.vercel]` entrypoint |
| `.python-version` | create | `3.13` |
| `public/index.html` | create | markup, labels, `data-i18n` keys |
| `public/styles.css` | create | palette tokens, glass cards, layout, motion |
| `public/i18n.js` | create | `STRINGS = {es, en}` |
| `public/app.js` | create | fetch, render, states, language switch |
| `public/fonts/nunito-latin-wght-normal.woff2`, `public/fonts/OFL.txt` | create | self-hosted font + licence |
| `scripts/serve_local.py` | create | dev-only server: API + `public/` on one port |
| `vercel.json` | create | `excludeFiles`, security headers |
| `.github/workflows/smoke.yml` | create | post-deploy production check |
| `README.md`, `CHANGELOG.md`, `docs/ci.md`, spec | modify | docs |

---

### Task 1: API

**Files:** create `name_selector/api.py`, `tests/test_api.py`, `.python-version`; modify `pyproject.toml`.

**Interfaces:**
- Consumes: `dataset.load() -> (list[Candidate], dict[str,int])`; `scoring.rank(candidates, census, weights, ascii_only, surnames)`;
  `scoring.excluded_by_handles(candidates, surnames) -> list[tuple[Candidate, list[BadHandle]]]`; `scoring.ascii_score(str) -> float`.
- Produces: `name_selector.api.app` (FastAPI); `GET /api/rank`, `GET /api/health`; JSON shape per spec §3.

- [ ] **Step 1: dependencies and Vercel config**

`pyproject.toml`: add `"fastapi>=0.115"` to `dependencies`; add `"httpx>=0.27"`, `"uvicorn>=0.30"` to the `dev` group; append

```toml
[tool.vercel]
entrypoint = "name_selector.api:app"
```

`.python-version`: `3.13`. Run `uv lock && uv sync`.

- [ ] **Step 2: failing tests** — `tests/test_api.py`

```python
import re
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
        "rank", "name", "total", "criteria", "syllables", "stress", "census_frequency", "births",
    }
    assert set(first["criteria"]) == {"anonymity", "ascii", "song", "spelling", "current", "systems"}
    assert first["total"] == round(first["total"], 3)


def test_surname_excludes_gala_for_gordo_and_is_not_cached():
    res = rank(surname1="Ordo")
    gala = next(e for e in res.json()["excluded"] if e["name"] == "Gala")

    assert {"handle": "gordo", "pattern": "n[0] + s1", "word": "gordo", "tier": "negative"} in gala["reasons"]
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
    def boom():
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
        assert re.search(rf"\.{field}\b", js), f"app.js no longer reads .{field}; update the contract"
    assert all(set(reads["names"]) <= set(n) for n in body["names"])
    assert all(set(reads["excluded"]) <= set(e) for e in body["excluded"])
    assert all(set(reads["reasons"]) <= set(r) for e in body["excluded"] for r in e["reasons"])
    assert set(reads["data"]) <= set(body["data"])
```

- [ ] **Step 3: run, expect failure** — `uv run pytest tests/test_api.py -q` → `ModuleNotFoundError: name_selector.api`.

- [ ] **Step 4: implement** — `name_selector/api.py`

```python
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
        s
        for s in (_clean_surname("surname1", surname1), _clean_surname("surname2", surname2))
        if s
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
```

- [ ] **Step 5: run** — `uv run pytest -q --deselect tests/test_api.py::test_frontend_reads_only_fields_the_api_returns`
  → all pass. The contract test needs `public/app.js` and goes green in Task 2 (same PR).

- [ ] **Step 6: commit** — `git add -A && git commit -m "feat(api): add FastAPI /api/rank and /api/health for Vercel"`

---

### Task 2: Frontend

**Files:** create `public/index.html`, `public/styles.css`, `public/i18n.js`, `public/app.js`,
`public/fonts/*`, `scripts/serve_local.py`.

**Interfaces:**
- Consumes: `GET /api/rank?top=20[&surname1][&surname2][&ascii_only=true]` → spec §3 JSON;
  `422` → invalid surname message; other non-2xx / network error → generic error + retry.
- Produces: page at `/`; `public/app.js` reads `.names[].rank|name|total`, `.excluded[].name|reasons`,
  `.reasons[].handle|word`, `.data.census_date|birth_years` (pinned by the contract test).

- [ ] **Step 1: font** — download Nunito variable (latin) and its licence:
  `curl -fsSLo public/fonts/nunito-latin-wght-normal.woff2 https://cdn.jsdelivr.net/npm/@fontsource-variable/nunito/files/nunito-latin-wght-normal.woff2`
  and `curl -fsSLo public/fonts/OFL.txt https://cdn.jsdelivr.net/npm/@fontsource-variable/nunito/LICENSE`.
  Verify the woff2 starts with `wOF2`.

- [ ] **Step 2: `public/i18n.js`** — `export const STRINGS = { es: {...}, en: {...} }` with keys:
  `title, tagline, surname1, surname2, asciiOnly, search, loading, error, retry, invalid, empty,
  excludedTitle (fn n), excludedNote, source (fn date, years), github, langToggle`.

- [ ] **Step 3: `public/index.html`** — single column: header (`h1`, tagline, lang button), `form#search`
  (two labelled inputs `surname1`/`surname2`, `maxlength=40`, `autocomplete=family-name`, checkbox switch
  `ascii`, submit), `section#results[aria-live=polite]` with `ol#names`, `div#excluded`, `div#status`,
  footer `#source` + GitHub link. Static strings via `data-i18n="key"`. `<script type="module" src="/app.js">`.
  No inline styles or scripts (CSP).

- [ ] **Step 4: `public/styles.css`** — `@font-face` Nunito (`font-display: swap`), `:root` palette tokens
  (Global Constraints), `body` background = three radial gradients (sky, pink, lilac) over `--white`,
  `.blob` drift animation off under `prefers-reduced-motion`, `.glass` cards, `.bar` with gradient fill
  width from `--score` custom property, coral button with navy text, focus-visible rings, skeleton shimmer,
  max-width 640px, works at 320px.

- [ ] **Step 5: `public/app.js`** — ES module: language init (localStorage in try/catch → `navigator.language`
  → `es`), `applyStaticStrings()`, `search()` building `URLSearchParams`, `render(body)` building rows with
  `document.createElement` + `textContent`, bar width via `style.setProperty("--score", total)`,
  excluded note highlighting `reason.word` inside `reason.handle` with a `<b>` element, states
  (loading skeleton, 422 → `invalid`, error + retry button, empty), re-render last result on language switch,
  initial `search()` on load.

- [ ] **Step 6: `scripts/serve_local.py`** (dev only; Vercel serves `public/` itself)

```python
"""Local preview: API + static frontend on one port. Not used on Vercel.

    uv run uvicorn serve_local:app --app-dir scripts --reload
"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from name_selector.api import app

app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "public", html=True))
```

- [ ] **Step 7: run** — `uv run pytest -q` → all pass including the contract test; `uv run ruff check . && uv run ruff format --check .`.

- [ ] **Step 8: browser check** — start `serve_local`, open `http://127.0.0.1:8000/` at desktop and 375px:
  default list renders; `Ordo` + `López` → Gala/Ana excluded with bold word; `L0pez` → invalid message;
  ES↔EN switch re-renders; stop server → retry state. Fix anything found.

- [ ] **Step 9: commit** — `git commit -m "feat(web): add bilingual frontend in Nube moderna palette"`

---

### Task 3: Vercel config, smoke check, docs

**Files:** create `vercel.json`, `.github/workflows/smoke.yml`; modify `README.md`, `CHANGELOG.md`,
`docs/ci.md`, spec.

- [ ] **Step 1: `vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "name_selector/api.py": {
      "excludeFiles": "{tests/**,docs/**,data/raw/**,public/**,scripts/**,.github/**,.superpowers/**}"
    }
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {"key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"},
        {"key": "Referrer-Policy", "value": "no-referrer"},
        {"key": "X-Content-Type-Options", "value": "nosniff"},
        {"key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()"}
      ]
    }
  ]
}
```

- [ ] **Step 2: `.github/workflows/smoke.yml`** — on `deployment_status`; job runs only when
  `state == 'success'` and `environment == 'Production'`; base URL from repo variable `PRODUCTION_URL`
  (fallback `https://ine-name-score-for-dev-parents.vercel.app`); curl `/api/health` (`.status == "ok"`),
  `/api/rank?top=3` (3 names, `census_date` present), `/` (200, contains `app.js`); `permissions: {}`.
  Previews are behind Vercel Deployment Protection, so they are not curled.

- [ ] **Step 3: lint workflows** — `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest`.

- [ ] **Step 4: docs** — README "Web" section (URL, local preview command, privacy note incl. Vercel's own
  request logs); CHANGELOG `0.3.0`; `docs/ci.md` smoke section; spec: smoke = production only, `surname2`
  alone is used. Bump version to `0.3.0`.

- [ ] **Step 5: commit** — `git commit -m "ci: add Vercel config, security headers and production smoke check"`

---

### Task 4: Ship

- [ ] Full suite + lint + secret scan (`detect-secrets-hook` on changed files).
- [ ] Push `feature/web-app`, open PR → CI → auto-merge → Vercel production deploy.
- [ ] Verify production: smoke workflow green; `/`, `/api/health`, `/api/rank?surname1=Ordo` from curl;
  response headers include CSP and cache rules. If `/` is not served from `public/index.html`,
  fix in a follow-up PR (fallback: FastAPI `app.frontend`/route) and re-verify.
