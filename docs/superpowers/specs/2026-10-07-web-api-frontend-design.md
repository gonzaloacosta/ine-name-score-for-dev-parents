# Web API + frontend on Vercel — design

Date: 2026-10-07 · Status: approved, implemented

## 1. Goal

Make the existing `name-selector` ranking usable from a browser, hosted for free.

**Stated by Gonzalo:** expose the scorer as an API on a free host; a simple web frontend;
soft newborn / Nativity colours (sky blue, pale pink, lilac) with modern accents; Vercel;
v1 features = ranking + surnames filter only; bilingual ES/EN; palette "B · Nube moderna";
single-column layout.

**Assumptions (confirmed during brainstorming):** personal / family use, zero cost, no
accounts, no server-side storage.

**Success criteria**

- Opening the production URL shows the default top-20 ranking.
- Entering surnames removes names whose future email/username spells a bad word and shows
  why (`Gala → gordo@`).
- Works on desktop and phone, in Spanish and English.
- Every merge to `main` deploys to production automatically; every PR gets a preview URL.
- Costs nothing (Vercel Hobby).

**Out of scope for v1:** custom weights, per-name detail view, shortlist/favourites,
accounts, analytics, dark mode.

## 2. Architecture

```
browser ──GET /──────────────▶ Vercel CDN ── public/ (index.html, styles.css, app.js, i18n.js, fonts/)
        ──GET /api/rank?...──▶ Vercel Function (Python 3.13) ── name_selector.api:app (FastAPI)
                                                              └─ rank(), excluded_by_handles(), data/processed/*.csv
```

| Unit | Responsibility | Depends on |
|---|---|---|
| `name_selector/api.py` | HTTP layer: validate query, call scoring, serialise JSON, cache headers | `dataset`, `scoring`, `handles` |
| `public/` | Static UI: form, fetch, render, i18n | `/api/rank` contract only |
| `vercel.json` | Function bundle exclusions, security headers | — |
| `pyproject.toml` | `fastapi` dependency, `[tool.vercel] entrypoint = "name_selector.api:app"` | — |
| `.python-version` | Pin Python 3.13 for Vercel | — |

The scoring code (`scoring.py`, `handles.py`, `phonetics.py`, `dataset.py`) is reused
unchanged. Data is loaded once per warm function instance (`functools.cache`).

## 3. API contract

### `GET /api/rank`

| Param | Type | Default | Validation |
|---|---|---|---|
| `surname1` | string | none | optional; 1–40 chars; Unicode letters, space, `-`, `'` only |
| `surname2` | string | none | same as `surname1`; used as the only surname if `surname1` is absent |
| `top` | int | 20 | 1–200; returns all names if the pool (105 today) is smaller |
| `ascii_only` | bool | false | |

Two surname fields (not one free-text field) because compound surnames contain spaces
("de la Fuente").

**200 response**

```json
{
  "names": [
    {
      "rank": 1,
      "name": "Paula",
      "total": 0.928,
      "criteria": {"anonymity": 0.82, "ascii": 1.0, "song": 1.0,
                   "spelling": 1.0, "current": 0.73, "systems": 1.0},
      "syllables": 2,
      "stress": "llana",
      "census_frequency": 123456,
      "births": {"2023": 1650, "2024": 1588}
    }
  ],
  "excluded": [
    {"name": "Gala",
     "reasons": [{"handle": "gordo", "pattern": "n[0] + s1",
                  "word": "gordo", "tier": "negative"}]}
  ],
  "data": {"census_date": "2025-01-01", "birth_years": [2023, 2024]}
}
```

Numbers above are illustrative; real values come from the INE CSVs. `total` and criteria
are rounded to 3 decimals. `excluded` is `[]` when no surnames are given.

**Headers**

- No surnames: `Cache-Control: public, s-maxage=86400, stale-while-revalidate=604800`
  (identical for everyone; CDN serves it without invoking Python).
- With surnames: `Cache-Control: no-store` (surnames never stored in shared caches).

**Errors**

- Invalid input → `422` with FastAPI's JSON validation detail.
- Unexpected error → logged with route and error type (never the surnames) → `500`
  `{"detail": "internal error"}`; no stack traces in responses.

### `GET /api/health`

`200 {"status": "ok"}`. Used by the post-deploy smoke check.

### Privacy

The API is stateless. Surnames are not logged, stored or cached. No cookies.

## 4. Frontend

**Files:** `public/index.html`, `public/styles.css`, `public/app.js`, `public/i18n.js`,
`public/fonts/` (self-hosted Nunito, woff2, OFL licence). Plain HTML/CSS/JS, no framework,
no build step.

**Layout (single column, max-width ~640px, same structure on phone):**

1. Header: title + tagline, ES·EN pill (top right).
2. Glass form card: "Primer apellido", "Segundo apellido", switch "Solo nombres sin tilde",
   coral "Buscar nombres" button.
3. Results: glass rows `rank · name · gradient score bar · total`.
4. Coral note: "N excluidas por su email" + `Name → handle@` with the bad word in bold.
5. Footer: data source (INE, census 01/01/2025, births 2023–2024) + GitHub link.

**Behaviour**

- On load: fetch default ranking (`top=20`) and render.
- Submit: fetch with surnames + `ascii_only`, re-render.
- Loading: skeleton (shimmer) rows. Error: friendly message + retry button.
  Empty (all filtered): explanatory message.
- Language: Spanish default; English if `navigator.language` starts with `en`; the pill
  toggles and the choice is kept in `localStorage` (wrapped in try/catch; works without it).
  Only UI strings are translated; names and handles are shown as-is.

**Palette B · Nube moderna (CSS custom properties)**

| Token | Value | Use |
|---|---|---|
| `--white` | `#F7F9FC` | page base |
| `--sky` | `#CFE6FA` | cloud blob |
| `--pink` | `#F8D7E3` | cloud blob |
| `--lilac` | `#E3D7F7` | cloud blob, switch |
| `--coral` | `#FF9F8A` | button, exclusion note tint |
| `--navy` | `#1F2544` | text, button text |
| bar gradient | `#8EC5F0 → #C3A8EE → #F4A9C4` | score bars |

Hero name text uses a deeper gradient of the same hues, `#3F7FC9 → #7A55C7 → #C9507E`
(≥ 3.3:1 on every cloud; the pastel bar gradient measured 1.5–2:1 and failed WCAG AA).

Glass cards: `rgba(255,255,255,.62)` + `backdrop-filter: blur(10px)` + white 1px border.
Cloud blobs drift slowly; animation disabled under `prefers-reduced-motion`.
Button text is navy (≈7:1 on coral), not white (≈2:1, fails WCAG AA). Light theme only.

**Security and accessibility**

- API data inserted with `textContent` / DOM APIs only, never `innerHTML`.
- Labelled inputs, `aria-live="polite"` results region, full keyboard use, focus styles,
  layout works from 320px wide without horizontal scroll.

## 5. Deploy and configuration

**`vercel.json`**

- `functions["name_selector/api.py"].excludeFiles`: `tests/**`, `docs/**`, `data/raw/**`,
  `public/**`, `.github/**`.
- `headers` for all routes:
  - `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self';
    font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';
    base-uri 'none'; form-action 'self'`
  - `Referrer-Policy: no-referrer`
  - `X-Content-Type-Options: nosniff`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`

**Flow** (Vercel GitHub integration, project already imported by Gonzalo, root `./`,
preset Python, no environment variables):

```
PR opened  → CI (lint + tests, existing)  +  Vercel preview deploy
CI green   → auto-merge to main (existing) → Vercel production deploy
```

**Post-deploy smoke check:** new workflow `.github/workflows/smoke.yml` on the
`deployment_status` event (state `success`, environment `Production`). It requests
`/api/health`, `/api/rank` and `/` on the production domain (repo variable `PRODUCTION_URL`,
default `https://ine-name-score-for-dev-parents.vercel.app`). Preview URLs are not checked by CI:
Vercel Deployment Protection answers them with 401 and the design keeps no bypass secret.
No token permissions, no secrets. Not a required check in branch protection (deploy timing is
independent of CI).

**Known first-deploy state:** the initial import build failed with
"No python entrypoint found" because `main` has no web app yet. Resolved by
`[tool.vercel] entrypoint` in this work.

## 6. Testing

- `tests/test_api.py` (FastAPI `TestClient`, no network):
  - default request → 20 names, `excluded == []`, `data` metadata present;
  - `surname1=Ordo` → "Gala" excluded with word `gordo`;
  - `ascii_only=true` → no name with diacritics (e.g. "Lucía" absent);
  - `top=0`, `top=201`, digits / `<script>` / 41-char surname → 422;
  - cache headers: `public, s-maxage…` without surnames, `no-store` with surnames;
  - `/api/health` → `{"status": "ok"}`;
  - contract test: response keys equal the set `public/app.js` reads (listed in the test).
- Existing CI runs the new tests on Python 3.11–3.13; `httpx2` (Starlette's test-client
  transport) added to the dev group.
- Manual check before merge: real page in a browser at desktop and 375px widths, both
  languages, surname filter, error state (API stopped).
- After merge: smoke workflow on the preview and production URLs.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Cold start ~1s after idle | CDN caches the default ranking; skeleton rows while loading |
| Vercel Python runtime / FastAPI detection changes | Explicit `tool.vercel.entrypoint`; smoke check catches broken deploys |
| Word list shows offensive words in the UI | Shown only as the reason a name was excluded, in context |
| `app.js` and API drift apart | Contract test in CI |
