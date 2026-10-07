# Changelog

## 0.5.0 - 2026-10-07

### Changed
- Repository renamed to `gonzaloacosta/name-score` (old URL redirects).
- Vercel project renamed: production is `https://name-score.vercel.app` (the old
  `ine-name-score-for-dev-parents.vercel.app` now 307-redirects). Worker `ORIGIN` and the
  smoke check point at the new domain.
- Frontend uses relative URLs only, so it runs at a domain root or under a path prefix.

### Added
- Cloudflare Worker (`deploy/cloudflare-worker/`) serving the app at
  `gonzaloacosta.me/name-score/`; tested locally with `wrangler dev` (82/82 browser checks).

### Security
- Worker: protocol-relative paths (`/name-score//host/x`) could reach other hosts (open
  proxy). Fixed before the first deploy; covered by Node tests run in CI.
- Worker: origin redirects are rewritten under `/name-score/` instead of escaping to the
  domain root.

## 0.4.0 - 2026-10-07

### Added
- Boys' names: INE census (`Hombres`) and births (boys' columns), boys' spelling lexicon,
  `sex` parameter on the API, `--sex` on the CLI, Niña/Niño toggle on the web (`?sexo=nino`).
- Score any name, not only the top 100: `explain()` / `name-selector explain` /
  `GET /api/explain`, measured against the newborn pool.
- Web score page (`/nombre.html`): opened from any name in the list or from the new
  "¿Ya tenéis un nombre en mente?" field; shows each criterion, INE figures and the
  emails/usernames for the family's surnames.

### Changed
- Tagline now states that names are safe, easy to pair with surnames and free of joke-prone
  email combinations.
- Census CSVs keep compound names (María José) for lookups; Ç is kept in keys like Ñ.
- `phonetic_key` is memoised: uncached API calls drop from ~280 ms to under 15 ms.

### Fixed
- Site no longer goes blank when the browser blocks site storage.
- Names without vowels return 422 instead of 500; unknown sounds get no spelling credit.
- Boys' stress: Eric, Erik, Axel, Liam (llana) and Unai, Arnau (aguda).
- Score page rank matches the surname-filtered list; dropped names say so.

## 0.3.0 - 2026-10-07

### Added
- Web API (`name_selector/api.py`, FastAPI): `GET /api/rank` with surnames filter, `top`,
  `ascii_only`; `GET /api/health`. Default ranking cached at the CDN, surname queries `no-store`.
- Bilingual (ES/EN) frontend in `public/`: song-line hero, palette "Nube moderna",
  self-hosted Nunito, accessible and responsive.
- Vercel deployment (`[tool.vercel] entrypoint`, `vercel.json` with security headers) and a
  production smoke-check workflow.

## 0.2.0 - 2026-10-07

### Added
- `rank --surnames`: exclude names whose future email/username spells an offensive or
  negative word (e.g. Gonzalo + Ordo -> `gordo`), listing the reason.
- `handles NAME SURNAME...` command to audit one full name.
- Curated Spanish/English word lists in `name_selector/wordlists/`.
- CI (lint + tests on Python 3.11–3.13) with auto squash-merge, and branch protection on `main`.

## 0.1.0 - 2026-10-06

### Added
- `name-selector fetch|rank|explain` CLI.
- INE census (01/01/2025) and newborn 2023–2024 parsers, with the processed CSVs in the repo.
- Six scoring criteria with configurable weights: anonymity, ascii, song, spelling, current,
  systems.
