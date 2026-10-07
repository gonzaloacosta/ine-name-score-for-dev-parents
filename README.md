# name-score

[![CI](https://github.com/gonzaloacosta/name-score/actions/workflows/ci.yml/badge.svg)](https://github.com/gonzaloacosta/name-score/actions/workflows/ci.yml)

Ranks Spanish girls' and boys' names on four things at once:

1. **Information security**: the name survives IT systems intact (no accents/ñ, no reserved
   words), is spelled only one way, and has enough namesakes to make OSINT targeting harder.
2. **Normal in Spain**: candidates are only names in the INE top-100 for newborn girls or boys.
3. **"Cumpleaños feliz" fit**: 2–3 syllables, stressed on the penultimate syllable, ending in
   a vowel.
4. **No embarrassing email/username**: given the surnames, names whose future handle spells a
   bad word are excluded (Gonzalo + Ordo -> `gordo@`, Ana + López -> `analopez@`).

All data comes from the [INE](https://www.ine.es/daco/daco42/nombyapel/nombyapel.htm)
(census of 01/01/2025 + newborn names for 2023 and 2024).

## Web

**https://ine-name-score-for-dev-parents.vercel.app** (Spanish / English).

Choose girl or boy, type both surnames to drop names whose future email would read badly, and
tap any name (or type one you already like) to open its score page: the web version of
`name-selector explain`, with every criterion explained, INE figures and its emails checked
against your surnames. The pages call a small JSON API on the same domain:

```bash
curl "https://ine-name-score-for-dev-parents.vercel.app/api/rank?top=5&surname1=Ordo&surname2=L%C3%B3pez"
curl "https://ine-name-score-for-dev-parents.vercel.app/api/rank?sex=male&top=5"
curl "https://ine-name-score-for-dev-parents.vercel.app/api/explain?name=Bego%C3%B1a&surname1=Ordo"
```

| Endpoint | Param | Default | Notes |
|---|---|---|---|
| both | `sex` | `female` | `female` or `male` |
| both | `surname1`, `surname2` | none | optional; letters, spaces, `-`, `'`; max 40 chars |
| `/api/rank` | `top` | 20 | 1–200 |
| `/api/rank` | `ascii_only` | false | only names without accents |
| `/api/explain` | `name` | required | any name; outside the top 100 it is scored against it |

Web pages: `/?sexo=nina|nino` (list) and `/nombre.html?nombre=Julia&sexo=nina` (score page).
Surnames move between pages in the browser's session storage, never in a URL.

Privacy: the API keeps no state, and our code never logs, stores or caches surnames
(responses with surnames are `no-store`). Vercel's own request logs may include the URL for a
short retention period.

Run it locally (API + page on one port):

```bash
uv run uvicorn serve_local:app --app-dir scripts --reload   # http://127.0.0.1:8000
```

Hosting: Vercel Hobby, deployed by Vercel's GitHub app on every merge to `main` (previews per
PR). A Cloudflare Worker can also serve it under `gonzaloacosta.me/name-score/`; the site uses
relative URLs so it works at a domain root or under a path prefix. See
[docs/deployment.md](docs/deployment.md). Design and decisions: [docs/superpowers/specs/2026-10-07-web-api-frontend-design.md](docs/superpowers/specs/2026-10-07-web-api-frontend-design.md).

## CLI

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run name-selector rank                     # top 20
uv run name-selector rank --ascii-only --top 10
uv run name-selector explain julia            # score breakdown for any name
uv run name-selector --sex male rank          # boys' names (default: female)
uv run name-selector --sex male explain álvaro
uv run name-selector rank --surnames Ordo López        # drop names with bad handles
uv run name-selector handles Lucía Ocaña Pérez         # check one full name (exit 1 if bad)
uv run name-selector --weights song=0.4,ascii=0 rank   # change priorities
uv run name-selector fetch                    # re-download INE data and rebuild CSVs
uv run name-selector fetch --years 2023 2024 2025      # once INE publishes 2025
```

Example (default weights):

```
  #  name        total anonymity     ascii      song  spelling   current   systems
  1  Paula       0.928      0.82      1.00      1.00      1.00      0.73      1.00  2·llana
  2  Julia       0.925      0.77      1.00      1.00      1.00      0.84      1.00  2·llana
  3  Carmen      0.922      0.92      1.00      0.85      1.00      0.72      1.00  2·llana
```

Criteria and weights: [docs/methodology.md](docs/methodology.md).

## Development

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

`main` is protected: changes go through a PR, CI runs lint + tests on Python 3.11–3.13 and
squash-merges automatically when green. See [docs/ci.md](docs/ci.md).

Layout: `name_selector/ine.py` (download/parse), `dataset.py` (load CSVs),
`phonetics.py` (syllables, stress, sound-alike key), `lexicon.py` (accents INE strips),
`scoring.py` (criteria), `handles.py` + `wordlists/` (email/username filter), `cli.py`,
`api.py` (web API). The frontend lives in `public/` (no build step).
The processed CSVs in `data/processed/` are kept in the repo so the tool works offline. Raw spreadsheets go to `data/raw/` (git-ignored).
