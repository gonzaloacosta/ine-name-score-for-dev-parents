# Changelog

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
