# Deployment

```
browser ── gonzaloacosta.me/name-score/* ──▶ Cloudflare Worker "name-score" ──▶ Vercel project
        ── gonzaloacosta.me/*  (rest)    ──▶ GitHub Pages (cv-landing-page)
        ── <project>.vercel.app          ──▶ Vercel project (direct)
```

## Vercel

Deployed by Vercel's GitHub app: every PR gets a preview, every merge to `main` goes to
production. No secrets live in GitHub.

## Cloudflare Worker (path `gonzaloacosta.me/name-score/`)

Code: [`deploy/cloudflare-worker/worker.js`](../deploy/cloudflare-worker/worker.js).

- `/name-score` → 301 to `/name-score/` (relative URLs resolve against the directory).
- Strips the prefix and fetches the same path from `ORIGIN` (the Vercel URL).
- GET/HEAD only (405 otherwise); forwards only `Accept` and `Accept-Language`.
- The path is assigned onto the origin URL, never resolved as a relative reference: a path
  like `/name-score//evil.example/x` cannot turn the Worker into an open proxy.
- Tests: `node --test deploy/cloudflare-worker/worker.test.mjs` (also run by pytest/CI).
- Vercel's response headers (CSP, `Cache-Control`) pass through unchanged.
- Redirects from the origin (`Location: /x` or `https://<origin>/x`) are rewritten to
  `/name-score/x`, so they never drop visitors on GitHub Pages.

Deploy (needs a Cloudflare login with Workers permissions on the account):

```bash
cd deploy/cloudflare-worker
npx wrangler login
npx wrangler deploy        # creates the worker and both routes on the gonzaloacosta.me zone
```

Test locally against the dev server before deploying:

```bash
uv run uvicorn serve_local:app --app-dir scripts --port 8000 &
cd deploy/cloudflare-worker && npx wrangler dev --var ORIGIN:http://127.0.0.1:8000
# open http://127.0.0.1:8787/name-score/
```

If the Vercel URL changes (project rename), update `ORIGIN` in `wrangler.toml` and redeploy.

## Why relative URLs

A URL starting with `/` ignores the `/name-score/` prefix and would hit GitHub Pages.
`tests/test_frontend_paths.py` fails if any root-absolute URL comes back.
